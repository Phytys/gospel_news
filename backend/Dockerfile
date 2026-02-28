FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for trafilatura + lxml
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libxml2-dev     libxslt1-dev     zlib1g-dev     libffi-dev     curl   && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY config /app/config

EXPOSE 8000
