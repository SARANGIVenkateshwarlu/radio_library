"""Cantonese tone-contour graph.

Extracts the pitch (F0) of a recording and plots it on a **relative 5-level
pitch grid** (not absolute Hz), syllable by syllable, with the ideal tone
templates overlaid and colour feedback:

* **green** = the syllable's contour roughly matches its target tone,
* **orange** = tone confusion (e.g. flattening a rising Tone 2 into a flat Tone 3).

Pitch is estimated with a lightweight autocorrelation tracker (numpy only), and
the recording is calibrated to the speaker's own range (10th-90th percentile).

LSHK tone contours (5-level scale, 1 low - 5 high):
T1 55/51, T2 35, T3 33, T4 21/11, T5 23, T6 22.
"""
from __future__ import annotations

import io
import subprocess

import numpy as np

from . import config
from .jyutping_tool import to_jyutping

# tone -> (start_level, end_level) on the 5-level relative scale
TONES = {1: (5, 5), 2: (3, 5), 3: (3, 3), 4: (2, 1), 5: (2, 3), 6: (2, 2)}
TONE_NAMES = {1: "陰平", 2: "陰上", 3: "陰去", 4: "陽平", 5: "陽上", 6: "陽去"}


def _envelope(x: np.ndarray, sr: int = 16000, frame: float = 0.02,
              hop: float = 0.01):
    """Short-time RMS amplitude envelope (normalised 0..1)."""
    n, h = int(frame * sr), int(hop * sr)
    t, r = [], []
    for i in range(0, max(0, len(x) - n), h):
        seg = x[i:i + n]
        t.append((i + n / 2) / sr)
        r.append(float(np.sqrt((seg ** 2).mean())))
    r = np.array(r)
    if r.size and r.max() > 0:
        r = r / r.max()
    return np.array(t), r


