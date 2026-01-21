FROM python:3.10-slim

# Chromium 설치
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# lib 파일 복사 및 설치 (SSL 검증 우회)
COPY lib /tmp/lib
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r /tmp/lib && rm /tmp/lib

WORKDIR /app
ENV RUNNING_IN_DOCKER=true
# Python 크롤러 코드 복사
COPY skt_crawler.py lguplus_crawler.py /app/
