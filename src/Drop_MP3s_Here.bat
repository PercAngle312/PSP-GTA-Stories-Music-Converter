@echo off
REM Drag one or more MP3s (or a folder of them) onto this file.
REM Edit the two lines below to write straight to your PSP Memory Stick.
REM Example:  set PSPDRIVE=E:     set GAMEID=ULUS10041
set PSPDRIVE=
set GAMEID=

cd /d "%~dp0"
if "%~1"=="" (
  echo Drag your MP3 files or a music folder onto this file.
  pause
  exit /b
)
if "%PSPDRIVE%"=="" (
  python mp3_to_gta.py %* --out "%~dp0gta_output"
) else (
  python mp3_to_gta.py %* --psp %PSPDRIVE% --game %GAMEID%
)
echo.
pause
