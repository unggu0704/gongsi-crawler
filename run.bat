@echo off
chcp 65001 >nul
echo ========================================
echo 공시지원금 크롤러 실행
echo ========================================
echo.

REM Podman 실행 확인 및 시작
echo [준비] Podman 상태 확인 중...

podman machine list 2>nul | findstr "Currently running" >nul
if %errorlevel% neq 0 (
    echo Podman Machine 시작 중...
    podman machine start 2>nul
    if %errorlevel% equ 0 (
        echo 대기 중... (30초)
        timeout /t 30 /nobreak >nul
    )
    echo Podman 준비 완료!
) else (
    echo Podman 이미 실행 중
)
echo.

if not exist output mkdir output

echo [1/2] SKT 크롤러 실행 중...
podman run --rm -v ./output:/app/output gongsi-crawler python -u skt_crawler.py

echo [2/2] LG U+ 크롤러 실행 중...
podman run --rm -v ./output:/app/output --shm-size=2g gongsi-crawler python -u lguplus_crawler.py

echo.
echo ========================================
echo 완료! output 폴더에서 결과를 확인하세요.
echo ========================================
pause
