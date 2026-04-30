# Placeholder — finalized in stage 7.
# Target: CUDA runtime for RTX 5090 + ffmpeg + neylo package.
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY env/requirements.txt /app/env/requirements.txt
RUN pip install --no-cache-dir -r env/requirements.txt

COPY . /app
RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "neylo"]
