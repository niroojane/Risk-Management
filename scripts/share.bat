@echo off
rem Shared launcher used by share-binance.bat and share-yahoo.bat: a temporary public link to the web app.
rem Usage: share.bat <MARKET> <BACKEND_PORT> <FRONTEND_PORT> <SHARE_PORT> <LABEL>
rem Starts the app with launch.bat if its backend isn't running, then a second frontend on SHARE_PORT
rem that forwards /api to the backend, and a cloudflared quick tunnel to it. Anyone with the link uses your .env credentials.

setlocal
set "MARKET=%~1"
set "BACKEND_PORT=%~2"
set "FRONTEND_PORT=%~3"
set "SHARE_PORT=%~4"
set "LABEL=%~5"
set "ROOT=%~dp0.."
set "FRONTEND=%ROOT%\frontend"

call :find_cloudflared
if not defined CLOUDFLARED (
    echo cloudflared is not installed. Installing it with winget...
    winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
    call :find_cloudflared
)
if not defined CLOUDFLARED (
    echo cloudflared was not found. Install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    echo then run this file again.
    pause
    exit /b 1
)

netstat -ano | findstr /R /C:":%BACKEND_PORT% .*LISTENING" >nul
if errorlevel 1 (
    echo Starting the %LABEL% app...
    call "%~dp0launch.bat" %MARKET% %BACKEND_PORT% %FRONTEND_PORT% %LABEL% || exit /b 1
)

rem VITE_API_URL=/ makes the browser call this frontend, which forwards /api to BACKEND_URL (vite.config.ts)
set "VITE_API_URL=/"
set "BACKEND_URL=http://localhost:%BACKEND_PORT%"
start "Risk Management %LABEL% - shared frontend" /D "%FRONTEND%" cmd /k "npm.cmd run dev -- --port %SHARE_PORT% --strictPort"
timeout /t 6 /nobreak >nul

echo.
echo Your link is the https://....trycloudflare.com address printed below. It works while this window,
echo the backend and the shared frontend windows stay open. Close this window to stop sharing.
echo.
"%CLOUDFLARED%" tunnel --no-autoupdate --url http://localhost:%SHARE_PORT%
exit /b 0

rem cloudflared on the PATH, or where winget installs it (the PATH of this window isn't refreshed after an install)
:find_cloudflared
set "CLOUDFLARED="
for /f "delims=" %%P in ('where cloudflared 2^>nul') do if not defined CLOUDFLARED set "CLOUDFLARED=%%P"
if defined CLOUDFLARED exit /b 0
for %%P in ("%ProgramFiles(x86)%\cloudflared\cloudflared.exe" "%ProgramFiles%\cloudflared\cloudflared.exe") do if not defined CLOUDFLARED if exist %%P set "CLOUDFLARED=%%~P"
exit /b 0
