@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==================================
echo   DamaiHelper 一键打包脚本
echo ==================================
echo.

cd /d "%~dp0.."
set PROJECT_DIR=%CD%
echo 📁 项目目录: %PROJECT_DIR%
echo.

:: 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未安装 Node.js
    echo 请访问 https://nodejs.org 下载安装
    pause
    exit /b 1
)
node --version
npm --version
echo.

:: 询问打包平台
echo 请选择打包平台：
echo 1) Mac (dmg)
echo 2) Windows (exe)
echo 3) 两者都打包
set /p platform_choice="请输入选项 (1/2/3): "

if "%platform_choice%"=="1" (
    set BUILD_MAC=true
    set BUILD_WIN=false
) else if "%platform_choice%"=="2" (
    set BUILD_MAC=false
    set BUILD_WIN=true
) else if "%platform_choice%"=="3" (
    set BUILD_MAC=true
    set BUILD_WIN=true
) else (
    echo ❌ 无效选项
    pause
    exit /b 1
)

echo.
echo ==================================
echo   步骤 1/3: 构建前端
echo ==================================
cd "%PROJECT_DIR%\frontend"

if not exist "node_modules" (
    echo 📦 安装前端依赖...
    call npm install
) else (
    echo ✅ 前端依赖已安装
)

echo 🔨 构建前端...
call npm run build

if not exist "build" (
    echo ❌ 前端构建失败
    pause
    exit /b 1
)
echo ✅ 前端构建完成
echo.

echo ==================================
echo   步骤 2/3: 准备 Electron
echo ==================================
cd "%PROJECT_DIR%\electron"

if not exist "node_modules" (
    echo 📦 安装 Electron 依赖...
    call npm install
) else (
    echo ✅ Electron 依赖已安装
)
echo.

echo ==================================
echo   步骤 3/3: 打包应用
echo ==================================

if "%BUILD_MAC%"=="true" (
    echo 🍎 打包 Mac 版本...
    call npm run build:mac
    echo ✅ Mac 版本打包完成
    echo.
)

if "%BUILD_WIN%"=="true" (
    echo 🪟 打包 Windows 版本...
    call npm run build:win
    echo ✅ Windows 版本打包完成
    echo.
)

echo ==================================
echo   ✅ 打包完成！
echo ==================================
echo.
echo 📦 打包文件位置：
echo    %PROJECT_DIR%\electron\dist\
echo.

if exist "%PROJECT_DIR%\electron\dist" (
    echo 生成的文件：
    dir /b "%PROJECT_DIR%\electron\dist\*.dmg" "%PROJECT_DIR%\electron\dist\*.exe" "%PROJECT_DIR%\electron\dist\*.zip" 2>nul
)

echo.
echo 🎉 下一步：
echo    1. 在 electron\dist\ 目录找到安装包
echo    2. 测试安装包是否正常运行
echo    3. 上传到网盘或服务器
echo    4. 发送给朋友测试
echo.
echo 📖 测试指南: %PROJECT_DIR%\ANDROID_TEST_GUIDE.md
echo.

pause

