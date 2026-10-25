@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0patches\wii_chess_europe.ips" (
  echo Required patches\wii_chess_europe.ips is missing.
  echo This file is not included. See patches\README.md.
  pause
  exit /b 1
)
py -3 -m PyInstaller --noconfirm --clean --onefile --console --name WFC-Modder --add-data "%~dp0patches\wii_chess_europe.ips;patches" "%~dp0wfc_modder.py"
if errorlevel 1 (
  echo.
  echo Build failed. Install PyInstaller with: py -3 -m pip install pyinstaller
  pause
  exit /b 1
)
copy /y "%~dp0dist\WFC-Modder.exe" "%~dp0WFC Modder.exe" >nul
if errorlevel 1 (
  echo.
  echo Build succeeded, but copying the executable to the project folder failed.
  pause
  exit /b 1
)
echo.
echo Built: WFC Modder.exe
pause
endlocal
