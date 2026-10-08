"""Streamlit app: process recordings and browse the Cantonese learning library.

Run:  streamlit run streamlit_app.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import cleanup, config, library, recorder, schedule, vocab  # noqa: E402
from app.graph import run  # noqa: E402

st.set_page_config(page_title="HK Radio Cantonese Library", page_icon="📻", layout="wide")
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

tab_sched, tab_record, tab_process, tab_library, tab_vocab = st.tabs(
    ["🗓️ Radio Time Table", "🔴 Record radio", "⚙️ Process recording",
     "📚 Library", "🗂️ VocabBank"]
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
        st.markdown("**Jyutping:**")
        for j, s in enumerate(block, 1):
            st.markdown(f"{j}. `{s.get('jyutping','')}`")
        st.markdown("**English:**")
        for j, s in enumerate(block, 1):
            st.markdown(f"{j}. {s.get('english','')}")
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

    if "rec_job" not in st.session_state:
        st.session_state.rec_job = None

    job_id = st.session_state.rec_job
    running = job_id and recorder.job_status(job_id)["running"]

    bc1, bc2 = st.columns(2)
    if bc1.button("🔴 Start recording", type="primary", disabled=bool(running),
                  key="record_start", width="stretch"):
        try:
            job = recorder.start_recording(station, stream_url, duration_s, bitrate)
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

with tab_process:
    st.subheader("Run the LangGraph pipeline on a recording")

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

    mock = st.checkbox(
        "Use mock ASR (offline demo transcript — leave OFF for real recordings)",
        value=False,
    )
    clean = st.checkbox(
        "Clean audio first — isolate voice / remove background music "
        f"({'Demucs' if cleanup.demucs_available() else 'ffmpeg'} · slower)",
        value=cleanup.demucs_available(),
    )

    if st.button("▶️ Run pipeline", type="primary") and audio_path:
        with st.status("Running LangGraph pipeline…", expanded=True) as status:
            for step in ["load_audio", "cleanup_audio", "transcribe", "correct",
                         "jyutping", "translate", "segment_blocks",
                         "review_quality", "generate_pdf", "save_to_library"]:
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
                               file_name=pdf_path.name, mime="application/pdf")

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
        st.markdown(
            f"[🔗 Hear pronunciation & examples on words.hk]"
            f"(https://words.hk/zidin/{quote(e['word'])})")
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
    all_vocab = vocab.collect_vocab()
    by_group = vocab.groups()

    if not all_vocab:
        st.info("No vocabulary yet — process a recording in the ⚙️ tab first.")
    else:
        hist = vocab.load_history()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total words", len(all_vocab))
        m2.metric("Sessions", len(by_group))
        m3.metric("Quiz attempts", len(hist))

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
                                  format_func=lambda g: labels[g])
            entries = by_group[chosen]
            st.dataframe(
                [{"Word": e["word"], "Jyutping": e["jyutping"],
                  "Meaning": e["meaning"], "In context": e["sentence"],
                  "words.hk": f"https://words.hk/zidin/{quote(e['word'])}"}
                 for e in entries],
                column_config={
                    "words.hk": st.column_config.LinkColumn(
                        "Pronunciation & examples",
                        display_text="🔗 words.hk",
                        help="Open on words.hk to hear the pronunciation and "
                             "see Cantonese usage examples",
                    ),
                },
                width='stretch',
            )
            d1, d2 = st.columns(2)
            d1.download_button("⬇️ This session (CSV)", vocab.vocab_csv(entries),
                               file_name=f"{chosen}_vocab.csv", mime="text/csv")
            d2.download_button("⬇️ All sessions (CSV)", vocab.vocab_csv(all_vocab),
                               file_name="vocabbank_all.csv", mime="text/csv")

        with quiz_tab:
            _render_quiz()

        with hist_tab:
            _render_history(hist)
