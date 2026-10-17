@echo off
rem Crypto version (Binance prices and account): backend on port 8000, app on http://localhost:5173
call "%~dp0scripts\launch.bat" crypto 8000 5173 Binance
