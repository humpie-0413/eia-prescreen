@echo off
REM ─────────────────────────────────────────
REM EIA Pre-Screen 로컬 실행 스크립트
REM 백엔드(8000) + 프론트엔드(3000) 동시 실행
REM ─────────────────────────────────────────

echo.
echo  EIA Pre-Screen Local Runner
echo  ============================
echo.

REM 프로젝트 루트로 이동
cd /d "%~dp0\.."

REM .env 확인
if not exist ".env" (
    echo [ERROR] .env 파일이 없습니다.
    echo         cp .env.example .env 를 먼저 실행하세요.
    pause
    exit /b 1
)

REM DEMO_MODE 확인
findstr /C:"DEMO_MODE=true" .env >nul 2>&1
if errorlevel 1 (
    echo [WARN] .env에 DEMO_MODE=true 가 없습니다. 데모 데이터가 동작하지 않을 수 있습니다.
)

echo [1/2] Backend (uvicorn) 시작 중... http://localhost:8000
echo [2/2] Frontend (pnpm dev) 시작 중... http://localhost:3000
echo.
echo  종료: 이 창을 닫거나 Ctrl+C
echo.

REM 백엔드: 새 터미널에서 실행
start "EIA-Backend" cmd /k "cd /d %cd% && python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"

REM 프론트엔드: 새 터미널에서 실행
start "EIA-Frontend" cmd /k "cd /d %cd%\frontend && pnpm dev"

REM 3초 후 브라우저 열기
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo  백엔드: http://localhost:8000/health
echo  프론트엔드: http://localhost:3000
echo  API 문서: http://localhost:8000/docs
echo.
pause
