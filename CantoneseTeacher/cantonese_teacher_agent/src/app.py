"""Streamlit mobile app: Cantonese Class Teacher Agent.

Run on your computer, open from your phone on the same Wi-Fi:

    streamlit run src/app.py --server.address 0.0.0.0

Then browse to http://<your-computer-ip>:8501 on your phone.
The "Take photo" button opens the phone camera directly.

Follows the locked spec in RULES.md: colour-matched words, fixed font
sizes, one PDF per image.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent
import pdf_generator

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="廣東話課堂 Cantonese Class",
    page_icon="🚌",
    layout="centered",
)

st.title("🚌 廣東話課堂 Cantonese Class")
st.caption("Take a photo → get a printable Cantonese worksheet PDF. "
           "影張相 → 即刻出廣東話工作紙。")

# ---------------- options ----------------
with st.expander("⚙️ Options 選項", expanded=False):
    theme = st.text_input("Lesson theme 主題 (optional)", value="")
    num_qa = st.slider("Q&A pairs 問答數量", 2, 5, 3)
    difficulty = st.selectbox("Level 程度", ["Beginner 初級", "Intermediate 中級"])
    add_to_filename = st.checkbox("Add date to filename 檔名加日期", value=True)

has_key = bool(os.environ.get("OPENAI_API_KEY"))
if not has_key:
    st.info("No OPENAI_API_KEY set — running in demo mode: the built-in "
            "minibus lesson will be used for any photo. Set the key on the "
            "server for live AI generation.", icon="ℹ️")

# ---------------- photo input ----------------
tab_cam, tab_up = st.tabs(["📷 Take photo 影相", "🖼️ Upload 上載"])
photo = None
with tab_cam:
    cam = st.camera_input("Point at anything in Hong Kong and shoot")
    if cam:
        photo = cam
with tab_up:
    up = st.file_uploader("JPG / PNG / HEIC", type=["jpg", "jpeg", "png", "heic"])
    if up:
        photo = up

if photo:
    st.image(photo, caption="Your photo 你嘅相", use_container_width=True)

# ---------------- generate ----------------
if st.button("✨ Generate Worksheet 生成工作紙", type="primary",
             use_container_width=True, disabled=photo is None):
    suffix = ".jpg" if (photo.type or "").endswith("jpeg") else ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(photo.getvalue())
        img_path = f.name

    with st.spinner(" analysing photo & building PDF... 分析緊張相，整緊PDF"):
        try:
            if has_key:
                lesson = agent.describe_image(img_path)
                lesson = agent.generate_lesson(lesson)
            else:
                lesson = json.loads(
                    (ROOT / "data" / "minibus_lesson.json").read_text("utf-8"))

            if theme.strip():
                lesson["title"] = f"Cantonese Class 廣東話課堂 – {theme.strip()}"
            lesson["qa"] = lesson["qa"][:num_qa]

            name = (theme.strip() or "worksheet").replace(" ", "_")
            if add_to_filename:
                name += "_" + datetime.now().strftime("%Y%m%d_%H%M")
            pdf_path = OUT_DIR / f"{name}.pdf"
            pdf_generator.build_pdf(lesson, img_path, str(pdf_path))
        except Exception as e:
            st.error(f"Generation failed 生成失敗: {e}")
            st.stop()

    st.success("Worksheet ready! 工作紙整好喇！")
    st.download_button(
        "⬇️ Download PDF 下載",
        data=Path(pdf_path).read_bytes(),
        file_name=Path(pdf_path).name,
        mime="application/pdf",
        use_container_width=True,
    )
