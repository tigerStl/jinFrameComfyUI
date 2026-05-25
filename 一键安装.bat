@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "INSTALLER=%~dp0allInOneInstall\AllInOneInstall.exe"
if exist "%~dp0allInOneInstall\一键安装.exe" set "INSTALLER=%~dp0allInOneInstall\一键安装.exe"

if not exist "%INSTALLER%" (
    echo [错误] 未找到 allInOneInstall\AllInOneInstall.exe
    echo 请从发布包获取完整仓库（需包含 allInOneInstall 目录）。
    pause
    exit /b 1
)

echo 金帧 AI 视频平台 - 一键安装
echo 可从 CMD 运行；安装过程会自动调用 PowerShell（Windows 自带）。
echo.
"%INSTALLER%" %*
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
    echo.
    echo 安装未成功完成，退出码 %ERR%
)
pause
exit /b %ERR%
