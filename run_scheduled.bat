@echo off
chcp 65001 >nul

cd /d "%~dp0"

if not exist logs mkdir logs

set "LOG_DATE=%date:~0,4%%date:~5,2%%date:~8,2%"
set "LOG_TIME=%time:~0,2%%time:~3,2%"
set "LOG_TIME=%LOG_TIME: =0%"
set "LOG_FILE=logs\%LOG_DATE%_%LOG_TIME%.log"

echo 크롤러 실행 시작: %date% %time%
echo 크롤러 실행 시작: %date% %time% >> "%LOG_FILE%" 2>&1

REM 화면과 로그 파일 둘 다 출력
call run.bat 2>&1 | tee "%LOG_FILE%"

echo 크롤러 실행 종료: %date% %time%
echo 크롤러 실행 종료: %date% %time% >> "%LOG_FILE%" 2>&1

pause
