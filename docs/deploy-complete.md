# DamaiHelper 完整部署流程
# 域名: deshuai.cloud
# 服务器IP: 175.178.121.104

## 📋 部署步骤总览

```
第一步：配置服务器环境（10分钟）
第二步：上传网站文件（2分钟）
第三步：配置域名解析（5分钟）
第四步：安装SSL证书（5分钟）
第五步：打包并上传软件（30分钟）
```

---

## 🚀 第一步：配置服务器环境

### 1.1 连接到服务器

**在Mac终端执行：**

```bash
ssh root@175.178.121.104
```

输入密码后继续。

---

### 1.2 一键配置脚本

**在服务器上，复制粘贴以下整段命令：**

```bash
#!/bin/bash
echo "开始配置服务器..."

# 更新系统
apt update && apt upgrade -y

# 安装Nginx
apt install nginx -y

# 启动Nginx
systemctl start nginx
systemctl enable nginx

# 配置防火墙
ufw allow 80
ufw allow 443
ufw allow 22
echo "y" | ufw enable

# 创建网站目录
mkdir -p /var/www/damaihelper/downloads

# 配置Nginx（临时使用IP）
cat > /etc/nginx/sites-available/damaihelper << 'EOF'
server {
    listen 80;
    server_name 175.178.121.104 deshuai.cloud www.deshuai.cloud;
    
    root /var/www/damaihelper;
    index index.html;
    
    # 网站主页
    location / {
        try_files $uri $uri/ =404;
    }
    
    # 下载文件
    location /downloads/ {
        alias /var/www/damaihelper/downloads/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }
    
    # 日志
    access_log /var/log/nginx/damaihelper_access.log;
    error_log /var/log/nginx/damaihelper_error.log;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# 启用站点
ln -sf /etc/nginx/sites-available/damaihelper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试配置
nginx -t

# 重启Nginx
systemctl restart nginx

# 设置权限
chown -R www-data:www-data /var/www/damaihelper
chmod -R 755 /var/www/damaihelper

echo ""
echo "✅ 服务器配置完成！"
echo "现在可以上传文件了"
```

---

## 📤 第二步：上传网站文件

### 2.1 上传HTML和CSS

**在Mac上，新开一个终端窗口：**

```bash
# 进入项目目录
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 上传网站文件
scp website/index.html root@175.178.121.104:/var/www/damaihelper/
scp website/style.css root@175.178.121.104:/var/www/damaihelper/
```

### 2.2 验证上传

**测试访问：**

在浏览器打开：`http://175.178.121.104`

应该能看到网站了！

---

## 🌐 第三步：配置域名解析

### 3.1 登录腾讯云控制台

1. 打开浏览器，访问：https://console.cloud.tencent.com/
2. 登录你的腾讯云账号

### 3.2 配置DNS解析

**步骤：**

```
1. 在控制台搜索框输入"DNS解析"
2. 点击"DNS解析 DNSPod"
3. 找到你的域名 deshuai.cloud，点击"解析"
4. 点击"添加记录"
```

**添加第一条记录：**
```
记录类型：A
主机记录：@
记录值：175.178.121.104
TTL：600
```
点击"保存"

**添加第二条记录：**
```
记录类型：A
主机记录：www
记录值：175.178.121.104
TTL：600
```
点击"保存"

### 3.3 等待DNS生效

**通常需要5-10分钟**

测试是否生效：

```bash
# 在Mac终端执行
ping deshuai.cloud
```

如果返回 `175.178.121.104`，说明解析成功！

### 3.4 测试域名访问

在浏览器打开：`http://deshuai.cloud`

应该能看到网站了！

---

## 🔒 第四步：安装SSL证书（HTTPS）

### 4.1 安装Certbot

**在服务器上执行：**

```bash
# 安装Certbot
apt install certbot python3-certbot-nginx -y
```

### 4.2 申请SSL证书

**执行以下命令（替换邮箱为你的真实邮箱）：**

```bash
certbot --nginx -d deshuai.cloud -d www.deshuai.cloud --email your@email.com --agree-tos --no-eff-email --redirect
```

**按提示操作：**
- 输入你的邮箱（用于接收证书到期提醒）
- 同意服务条款（输入 Y）
- 是否接收邮件（输入 N）
- 选择重定向HTTP到HTTPS（输入 2）

### 4.3 设置自动续期

```bash
# 测试自动续期
certbot renew --dry-run

# 添加定时任务
(crontab -l 2>/dev/null; echo "0 2 * * * certbot renew --quiet") | crontab -
```

### 4.4 测试HTTPS

在浏览器打开：`https://deshuai.cloud`

应该看到：
- ✅ 绿色小锁图标
- ✅ 网站正常显示
- ✅ HTTP自动跳转到HTTPS

---

## 📦 第五步：打包并上传软件

### 5.1 打包Mac版本

**在Mac上执行：**

