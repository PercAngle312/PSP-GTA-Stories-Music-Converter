@echo off
echo Installing the audio decoder (one time only)...
python -m pip install miniaudio || py -m pip install miniaudio
echo.
echo Done. You can now double-click Start_GUI.bat
pause
