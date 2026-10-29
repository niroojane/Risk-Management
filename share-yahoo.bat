@echo off
rem Temporary public link to the multi-asset version (Yahoo Finance): starts it if needed, shared frontend on port 5175
call "%~dp0scripts\share.bat" multi_asset 8001 5174 5175 Yahoo
