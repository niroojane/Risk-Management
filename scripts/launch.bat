@echo off
rem Shared launcher used by start-binance.bat and start-yahoo.bat.
rem Usage: launch.bat <MARKET> <BACKEND_PORT> <FRONTEND_PORT> <LABEL>
rem First run: creates backend\.venv and installs the Python / npm packages.

setlocal
set "MARKET=%~1"
set "BACKEND_PORT=%~2"
set "FRONTEND_PORT=%~3"
set "LABEL=%~4"
set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "BASE_PYTHON=C:\Users\Admin\anaconda3\python.exe"

where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo Node.js is not installed. Install the LTS version from https://nodejs.org and run this file again.
    pause
    exit /b 1
)

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
    echo Creating the backend Python environment...
    "%BASE_PYTHON%" -m venv "%BACKEND%\.venv" || goto :error
)
"%BACKEND%\.venv\Scripts\python.exe" -c "import fastapi, scipy, statsmodels, openpyxl, yfinance" >nul 2>nul
if errorlevel 1 (
    echo Installing the backend packages...
    "%BACKEND%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt" || goto :error
)

if not exist "%FRONTEND%\node_modules" (
    echo Installing the frontend packages...
    pushd "%FRONTEND%"
    call npm.cmd install || (popd & goto :error)
    popd
)

rem MARKET is read by the backend settings; VITE_API_URL points the frontend at this backend.
set "VITE_API_URL=http://localhost:%BACKEND_PORT%"
start "Risk Management %LABEL% - backend" /D "%BACKEND%" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port %BACKEND_PORT%"
start "Risk Management %LABEL% - frontend" /D "%FRONTEND%" cmd /k "npm.cmd run dev -- --port %FRONTEND_PORT% --strictPort"

rem Give the servers a few seconds, then open the app
timeout /t 6 /nobreak >nul
start "" http://localhost:%FRONTEND_PORT%
exit /b 0

:error
echo.
echo Setup failed - see the messages above.
pause
exit /b 1