def _decode(audio_path: str, sr: int = 16000) -> np.ndarray:
    raw = subprocess.run(
        [config.FFMPEG_BINARY, "-v", "quiet", "-i", audio_path,
         "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def extract_f0(x: np.ndarray, sr: int = 16000, frame=0.04, hop=0.01,
               fmin: float = 70, fmax: float = 400):
    """Return (times, f0). f0 is NaN on unvoiced frames."""
    n, h = int(frame * sr), int(hop * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    times, f0 = [], []
    for i in range(0, max(0, len(x) - n), h):
        seg = x[i:i + n] - x[i:i + n].mean()
        t = (i + n / 2) / sr
        times.append(t)
        if np.sqrt((seg ** 2).mean()) < 1e-4:          # silence / unvoiced
            f0.append(np.nan)
            continue
        corr = np.correlate(seg, seg, "full")[len(seg) - 1:]
        band = corr[lo:hi]
        if len(band) == 0 or corr[0] <= 0:
            f0.append(np.nan)
            continue
        lag = lo + int(band.argmax())
        if corr[lag] < 0.30 * corr[0]:                 # weak periodicity
            f0.append(np.nan)
        else:
            f0.append(sr / lag)
    return np.array(times), np.array(f0)


def _levels(f0: np.ndarray) -> np.ndarray:
    """Map Hz -> 1..5 relative pitch, calibrated to the speaker's range."""
    voiced = f0[np.isfinite(f0)]
    if voiced.size < 3:
        return np.full_like(f0, np.nan)
    lo, hi = np.percentile(voiced, 10), np.percentile(voiced, 90)
    if hi <= lo:
        hi = lo * 1.2 + 1
    lv = 1 + 4 * (np.log(f0) - np.log(lo)) / (np.log(hi) - np.log(lo))
    return np.clip(lv, 1, 5)


def expand_word_windows(words: list[dict]) -> list[dict]:
    """Split ASR word timestamps into per-character (syllable) windows."""
    out = []
    for w in words or []:
        chars = [c for c in (w.get("word") or "") if "\u3400" <= c <= "\u9fff"]
        if not chars:
            continue
        a, b, k = float(w["start"]), float(w["end"]), len(chars)
        for i in range(k):
            out.append({"start": a + (b - a) * i / k,
                        "end": a + (b - a) * (i + 1) / k})
    return out


def _direction(start: float, end: float, deadband: float = 0.4) -> int:
    """+1 rising, -1 falling, 0 flat (deadband on the 5-level scale)."""
    d = end - start
    return 1 if d > deadband else -1 if d < -deadband else 0


def _syllables(text: str) -> list[dict]:
    out = []
    for token in to_jyutping(text).split():
        if token and token[-1].isdigit() and token[0].isalpha():
            out.append({"jyutping": token, "tone": int(token[-1])})
    return out


def analyze(target_text: str, audio_path: str, windows: list[dict] | None = None) -> dict:
    """``windows`` (optional) are ASR word timestamps to align syllables; if
    omitted/fewer than the syllable count, the voiced span is split evenly."""
    sr = 16000
    x = _decode(audio_path, sr)
    times, f0 = extract_f0(x, sr)
    levels = _levels(f0)

    syl = _syllables(target_text)
    chars = [c for c in target_text if "\u3400" <= c <= "\u9fff"]
    if not syl:
        syl = [{"jyutping": "", "tone": 0}]
        chars = [""]

    voiced_t = times[np.isfinite(levels)]
    if voiced_t.size:
        t0, t1 = float(voiced_t.min()), float(voiced_t.max())
    else:
        t0, t1 = 0.0, float(times.max() if times.size else 1.0)
    edges = np.linspace(t0, t1, len(syl) + 1)
    if windows and len(windows) >= len(syl):
        spans = [(float(windows[i]["start"]), float(windows[i]["end"]))
                 for i in range(len(syl))]
    else:
        spans = [(float(edges[i]), float(edges[i + 1])) for i in range(len(syl))]

    result = {"times": times.tolist(), "levels": levels.tolist(), "syllables": []}
    for i, s in enumerate(syl):
        a, b = spans[i]
        mask = (times >= a) & (times < b) & np.isfinite(levels)
        pts = [(float(times[k]), float(levels[k])) for k in np.where(mask)[0]]
        ts, te = TONES.get(s["tone"], (None, None))
        ust, uen = None, None
        match = None
        if len(pts) >= 3:
            k = max(1, len(pts) // 3)
            ust = float(np.mean([p[1] for p in pts[:k]]))
            uen = float(np.mean([p[1] for p in pts[-k:]]))
            if ts is not None:
                # tone confusion = wrong *direction* (rising/flat/falling);
                # for flat tones fall back to comparing the mean level.
                du = _direction(ust, uen)
                dt = _direction(ts, te)
                if du == dt and (dt != 0 or
                                 abs((ust + uen) / 2 - (ts + te) / 2) <= 1.5):
                    match = True
                else:
                    match = False
        result["syllables"].append({
            "char": chars[i] if i < len(chars) else "",
            "jyutping": s["jyutping"], "tone": s["tone"],
            "tone_name": TONE_NAMES.get(s["tone"], ""),
            "template": (ts, te), "start": a, "end": b,
            "mid": (a + b) / 2, "points": pts,
            "user_start": ust, "user_end": uen, "match": match,
        })
    return result


# ---- pitch-monitor dashboard ------------------------------------------------
# 5-level pitch -> relative semitones (level 3 = speaker baseline = 0)
_LEVEL_ST = {1: -4, 2: -2, 3: 0, 4: 2, 5: 4}


def tone_template_semitones(tone: int):
    s, e = TONES.get(tone, (None, None))
    if s is None:
        return None
    return (_LEVEL_ST.get(s, 0), _LEVEL_ST.get(e, 0))


def baseline(f0: np.ndarray) -> float | None:
    v = f0[np.isfinite(f0)]
    return float(np.median(v)) if v.size else None


def to_semitones(f0: np.ndarray, base: float | None) -> np.ndarray:
    if not base:
        return np.full_like(f0, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 12.0 * np.log2(f0 / base)


def _corr(a, b) -> float | None:
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    if a.size < 3 or a.std() < 1e-6 or b.std() < 1e-6:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _spans(ts: np.ndarray, n: int, windows: list[dict] | None, t0: float, t1: float):
    if windows and len(windows) >= n:
        return [(float(windows[i]["start"]), float(windows[i]["end"])) for i in range(n)]
    edges = np.linspace(t0, t1, n + 1)
    return [(float(edges[i]), float(edges[i + 1])) for i in range(n)]


def _voiced_span(times: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    vt = times[np.isfinite(y)]
    if vt.size:
        return float(vt.min()), float(vt.max())
    return 0.0, float(times.max() if times.size else 1.0)


def _aligned_points(times, y, spans):
    """x in syllable-index space (i + fraction), y values; NaN gaps dropped."""
    xs, ys = [], []
    for i, (a, b) in enumerate(spans):
        sel = (times >= a) & (times < b) & np.isfinite(y)
        span = max(1e-6, b - a)
        xs.extend((i + (times[sel] - a) / span).tolist())
        ys.extend(y[sel].tolist())
    return xs, ys


def _sample(times, y, a, b, k=10):
    xs = np.linspace(a, b, k, endpoint=False) + (b - a) / (2 * k)
    idx = np.clip(np.searchsorted(times, xs), 0, max(0, len(y) - 1))
    return y[idx]


def build_dashboard(target_text: str, learner_audio: str,
                    reference_audio: str | None = None,
                    windows: list[dict] | None = None,
                    ref_windows: list[dict] | None = None,
                    mode: str = "semitones", meter_range: float = 6.0) -> tuple[dict, bytes]:
    """Full attempt analysis + dashboard PNG. ``mode`` = semitones | hz."""
    syl = _syllables(target_text)
    chars = [c for c in target_text if "\u3400" <= c <= "\u9fff"]
    if not syl:
        syl, chars = [{"jyutping": "", "tone": 0}], [""]
    n = len(syl)

    lsamples = _decode(learner_audio)
    lt, lf0 = extract_f0(lsamples)
    lb = baseline(lf0)
    lsem = to_semitones(lf0, lb)
    lseries = lsem if mode == "semitones" else lf0
    l0, l1 = _voiced_span(lt, lseries)
    lspans = _spans(lt, n, windows, l0, l1)
    lx, lyv = _aligned_points(lt, lseries, lspans)
    lt_env, l_env = _envelope(lsamples)
    lwx, lwy = _aligned_points(lt_env, l_env, lspans)

    rx, ryv, rspans = [], [], None
    rwx, rwy = [], []
    if reference_audio:
        rsamples = _decode(reference_audio)
        rt, rf0 = extract_f0(rsamples)
        rb = baseline(rf0)
        rsem = to_semitones(rf0, rb)
        rseries = rsem if mode == "semitones" else rf0
        r0, r1 = _voiced_span(rt, rseries)
        rspans = _spans(rt, n, ref_windows, r0, r1)
        rx, ryv = _aligned_points(rt, rseries, rspans)
        rt_env, r_env = _envelope(rsamples)
        rwx, rwy = _aligned_points(rt_env, r_env, rspans)

    syllables = []
    devs = []
    accs = []
    for i, s in enumerate(syl):
        lpts = _sample(lt, lseries, lspans[i][0], lspans[i][1], 10)
        if reference_audio:
            rpts = _sample(rt, rseries, rspans[i][0], rspans[i][1], 10)
        else:
            tpl = tone_template_semitones(s["tone"])
            rpts = np.linspace(tpl[0], tpl[1], 10) if (tpl and mode == "semitones") \
                else np.full(10, np.nan)
        ok = np.isfinite(lpts) & np.isfinite(rpts)
        dev = float(np.mean(lpts[ok] - rpts[ok])) if ok.any() else None
        if dev is not None:
            devs.append(dev)

        # accuracy for this syllable: contour match (semitones) + wave match
        lp = _sample(lt, lsem, lspans[i][0], lspans[i][1], 12)
        if reference_audio:
            rp = _sample(rt, rsem, rspans[i][0], rspans[i][1], 12)
        else:
            tpl = tone_template_semitones(s["tone"])
            rp = np.linspace(tpl[0], tpl[1], 12) if tpl else np.full(12, np.nan)
        m = np.isfinite(lp) & np.isfinite(rp)
        pitch_score = None
        if m.sum() >= 3:
            dev_st = float(np.mean(lp[m] - rp[m]))
            level_pen = min(1.0, abs(dev_st) / 6.0)
            c = _corr(lp, rp)
            pitch_score = 100 * (0.6 * (1 - level_pen) + 0.4 * max(0, c)) \
                if c is not None else 100 * (1 - level_pen)
        wave_score = None
        if reference_audio and rspans:
            lwv = _sample(lt_env, l_env, lspans[i][0], lspans[i][1], 12)
            rwv = _sample(rt_env, r_env, rspans[i][0], rspans[i][1], 12)
            c = _corr(lwv, rwv)
            if c is not None:
                wave_score = 100 * max(0, c)
        parts = [(pitch_score, 0.7)] if pitch_score is not None else []
        if wave_score is not None:
            parts.append((wave_score, 0.3))
        acc = round(sum(v * w for v, w in parts) / sum(w for _, w in parts)) \
            if parts else None
        if acc is not None:
            accs.append(acc)

        if dev is None:
            verdict = "—"
        elif abs(dev) <= meter_range * 0.33:
            verdict = "near target"
        elif dev > meter_range * 0.66:
            verdict = "well above"
        elif dev > 0:
            verdict = "above"
        elif dev < -meter_range * 0.66:
            verdict = "well below"
        else:
            verdict = "below"
        syllables.append({
            "char": chars[i] if i < len(chars) else "", "jyutping": s["jyutping"],
            "tone": s["tone"], "tone_name": TONE_NAMES.get(s["tone"], ""),
            "deviation": dev, "verdict": verdict, "accuracy": acc,
        })

    overall = float(np.mean(devs)) if devs else None
    accuracy = round(float(np.mean(accs))) if accs else None
    result = {
        "mode": mode, "meter_range": meter_range,
        "current_hz": round(lb, 1) if lb else None,
        "syllables": syllables, "overall_deviation": overall,
        "accuracy": accuracy,
        "learner": {"x": lx, "y": lyv}, "reference": {"x": rx, "y": ryv},
        "learner_wave": {"x": lwx, "y": lwy},
        "reference_wave": {"x": rwx, "y": rwy},
        "labels": [f"{chars[i] if i < len(chars) else ''}\n{syl[i]['jyutping']}"
                   for i in range(n)],
    }
    return result, render_dashboard(result)


def render_wave(result: dict) -> bytes:
    """Waveform-distribution view: amplitude (ref vs learner) + pitch contour
    with high/mid/low tone registers, aligned by syllable."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    mode = result.get("mode", "semitones")
    ylabel = "Relative pitch (semitones)" if mode == "semitones" else "Pitch (Hz)"
    n = len(result["labels"])

    fig = plt.figure(figsize=(10.5, 6.2), dpi=130)
    gs = GridSpec(2, 1, height_ratios=[1, 1.25], hspace=0.5)
    axw = fig.add_subplot(gs[0])
    axp = fig.add_subplot(gs[1])

    # ---- waveform distribution (X = syllable position, Y = amplitude) ----
    rw = result["reference_wave"]
    lw = result["learner_wave"]
    if rw["x"]:
        axw.plot(rw["x"], rw["y"], color="#555555", lw=1.4, ls="--",
                 label="Reference 參考")
    if lw["x"]:
        axw.plot(lw["x"], lw["y"], color="#1f618d", lw=1.6,
                 label="Your voice 你嘅聲音")
        axw.fill_between(lw["x"], 0, lw["y"], color="#1f618d", alpha=0.18)
    for i in range(n):
        axw.axvline(i, color="#e5e7eb", lw=0.8, zorder=0)
    axw.set_xticks([i + 0.5 for i in range(n)])
    axw.set_xticklabels(result["labels"], fontsize=9)
    axw.set_ylabel("Amplitude (norm.)")
    axw.set_ylim(0, 1.05)
    axw.set_title("Waveform distribution — reference vs your voice", fontsize=11)
    axw.legend(loc="upper right", fontsize=9, frameon=False)
    axw.margins(x=0.01)

    # ---- pitch contour with tone registers (high / mid / low) ----
    if mode == "semitones":
        axp.axhspan(2, 6, color="#eef5ff")     # high register
        axp.axhspan(-1, 2, color="#f3f7f3")    # mid register
        axp.axhspan(-6, -1, color="#fff5ee")   # low register
        axp.axhline(0, color="#cccccc", lw=0.8, ls=":")
        axp.set_ylim(-6, 6)
    ref = result["reference"]
    if ref["x"]:
        axp.plot(ref["x"], ref["y"], color="#555555", lw=2, ls="--",
                 label="Reference 參考")
    learner = result["learner"]
    if learner["x"]:
        axp.plot(learner["x"], learner["y"], color="#1f618d", lw=2.8,
                 label="Your voice 你嘅聲音")
    for i in range(n):
        axp.axvline(i, color="#e5e7eb", lw=0.8, zorder=0)
    axp.set_xticks([i + 0.5 for i in range(n)])
    axp.set_xticklabels(result["labels"], fontsize=9)
    axp.set_ylabel(ylabel)
    axp.set_title("Tone modulation — contour vs reference (high / mid / low)",
                  fontsize=11)
    axp.legend(loc="upper right", fontsize=9, frameon=False)
    axp.margins(x=0.01)

    buf = io.BytesIO()
    fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.10)
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def render_dashboard(result: dict) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    mode = result.get("mode", "semitones")
    ylabel = "Relative pitch (semitones)" if mode == "semitones" else "Pitch (Hz)"
    n = len(result["labels"])

    fig = plt.figure(figsize=(10.5, 5.4), dpi=130)
    gs = GridSpec(2, 1, height_ratios=[4, 1], hspace=0.55)
    ax = fig.add_subplot(gs[0])
    axm = fig.add_subplot(gs[1])

    # reference (dashed gray) then learner (solid blue)
    ref = result["reference"]
    if ref["x"]:
        ax.plot(ref["x"], ref["y"], color="#555555", lw=2, ls="--",
                label="Reference 參考", zorder=2)
    learner = result["learner"]
    if learner["x"]:
        ax.plot(learner["x"], learner["y"], color="#1f618d", lw=2.8,
                label="Your voice 你嘅聲音", zorder=3)

    for i in range(n):
        ax.axvline(i, color="#e5e7eb", lw=0.8, zorder=0)
    ax.set_xticks([i + 0.5 for i in range(n)])
    ax.set_xticklabels(result["labels"], fontsize=9)
    ax.set_ylabel(ylabel)
    ax.set_title("Cantonese pitch monitor — aligned by syllable", fontsize=11)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.margins(x=0.01)
    if mode == "semitones":
        ax.axhline(0, color="#cccccc", lw=0.8, ls=":")

    # deviation meter
    rng = result.get("meter_range", 6.0)
    axm.set_xlim(-rng, rng)
    axm.set_ylim(0, 1)
    axm.axvspan(-rng, -rng * 0.33, color="#fdecea")
    axm.axvspan(-rng * 0.33, rng * 0.33, color="#e8f5e9")
    axm.axvspan(rng * 0.33, rng, color="#fdecea")
    dev = result.get("overall_deviation")
    unit = "st" if mode == "semitones" else "Hz"
    if dev is not None:
        d = max(-rng, min(rng, dev))
        axm.plot([d], [0.5], marker="o", color="#111827", ms=12, zorder=3)
        axm.text(d, 0.95, f"{dev:+.1f} {unit}", ha="center", va="top", fontsize=9)
    else:
        axm.text(0, 0.5, "insufficient pitch data", ha="center", va="center",
                 fontsize=9, color="#888888")
    axm.set_yticks([])
    axm.set_xticks([-rng, 0, rng])
    axm.set_xticklabels([f"-{rng:g} {unit}", "near target", f"+{rng:g} {unit}"],
                        fontsize=9)
    axm.set_title("Relative deviation (learner - reference)", fontsize=10)

    buf = io.BytesIO()
    fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def render_png(result: dict) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei", "Microsoft YaHei", "SimHei", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=130)

    # 5-level relative grid + guide bands
    ax.axhspan(4, 5.2, color="#eef5ff", zorder=0)     # high
    ax.axhspan(2.5, 3.5, color="#f3f7f3", zorder=0)   # mid
    ax.axhspan(0.8, 2, color="#fff5ee", zorder=0)     # low
    for lvl in range(1, 6):
        ax.axhline(lvl, color="#dddddd", lw=0.8, ls=":", zorder=1)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylim(0.8, 5.2)
    ax.set_ylabel("Relative pitch level (1 low – 5 high)")

    for s in result["syllables"]:
        a, b = s["start"], s["end"]
        # target (ghost) template
        if s["template"][0] is not None:
            ax.plot([a, b], list(s["template"]), color="#999999", lw=1.6,
                    ls="--", zorder=2, alpha=0.8)
        # user trace (colored by match)
        if len(s["points"]) >= 2:
            color = "#1e8449" if s["match"] else "#b9770e"
            xs = [p[0] for p in s["points"]]
            ys = [p[1] for p in s["points"]]
            ax.plot(xs, ys, color=color, lw=2.4, zorder=3)
            ax.scatter(xs, ys, color=color, s=6, zorder=4)

    mids = [s["mid"] for s in result["syllables"]]
    labels = [f"{s['char']}\n{s['jyutping']}" for s in result["syllables"]]
    ax.set_xticks(mids)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Syllable (傳統字 + Jyutping)")
    ax.set_title("Cantonese tone-contour graph — solid = you, dashed = target",
                 fontsize=11)
    ax.grid(False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
