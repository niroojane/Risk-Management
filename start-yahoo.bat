@echo off
rem Multi-asset version (Yahoo Finance prices, ETF Excel portfolio on GitHub): backend on port 8001, app on http://localhost:5174
rem Both versions can run side by side; each keeps its own workspace in the browser.
call "%~dp0scripts\launch.bat" multi_asset 8001 5174 Yahoo
