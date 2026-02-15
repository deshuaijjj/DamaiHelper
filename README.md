<div align="center">

# 🎫 DamaiHelper

**公平抢票助手 - 让技术为每个人服务**

[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)]()

[官方网站](https://deshuai.cloud) • [使用教程](https://deshuai.cloud/guide.html) • [问题反馈](https://github.com/deshuaijjj/DamaiHelper/issues)

</div>

---

##  项目简介

DamaiHelper 是一款**完全免费、开源透明**的大麦抢票助手。在演出票务市场，专业黄牛团队利用技术优势垄断票源，普通用户几乎没有机会。我们的使命是**打破技术壁垒，对抗黄牛垄断**，让每个人都有平等的机会。

###  核心特性

-  **智能自动化** - 毫秒级响应速度，比手动快 10 倍
-  **多设备支持** - 同时控制多部手机，大幅提高成功率
-  **精准时间同步** - NTP 协议同步，精确到毫秒级
-  **智能重试机制** - 失败自动重试，不放过任何机会
-  **安全可靠** - 完全开源，代码透明可审计
-  **自动更新** - 云端配置自动同步，持续适配 APP 版本
-  **永久免费** - 无广告、无收费、无数据收集

### 🎯 支持平台

| 平台 | 状态 | 说明 |
|------|------|------|
| **Android** |  完全支持 | 推荐使用，配置简单 |
| **iOS** |  开发中 | 需要复杂配置，暂不推荐 |

---

##  快速开始

### 系统要求

- **电脑**：macOS 10.15+ 或 Windows 10+
- **手机**：Android 5.0+ （推荐）
- **其他**：USB 数据线、大麦 APP

### 方式一：下载安装包（推荐）

1. 访问 [官方网站](https://deshuai.cloud) 下载对应平台的安装包
2. 安装并打开 DamaiHelper
3. 按照 [使用教程](https://deshuai.cloud/guide.html) 操作

### 方式二：源码运行

```bash
# 1. 克隆项目
git clone https://github.com/deshuaijjj/DamaiHelper.git
cd DamaiHelper

# 2. 快速测试（Android）
cd android-release
./test-android.sh        # Mac/Linux
# 或
test-android.bat         # Windows

# 3. 打包应用
./build.sh               # Mac/Linux
# 或
build.bat                # Windows
```

---

##  详细文档

-  [Android 快速开始](android-release/QUICKSTART-ANDROID.md) - 5 分钟上手
-  [Android 测试指南](android-release/ANDROID_TEST_GUIDE.md) - 完整测试流程
-  [使用文档](docs/usage.md) - 详细功能说明
-  [部署文档](docs/deploy-complete.md) - 服务器部署指南

---

## 🛠️ 技术架构

### 技术栈

```
前端：Electron + React
后端：Python + FastAPI
Android：uiautomator2
iOS：WebDriverAgent（开发中）
```

### 项目结构

```
DamaiHelper/
├── backend/              # Python 后端服务
│   ├── automation/       # 自动化核心逻辑
│   │   ├── android_driver.py    # Android 设备控制
│   │   └── ios_driver.py        # iOS 设备控制
│   ├── core/             # 核心功能模块
│   │   ├── device_manager.py    # 设备管理
│   │   └── scheduler.py         # 任务调度
│   ├── main.py           # 后端入口
│   └── requirements.txt  # Python 依赖
│
├── frontend/             # React 前端界面
│   ├── src/
│   │   ├── App.js        # 主应用组件
│   │   └── App.css       # 样式文件
│   └── package.json      # 前端依赖
│
├── electron/             # Electron 主进程
│   ├── main.js           # Electron 入口
│   ├── preload.js        # 预加载脚本
│   └── package.json      # Electron 依赖
│
├── android-release/      # Android 版本工具
│   ├── test-android.sh   # 一键测试脚本
│   └── build.sh          # 一键打包脚本
│
├── scripts/              # 工具脚本
│   ├── build.sh          # 打包脚本
│   └── deploy.sh         # 部署脚本
│
├── website/              # 官方网站
│   ├── index.html        # 首页
│   ├── guide.html        # 使用教程
│   └── style.css         # 样式文件
│
└── docs/                 # 文档目录
    ├── usage.md          # 使用文档
    └── deploy-complete.md # 部署文档
```

### 核心依赖

**Python 后端：**
- `fastapi` - 高性能 Web 框架
- `uiautomator2` - Android 自动化
- `facebook-wda` - iOS 自动化（开发中）
- `opencv-python` - 图像识别
- `websockets` - 实时通信

**前端界面：**
- `electron` - 跨平台桌面应用
- `react` - UI 框架
- `electron-builder` - 应用打包

---

##  工作原理

### 自动化流程

```
1. 设备连接
   └─> USB 连接手机，ADB 自动识别设备

2. 时间同步
   └─> NTP 协议同步，精确到毫秒级

3. 提前准备（开票前 30 秒）
   └─> 自动打开 APP，进入购买页面，定位按钮

4. 精准执行（开票瞬间）
   └─> 自动点击购买，选择票档和数量

5. 智能重试
   └─> 失败立即重试，多设备并发操作
```

### 技术亮点

- **多重定位策略**：文本识别 + 坐标定位 + 图像识别，确保准确性
- **智能等待机制**：动态检测页面加载状态，避免操作失败
- **并发控制**：多设备异步操作，互不干扰
- **日志追踪**：详细记录每一步操作，便于问题排查

---

##  开发指南

### 环境准备

```bash
# 1. 安装 Python 3.9+
python3 --version

# 2. 安装 Node.js 16+
node --version

# 3. 安装 Android SDK（Android 开发）
brew install android-platform-tools  # Mac
# 或从官网下载：https://developer.android.com/studio/releases/platform-tools

# 4. 安装 Xcode（iOS 开发，仅 Mac）
xcode-select --install
```

### 本地开发

```bash
# 终端 1 - 启动后端
cd backend
pip3 install -r requirements.txt
python3 main.py
# 后端运行在 http://localhost:8000

# 终端 2 - 启动前端
cd frontend
npm install
npm start
# 前端运行在 http://localhost:3000

# 终端 3 - 启动 Electron
cd electron
npm install
npm start
```

### 打包发布

```bash
# 进入 Android 版本目录
cd android-release

# 运行打包脚本
./build.sh               # Mac/Linux
# 或
build.bat                # Windows

# 选择平台
# 1: Mac (dmg)
# 2: Windows (exe)
# 3: 两者都打包

# 打包完成后，文件在 electron/dist/ 目录
```

### 测试流程

```bash
# 1. 连接 Android 设备
adb devices

# 2. 运行测试脚本
cd android-release
./test-android.sh        # Mac/Linux
# 或
test-android.bat         # Windows

# 3. 查看测试结果
# 脚本会自动检测设备、安装依赖、测试连接
```

---

## 📱 使用说明

### 第一步：准备工作

-  一台电脑（Mac 或 Windows）
-  一部 Android 手机（已安装大麦 APP）
-  一根 USB 数据线
-  开启手机的"USB 调试"模式

### 第二步：连接设备

```bash
# Android 用户
1. 设置 → 关于手机 → 连续点击"版本号"7次
2. 设置 → 开发者选项 → 开启"USB 调试"
3. 用数据线连接手机到电脑
4. 手机弹出提示，点击"允许 USB 调试"
```

### 第三步：配置任务

1. 填写演出名称
2. 粘贴演出链接（从大麦 APP 分享获取）
3. 设置开票时间（精确到秒）
4. 选择票档和数量
5. 勾选要使用的设备

### 第四步：开始抢票

1. 点击"启动任务"
2. 软件会在开票前 30 秒自动准备
3. 开票瞬间自动执行
4. 抢到票后立即通知

详细教程请访问：[https://deshuai.cloud/guide.html](https://deshuai.cloud/guide.html)

---

##  常见问题

<details>
<summary><b>Q: 软件识别不到我的手机怎么办？</b></summary>

**A:** 请检查：
- 数据线是否支持数据传输（不是只能充电的线）
- Android 是否开启了"USB 调试"
- 尝试更换 USB 接口或重新插拔数据线
- 运行 `adb devices` 检查设备连接状态

</details>

<details>
<summary><b>Q: 抢票成功率有多高？</b></summary>

**A:** 成功率取决于多个因素：
- 票量多少（票越多成功率越高）
- 网络速度（建议使用有线网络）
- 设备数量（多设备并发提高成功率）
- 竞争激烈程度（热门演出竞争更激烈）

建议使用多个设备同时抢票，可以大幅提高成功率。

</details>

<details>
<summary><b>Q: 会不会被封号？</b></summary>

**A:** 存在一定风险：
- 使用自动化工具可能违反平台服务条款
- 建议使用小号测试
- 不要频繁使用
- 仅用于个人购票，不要商业化

</details>

<details>
<summary><b>Q: iOS 版本什么时候发布？</b></summary>

**A:** iOS 版本正在开发中，但由于苹果的安全限制，配置过程较为复杂：
- 需要安装 Xcode（约 12GB）
- 需要配置 WebDriverAgent 并签名
- 免费账号每 7 天需重新签名

目前强烈推荐使用 **Android 版本**，安装简单，功能完整。

</details>

<details>
<summary><b>Q: 软件收费吗？</b></summary>

**A:** 完全免费：
-  软件永久免费使用
-  无任何隐藏收费
-  无广告，无数据收集
-  完全开源，代码透明

</details>

更多问题请访问：[GitHub Issues](https://github.com/deshuaijjj/DamaiHelper/issues)

---

##  贡献指南

我们欢迎任何形式的贡献！

### 如何贡献

1. **Fork** 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 **Pull Request**

### 贡献方向

-  报告 Bug
-  提出新功能建议
-  改进文档
-  提交代码修复
-  翻译文档

---

## ⚠️ 免责声明

1. **本软件仅供学习研究使用**，使用本软件可能违反平台服务条款
2. **账号风险由用户自行承担**，建议使用小号测试
3. **请勿用于商业牟利**，作者不承担任何法律责任
4. **使用本软件即表示同意**以上条款

---

## 📄 开源协议

本项目采用 [GPL-3.0 License](LICENSE) 开源协议。

这意味着：
-  可以自由使用、修改、分发
-  必须开源衍生作品
-  必须保留原作者版权信息
-  不提供任何担保

---

##  Star History

如果这个项目对你有帮助，请给我们一个 ⭐️ Star！

[![Star History Chart](https://api.star-history.com/svg?repos=deshuaijjj/DamaiHelper&type=Date)](https://star-history.com/#deshuaijjj/DamaiHelper&Date)

---

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和使用者！

特别感谢以下开源项目：
- [uiautomator2](https://github.com/openatx/uiautomator2) - Android 自动化框架
- [Electron](https://www.electronjs.org/) - 跨平台桌面应用框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [React](https://reactjs.org/) - 用户界面库

---

## 📞 联系方式

-  官方网站：[https://deshuai.cloud](https://deshuai.cloud)
-  使用教程：[https://deshuai.cloud/guide.html](https://deshuai.cloud/guide.html)
-  问题反馈：[GitHub Issues](https://github.com/deshuaijjj/DamaiHelper/issues)

---

<div align="center">

**让技术为每个人服务，而不是成为少数人牟利的工具**

Made with ❤️ by DamaiHelper Team

</div>
