@echo off
chcp 65001 >nul
echo ========================================
echo 공시지원금 크롤러 실행
echo ========================================
echo.

if not exist output mkdir output

echo [1/3] 이미지 빌드 중...
podman build -t gongsi-crawler . -q

echo [2/3] SKT 크롤러 실행 중...
podman run --rm -v ./output:/app/output gongsi-crawler python skt_crawler.py

echo [3/3] LG U+ 크롤러 실행 중...
podman run --rm -v ./output:/app/output --shm-size=2g gongsi-crawler python lguplus_crawler.py

echo.
echo ========================================
echo 완료! output 폴더에서 결과를 확인하세요.
echo ========================================
pause
