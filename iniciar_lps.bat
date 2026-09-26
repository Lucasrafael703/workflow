@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "URL=http://127.0.0.1:8000/"

start "LPS - Servidor" /min "%PYTHON%" manage.py runserver 127.0.0.1:8000

timeout /t 3 /nobreak >nul

set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if exist "%CHROME%" (
    start "" "%CHROME%" --new-window "%URL%"
) else (
    start "" "%URL%"
)

endlocal
