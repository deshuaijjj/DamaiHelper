# DamaiHelper 使用文档

## 📋 目录
- [系统要求](#系统要求)
- [安装步骤](#安装步骤)
- [使用教程](#使用教程)
- [常见问题](#常见问题)

## 系统要求

### Mac用户
- macOS 10.15 或更高版本
- 支持iOS设备（iPhone/iPad）
- 需要安装Xcode Command Line Tools

### Windows用户
- Windows 10 或更高版本
- 支持Android设备
- 需要安装Android SDK Platform Tools

## 安装步骤

### 1. 安装依赖工具

#### Mac用户（iOS支持）

```bash
# 安装Homebrew（如果还没安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装libimobiledevice（iOS设备管理）
brew install libimobiledevice

# 安装ideviceinstaller
brew install ideviceinstaller

# 安装Python依赖
cd backend
pip3 install -r requirements.txt
```

#### Mac/Windows用户（Android支持）

```bash
# 安装ADB（Android调试桥）
# Mac:
brew install android-platform-tools

# Windows:
# 下载 Android SDK Platform Tools
# https://developer.android.com/studio/releases/platform-tools

# 安装Python依赖
cd backend
pip3 install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 安装Electron依赖

```bash
cd electron
npm install
```

## 使用教程

### 第一步：连接设备

#### Android设备
1. 在手机上开启"开发者选项"
   - 进入设置 -> 关于手机
   - 连续点击"版本号"7次
   - 返回设置，找到"开发者选项"
   
2. 开启"USB调试"
   - 进入开发者选项
   - 打开"USB调试"开关
   
3. 用数据线连接手机到电脑
   - 手机会弹出"允许USB调试"提示
   - 点击"允许"

4. 验证连接
```bash
adb devices
# 应该显示你的设备ID
```

#### iOS设备（仅Mac）
1. 用数据线连接iPhone到Mac
2. iPhone会弹出"信任此电脑"提示
3. 点击"信任"并输入密码
4. 验证连接
```bash
idevice_id -l
# 应该显示你的设备UDID
```

### 第二步：启动软件

#### 开发模式（测试用）

```bash
# 终端1：启动后端
cd backend
python3 main.py

# 终端2：启动前端
cd frontend
npm start

# 终端3：启动Electron（可选）
cd electron
npm start
```

#### 生产模式（打包后）

```bash
# 构建前端
cd frontend
npm run build

# 启动Electron
cd electron
npm start
```

### 第三步：使用软件

1. **扫描设备**
   - 打开软件
   - 点击"扫描设备"按钮
   - 等待设备自动连接

2. **创建抢票任务**
   - 点击"创建任务"按钮
   - 填写演出信息：
     - 演出名称：例如"周杰伦演唱会"
     - 演出链接：粘贴大麦详情页URL
     - 开票时间：选择准确的开票时间
     - 目标票价：选择想要的票档（可选）
     - 购买数量：1-6张
     - 选择设备：勾选要使用的设备
   - 点击"创建任务"

3. **启动任务**
   - 在任务列表中找到刚创建的任务
   - 点击"启动"按钮
   - 软件会在开票前30秒自动准备
   - 开票时自动点击购买

4. **等待结果**
   - 观察任务状态变化
   - 成功后会显示"成功"标签
   - 失败会显示"失败"标签

## 常见问题

### Q1: 扫描不到Android设备？

**解决方案：**
1. 确认USB调试已开启
2. 尝试更换数据线（有些线只能充电）
3. 运行 `adb devices` 检查连接
4. 如果显示"unauthorized"，重新在手机上点击"允许"

### Q2: 扫描不到iOS设备？

**解决方案：**
1. 确认已点击"信任此电脑"
2. 运行 `idevice_id -l` 检查连接
3. 如果没有输出，重新拔插数据线
4. 确认已安装 libimobiledevice

### Q3: 提示"大麦APP未安装"？

**解决方案：**
1. 在手机上安装大麦APP
2. 打开APP并登录账号
3. 重新扫描设备

### Q4: 抢票失败？

**可能原因：**
1. 网络延迟
2. 票已售罄
3. APP界面变化，按钮识别失败
4. 遇到验证码

**建议：**
1. 使用多个设备同时抢
2. 确保网络稳定
3. 提前测试设备连接

### Q5: iOS设备需要安装WebDriverAgent？

**解决方案：**
iOS自动化需要WebDriverAgent，这是一个复杂的过程：

1. 安装Xcode
2. 克隆WebDriverAgent项目
3. 使用Xcode打开并编译
4. 安装到iPhone

详细教程请参考：[WebDriverAgent安装指南](https://github.com/appium/WebDriverAgent)

**简化方案：**
如果觉得太复杂，建议：
- 使用Android设备（更简单）
- 或者等待我们提供一键安装脚本

### Q6: 会不会被封号？

**风险说明：**
- 使用自动化工具存在封号风险
- 建议使用小号测试
- 不要频繁使用
- 仅供个人学习研究

### Q7: 如何提高成功率？

**建议：**
1. 使用多个设备同时抢
2. 提前测试流程
3. 确保网络稳定（WiFi或4G）
4. 提前在APP中登录并完善信息
5. 选择相对冷门的场次

## 技术支持

- GitHub Issues: [提交问题](https://github.com/yourusername/DamaiHelper/issues)
- 文档更新: 持续更新中

## 免责声明

本软件仅供学习研究使用，使用本软件可能违反平台服务条款，账号风险由用户自行承担。
请勿用于商业牟利，作者不承担任何法律责任。

