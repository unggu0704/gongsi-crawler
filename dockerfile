FROM python:3.10-slim

# Chrome 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O /tmp/chrome-key.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg /tmp/chrome-key.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /tmp/chrome-key.gpg

# lib 파일 복사 및 설치
COPY lib /tmp/lib
RUN pip install --no-cache-dir -r /tmp/lib && rm /tmp/lib

COPY skt_crawler.py lguplus_crawler.py /app/

WORKDIR /app
