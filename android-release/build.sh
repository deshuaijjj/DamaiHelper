#!/bin/bash

# DamaiHelper 一键打包脚本
# 用于快速打包 Mac 和 Windows 版本

set -e  # 遇到错误立即退出

echo "=================================="
echo "  DamaiHelper 一键打包脚本"
echo "=================================="
echo ""

# 获取项目根目录（当前目录）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "📁 项目目录: $PROJECT_DIR"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未安装 Node.js"
    echo "请访问 https://nodejs.org 下载安装"
    exit 1
fi
echo "✅ Node.js 版本: $(node --version)"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 未安装 npm"
    exit 1
fi
echo "✅ npm 版本: $(npm --version)"
echo ""

# 询问打包平台
echo "请选择打包平台："
echo "1) Mac (dmg)"
echo "2) Windows (exe)"
echo "3) 两者都打包"
read -p "请输入选项 (1/2/3): " platform_choice

case $platform_choice in
    1)
        BUILD_MAC=true
        BUILD_WIN=false
        ;;
    2)
        BUILD_MAC=false
        BUILD_WIN=true
        ;;
    3)
        BUILD_MAC=true
        BUILD_WIN=true
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "=================================="
echo "  步骤 1/3: 构建前端"
echo "=================================="
cd "$PROJECT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
else
    echo "✅ 前端依赖已安装"
fi

echo "🔨 构建前端..."
npm run build

if [ ! -d "build" ]; then
    echo "❌ 前端构建失败"
    exit 1
fi
echo "✅ 前端构建完成"
echo ""

echo "=================================="
echo "  步骤 2/3: 准备 Electron"
echo "=================================="
cd "$PROJECT_DIR/electron"

if [ ! -d "node_modules" ]; then
    echo "📦 安装 Electron 依赖..."
    npm install
else
    echo "✅ Electron 依赖已安装"
fi
echo ""

echo "=================================="
echo "  步骤 3/3: 打包应用"
echo "=================================="

if [ "$BUILD_MAC" = true ]; then
    echo "🍎 打包 Mac 版本..."
    npm run build:mac
    echo "✅ Mac 版本打包完成"
    echo ""
fi

if [ "$BUILD_WIN" = true ]; then
    echo "🪟 打包 Windows 版本..."
    npm run build:win
    echo "✅ Windows 版本打包完成"
    echo ""
fi

echo "=================================="
echo "  ✅ 打包完成！"
echo "=================================="
echo ""
echo "📦 打包文件位置："
echo "   $PROJECT_DIR/electron/dist/"
echo ""

# 列出打包文件
if [ -d "$PROJECT_DIR/electron/dist" ]; then
    echo "生成的文件："
    ls -lh "$PROJECT_DIR/electron/dist/" | grep -E '\.(dmg|exe|zip)$' || echo "   (未找到打包文件)"
fi

echo ""
echo "🎉 下一步："
echo "   1. 在 electron/dist/ 目录找到安装包"
echo "   2. 测试安装包是否正常运行"
echo "   3. 上传到网盘或服务器"
echo "   4. 发送给朋友测试"
echo ""
echo "📖 测试指南: $PROJECT_DIR/ANDROID_TEST_GUIDE.md"
echo ""

