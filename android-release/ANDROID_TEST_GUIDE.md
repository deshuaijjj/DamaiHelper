# Android 版本测试指南

## 📱 给测试人员的说明

感谢你帮忙测试 DamaiHelper Android 版本！

## 🔧 测试前准备

### 1. 硬件要求
- ✅ 一部 Android 手机（已安装大麦APP并登录）
- ✅ 一根 USB 数据线
- ✅ 一台电脑（Mac 或 Windows）

### 2. 软件要求

#### Mac 用户：
```bash
# 安装 Homebrew（如果还没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 ADB
brew install android-platform-tools

# 验证安装
adb version
```

#### Windows 用户：
1. 下载 ADB 工具：https://developer.android.com/studio/releases/platform-tools
2. 解压到 `C:\adb`
3. 添加到系统环境变量 PATH
4. 打开命令提示符，输入 `adb version` 验证

### 3. 开启手机 USB 调试

**重要步骤：**

1. 进入手机设置 → 关于手机
2. 连续点击"版本号"7次（开启开发者模式）
3. 返回设置 → 开发者选项
4. 打开"USB调试"开关
5. 连接手机到电脑
6. 手机会弹出"允许USB调试"，点击"允许"（勾选"始终允许"）

**验证连接：**
```bash
adb devices
```

应该显示类似：
```
List of devices attached
XXXXXX    device
```

如果显示 `unauthorized`，请在手机上重新授权。

## 🚀 快速测试（不打包）

### 方法1：直接运行（推荐用于快速测试）

```bash
# 1. 进入项目目录
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 2. 安装 Python 依赖（只需一次）
cd backend
pip3 install -r requirements.txt

# 3. 测试 Android 连接
python3 -c "
from automation.android_driver import AndroidDriver
driver = AndroidDriver()
if driver.connect():
    print('✅ 设备连接成功')
    print('设备信息:', driver.get_device_info())
    print('大麦APP已安装:', driver.is_app_installed())
    if driver.is_app_installed():
        print('正在启动大麦APP...')
        driver.start_app()
        print('✅ 测试成功！')
else:
    print('❌ 设备连接失败')
"

# 4. 启动后端服务（新终端）
cd backend
python3 main.py

# 5. 启动前端（新终端）
cd frontend
npm install  # 只需一次
npm start

# 6. 启动 Electron（新终端）
cd electron
npm install  # 只需一次
npm start
```

## 📦 打包测试版本

### Mac 打包：

```bash
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 1. 构建前端
cd frontend
npm install
npm run build

# 2. 打包 Electron
cd ../electron
npm install
npm run build:mac

# 打包完成后，文件在：
# electron/dist/DamaiHelper-Mac-1.0.0.dmg
```

### Windows 打包：

```bash
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 1. 构建前端
cd frontend
npm install
npm run build

# 2. 打包 Electron
cd ../electron
npm install
npm run build:win

# 打包完成后，文件在：
# electron/dist/DamaiHelper-Windows-1.0.0.exe
```

## 📤 发送给朋友测试

### 打包后发送：

1. 找到打包文件：
   - Mac: `electron/dist/DamaiHelper-Mac-1.0.0.dmg`
   - Windows: `electron/dist/DamaiHelper-Windows-1.0.0.exe`

2. 上传到网盘（百度网盘、阿里云盘等）

3. 发送给朋友，附带以下说明：

```
【DamaiHelper 测试版】

安装步骤：
1. 下载安装包
2. 双击安装
3. 安装 Python 3.9+ (https://www.python.org)
4. 安装 ADB 工具（见下方链接）
5. 开启手机 USB 调试
6. 连接手机到电脑
7. 打开 DamaiHelper

详细教程：
https://github.com/yourusername/DamaiHelper/blob/main/ANDROID_TEST_GUIDE.md
```

## 🧪 测试清单

请测试人员完成以下测试项：

### 基础功能测试

- [ ] 软件能正常启动
- [ ] 界面显示正常，无乱码
- [ ] 点击"扫描设备"能识别到手机
- [ ] 设备信息显示正确（品牌、型号、系统版本）
- [ ] 点击"测试"按钮，手机能自动打开大麦APP

### 任务创建测试

- [ ] 能创建新任务
- [ ] 填写演出信息、开票时间
- [ ] 选择设备
- [ ] 任务列表正常显示

### 抢票流程测试（可选，需要真实演出）

- [ ] 任务能正常启动
- [ ] 开票前30秒自动打开APP
- [ ] 开票时自动点击购买按钮
- [ ] 实时状态更新正常
- [ ] 失败后能自动重试

## ❗ 常见问题

### 问题1：找不到设备

**解决方案：**
```bash
# 检查 ADB 是否安装
adb version

# 检查设备连接
adb devices

# 重启 ADB 服务
adb kill-server
adb start-server
adb devices
```

### 问题2：设备显示 unauthorized

**解决方案：**
- 在手机上重新点击"允许USB调试"
- 勾选"始终允许"
- 拔掉重新插入数据线

### 问题3：找不到大麦APP

**解决方案：**
```bash
# 检查大麦APP是否安装
adb shell pm list packages | grep damai

# 如果包名不同，需要修改代码中的包名
```

### 问题4：Python 依赖安装失败

**解决方案：**
```bash
# 使用国内镜像源
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题5：软件启动后端失败

**解决方案：**
```bash
# 手动测试后端
cd backend
python3 main.py

# 查看错误信息，通常是依赖未安装
pip3 install -r requirements.txt
```

## 📝 反馈信息

测试完成后，请提供以下信息：

### 系统信息
- 操作系统：Mac / Windows（版本号）
- Python 版本：`python3 --version`
- ADB 版本：`adb version`

### 手机信息
- 手机品牌和型号：
- Android 版本：
- 大麦APP版本：

### 测试结果
- 成功的功能：
- 失败的功能：
- 错误截图：
- 终端错误信息：

### 建议
- 使用体验：
- 改进建议：

## 📞 联系方式

遇到问题可以：
1. 截图错误信息发给我
2. 在 GitHub 提 Issue
3. 发送完整的终端日志

---

**感谢你的测试！🎉**

