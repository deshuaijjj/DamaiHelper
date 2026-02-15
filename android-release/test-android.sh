#!/bin/bash

# DamaiHelper 快速测试脚本
# 用于本地测试，无需打包

set -e

echo "=================================="
echo "  DamaiHelper 快速测试"
echo "=================================="
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📁 项目目录: $PROJECT_DIR"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未安装 Python3"
    echo "请访问 https://www.python.org 下载安装"
    exit 1
fi
echo "✅ Python 版本: $(python3 --version)"

# 检查 ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️  警告: 未安装 ADB"
    echo "Mac 用户: brew install android-platform-tools"
    echo "Windows 用户: 下载 https://developer.android.com/studio/releases/platform-tools"
    echo ""
    read -p "是否继续？(y/n) " continue_choice
    if [ "$continue_choice" != "y" ]; then
        exit 1
    fi
else
    echo "✅ ADB 版本: $(adb version | head -n 1)"
fi

echo ""
echo "=================================="
echo "  检查 Android 设备"
echo "=================================="

# 检查设备连接
devices=$(adb devices | grep -v "List of devices" | grep "device$" | wc -l)
if [ "$devices" -eq 0 ]; then
    echo "⚠️  未检测到 Android 设备"
    echo ""
    echo "请确保："
    echo "  1. 手机已开启 USB 调试"
    echo "  2. 手机已连接到电脑"
    echo "  3. 手机上已授权 USB 调试"
    echo ""
    read -p "是否继续？(y/n) " continue_choice
    if [ "$continue_choice" != "y" ]; then
        exit 1
    fi
else
    echo "✅ 检测到 $devices 个设备"
    adb devices
fi

echo ""
echo "=================================="
echo "  安装 Python 依赖"
echo "=================================="
cd "$PROJECT_DIR/backend"

if [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 找不到 requirements.txt"
    exit 1
fi

echo "📦 安装依赖（可能需要几分钟）..."
pip3 install -r requirements.txt -q

echo "✅ 依赖安装完成"
echo ""

echo "=================================="
echo "  测试 Android 驱动"
echo "=================================="

python3 << 'EOF'
import sys
sys.path.insert(0, '.')

try:
    from automation.android_driver import AndroidDriver
    
    print("🔍 正在连接设备...")
    driver = AndroidDriver()
    
    if driver.connect():
        print("✅ 设备连接成功！")
        print("")
        
        info = driver.get_device_info()
        print("📱 设备信息:")
        print(f"   品牌: {info.get('brand', 'Unknown')}")
        print(f"   型号: {info.get('model', 'Unknown')}")
        print(f"   系统: Android {info.get('version', 'Unknown')}")
        print(f"   分辨率: {info.get('display', 'Unknown')}")
        print("")
        
        if driver.is_app_installed():
            print("✅ 大麦APP已安装")
            print("")
            print("🚀 正在启动大麦APP...")
            if driver.start_app():
                print("✅ 大麦APP启动成功！")
                print("")
                print("🎉 测试通过！你的设备可以正常使用。")
            else:
                print("❌ 启动大麦APP失败")
                sys.exit(1)
        else:
            print("⚠️  未安装大麦APP")
            print("请在手机上安装大麦APP后重试")
            sys.exit(1)
    else:
        print("❌ 设备连接失败")
        print("")
        print("请检查:")
        print("  1. 手机是否开启USB调试")
        print("  2. 是否授权了USB调试")
        print("  3. 数据线是否正常")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "  ✅ 所有测试通过！"
    echo "=================================="
    echo ""
    echo "🎯 下一步："
    echo ""
    echo "方式1: 启动完整应用（推荐）"
    echo "   终端1: cd backend && python3 main.py"
    echo "   终端2: cd frontend && npm start"
    echo "   终端3: cd electron && npm start"
    echo ""
    echo "方式2: 打包发布"
    echo "   ./scripts/build.sh"
    echo ""
else
    echo ""
    echo "=================================="
    echo "  ❌ 测试失败"
    echo "=================================="
    echo ""
    echo "请根据上面的错误信息排查问题"
    echo "或查看测试指南: ANDROID_TEST_GUIDE.md"
    exit 1
fi

