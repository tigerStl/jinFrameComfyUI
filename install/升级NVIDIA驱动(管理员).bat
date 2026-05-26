@echo off
chcp 65001 >nul
title JinFrame - NVIDIA Driver (Admin)
cd /d "%~dp0\.."
echo.
echo JinFrame: install latest GeForce driver (580+ for RTX 3050 / cu130)
echo UAC will ask for Administrator - click Yes
echo Install uses -n (no reboot until you choose to restart)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_nvidia_driver.ps1" -RepoRoot "%CD%" -MinVersion 580.0 -TryElevate -NoElevate
set ERR=%ERRORLEVEL%
echo.
if %ERR% equ 0 (
  echo Driver step done. Finish other install tasks, then REBOOT when prompted.
) else (
  echo Failed exit %ERR%. Download from https://www.nvidia.com/Download/index.aspx
)
echo.
pause
exit /b %ERR%
