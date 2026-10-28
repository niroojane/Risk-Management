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

where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo Node.js is not installed. Install the LTS version from https://nodejs.org and run this file again.
    pause
    exit /b 1
)

if exist "%BACKEND%\.venv\Scripts\python.exe" goto :venv_ready
call :find_python
if not defined PYTHON_EXE (
    echo Python 3.11 or newer was not found. Install it from https://www.python.org/downloads
    echo or Anaconda, or set BASE_PYTHON to its python.exe, then run this file again.
    pause
    exit /b 1
)
echo Creating the backend Python environment with %PYTHON_EXE%...
"%PYTHON_EXE%" -m venv "%BACKEND%\.venv" || goto :error
:venv_ready
"%BACKEND%\.venv\Scripts\python.exe" -c "import fastapi, scipy, statsmodels, openpyxl, yfinance, sklearn, hmmlearn" >nul 2>nul
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

rem Python 3.11+ used to create backend\.venv (first run only), in this order:
rem BASE_PYTHON if set, the py launcher, python on the PATH, then the usual Anaconda / Miniconda folders.
:find_python
set "PYTHON_EXE="
if defined BASE_PYTHON call :try_python "%BASE_PYTHON%"
if defined PYTHON_EXE exit /b 0
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PYTHON_EXE call :try_python "%%P"
if defined PYTHON_EXE exit /b 0
for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYTHON_EXE call :try_python "%%P"
if defined PYTHON_EXE exit /b 0
for %%P in ("%USERPROFILE%\anaconda3\python.exe" "%USERPROFILE%\miniconda3\python.exe" "%LOCALAPPDATA%\anaconda3\python.exe" "%LOCALAPPDATA%\miniconda3\python.exe" "%ProgramData%\anaconda3\python.exe" "%ProgramData%\miniconda3\python.exe") do if not defined PYTHON_EXE call :try_python %%P
exit /b 0

:try_python
if not exist "%~1" exit /b 1
rem Skips the Microsoft Store placeholder and versions older than 3.11
"%~1" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul || exit /b 1
set "PYTHON_EXE=%~1"
exit /b 0
