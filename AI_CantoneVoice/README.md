# AI_CantoneVoice

Cantonese **Transcript-to-AI Voice** — turn written Cantonese into natural Hong
Kong Cantonese speech.

- **Full blueprint:** [`REPORT.md`](REPORT.md) — research review, model
  comparison, architecture, data strategy, training, evaluation, deployment,
  roadmap, risks, components/recommendations.
- **Working baseline in the app:** the Streamlit **🎙️ AI CantoneVoice** tab
  synthesises Cantonese with the free Microsoft Edge `zh-HK` neural voices
  (`edge-tts`) — no GPU, no API key.
- **Recommended production engine:** **CosyVoice 2** continued-trained on
  Cantonese (CosyVoice2-Yue-style model) with LSHK-Jyutping G2P + a
  statement/question classifier + prosody/emotion conditioning.

## Quick start (standalone)

```bash
pip install -r requirements.txt
python src/text_norm.py "今日天氣好好，不如去飲茶？"
python src/g2p.py "今日天氣好好"           # -> LSHK Jyutping
python src/tts_engine.py "早晨" --out out.mp3   # Edge zh-HK voice
uvicorn src.service:app --reload          # FastAPI: http://127.0.0.1:8000
```

## Notes
- Jyutping = LSHK scheme, tone numbers 1–6; dictionary-based (pycantonese).
- Evaluate with **MOS + tone accuracy + speaker similarity + latency**.
- Licences/versions for third-party models/datasets: see `REPORT.md`
  §12 — several are marked **“requires verification.”**
