# syntax=docker/dockerfile:1

########################  Stage 1: builder  ########################
FROM python:3.11-slim-bullseye AS builder

# Official Debian + PyPI only (server is not in China).
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build toolchain needed to compile any sdist-only wheels.
# Retry apt up to 3 times to survive transient mirror/network failures.
RUN for i in 1 2 3; do \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential \
            git \
        && break || { echo "apt attempt $i failed, retrying..."; sleep 5; }; \
    done \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt ./

# Install into an isolated prefix so we can copy just the packages later.
RUN pip install --no-cache-dir --prefix=/install --retries 3 --timeout 60 -r requirements.txt

########################  Stage 2: runtime  ########################
FROM python:3.11-slim-bullseye AS runtime

WORKDIR /MoneyPrinterTurbo
RUN chmod 777 /MoneyPrinterTurbo
ENV PYTHONPATH="/MoneyPrinterTurbo" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime system binaries ONLY (moviepy needs ffmpeg; app needs imagemagick).
# Retry apt up to 3 times to survive transient mirror/network failures.
RUN for i in 1 2 3; do \
        apt-get update && apt-get install -y --no-install-recommends \
            ffmpeg \
            imagemagick \
        && break || { echo "apt attempt $i failed, retrying..."; sleep 5; }; \
    done \
    && rm -rf /var/lib/apt/lists/*

# ImageMagick policy fix (bullseye ships ImageMagick 6 -> /etc/ImageMagick-6).
RUN sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml

# Bring in the Python packages + console scripts built in stage 1.
COPY --from=builder /install /usr/local

# App code (respects .dockerignore: venv, __pycache__, .git, storage, config.toml).
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "./webui/Main.py", \
     "--browser.serverAddress=127.0.0.1", \
     "--server.enableCORS=True", \
     "--browser.gatherUsageStats=False", \
     "--server.showEmailPrompt=False"]
