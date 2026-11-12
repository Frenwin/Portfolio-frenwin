FROM python:3.11-slim-bookworm

# Spark 3.5 runs on Java 17 (bookworm's default JRE).
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Resolve Delta Lake and hadoop-aws jars at build time so runs work offline and start fast.
COPY warmup.py .
RUN python warmup.py && rm warmup.py

ENV PYTHONPATH=/app