```bash
# 进入项目目录
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 构建前端
cd frontend
npm install
npm run build

# 打包Electron
cd ../electron
npm install
npm install electron-builder --save-dev

# 修改package.json添加打包配置
cat > package.json << 'EOF'
{
  "name": "damai-helper-electron",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "dependencies": {
    "electron": "^27.0.0"
  },
  "devDependencies": {
    "electron-builder": "^24.6.4"
  },
  "build": {
    "appId": "com.damaihelper.app",
    "productName": "DamaiHelper",
    "directories": {
      "output": "dist"
    },
    "files": [
      "**/*",
      "../frontend/build/**/*",
      "../backend/**/*"
    ],
    "mac": {
      "category": "public.app-category.utilities",
      "target": ["dmg"],
      "icon": "icon.png"
    },
    "dmg": {
      "title": "DamaiHelper",
      "icon": "icon.png"
    }
  }
}
EOF

# 开始打包
npm run build

# 打包完成后，文件在：
# electron/dist/DamaiHelper-1.0.0.dmg
```

### 5.2 上传软件到服务器

```bash
# 在Mac上执行
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 上传Mac版本
scp electron/dist/DamaiHelper-1.0.0.dmg root@175.178.121.104:/var/www/damaihelper/downloads/DamaiHelper-Mac-v1.0.0.dmg

# 如果有Windows版本也上传
# scp electron/dist/DamaiHelper-Setup-1.0.0.exe root@175.178.121.104:/var/www/damaihelper/downloads/DamaiHelper-Windows-v1.0.0.exe
```

### 5.3 验证下载

访问：`https://deshuai.cloud`

点击"下载 Mac 版本"按钮，应该能下载文件！

---

## ✅ 完整检查清单

部署完成后，逐项检查：

- [ ] 访问 https://deshuai.cloud 能看到网站
- [ ] 有绿色小锁图标（HTTPS）
- [ ] HTTP自动跳转到HTTPS
- [ ] 网站样式正常显示
- [ ] 导航链接可以点击
- [ ] 页面滚动流畅
- [ ] 点击"下载 Mac 版本"能下载文件
- [ ] 手机访问正常
- [ ] www.deshuai.cloud 也能访问

---

## 🔧 常用维护命令

### 查看网站状态
```bash
# 连接服务器
ssh root@175.178.121.104

# 查看Nginx状态
systemctl status nginx

# 查看访问日志
tail -f /var/log/nginx/damaihelper_access.log

# 查看错误日志
tail -f /var/log/nginx/damaihelper_error.log
```

### 更新网站
```bash
# 在Mac上
cd /Users/zhangyuxin/Desktop/DamaiHelper
scp website/index.html root@175.178.121.104:/var/www/damaihelper/
scp website/style.css root@175.178.121.104:/var/www/damaihelper/
```

### 更新软件
```bash
# 在Mac上
cd /Users/zhangyuxin/Desktop/DamaiHelper
scp electron/dist/新版本.dmg root@175.178.121.104:/var/www/damaihelper/downloads/
```

### 重启服务
```bash
# 在服务器上
systemctl restart nginx
```

### 查看证书状态
```bash
# 在服务器上
certbot certificates
```

---

## 🆘 故障排查

### 问题1：域名无法访问

**检查DNS解析：**
```bash
# 在Mac上
ping deshuai.cloud
nslookup deshuai.cloud
```

如果没有返回 `175.178.121.104`，等待DNS生效（最多24小时）

**检查Nginx：**
```bash
# 在服务器上
systemctl status nginx
nginx -t
```

### 问题2：SSL证书申请失败

**原因：**
- DNS还没生效
- 80端口没开放
- Nginx配置错误

**解决：**
```bash
# 检查DNS
ping deshuai.cloud

# 检查端口
ufw status

# 检查Nginx配置
nginx -t
```

### 问题3：下载404

**检查文件是否存在：**
```bash
# 在服务器上
ls -lh /var/www/damaihelper/downloads/
```

**检查权限：**
```bash
# 在服务器上
chown -R www-data:www-data /var/www/damaihelper
chmod -R 755 /var/www/damaihelper
```

### 问题4：样式不显示

**检查文件：**
```bash
# 在服务器上
ls -lh /var/www/damaihelper/
```

应该有：
- index.html
- style.css

**清除浏览器缓存：**
- Mac: Cmd + Shift + R
- Windows: Ctrl + Shift + R

---

## 📊 部署时间估算

```
第一步：配置服务器     10分钟
第二步：上传网站文件    2分钟
第三步：配置域名解析    5分钟（等待生效10分钟）
第四步：安装SSL证书     5分钟
第五步：打包上传软件    30分钟
-----------------------------------
总计：约 1小时
```

---

## 🎉 完成后的效果

**用户访问流程：**

1. 用户在浏览器输入：`deshuai.cloud`
2. 自动跳转到：`https://deshuai.cloud`
3. 看到漂亮的网站
4. 点击"下载 Mac 版本"
5. 下载 `DamaiHelper-Mac-v1.0.0.dmg`
6. 双击安装
7. 开始使用！

---

## 📝 下一步优化

1. **添加备案号**
   - 在网站底部显示备案号
   - 链接到工信部网站

2. **添加统计**
   - 接入百度统计或Google Analytics
   - 了解访问量和用户行为

3. **添加CDN**
   - 使用腾讯云CDN加速
   - 提升访问速度

4. **添加监控**
   - 设置网站监控
   - 及时发现问题

---

## 🚀 现在开始部署！

按照上面的步骤，一步一步执行。

**第一步：连接服务器**
```bash
ssh root@175.178.121.104
```

然后复制"第一步"的配置脚本执行。

有任何问题随时告诉我！💪

