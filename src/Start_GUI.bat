@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw gta_music_gui.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw gta_music_gui.py & exit /b)
echo Python was not found. Install it from python.org (tick "Add Python to PATH"),
echo then run Install_Requirements.bat once.
pause
