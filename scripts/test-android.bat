@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==================================
echo   DamaiHelper 快速测试 (Windows)
echo ==================================
echo.

cd /d "%~dp0.."
set PROJECT_DIR=%CD%
echo 📁 项目目录: %PROJECT_DIR%
echo.

:: 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 错误: 未安装 Python
    echo 请访问 https://www.python.org 下载安装
    pause
    exit /b 1
)
python --version
echo.

:: 检查 ADB
where adb >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  警告: 未安装 ADB
    echo 请下载: https://developer.android.com/studio/releases/platform-tools
    echo.
    set /p continue="是否继续？(y/n): "
    if /i not "!continue!"=="y" exit /b 1
) else (
    adb version | findstr "Android"
)
echo.

echo ==================================
echo   检查 Android 设备
echo ==================================
adb devices
echo.

echo ==================================
echo   安装 Python 依赖
echo ==================================
cd "%PROJECT_DIR%\backend"
echo 📦 安装依赖（可能需要几分钟）...
python -m pip install -r requirements.txt -q
echo ✅ 依赖安装完成
echo.

echo ==================================
echo   测试 Android 驱动
echo ==================================
python -c "import sys; sys.path.insert(0, '.'); from automation.android_driver import AndroidDriver; driver = AndroidDriver(); print('🔍 正在连接设备...'); result = driver.connect(); print('✅ 设备连接成功！' if result else '❌ 设备连接失败'); info = driver.get_device_info() if result else {}; print(f'\n📱 设备信息:\n   品牌: {info.get(\"brand\", \"Unknown\")}\n   型号: {info.get(\"model\", \"Unknown\")}\n   系统: Android {info.get(\"version\", \"Unknown\")}') if result else None; print(f'\n✅ 大麦APP已安装' if result and driver.is_app_installed() else '\n⚠️  未安装大麦APP') if result else None; driver.start_app() if result and driver.is_app_installed() else None; print('\n🎉 测试通过！') if result and driver.is_app_installed() else None"

if %errorlevel% equ 0 (
    echo.
    echo ==================================
    echo   ✅ 所有测试通过！
    echo ==================================
    echo.
    echo 🎯 下一步：
    echo.
    echo 方式1: 启动完整应用
    echo    终端1: cd backend ^&^& python main.py
    echo    终端2: cd frontend ^&^& npm start
    echo    终端3: cd electron ^&^& npm start
    echo.
    echo 方式2: 打包发布
    echo    scripts\build.bat
    echo.
) else (
    echo.
    echo ==================================
    echo   ❌ 测试失败
    echo ==================================
    echo.
    echo 请根据上面的错误信息排查问题
    echo 或查看测试指南: ANDROID_TEST_GUIDE.md
)

pause

