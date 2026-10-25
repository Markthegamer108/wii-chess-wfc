@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0WFC Modder.exe" (
  "%~dp0WFC Modder.exe" %*
) else (
  py -3 "%~dp0wfc_modder.py" %*
)
if errorlevel 1 (
  echo.
  echo WFC Modder exited with an error.
  pause
)
endlocal
