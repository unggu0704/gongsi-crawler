@echo off
chcp 65001 >nul
echo ========================================
echo 작업 스케줄러 제거
echo ========================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 관리자 권한이 필요합니다!
    pause
    exit /b 1
)

schtasks /Delete /TN "공시지원금_크롤러" /F

if %errorlevel% equ 0 (
    echo ✅ 작업 스케줄러 제거 완료!
) else (
    echo ❌ 작업 스케줄러 제거 실패!
)

pause
