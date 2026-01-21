@echo off
chcp 65001 >nul
echo ========================================
echo 공시지원금 크롤러 실행
echo ========================================
echo.

if not exist output mkdir output

echo [준비] 이미지 빌드 중...
podman build -t gongsi-crawler --tls-verify=false . -q
if %errorlevel% neq 0 (
    echo 빌드 실패! 오류를 확인하세요.
    pause
    exit /b 1
)
echo.
echo [1/2] LG U+ 크롤러 실행 중...
podman run --rm -v ./output:/app/output -v ./lguplus_crawler.py:/app/lguplus_crawler.py --shm-size=2g gongsi-crawler python lguplus_crawler.py

echo [2/2] SKT 크롤러 실행 중...
podman run --rm -v ./output:/app/output -v ./skt_crawler.py:/app/skt_crawler.py gongsi-crawler python skt_crawler.py


echo.
echo ========================================
echo 완료! output 폴더에서 결과를 확인하세요.
echo ========================================
pause
