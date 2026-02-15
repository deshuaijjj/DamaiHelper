# 🚀 快速开始 - Android 版本

## 一键测试（推荐）

```bash
# 进入项目目录
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 运行测试脚本
./scripts/test-android.sh
```

这个脚本会自动：
- ✅ 检查 Python 和 ADB 是否安装
- ✅ 检测 Android 设备连接
- ✅ 安装 Python 依赖
- ✅ 测试设备连接和大麦APP

## 一键打包

```bash
# 进入项目目录
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 运行打包脚本
./scripts/build.sh
```

选择要打包的平台：
- 1: Mac (dmg)
- 2: Windows (exe)
- 3: 两者都打包

打包完成后，文件在 `electron/dist/` 目录。

## 手动测试（开发模式）

### 终端1 - 启动后端
```bash
cd /Users/zhangyuxin/Desktop/DamaiHelper/backend
pip3 install -r requirements.txt  # 只需一次
python3 main.py
```

### 终端2 - 启动前端
```bash
cd /Users/zhangyuxin/Desktop/DamaiHelper/frontend
npm install  # 只需一次
npm start
```

### 终端3 - 启动 Electron
```bash
cd /Users/zhangyuxin/Desktop/DamaiHelper/electron
npm install  # 只需一次
npm start
```

## 发送给朋友测试

1. 打包应用：`./scripts/build.sh`
2. 找到安装包：`electron/dist/DamaiHelper-Mac-1.0.0.dmg`
3. 上传到网盘
4. 发送下载链接 + `ANDROID_TEST_GUIDE.md`

## 常见问题

### ADB 未安装
```bash
# Mac
brew install android-platform-tools

# Windows
# 下载: https://developer.android.com/studio/releases/platform-tools
```

### 找不到设备
```bash
# 检查设备
adb devices

# 重启 ADB
adb kill-server
adb start-server
```

### Python 依赖安装慢
```bash
# 使用国内镜像
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 详细文档

- 完整测试指南：`ANDROID_TEST_GUIDE.md`
- 使用文档：`docs/usage.md`
- 部署文档：`docs/deploy-complete.md`

