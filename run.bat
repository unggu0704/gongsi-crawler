@echo off
chcp 65001 >nul
echo ========================================
echo 공시지원금 크롤러 실행
echo ========================================
echo.

if not exist output mkdir output

REM 이미지가 없을 때만 빌드
podman image exists gongsi-crawler
if %errorlevel% neq 0 (
    echo [빌드] 처음 실행이거나 이미지가 없습니다. 빌드 중...
    podman build -t gongsi-crawler -f dockerfile --tls-verify=false .
    echo.
) else (
    echo [빌드] 이미지가 이미 존재합니다. 빌드 건너뛰기.
    echo.
)

echo [1/2] SKT 크롤러 실행 중...
podman run --rm -v ./output:/app/output gongsi-crawler python skt_crawler.py

echo [2/2] LG U+ 크롤러 실행 중...
podman run --rm -v ./output:/app/output --shm-size=2g gongsi-crawler python lguplus_crawler.py

echo.
echo ========================================
echo 완료! output 폴더에서 결과를 확인하세요.
echo ========================================
pause
