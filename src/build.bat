@echo off
chcp 65001 >nul
echo ========================================
echo 이미지 빌드
echo ========================================
echo.

echo 빌드 중...
podman build -t gongsi-crawler --tls-verify=false .

if %errorlevel% neq 0 (
    echo 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ========================================
echo 빌드 완료!
echo ========================================
pause
