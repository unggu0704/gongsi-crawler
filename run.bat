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
    if %errorlevel% neq 0 (
        echo Podman Machine 시작 실패!
        pause
        exit /b 1
    )
) else (
    echo Podman 이미 실행 중
)

REM Podman 연결이 준비될 때까지 대기
echo Podman 연결 확인 중...
set /a retry_count=0
set /a max_retries=20

:wait_for_podman
podman info >nul 2>&1
if %errorlevel% equ 0 (
    echo Podman 준비 완료!
    goto podman_ready
)

set /a retry_count+=1
if %retry_count% geq %max_retries% (
    echo Podman 연결 시간 초과! 다시 시도해주세요.
    echo.
    echo 해결 방법:
    echo 1. podman machine stop
    echo 2. podman machine start
    echo 3. 다시 실행
    pause
    exit /b 1
)

echo 대기 중... (%retry_count%/%max_retries%)
timeout /t 3 /nobreak >nul
goto wait_for_podman

:podman_ready
echo.

if not exist output mkdir output

echo [1/2] SKT 크롤러 실행 중...
podman run --rm -v ./output:/app/output gongsi-crawler python -u skt_crawler.py
if %errorlevel% neq 0 (
    echo SKT 크롤러 실행 실패! (오류 코드: %errorlevel%)
    echo 이미지가 빌드되지 않았을 수 있습니다. build.bat를 먼저 실행하세요.
)
echo.

echo [2/2] LG U+ 크롤러 실행 중...
podman run --rm -v ./output:/app/output --shm-size=2g gongsi-crawler python -u lguplus_crawler.py
if %errorlevel% neq 0 (
    echo LG U+ 크롤러 실행 실패! (오류 코드: %errorlevel%)
    echo 이미지가 빌드되지 않았을 수 있습니다. build.bat를 먼저 실행하세요.
)

echo.
echo ========================================
echo 완료! output 폴더에서 결과를 확인하세요.
echo ========================================
pause
