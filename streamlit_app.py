"""Streamlit app: process recordings and browse the Cantonese learning library.

Run:  streamlit run streamlit_app.py
"""
import io
import json
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import (  # noqa: E402
    audio_util,
    cantonevoice,
    cantonese_teacher,
    cleanup,
    config,
    library,
    phrases,
    pronunciation,
    recorder,
    schedule,
    vocab,
    vocab_pdf,
    voice_graph,
)
from app.graph import run  # noqa: E402

st.set_page_config(page_title="HK Radio Cantonese Library", page_icon="📻", layout="wide")

# ---- Classic "paper & serif" theme (complements .streamlit/config.toml) ----
st.markdown(
    """
    <style>
    :root {
        --classic-ink: #2a2a2a;
        --classic-paper: #fbf7ef;
        --classic-parchment: #f1eadb;
        --classic-accent: #7c2d12;
        --classic-rule: #d9cdb8;
    }
    [data-testid="stAppViewContainer"] { background: var(--classic-paper); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: var(--classic-parchment); }
    html, body, [class*="st-"], .stMarkdown, p, li, span, label,
    input, textarea, select, button {
        font-family: Georgia, "Times New Roman", "Songti SC",
                     "Microsoft JhengHei", serif !important;
        color: var(--classic-ink);
    }
    h1, h2, h3, h4 {
        font-family: Georgia, "Times New Roman", "Songti SC",
                     "Microsoft JhengHei", serif !important;
        color: #3a2a1a !important;
        letter-spacing: .2px;
    }
    h1 { border-bottom: 3px double var(--classic-accent); padding-bottom: .35rem; }
    h2 { border-bottom: 1px solid var(--classic-rule); padding-bottom: .25rem; }
    .stButton > button, .stDownloadButton > button {
        border: 1px solid var(--classic-accent) !important;
        border-radius: 6px !important;
        background: #fffaf0 !important;
        color: #5b2d0c !important;
        font-weight: 600;
        box-shadow: 0 1px 2px rgb(60 40 20 / 8%);
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: var(--classic-accent) !important; color: #fff !important;
    }
    .stTabs [data-baseweb="tab"] { font-weight: 600; }
    .stTabs [aria-selected="true"] {
        color: var(--classic-accent) !important;
        border-bottom-color: var(--classic-accent) !important;
    }
    [data-testid="stMetric"] {
        background: #fffaf0;
        border: 1px solid var(--classic-rule);
        border-radius: 8px;
        padding: 10px 14px;
    }
    [data-testid="stMetricValue"] { color: #3a2a1a; }
    [data-testid="stExpander"] {
        border: 1px solid var(--classic-rule) !important;
        border-radius: 8px;
    }
    code, pre, kbd { font-family: "Consolas", "Courier New", monospace !important; }
    hr { border-color: var(--classic-rule); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📻 HK Radio → Cantonese Learning Library")

if config.LLM_ENABLED:
    st.caption(
        f"LLM: **{config.LLM_PROVIDER}** · `{config.LLM_MODEL}` @ "
        f"`{config.OPENAI_BASE_URL}`"
    )
else:
    st.warning(
        "No LLM API key configured — running in offline **mock mode** "
        "(rough-gloss translations, not real English). Add your xAI key as "
        "`OPENAI_API_KEY` (`xai-...`) to `.env` or `.streamlit/secrets.toml`, "
        "then restart the app. See README."
    )

(tab_sched, tab_record, tab_process, tab_library, tab_vocab, tab_pron,
 tab_teacher, tab_voice) = st.tabs(
    ["🗓️ Radio Time Table", "🔴 Record radio", "⚙️ Process recording",
     "📚 Library", "🗂️ VocabBank", "🗣️ Pronunciations", "🎓 Cantonese Teacher",
     "🎙️ AI CantoneVoice"]
)


def set_review_status(recording_id: str) -> None:
    library.update_review_status(recording_id, st.session_state[f"status_{recording_id}"])


def fmt_ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def show_segments(segments):
    if not segments:
        return
    blocks: dict[int, list] = {}
    for s in segments:
        blocks.setdefault(s.get("block", 0), []).append(s)
    for bi in sorted(blocks):
        block = blocks[bi]
        st.markdown(
            f"**Block {bi + 1}** · "
            f"[{fmt_ts(block[0].get('start', 0))} – {fmt_ts(block[-1].get('end', 0))}]"
        )
        st.markdown("**Cantonese:**")
        for j, s in enumerate(block, 1):
            text = s.get("corrected") or s.get("cantonese", "")
            mark = " 〔?〕" if s.get("uncertain") and "〔?〕" not in text else ""
            st.markdown(f"{j}. {text}{mark}")
            verbatim = s.get("verbatim_transcript")
            if verbatim and verbatim != text:
                st.caption(f"verbatim: {verbatim}")
        st.markdown("**Jyutping · English**")
        st.table({
            "Jyutping": [f"{j}. {s.get('jyutping', '')}"
                         for j, s in enumerate(block, 1)],
            "English": [f"{j}. {s.get('english', '')}"
                        for j, s in enumerate(block, 1)],
        })
        for j, s in enumerate(block, 1):
            if s.get("needs_human_review"):
                st.caption(f"⚠ line {j}: {s.get('review_reason', 'needs review')}")
        st.divider()

    seen, vocab = set(), []
    for s in segments:
        for v in s.get("vocabulary") or []:
            if v.get("word") and v["word"] not in seen:
                seen.add(v["word"])
                vocab.append(v)
    if vocab:
        st.markdown("**Vocabulary (全篇詞彙)**")
        st.table([
            {"Word": v["word"], "Jyutping": v.get("jyutping", ""),
             "Meaning": v.get("meaning", "")}
            for v in vocab
        ])


with tab_sched:
    st.subheader("RTHK radio timetable — today")
    c1, c2 = st.columns([1, 4])
    if c1.button("🔄 Refresh"):
        schedule.get_timetable(force=True)
        st.rerun()
    c2.caption(
        "**Green + bold** = talk / discussion / speech / chit-chat (good "
        "listening practice) · **grey with (music)** = music · **red** = on air now."
    )
    try:
        timetable = schedule.get_timetable()
    except Exception as exc:  # network / parsing failure
        timetable = None
        st.error(f"Could not load the RTHK schedule: {exc}")
    if timetable:
        channel_tabs = st.tabs([schedule.CHANNELS[n] for n in range(1, 6)])
        now = datetime.now()
        for channel_tab, n in zip(channel_tabs, range(1, 6)):
            with channel_tab:
                rows = timetable.get(n, [])
                live = schedule.on_air(rows, now)
                if not rows:
                    st.info("No schedule available for this channel.")
                    continue
                if live:
                    st.markdown(f"🔴 **On air now:** {live['title']} "
                                f"({live['time']})")
                for r in rows:
                    line = f"{r['time']} · {r['title']}"
                    if r["category"] == "music":
                        line += " (music)"
                    if live is not None and r is live:
                        st.markdown(
                            f"<span style='color:#d32f2f;font-weight:800'>"
                            f"{line}</span>", unsafe_allow_html=True)
                    elif r["category"] == "talk":
                        st.markdown(
                            f"<span style='color:#1a7f37;font-weight:700'>"
                            f"{line}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:#888888'>{line}</span>",
                                    unsafe_allow_html=True)

with tab_record:
    st.subheader("Record HK internet radio directly to MP3")
    st.caption(
        "Captures the station's own digital stream (no microphone → no room noise). "
        "MP3's highest standard quality is 320 kbps; recordings for personal study only."
    )
    st.markdown(
        """
        <style>
        div[class*="st-key-record_start"] button,
        div[class*="st-key-record_stop"] button {
            font-size: 1.6rem !important;
            font-weight: 800 !important;
            letter-spacing: .5px !important;
            padding: 1.2rem 1.4rem !important;
            min-height: 4.5rem !important;
            border-radius: 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not recorder.ffmpeg_available():
        st.error(
            "**ffmpeg is not installed** — recording is disabled. Install it and "
            "restart the app:\n\n```\nwinget install Gyan.FFmpeg\n```\n"
            "Then reopen this terminal (ffmpeg must be on PATH), or set "
            "`FFMPEG_BINARY` to the full path of `ffmpeg.exe`."
        )

    station = st.selectbox("Station", list(recorder.STATIONS.keys()),
                           index=list(recorder.STATIONS).index("RTHK Radio 5"))
    stream_url = st.text_input("Stream URL", value=recorder.STATIONS[station])

    st.markdown("**🎧 Listen live**")
    playing = st.toggle("▶️ Play / ⏹️ Stop", value=False)
    if playing:
        st.audio(stream_url, format="audio/mpeg", autoplay=True)

    st.markdown("**🔴 Record**")
    c1, c2 = st.columns(2)
    dur_label = c1.selectbox("Duration", ["5 min", "10 min", "30 min", "1 hour", "Custom"])
    if dur_label == "Custom":
        duration_s = int(c2.number_input("Custom duration (minutes)", 1, 720, 15) * 60)
    else:
        duration_s = {"5 min": 300, "10 min": 600, "30 min": 1800, "1 hour": 3600}[dur_label]
    bitrate = c2.selectbox("MP3 quality", recorder.BITRATES,
                           index=recorder.BITRATES.index("320k"))
    buffer_s = st.slider(
        "Stream buffer / disconnect tolerance (seconds)", 0, 30, 12,
        help="ffmpeg keeps this many seconds buffered and auto-reconnects, so "
             "brief stream drops don't break a continuous recording.",
    )

    if "rec_job" not in st.session_state:
        st.session_state.rec_job = None

    job_id = st.session_state.rec_job
    running = job_id and recorder.job_status(job_id)["running"]

    bc1, bc2 = st.columns(2)
    if bc1.button("🔴 Start recording", type="primary", disabled=bool(running),
                  key="record_start", width="stretch"):
        try:
            job = recorder.start_recording(station, stream_url, duration_s,
                                           bitrate, buffer_s=buffer_s)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            st.session_state.rec_job = job["id"]
            st.rerun()
    if bc2.button("⏹️ Stop", disabled=not running, key="record_stop",
                  width="stretch"):
        recorder.stop_recording(job_id)
        st.rerun()

    if job_id:
        stt = recorder.job_status(job_id)
        st.progress(stt["progress"],
                    text=f"{stt['station']} — {int(stt['elapsed_s'])}s / {stt['duration_s']}s "
                         f"@ {stt['bitrate']} · {stt['size_bytes']/1024:.0f} KB")
        if stt["running"]:
            st.info(f"Recording → `{stt['out_path']}`")
            time.sleep(2)
            st.rerun()
        elif stt["finished"]:
            st.success(f"Saved: `{stt['out_path']}` — switch to ⚙️ Process recording to transcribe it.")
            st.session_state.rec_job = None
        elif stt["error"]:
            st.error("ffmpeg exited with an error — check the stream URL.")
            if stt.get("error_tail"):
                st.code(stt["error_tail"])
            st.session_state.rec_job = None

def process_controls(audio_path, kp):
    mock = st.checkbox(
        "Use mock ASR (offline demo transcript — leave OFF for real recordings)",
        value=False, key=f"{kp}_mock",
    )
    clean = st.checkbox(
        "Clean audio first — isolate voice / remove background music "
        f"({'Demucs' if cleanup.demucs_available() else 'ffmpeg'} · slower)",
        value=cleanup.demucs_available(), key=f"{kp}_clean",
    )

    if st.button("▶️ Run pipeline", type="primary", key=f"{kp}_run") and audio_path:
        with st.status("Running LangGraph pipeline…", expanded=True) as status:
            for step in ["load_audio", "cleanup_audio", "transcribe", "correct",
                         "jyutping", "translate", "validate_output",
                         "segment_blocks", "review_quality", "generate_pdf",
                         "save_to_library"]:
                st.write(f"• {step}")
            final = run(audio_path, mock_asr=mock, clean_audio=clean)
            status.update(label=f"Done: {final['recording_id']}", state="complete")
        st.success(f"Recording `{final['recording_id']}` processed and saved to the library.")
        method = final.get("cleanup_method")
        if method and method != "off":
            st.caption(f"🎚️ Audio cleaned via: **{method}**")
        qr = final.get("quality_review") or {}
        if qr.get("status") == "ok":
            st.markdown(f"**🔎 LLM quality review — accuracy "
                        f"{qr.get('accuracy_score', '?')}/100**")
            if qr.get("summary"):
                st.caption(qr["summary"])
            for it in qr.get("issues") or []:
                st.warning(f"#{it.get('segment')}: {it.get('problem')} → "
                           f"{it.get('suggestion')}")
        elif qr.get("status") == "skipped":
            st.info("LLM quality review skipped — no LLM configured.")
        show_segments(final["segments"])
        pdf_path = Path(final["pdf_path"])
        if pdf_path.exists():
            st.download_button("⬇️ Download PDF", pdf_path.read_bytes(),
                               file_name=pdf_path.name, mime="application/pdf",
                               key=f"{kp}_dl")


with tab_process:
    st.subheader("Run the LangGraph pipeline on a recording")
    proc_r, proc_c = st.tabs(["📻 Radio recordings", "⬆️ Custom MP3"])

    with proc_r:
        audio_files = sorted(
            config.AUDIO_DIR.glob("*.mp3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if audio_files:
            by_name = {p.name: str(p) for p in audio_files}
            chosen = st.selectbox(
                f"Audio file ({len(audio_files)} in audio/ — latest first)",
                list(by_name),
            )
            audio_path = by_name[chosen]
            st.caption(f"Path: `{audio_path}`")
        else:
            st.info("No MP3s in `audio/` yet — record one in the 🔴 Record radio tab.")
            audio_path = st.text_input(
                "Audio file path", value="audio/2026-10-07_RTHK_5min.mp3")
        process_controls(audio_path, kp="radio")

    with proc_c:
        saved = st.session_state.get("custom_audio")
        if saved and Path(saved).exists():
            st.success(f"Saved: `{saved}`")
            c_clear, _ = st.columns([1, 3])
            if c_clear.button("✖️ Clear / pick another"):
                st.session_state.pop("custom_audio", None)
                st.rerun()
            st.caption(
                "This file is now in `audio/` and is processed exactly like a radio "
                "MP3 — full pipeline: cleanup → ASR → Jyutping → translation → "
                "validation → LLM review → PDF → library."
            )
            process_controls(saved, kp="custom")
        else:
            up = st.file_uploader(
                "Upload an MP3 (YouTube, podcast, phone — any local file)",
                type=["mp3"],
            )
            src = st.text_input("Source / title tag (used in the file name)",
                                value="custom")
            if up is not None:
                st.audio(up.getvalue(), format="audio/mpeg")
                if st.button("▶️ Save to audio/ and process", type="primary",
                             key="save_custom"):
                    path, dur = audio_util.save_upload_mp3(up.getvalue(), src)
                    st.session_state["custom_audio"] = path
                    st.rerun()

with tab_library:
    st.subheader("Saved recordings")
    records = library.list_recordings()
    if not records:
        st.info("Library is empty — process a recording first.")
    else:
        for rec in records:
            label = f"**{rec['recording_id']}** — {rec['station']} · {rec['recorded_at']} · {rec['review_status']}"
            with st.expander(label):
                c1, c2, c3 = st.columns(3)
                c1.metric("Duration", f"{(rec['duration_seconds'] or 0)//60} min")
                c2.write(f"🎧 `{rec['audio_file']}`")
                c3.write(f"📄 `{rec['pdf_file']}`")

                st.markdown("**🔊 Play recording**")
                pc1, pc2 = st.columns([1, 3])
                speed = pc1.selectbox(
                    "Speed", [0.5, 0.75, 1.0, 1.5, 2.0], index=2,
                    format_func=lambda x: f"{x:g}x",
                    key=f"speed_{rec['recording_id']}",
                )
                audio_bytes = audio_util.speed_adjusted(rec["audio_file"], speed)
                if audio_bytes:
                    pc2.audio(audio_bytes, format="audio/mpeg")
                else:
                    pc2.caption("Audio file not found.")

                segs = json.loads(rec["transcript_json"] or "[]")
                show_segments(segs)
                st.selectbox(
                    "Review status",
                    ["unreviewed", "partially_reviewed", "verified"],
                    index=["unreviewed", "partially_reviewed", "verified"].index(rec["review_status"]),
                    key=f"status_{rec['recording_id']}",
                    on_change=set_review_status,
                    args=(rec["recording_id"],),
                )
                pdf = Path(rec["pdf_file"] or "")
                if pdf.exists():
                    st.download_button("⬇️ Download PDF", pdf.read_bytes(),
                                       file_name=pdf.name, mime="application/pdf",
                                       key=f"dl_{rec['recording_id']}")


def _show_score(state):
    a = state.get("attempt") or {}
    st.metric("Score", f"{a.get('score', 0)}%",
              f"{a.get('correct', 0)} right / {a.get('wrong', 0)} wrong")
    if a.get("score") == 100:
        st.balloons()
        st.success("Perfect 100/100! Here is more vocabulary from your bank to keep going:")
        stats = vocab.load_stats()
        unseen = [
            e for e in vocab.collect_vocab()
            if stats.get(f"{e['word']}|{e.get('jyutping','')}", {}).get("seen", 0) == 0
        ]
        if unseen:
            st.dataframe(
                [{"Word": e["word"], "Jyutping": e["jyutping"], "Meaning": e["meaning"]}
                 for e in unseen[:20]],
                width='stretch',
            )
            if st.button("🎁 Bonus round (new words)", type="primary", key="bonus"):
                st.session_state.quiz = None
                st.rerun()
        else:
            st.info("No unseen words left — you've reviewed the whole bank. Add a new recording!")
    if st.button("🔄 Start another quiz", key="again"):
        st.session_state.quiz = None
        st.rerun()


def _render_quiz():
    st.caption(
        "No Chinese characters — Jyutping only. ~70% review (words you've seen) "
        "+ ~30% new, 6–10 questions mixing **Jyutping → meaning** and "
        "**meaning → Jyutping**, one idea per question. Immediate feedback with "
        "the correct answer, an audio replay, and the phrase in context."
    )
    state = st.session_state.get("quiz")
    if state is None:
        if st.button("▶️ Start quiz", type="primary"):
            questions = vocab.build_quiz()
            if not questions:
                st.warning("Need at least 2 vocabulary items to build a quiz.")
            else:
                st.session_state.quiz = {"questions": questions, "answers": [],
                                         "i": 0, "answered": False, "done": False}
                st.rerun()
        return
    if state.get("done"):
        _show_score(state)
        return

    qs = state["questions"]
    i = state["i"]
    q = qs[i]
    st.progress((i + (1 if state["answered"] else 0)) / len(qs),
                text=f"Question {i + 1} of {len(qs)}")

    if not state["answered"]:
        with st.form(key=f"qform_{i}"):
            st.markdown(f"**{q['prompt']}**")
            choice = st.radio("Choose one", q["options"], index=None,
                              key=f"qradio_{i}")
            if st.form_submit_button("Submit"):
                if choice is None:
                    st.warning("Pick an answer first.")
                else:
                    state["answers"].append(choice)
                    state["answered"] = True
                    st.rerun()
    else:
        choice = state["answers"][-1]
        if choice == q["answer"]:
            st.success(f"✅ Correct — {q['answer']}")
        else:
            st.error(f"❌ You chose: {choice}  \n\nCorrect: **{q['answer']}**")
        e = q["entry"]
        st.markdown(f"**Word:** {e['word']} ({e['jyutping']}) — {e['meaning']}")
        dicts = vocab.dictionary_links(e["word"])
        st.markdown("**🔎 Check meaning / Jyutping / examples:** " +
                    " · ".join(f"{i}) [{label}]({url})"
                              for i, (label, url) in enumerate(dicts, 1)))
        if e["sentence"]:
            st.markdown(f"**In context:** {e['sentence']}")
        if e["english"]:
            st.caption(e["english"])
        clip = vocab.clip_segment(e["audio_file"], e["start"], e["end"])
        if clip:
            st.audio(clip, format="audio/mp3")
            st.caption("🔊 Replay the phrase")
        if st.button("Next ▶️", type="primary"):
            state["i"] = i + 1
            state["answered"] = False
            if state["i"] >= len(qs):
                state["attempt"] = vocab.record_result(qs, state["answers"])
                state["done"] = True
            st.rerun()


def _render_history(hist):
    if not hist:
        st.info("No quiz attempts yet — take a quiz to start your history.")
        return
    st.dataframe(
        [{"When": a.get("ts"), "Score %": a.get("score"),
          "Correct": a.get("correct"), "Wrong": a.get("wrong"),
          "Questions": a.get("total"), "Words": ", ".join(a.get("words", []))}
         for a in reversed(hist)],
        width="stretch",
    )
    scores = [a.get("score", 0) for a in hist]
    c1, c2, c3 = st.columns(3)
    c1.metric("Attempts", len(hist))
    c2.metric("Best score", f"{max(scores)}%")
    c3.metric("Average", f"{round(sum(scores) / len(scores))}%")
    with st.expander("⚠️ Reset progress"):
        st.warning("Deletes all quiz attempts and per-word review counters.")
        if st.button("🗑️ Reset VocabBank progress"):
            vocab.HISTORY_PATH.unlink(missing_ok=True)
            vocab.STATS_PATH.unlink(missing_ok=True)
            st.session_state.quiz = None
            st.rerun()


with tab_vocab:
    st.subheader("VocabBank — vocabulary by session & quick quiz")

    rc1, rc2 = st.columns([1, 4])
    if rc1.button("🔄 Refresh list", type="primary", key="vocab_refresh_btn"):
        st.session_state["vocab_refresh"] = vocab.refresh_snapshot()
    snap = vocab.load_snapshot()
    all_vocab = snap if snap is not None else vocab.collect_vocab()
    by_group = vocab.groups(all_vocab)
    meta = vocab.snapshot_meta()
    if meta.get("refreshed_at"):
        rc2.caption(f"Last refreshed: {meta['refreshed_at']} · {meta['total']} words "
                    "recorded.")
    else:
        rc2.caption("**Pending updates** — click **🔄 Refresh list** to record "
                    "new/updated recordings into the vocabulary list.")
    msg = st.session_state.pop("vocab_refresh", None)
    if msg:
        st.success(f"List refreshed — {msg['total']} words total, "
                   f"{msg['new']} new/updated since last refresh.")

    if not all_vocab:
        st.info("No vocabulary yet — process a recording in the ⚙️ tab, then "
                "Refresh list.")
    else:
        hist = vocab.load_history()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Unique words", len(vocab.unique_words(all_vocab)),
                  help="Distinct word + Jyutping — same total as the dictionary PDF.")
        m2.metric("Entries", len(all_vocab),
                  help="Word mentions across sessions (duplicates counted).")
        m3.metric("Sessions", len(by_group))
        m4.metric("Quiz attempts", len(hist))

        bank_tab, quiz_tab, hist_tab = st.tabs(
            ["📖 Browse by session", "🎯 Quick quiz", "📈 Quiz history"])

        with bank_tab:
            labels = {g: vocab.group_label(v) for g, v in by_group.items()}
            order = sorted(
                labels,
                key=lambda g: by_group[g][0].get("recorded_at") or "",
                reverse=True,
            )
            chosen = st.selectbox("Session (group = one recording)", order,
                                  format_func=lambda g, _l=labels: _l.get(g, g))
            entries = by_group[chosen]
            table_rows = []
            for e in entries:
                links = dict(vocab.dictionary_links(e["word"]))
                table_rows.append({
                    "Word": e["word"], "Jyutping": e["jyutping"],
                    "Meaning": e["meaning"], "In context": e["sentence"],
                    "words.hk": links["words.hk"],
                    "jyutdictionary.com": links["jyutdictionary.com"],
                    "cantowords.com": links["cantowords.com"],
                })
            st.dataframe(
                table_rows,
                column_config={
                    "words.hk": st.column_config.LinkColumn(
                        "words.hk", display_text="open",
                        help="words.hk — pronunciation + examples"),
                    "jyutdictionary.com": st.column_config.LinkColumn(
                        "jyutdictionary.com", display_text="open",
                        help="jyutdictionary.com — meaning + Jyutping"),
                    "cantowords.com": st.column_config.LinkColumn(
                        "cantowords.com", display_text="open",
                        help="cantowords.com — meaning + examples"),
                },
                width='stretch',
            )
            st.markdown("**Download the whole bank**")
            d1, d2, d3 = st.columns(3)
            d1.download_button("⬇️ This session (CSV)", vocab.vocab_csv(entries),
                               file_name=f"{chosen}_vocab.csv", mime="text/csv")
            d2.download_button("⬇️ All sessions (CSV)", vocab.vocab_csv(all_vocab),
                               file_name="vocabbank_all.csv", mime="text/csv")
            buf = io.BytesIO()
            vocab_pdf.build_vocab_pdf(all_vocab, buf)
            d3.download_button(
                "⬇️ Dictionary PDF (all words)", buf.getvalue(),
                file_name=f"vocabbank_dictionary_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf")

        with quiz_tab:
            _render_quiz()

        with hist_tab:
            _render_history(hist)


with tab_pron:
    st.subheader("Pronunciations — phrase bank & shadowing")
    st.caption(
        "Reference dictionaries for meaning / Jyutping / examples: "
        "1) [words.hk](https://words.hk/) · 2) [jyutdictionary.com]"
        "(https://jyutdictionary.com/dictionary/) · "
        "3) [cantowords.com](https://cantowords.com/dictionary/)"
    )
    bank_tab, shadow_tab = st.tabs(["📇 Phrase bank", "🎧 Shadowing studio"])

    with bank_tab:
        cards = phrases.load_cards()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cards", len(cards))
        m2.metric("New this week", phrases.new_cards_this_week(),
                  help="Target 35–50 new cards/week")
        m3.metric("Review streak", f"{phrases.review_streak()} d",
                  help="Consecutive days with ≥10 reviews")
        m4.metric("Days on target (7d)", phrases.days_met_target_this_week(),
                  help="Days this week with ≥10 reviews (target 6–7)")

        st.markdown("**Daily review log**")
        rc1, rc2 = st.columns([1, 3])
        done = rc1.number_input("Reviews done today", 0, 1000, 0, key="rev_done")
        if rc2.button("➕ Log reviews"):
            phrases.log_reviews(int(done))
            st.rerun()

        st.markdown("**Add a phrase**")
        with st.form("add_phrase"):
            f1, f2 = st.columns(2)
            jy = f1.text_input("Jyutping")
            en = f2.text_input("English")
            topic = f1.text_input("Topic tag")
            audio = f2.text_input("Audio link / file (optional)")
            if st.form_submit_button("Add card"):
                if jy.strip() or en.strip():
                    phrases.add_card(jy, en, audio, topic)
                    st.rerun()
                else:
                    st.warning("Enter at least Jyutping or English.")

        with st.expander("➕ Add from a processed recording (auto-fill + audio clip)"):
            audio_files = sorted(config.AUDIO_DIR.glob("*.mp3"),
                                 key=lambda p: p.stat().st_mtime, reverse=True)
            if not audio_files:
                st.info("No recordings in audio/ yet.")
            else:
                names = [p.name for p in audio_files]
                by_name = {p.name: p for p in audio_files}
                pick_file = st.selectbox("Recording", names, key="pb_rec")
                segs = phrases.segments_for_audio(by_name[pick_file])
                if not segs:
                    st.info("No transcript for this recording yet.")
                else:
                    labels = [
                        f"{i + 1}. {s.get('normalized_cantonese') or s.get('corrected') or s.get('cantonese', '')}"
                        for i, s in enumerate(segs)
                    ]
                    idx = st.selectbox("Sentence", range(len(segs)),
                                       format_func=lambda i: labels[i], key="pb_seg")
                    s = segs[idx]
                    st.markdown(f"**Jyutping:** `{s.get('jyutping','')}`")
                    st.markdown(f"**English:** {s.get('english','')}")
                    t1, t2 = st.columns(2)
                    tag = t1.text_input("Topic tag", key="pb_tag")
                    if t2.button("Add this phrase"):
                        clip = phrases.clip_segment(
                            str(by_name[pick_file]), s.get("start", 0.0),
                            s.get("end", 0.0))
                        audio_ref = ""
                        if clip:
                            phrases.REC_DIR.mkdir(parents=True, exist_ok=True)
                            clip_path = phrases.REC_DIR / f"phrase_{uuid.uuid4().hex[:8]}.mp3"
                            clip_path.write_bytes(clip)
                            audio_ref = str(clip_path)
                        phrases.add_card(s.get("jyutping", ""), s.get("english", ""),
                                         audio_ref, tag)
                        st.success("Added to phrase bank.")
                        st.rerun()

        if cards:
            st.markdown("**Phrase bank**")
            st.dataframe(
                [{"Jyutping": c.get("jyutping", ""), "English": c.get("english", ""),
                  "Topic": c.get("topic", ""), "Audio": c.get("audio", ""),
                  "Added": (c.get("created_at") or "")[:10]}
                 for c in cards],
                width='stretch',
            )
            d1, d2 = st.columns(2)
            d1.download_button("⬇️ Export Anki/CSV", phrases.export_csv(cards),
                               file_name="phrase_bank.csv", mime="text/csv")
            pick_del = d2.selectbox("Delete a card", [c["id"] for c in cards],
                                    format_func=lambda cid, _cards=cards: next(
                                        (f"{(c.get('jyutping') or c.get('english'))[:40]}"
                                         for c in _cards if c["id"] == cid), cid),
                                    key="pb_del")
            if d2.button("🗑️ Delete selected"):
                phrases.delete_card(pick_del)
                st.rerun()
        else:
            st.info("No phrases yet — add your first card above.")

    with shadow_tab:
        st.markdown("**Play station**")
        audio_files = sorted(config.AUDIO_DIR.glob("*.mp3"),
                             key=lambda p: p.stat().st_mtime, reverse=True)
        if not audio_files:
            st.info("No audio files in audio/ yet — record an episode first.")
        else:
            names = [p.name for p in audio_files]
            by_name = {p.name: p for p in audio_files}
            pc1, pc2 = st.columns([3, 1])
            chosen = pc1.selectbox("Audio file", names, key="sh_file")
            speed = pc2.selectbox("Speed", [0.5, 0.75, 1.0, 1.5, 2.0], index=2,
                                  format_func=lambda x: f"{x:g}x", key="sh_speed")
            full = audio_util.speed_adjusted(str(by_name[chosen]), speed)
            if full:
                st.audio(full, format="audio/mpeg")

            st.divider()
            st.markdown("**Shadow a sentence** — listen → pause → repeat, "
                        "matching tone contour and speed")
            segs = phrases.segments_for_audio(by_name[chosen])
            if not segs:
                st.info("No transcript for this recording yet — process it first.")
            else:
                labels = [
                    f"{i + 1}. {s.get('normalized_cantonese') or s.get('corrected') or s.get('cantonese', '')}"
                    for i, s in enumerate(segs)
                ]
                idx = st.selectbox("Sentence", range(len(segs)),
                                   format_func=lambda i: labels[i], key="sh_seg")
                s = segs[idx]
                st.markdown(f"**Jyutping:** `{s.get('jyutping','')}`")
                st.markdown(f"**English:** {s.get('english','')}")
                clip = phrases.clip_segment(str(by_name[chosen]),
                                            s.get("start", 0.0), s.get("end", 0.0),
                                            speed=speed)
                if clip:
                    st.audio(clip, format="audio/mpeg")
                st.caption("1) Listen  2) Pause  3) Repeat aloud, matching tone & speed.")
                rec = st.audio_input("🎤 Record yourself and compare")
                if rec is not None:
                    mine = rec.getvalue() if hasattr(rec, "getvalue") else rec.read()
                    c1, c2 = st.columns(2)
                    c1.markdown("**Original**")
                    if clip:
                        c1.audio(clip, format="audio/mpeg")
                    c2.markdown("**You**")
                    c2.audio(mine, format="audio/wav")
                    if st.button("💾 Save my recording"):
                        phrases.save_recording(mine)
                        st.success("Saved to your shadowing recordings.")
                saved = phrases.list_recordings()
                if saved:
                    with st.expander(f"🎙️ My recordings ({len(saved)})"):
                        for path in saved[:20]:
                            st.caption(Path(path).name)
                            st.audio(Path(path).read_bytes(), format="audio/wav")


with tab_teacher:
    st.subheader("🎓 Cantonese Teacher — photo worksheet")
    tt_new, tt_prev = st.tabs(["📝 New worksheet", "📚 Previous lessons"])

    with tt_new:
        st.caption(
            "Upload a photo of a Hong Kong scene → a colour-coded Cantonese "
            "worksheet PDF in the CantoneseTeacher style "
            "(10 sentences · Q&A · vocabulary · 圖像教學工作紙). "
            f"Saved as `{datetime.now().strftime('%Y-%m-%d')}_lesson_N.pdf`."
        )
        tt_cam, tt_up = st.tabs(["📷 Camera", "🖼️ Upload"])
        photo = None
        with tt_cam:
            cam_on = st.toggle("📷 Turn on camera 開啟鏡頭", value=False,
                               key="teacher_cam_on")
            if cam_on:
                cam = st.camera_input("Point at a Hong Kong scene 影低香港日常景象",
                                      key="teacher_cam")
                if cam:
                    photo = cam
            else:
                st.info("Camera is **off**. Turn it on above, or use the "
                        "🖼️ Upload tab. 鏡頭已關閉，可開啟或改用上載。")
        with tt_up:
            up = st.file_uploader("Image JPG/PNG/HEIC",
                                  type=["jpg", "jpeg", "png", "heic"], key="teacher_up")
            if up:
                photo = up
        if photo is not None:
            st.image(photo.getvalue(), caption="Your photo 你嘅相")

        with st.expander("⚙️ Options 選項"):
            theme = st.text_input("Theme 主題 (optional)", value="", key="teacher_theme")
            num_qa = st.slider("Q&A pairs 問答數量", 2, 5, 3, key="teacher_qa")
            manual = st.text_area(
                "Manual description (optional — skips the vision model)",
                value="", key="teacher_manual")
            use_demo = st.checkbox(
                "Use built-in demo lesson (no AI generation)", value=False,
                key="teacher_demo")

        if st.button("✨ Generate worksheet PDF 生成工作紙", type="primary",
                     disabled=photo is None, key="teacher_gen"):
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
                f.write(photo.getvalue())
                img_path = f.name
            with st.spinner("Analysing photo & building PDF… 分析緊張相，整緊PDF"):
                pdf_path, warning, name = cantonese_teacher.generate_worksheet(
                    img_path, theme=theme, num_qa=num_qa,
                    description=manual, use_demo=use_demo)
            if warning:
                st.warning(warning)
            st.success(f"Worksheet ready! 工作紙整好喇（`{name}`）")
            st.download_button("⬇️ Download PDF 下載",
                               data=Path(pdf_path).read_bytes(),
                               file_name=Path(pdf_path).name,
                               mime="application/pdf")

    with tt_prev:
        st.markdown("**Previous lessons** — previously generated worksheets")
        lessons = cantonese_teacher.list_lessons()
        if not lessons:
            st.info("No previous lessons yet — generate a worksheet first.")
        else:
            st.caption(f"{len(lessons)} worksheet(s) in "
                       "`metadata/cantonese_teacher/`")
            names = [l["name"] for l in lessons]
            sel = st.selectbox("Review a lesson (date_lesson_N)", names,
                               key="teacher_prev_sel")
            chosen = next(l for l in lessons if l["name"] == sel)
            c1, c2, c3 = st.columns(3)
            c1.write(f"🗓️ Created: {chosen['mtime']}")
            c2.write(f"📦 {(chosen['size'] / 1024):.0f} KB")
            c3.download_button("⬇️ Download PDF", chosen["pdf"].read_bytes(),
                               file_name=chosen["pdf"].name, mime="application/pdf",
                               key="teacher_prev_dl")
            if chosen["json"].exists():
                try:
                    data = json.loads(chosen["json"].read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    data = {}
                if data:
                    with st.expander(f"👀 Review: {data.get('title', sel)}"):
                        st.markdown(f"**{data.get('title', sel)}**")
                        st.markdown("**Ten Key Sentences:**")
                        for i, s in enumerate(data.get("sentences", []), 1):
                            st.markdown(
                                f"{i}. **{s.get('cantonese')}** · {s.get('jyutping')} "
                                f"· *{s.get('english')}*")
                        qas = data.get("qa") or []
                        if qas:
                            st.markdown("**Q&A:**")
                            for i, q in enumerate(qas, 1):
                                st.markdown(f"Q{i}: {q.get('question_cantonese')} — "
                                            f"{q.get('question_english')}")
                                st.markdown(f"A{i}: {q.get('answer_cantonese')} — "
                                            f"{q.get('answer_english')}")
            st.markdown("---")
            st.markdown("**All generated files** (newest first)")
            for l in lessons:
                fc1, fc2 = st.columns([4, 1])
                fc1.caption(f"{l['name']} · {l['mtime']} · "
                            f"{(l['size'] / 1024):.0f} KB")
                fc2.download_button("PDF", l["pdf"].read_bytes(),
                                    file_name=l["pdf"].name, mime="application/pdf",
                                    key=f"dlprev_{l['name']}")


with tab_voice:
    st.subheader("🎙️ AI CantoneVoice — Cantonese transcript → AI voice")
    st.caption(
        "Turn written Cantonese into natural Hong Kong Cantonese speech. "
        "Baseline engine: free Microsoft Edge `zh-HK` neural voices "
        "(no GPU, no key). Recommended production engine: CosyVoice 2 "
        "fine-tuned on Cantonese (CosyVoice2-Yue) — see the Blueprint."
    )
    if not cantonevoice.available():
        st.error("`edge-tts` is not installed. Run: `pip install edge-tts`.")
    (voz_tab, test_tab, graph_tab, rep_tab, prod_tab) = st.tabs(
        ["🔊 Synthesize", "🎤 Pronunciation test", "📈 Tone graph",
         "📄 Blueprint (report)", "🏭 Production blueprint"])

    with voz_tab:
        text = st.text_area(
            "Cantonese text 粵語文字", value="今日天氣好好，不如我哋去飲茶？",
            height=120, key="cv_text")
        c1, c2, c3 = st.columns(3)
        voice = c1.selectbox("Voice 聲音", list(cantonevoice.VOICES),
                             format_func=lambda v: cantonevoice.VOICES[v], key="cv_voice")
        rate_label = c2.selectbox("Speed 速度", list(cantonevoice.RATES), index=2,
                                  key="cv_rate")
        pitch_label = c3.selectbox("Pitch 音高", list(cantonevoice.PITCHES), index=1,
                                   key="cv_pitch")
        if text.strip():
            st.caption(f"Jyutping: `{cantonevoice.reading(text)}`")
        if st.button("🔊 Generate Cantonese voice", type="primary", key="cv_gen",
                     disabled=not cantonevoice.available()):
            with st.spinner("Synthesising…"):
                try:
                    audio = cantonevoice.synthesize(
                        text, voice, rate=cantonevoice.RATES[rate_label],
                        pitch=cantonevoice.PITCHES[pitch_label])
                except Exception as exc:
                    audio = b""
                    st.error(f"Synthesis failed: {exc}")
            if audio:
                st.audio(audio, format="audio/mpeg")
                st.download_button("⬇️ Download MP3", audio,
                                   file_name="cantonevoice.mp3", mime="audio/mpeg")

    with graph_tab:
        st.markdown("**Pitch-monitor dashboard** — a live frequency readout, a "
                    "learner-vs-reference contour aligned by syllable, and a "
                    "relative-deviation meter. Cantonese is tonal, so the "
                    "*contour shape* (not a fixed musical note) carries meaning.")
        g_target = st.text_area("Target sentence 目標句子",
                                value="今日天氣好好，不如我哋去飲茶？", height=90,
                                key="vg_text")
        gc1, gc2 = st.columns(2)
        g_voice = gc1.selectbox("Reference voice 參考聲音", list(cantonevoice.VOICES),
                                format_func=lambda v: cantonevoice.VOICES[v],
                                key="vg_voice")
        g_mode = gc2.radio("Graph mode 模式",
                           ["Speaker-normalised (semitones)", "Raw (Hz)"],
                           key="vg_mode")
        mode = "semitones" if "semitones" in g_mode else "hz"
        g_view = st.radio("View 檢視",
                          ["Pitch monitor", "Waveform + contour"],
                          horizontal=True, key="vg_view")
        st.caption(f"Jyutping: `{cantonevoice.reading(g_target)}`")

        grec = st.audio_input("🎤 Record your attempt 錄低你嘅讀音", key="vg_rec")
        if grec is not None:
            data = grec.getvalue() if hasattr(grec, "getvalue") else grec.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(data)
                vg_path = f.name
            ref_path = None
            try:
                if cantonevoice.available():
                    ref_audio = cantonevoice.synthesize(g_target, g_voice)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as rf:
                        rf.write(ref_audio)
                        ref_path = rf.name
            except Exception:
                ref_path = None
            try:
                with st.spinner("Building the dashboard (first run loads the "
                                "Whisper model)…"):
                    windows = None
                    try:
                        windows = voice_graph.expand_word_windows(
                            pronunciation.transcribe_words(vg_path))
                    except Exception:
                        windows = None
                    ref_windows = None
                    if ref_path:
                        try:
                            ref_windows = voice_graph.expand_word_windows(
                                pronunciation.transcribe_words(ref_path))
                        except Exception:
                            ref_windows = None
                    result, png_pitch = voice_graph.build_dashboard(
                        g_target, vg_path, reference_audio=ref_path,
                        windows=windows, ref_windows=ref_windows, mode=mode)
                    png = (voice_graph.render_wave(result)
                           if g_view.startswith("Waveform") else png_pitch)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Current pitch 目前音高",
                          f"{result['current_hz']} Hz" if result["current_hz"] else "—")
                m2.metric("Syllables", len(result["syllables"]))
                dev = result["overall_deviation"]
                unit = "st" if mode == "semitones" else "Hz"
                m3.metric("Overall deviation",
                          f"{dev:+.1f} {unit}" if dev is not None else "—",
                          help="learner − reference (relative)")
                acc = result.get("accuracy")
                m4.metric("Accuracy 準確度",
                          f"{acc}/100" if acc is not None else "—",
                          help="wave + contour match vs reference (per syllable, "
                               "averaged). Full sentence or single word → 100 max.")

                st.image(png, caption="Pitch monitor 音高監測")
                ap1, ap2 = st.columns(2)
                if ref_path:
                    ap1.markdown("**Reference 參考**")
                    ap1.audio(Path(ref_path).read_bytes(), format="audio/mpeg")
                ap2.markdown("**Your voice 你嘅聲音**")
                ap2.audio(data, format="audio/wav")

                rows = []
                for s in result["syllables"]:
                    d = s["deviation"]
                    a = s.get("accuracy")
                    rows.append({
                        "Char": s["char"], "Jyutping": s["jyutping"],
                        "Tone": s["tone"], "Name": s["tone_name"],
                        "Deviation": f"{d:+.1f} {unit}" if d is not None else "—",
                        "Accuracy": f"{a}/100" if a is not None else "—",
                        "Verdict": s["verdict"],
                    })
                st.dataframe(rows, width="stretch")
                st.caption("The meter shows a **relative pitch difference**, not a "
                           "complete pronunciation judgment; tone, rhythm and "
                           "segmental quality are separate.")
                st.download_button("⬇️ Download dashboard (PNG)", png,
                                   file_name="pitch_monitor.png", mime="image/png")
            except Exception as exc:
                st.error(f"Could not build the dashboard: {exc}")

    with test_tab:
        st.markdown("Practice a sentence and get an instant **pronunciation "
                    "score** — the local Whisper model transcribes your speech, "
                    "then we compare characters **and tones** (LSHK Jyutping).")
        presets = [
            "今日天氣好好，不如我哋去飲茶？",
            "唔該，呢班車去唔去中環？",
            "我聽日有時間，我哋再傾。",
            "多謝你嘅幫忙，真係唔好意思。",
        ]
        t1, t2 = st.columns([2, 1])
        example = t2.selectbox("Examples 例子", presets, key="pt_example")
        t2.button("Use example 用例子", key="pt_use_example",
                  on_click=lambda e=example: st.session_state.update({"pt_text": e}))
        target = t1.text_area("Target sentence 目標句子", value=presets[0],
                              height=100, key="pt_text")

        vc = st.selectbox("Reference voice 參考聲音", list(cantonevoice.VOICES),
                          format_func=lambda v: cantonevoice.VOICES[v], key="pt_voice")
        ref_c1, ref_c2 = st.columns(2)
        if ref_c1.button("🔊 Hear reference 聽範例", key="pt_ref",
                         disabled=not cantonevoice.available()):
            with st.spinner("Synthesising reference…"):
                st.session_state["pt_ref_audio"] = cantonevoice.synthesize(target, vc)
        if st.session_state.get("pt_ref_audio"):
            ref_c2.audio(st.session_state["pt_ref_audio"], format="audio/mpeg")
        st.caption(f"Target Jyutping 目標粵拼: `{cantonevoice.reading(target)}`")

        rec = st.audio_input("🎤 Record your reading 錄低你嘅讀音", key="pt_rec")
        if rec is not None:
            data = rec.getvalue() if hasattr(rec, "getvalue") else rec.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(data)
                rec_path = f.name
            try:
                with st.spinner("Scoring your pronunciation (first run loads the "
                                "Whisper model)…"):
                    result = pronunciation.evaluate(target, rec_path)
            except Exception as exc:
                result = None
                st.error(f"Could not score: {exc}")
            if result:
                s1, s2, s3 = st.columns(3)
                s1.metric("Overall score", f"{result['score']}%")
                s2.metric("Character accuracy", f"{result['char_accuracy']}%")
                s3.metric("Tone accuracy", f"{result['tone_accuracy']}%")
                st.markdown(f"**Heard (ASR):** {result['spoken']}")
                st.caption(f"Target tones: `{result['target_tones']}`  ·  "
                           f"Heard tones: `{result['spoken_tones']}`")
                if result["differences"]:
                    st.dataframe(result["differences"], width="stretch")
                else:
                    st.success("Perfect match! 完全正確！")

    with rep_tab:
        st.markdown(cantonevoice.report_text())

    with prod_tab:
        st.caption("Production-grade blueprint — the full project development "
                   "report and starter service (`AI_CantoneVoice/"
                   "production_blueprint/`).")
        st.markdown(cantonevoice.production_report_text())
