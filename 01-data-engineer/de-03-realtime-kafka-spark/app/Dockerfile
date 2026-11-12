FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cache the Kafka connector jars in the image so the job starts without downloading.
COPY warmup.py .
RUN python warmup.py && rm warmup.py

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
