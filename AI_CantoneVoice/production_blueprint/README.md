# CantoneVoice Production Blueprint

Production-grade blueprint + starter service for the Cantonese
Transcript-to-AI Voice system.

- **Full report:** [`REPORT.md`](REPORT.md) — executive summary, architecture,
  model comparison, references, data pipeline, training, evaluation, deployment,
  roadmap, risks, components/recommendations, deliverables.
- **Starter API:** [`src/service.py`](src/service.py) — FastAPI
  (`POST /tts`, `POST /clone-voice`, `GET /voices`, `GET /jobs/{job_id}`) with a
  working **Edge `zh-HK`** baseline engine (free, no key).
- **Deploy:** `Dockerfile` + `docker-compose.yml`.

## Run

```bash
pip install -r requirements.txt
uvicorn src.service:app --reload        # http://127.0.0.1:8000/docs
```

## Docker

```bash
docker build -t cantonevoice .
docker run -p 8000:8000 cantonevoice
```

Recommended production engine: **CosyVoice 2** fine-tuned on Cantonese
(CosyVoice2-Yue-style) — see `REPORT.md` §3. Fallbacks: F5-TTS / Llasa-1B /
Azure `zh-HK`. Evaluate as `MOS + tone accuracy + speaker similarity + latency`.
