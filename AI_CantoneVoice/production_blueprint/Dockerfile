# CantoneVoice Production — API service (baseline Edge zh-HK engine)
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8000
# For GPU engines, base on nvidia/cuda and install torch + the chosen TTS model.
CMD ["uvicorn", "src.service:app", "--host", "0.0.0.0", "--port", "8000"]
