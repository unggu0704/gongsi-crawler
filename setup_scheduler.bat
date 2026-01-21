@echo off
chcp 65001 >nul
echo ========================================
echo Windows 작업 스케줄러 자동 설정
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 관리자 권한이 필요합니다!
    echo 우클릭 후 "관리자 권한으로 실행"을 선택하세요.
    pause
    exit /b 1
)

REM 현재 디렉토리 경로
set "CURRENT_DIR=%~dp0"
set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"

REM 로그 디렉토리 생성
if not exist "%CURRENT_DIR%\logs" mkdir "%CURRENT_DIR%\logs"

echo 경로: %CURRENT_DIR%
echo.

REM 실행 시간 입력 받기
echo 크롤러를 실행할 시간을 입력하세요 (24시간 형식)
echo 예시: 09:00, 14:30, 23:00
echo.
set /p RUN_TIME="실행 시간 (HH:MM): "

echo.
echo 작업 스케줄러 등록 중...
echo 실행 시간: 매일 %RUN_TIME%
echo.

REM 기존 작업 삭제 (있으면)
schtasks /Delete /TN "공시지원금_크롤러" /F >nul 2>&1

REM 새 작업 생성
schtasks /Create /TN "공시지원금_크롤러" /TR "\"%CURRENT_DIR%\run_scheduled.bat\"" /SC DAILY /ST %RUN_TIME% /RL HIGHEST /F

if %errorlevel% equ 0 (
    echo.
    echo ✅ 작업 스케줄러 등록 완료!
    echo.
    echo 📋 설정 내용:
    echo   - 작업 이름: 공시지원금_크롤러
    echo   - 실행 시간: 매일 %RUN_TIME%
    echo   - 실행 파일: %CURRENT_DIR%\run_scheduled.bat
    echo   - 로그 위치: %CURRENT_DIR%\logs
    echo.
    echo 💡 확인 방법:
    echo   1. "작업 스케줄러" 앱 실행
    echo   2. "작업 스케줄러 라이브러리"에서 "공시지원금_크롤러" 찾기
    echo.
    echo 💡 수동 테스트:
    echo   run_scheduled.bat 더블클릭
    echo.
) else (
    echo.
    echo ❌ 작업 스케줄러 등록 실패!
    echo.
    echo 잘못된 시간 형식일 수 있습니다.
    echo HH:MM 형식으로 정확히 입력하세요 (예: 09:00, 14:30)
    echo 숫자는 두 자리로 입력하세요 (예: 09:00, 아님: 9:00)
    echo.
)

pause
