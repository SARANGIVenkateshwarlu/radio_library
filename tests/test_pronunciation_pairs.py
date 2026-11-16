"""Self-check for the pronunciation scorer on the tone minimal pairs.

Exercises the full scoring path (char / tone / pitch / rhythm / fluency) on the
app's minimal-pair sentences, using Edge ``zh-HK`` reference audio:

* reference mode (same audio used as the reference) must score ~100,
* the dictionary readings shown to learners must be the HK spoken ones
  (識 sik1 vs 食 sik6, 買 maai5 vs 賣 maai6, 史 si2 vs 時 si4), and
* within each sentence the measured pitch must follow the tones
  (sik1 above sik6, si2 rising, si4 falling).

Usage (from the repo root)::

    python tests/test_pronunciation_pairs.py          # stub ASR (deterministic)
    python tests/test_pronunciation_pairs.py --asr    # real Whisper ASR

Set ``FFMPEG_BINARY`` if ffmpeg is not on ``PATH``. Audio checks need
``edge-tts`` and network access; they are skipped if unavailable.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import cantonevoice, pronunciation as P  # noqa: E402
from app.audio_util import probe_duration  # noqa: E402
from app.voice_graph import pitch_accuracy  # noqa: E402

# pair -> (expected dictionary Jyutping, expected tones)
EXPECTED = [
    (["sik1", "sik6"], [1, 6]),
    (["maai5", "maai6"], [5, 6]),
    (["si2", "si4"], [2, 4]),
]


class StubASR:
    """Returns the known sentence, so scoring logic is tested deterministically."""

    def __init__(self, spoken: str, duration: float):
        self.spoken = spoken
        self.duration = duration
        self.model = None

    def transcribe(self, audio_path):
        return [{"cantonese": self.spoken, "start": 0.0, "end": self.duration}]


def _mid(row: dict) -> float:
    return (row["measured_start"] + row["measured_end"]) / 2


def _moves(row: dict) -> float:
    return row["measured_end"] - row["measured_start"]


def check_pair_data() -> list[dict]:
    pairs = P.minimal_pairs()
    assert len(pairs) == len(EXPECTED), "minimal-pair list changed"
    for pair, (jyut, tones) in zip(pairs, EXPECTED):
        got_jyut = [w["jyutping"] for w in pair["words"]]
        got_tones = [w["tone"] for w in pair["words"]]
        assert got_jyut == jyut, f"{pair['sentence']}: {got_jyut} != {jyut}"
        assert got_tones == tones, f"{pair['sentence']}: {got_tones} != {tones}"
        assert len(set(got_tones)) == 2, "minimal pair must contrast two tones"
        print(f"  data ok: {pair['label']}  →  {pair['sentence']} "
              f"[{pair['jyutping']}]")
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asr", action="store_true",
                    help="use the real Whisper model instead of a stub")
    args = ap.parse_args()

    print("1) minimal-pair data (dictionary-derived HK readings)")
    pairs = check_pair_data()

    if not cantonevoice.available():
        print("\nedge-tts not installed — skipped audio scoring checks.")
        return 0

    print("\n2) scores on a correct take (reference voice = reference audio)")
    audio: list[str] = []
    scored: list[dict] = []
    try:
        for pair in pairs:
            sentence = pair["sentence"]
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(cantonevoice.synthesize(sentence))
                path = f.name
            audio.append(path)
            dur = probe_duration(path) or len(sentence) / 4.0
            if not args.asr:
                P._asr = StubASR(sentence, dur)
            r = P.evaluate(sentence, path, reference_audio=path)
            t = pitch_accuracy(sentence, path)  # no reference → tone templates
            scored.append(r)
            print(f"\n  {sentence}  [{pair['jyutping']}]")
            print(f"    heard     : {r['spoken']}")
            print(f"    char      : {r['char_accuracy']}   tone: {r['tone_accuracy']}"
                  f"   pitch: {r['pitch_accuracy']} ({r['pitch_mode']})"
                  f"   rhythm: {r['rhythm']}   fluency: {r['fluency']}"
                  f"   overall: {r['score']}")
            print(f"    template pitch (no reference): {t['score']}   "
                  f"F0: you {r['learner_f0_hz']} Hz / ref "
                  f"{r['reference_f0_hz']} Hz (shift {r['register_shift_st']} st)")
            for row in r["pitch_syllables"]:
                print(f"      {row['char']} {row['jyutping']:7} tone {row['tone']}"
                      f"  expected {row['expected']:>9}  measured "
                      f"{row['measured']:>9}  {row['verdict']}")
            assert r["char_accuracy"] == 100, "correct take must match characters"
            assert r["tone_accuracy"] == 100, "correct take must match tones"
            assert r["pitch_accuracy"] is not None, "pitch must be measurable"
            assert r["pitch_accuracy"] >= 95, "identical take must score ~100 pitch"
            assert r["score"] >= 95, "correct take must score >= 95"
            assert t["score"] is not None and t["score"] >= 50, \
                "template pitch should recognise a correct reading"

        print("\n3) within-sentence tone contrast (reference-mode pitch)")
        sik = scored[0]["pitch_syllables"]      # 我 識 食
        assert _mid(sik[1]) > _mid(sik[2]), \
            "sik1 (high) must sit above sik6 (low)"
        print(f"  識 sik1 level {_mid(sik[1]):+.1f} st  >  食 sik6 "
              f"{_mid(sik[2]):+.1f} st  ✓")

        maai = scored[1]["pitch_syllables"]     # 我 買 你 賣
        print(f"  買 maai5 level {_mid(maai[1]):+.1f} st (move "
              f"{_moves(maai[1]):+.1f})  ·  賣 maai6 level "
              f"{_mid(maai[3]):+.1f} st (move {_moves(maai[3]):+.1f})")

        si = scored[2]["pitch_syllables"]       # 我 時 時 讀 歷 史
        for row in si[1:3]:
            assert _moves(row) < -0.5, "si4 must fall"
        assert _moves(si[5]) > 0.5, "si2 must rise"
        print(f"  時 si4 move {_moves(si[1]):+.1f}, {_moves(si[2]):+.1f} st"
              f" (falling)  ·  史 si2 move {_moves(si[5]):+.1f} st (rising)  ✓")

        print("\nAll pronunciation minimal-pair checks passed.")
        return 0
    finally:
        for path in audio:
            try:
                os.unlink(path)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
