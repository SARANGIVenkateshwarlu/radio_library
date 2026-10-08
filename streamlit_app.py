"""Streamlit app: process recordings and browse the Cantonese learning library.

Run:  streamlit run streamlit_app.py
"""
import json
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config, library, recorder  # noqa: E402
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

tab_record, tab_process, tab_library = st.tabs(
    ["🔴 Record radio", "⚙️ Process recording", "📚 Library"]
)


def set_review_status(recording_id: str) -> None:
    library.update_review_status(recording_id, st.session_state[f"status_{recording_id}"])


def fmt_ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def show_segments(segments):
    for s in segments:
        st.markdown(f"**[{fmt_ts(s['start'])} – {fmt_ts(s['end'])}]**")
        st.markdown(f"**Cantonese:**\n\n🗣️ {s.get('corrected') or s.get('cantonese')}")
        st.markdown(f"**Jyutping:** `{s.get('jyutping','')}`")
        st.markdown(f"**English:** {s.get('english','')}")
        vocab = s.get("vocabulary") or []
        if vocab:
            st.markdown("**Vocabulary:**")
            for v in vocab:
                st.markdown(f"- {v['word']} {v['jyutping']} — {v['meaning']}")
        if s.get("uncertain"):
            st.warning("Contains uncertain items 〔?〕 — please review.")
        st.divider()


with tab_record:
    st.subheader("Record HK internet radio directly to MP3")
    st.caption(
        "Captures the station's own digital stream (no microphone → no room noise). "
        "MP3's highest standard quality is 320 kbps; recordings for personal study only."
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
    if bc1.button("🔴 Start recording", type="primary", disabled=bool(running)):
        try:
            job = recorder.start_recording(station, stream_url, duration_s, bitrate)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            st.session_state.rec_job = job["id"]
            st.rerun()
    if bc2.button("⏹️ Stop", disabled=not running):
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
    audio_files = sorted(config.AUDIO_DIR.glob("*.mp3"))
    audio_path = st.text_input(
        "Audio file path (YYYY-MM-DD_station_duration.mp3)",
        value=str(audio_files[0]) if audio_files else "audio/2026-10-07_RTHK_5min.mp3",
    )
    mock = st.checkbox(
        "Use mock ASR (offline demo transcript — leave OFF for real recordings)",
        value=False,
    )

    if st.button("▶️ Run pipeline", type="primary"):
        with st.status("Running LangGraph pipeline…", expanded=True) as status:
            for step in ["load_audio", "transcribe", "correct", "jyutping",
                         "translate", "generate_pdf", "save_to_library"]:
                st.write(f"• {step}")
            final = run(audio_path, mock_asr=mock)
            status.update(label=f"Done: {final['recording_id']}", state="complete")
        st.success(f"Recording `{final['recording_id']}` processed and saved to the library.")
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
