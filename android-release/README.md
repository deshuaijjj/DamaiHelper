# 📱 DamaiHelper Android 测试包

这是一个独立的测试包，解压后即可使用，无需其他配置。

## 📦 包含内容

```
android-release/
├── backend/              # Python 后端代码
├── frontend/             # React 前端代码
├── electron/             # Electron 桌面应用
├── build.sh              # Mac/Linux 打包脚本
├── build.bat             # Windows 打包脚本
├── test-android.sh       # Mac/Linux 测试脚本
├── test-android.bat      # Windows 测试脚本
├── QUICKSTART-ANDROID.md # 快速开始指南
├── ANDROID_TEST_GUIDE.md # 完整测试指南
└── README.md             # 本文件
```

## 🚀 快速开始

### Mac 用户

#### 1. 快速测试（推荐）
```bash
# 打开终端，进入解压后的文件夹
cd android-release

# 运行测试脚本
./test-android.sh
```

#### 2. 打包应用
```bash
# 打包成 .dmg 安装包
./build.sh
```

### Windows 用户

#### 1. 快速测试（推荐）
```cmd
# 打开命令提示符，进入解压后的文件夹
cd android-release

# 运行测试脚本
test-android.bat
```

#### 2. 打包应用
```cmd
# 打包成 .exe 安装包
build.bat
```

## ⚙️ 测试前准备

### 1. 安装必要软件

#### Python 3.9+
- Mac: `brew install python3` 或访问 https://www.python.org
- Windows: 访问 https://www.python.org 下载安装

#### ADB 工具
- Mac: `brew install android-platform-tools`
- Windows: 下载 https://developer.android.com/studio/releases/platform-tools

#### Node.js（仅打包时需要）
- 访问 https://nodejs.org 下载安装

### 2. 准备 Android 手机

1. 进入手机设置 → 关于手机
2. 连续点击"版本号"7次（开启开发者模式）
3. 返回设置 → 开发者选项
4. 打开"USB调试"开关
5. 用数据线连接手机到电脑
6. 手机弹出"允许USB调试"，点击"允许"（勾选"始终允许"）

### 3. 验证连接

```bash
# 检查设备是否连接
adb devices

# 应该显示类似：
# List of devices attached
# XXXXXX    device
```

## 📖 详细文档

- **快速问题排查**: 查看 `QUICKSTART-ANDROID.md`
- **完整测试指南**: 查看 `ANDROID_TEST_GUIDE.md`（给测试人员）

## 🎯 测试流程

### 方式1：快速测试（不打包）

运行测试脚本会自动：
1. ✅ 检查 Python 和 ADB 是否安装
2. ✅ 检测 Android 设备连接
3. ✅ 安装 Python 依赖
4. ✅ 测试设备连接和大麦APP
5. ✅ 自动启动大麦APP验证

### 方式2：完整测试（打包后）

1. 运行打包脚本生成安装包
2. 安装包位置：`electron/dist/`
3. 双击安装包安装
4. 打开应用测试完整功能

## 📦 打包后的文件

打包完成后，在 `electron/dist/` 目录会生成：

- **Mac**: `DamaiHelper-Mac-1.0.0.dmg`
- **Windows**: `DamaiHelper-Windows-1.0.0.exe`

## ✅ 测试清单

请测试以下功能：

### 基础功能
- [ ] 软件能正常启动
- [ ] 界面显示正常
- [ ] 点击"扫描设备"能识别手机
- [ ] 设备信息显示正确
- [ ] 点击"测试"按钮，手机自动打开大麦APP

### 任务功能
- [ ] 能创建新任务
- [ ] 填写演出信息
- [ ] 选择设备
- [ ] 任务列表正常显示

## ❗ 常见问题

### 问题1：找不到设备
```bash
# 重启 ADB
adb kill-server
adb start-server
adb devices
```

### 问题2：设备显示 unauthorized
- 在手机上重新点击"允许USB调试"
- 勾选"始终允许"

### 问题3：找不到大麦APP
- 确认手机已安装大麦APP
- 检查包名：`adb shell pm list packages | grep damai`

### 问题4：Python 依赖安装慢
```bash
# 使用国内镜像
cd backend
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 📝 反馈信息

测试完成后，请提供：

### 系统信息
- 操作系统：Mac / Windows（版本）
- Python 版本：`python3 --version`
- ADB 版本：`adb version`

### 手机信息
- 手机品牌和型号
- Android 版本
- 大麦APP版本

### 测试结果
- 成功的功能
- 失败的功能
- 错误截图
- 终端错误信息

## 🎉 开始测试

1. 确保已安装 Python 和 ADB
2. 手机开启 USB 调试并连接
3. 运行测试脚本：`./test-android.sh` (Mac) 或 `test-android.bat` (Windows)
4. 看到"测试通过"即可开始使用

---

**祝测试顺利！有问题随时反馈。**
