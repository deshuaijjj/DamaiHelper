# 服务器部署操作手册
# 服务器IP: 175.178.121.104

## 📋 完整操作流程

### 第一步：连接到服务器

```bash
# 在你的Mac终端执行
ssh root@175.178.121.104

# 输入密码（腾讯云发到你邮箱的）
```

---

### 第二步：安装Nginx和配置环境

**在服务器上执行以下命令：**

```bash
# 1. 更新系统
apt update && apt upgrade -y

# 2. 安装Nginx
apt install nginx -y

# 3. 启动Nginx
systemctl start nginx
systemctl enable nginx

# 4. 配置防火墙
ufw allow 80
ufw allow 443
ufw allow 22
ufw --force enable

# 5. 创建网站目录
mkdir -p /var/www/damaihelper/downloads

# 6. 设置权限
chown -R www-data:www-data /var/www/damaihelper
chmod -R 755 /var/www/damaihelper
```

---

### 第三步：配置Nginx（使用IP访问）

**在服务器上执行：**

```bash
# 创建Nginx配置文件
cat > /etc/nginx/sites-available/damaihelper << 'EOF'
server {
    listen 80;
    server_name 175.178.121.104;
    
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
```

---

### 第四步：上传文件到服务器

**在你的Mac上，新开一个终端窗口：**

```bash
# 进入项目目录
cd /Users/zhangyuxin/Desktop/DamaiHelper

# 1. 上传网站文件
scp website/index.html root@175.178.121.104:/var/www/damaihelper/
scp website/style.css root@175.178.121.104:/var/www/damaihelper/

# 2. 上传软件安装包（如果已经打包好）
# Mac版本
scp electron/dist/DamaiHelper-Mac-v1.0.0.dmg root@175.178.121.104:/var/www/damaihelper/downloads/

# Windows版本（如果有）
scp electron/dist/DamaiHelper-Windows-v1.0.0.exe root@175.178.121.104:/var/www/damaihelper/downloads/

# 如果文件名不同，可以先查看
ls electron/dist/
```

---

### 第五步：验证部署

**在浏览器访问：**

```
http://175.178.121.104
```

你应该看到新设计的苹果风格网站！

---

## 🎯 域名备案通过后的操作

### 当域名备案通过后，执行以下步骤：

**1. 配置域名解析（在腾讯云控制台）**

```
进入"域名管理" → 点击你的域名 → "解析"

添加两条记录：
记录1:
  - 记录类型: A
  - 主机记录: @
  - 记录值: 175.178.121.104
  - TTL: 600

记录2:
  - 记录类型: A
  - 主机记录: www
  - 记录值: 175.178.121.104
  - TTL: 600
```

**2. 更新Nginx配置（在服务器上）**

```bash
# 假设你的域名是 damaihelper.com，替换成你的实际域名
DOMAIN="你的域名.com"

# 更新Nginx配置
cat > /etc/nginx/sites-available/damaihelper << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN 175.178.121.104;
    
    root /var/www/damaihelper;
    index index.html;
    
    location / {
        try_files \$uri \$uri/ =404;
    }
    
    location /downloads/ {
        alias /var/www/damaihelper/downloads/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }
    
    access_log /var/log/nginx/damaihelper_access.log;
    error_log /var/log/nginx/damaihelper_error.log;
    
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# 重启Nginx
nginx -t
systemctl restart nginx
```

**3. 安装SSL证书**

```bash
# 安装Certbot
apt install certbot python3-certbot-nginx -y

# 申请证书（替换成你的域名和邮箱）
certbot --nginx -d 你的域名.com -d www.你的域名.com --email 你的邮箱@example.com --agree-tos --no-eff-email --redirect

# 设置自动续期
(crontab -l 2>/dev/null; echo "0 2 * * * certbot renew --quiet") | crontab -
```

**4. 访问HTTPS网站**

```
https://你的域名.com
```

---

## 🔧 常用命令

### 查看网站状态
```bash
# 查看Nginx状态
systemctl status nginx

# 查看访问日志
tail -f /var/log/nginx/damaihelper_access.log

# 查看错误日志
tail -f /var/log/nginx/damaihelper_error.log
```

### 重启服务
```bash
# 重启Nginx
systemctl restart nginx

# 重新加载配置（不中断服务）
systemctl reload nginx
```

### 查看文件
```bash
# 查看网站文件
ls -lh /var/www/damaihelper/

# 查看下载文件
ls -lh /var/www/damaihelper/downloads/
```

### 更新网站
```bash
# 在Mac上重新上传
scp website/index.html root@175.178.121.104:/var/www/damaihelper/
```

---

## 📱 测试清单

部署完成后，请测试：

- [ ] 访问 http://175.178.121.104 能看到网站
- [ ] 网站样式正常显示
- [ ] 导航链接可以点击
- [ ] 下载按钮可以点击（即使文件不存在也会有反应）
- [ ] 手机访问正常
- [ ] 页面滚动流畅

---

## ⚠️ 注意事项

1. **现在使用IP访问**
   - 临时地址：http://175.178.121.104
   - 可以分享给朋友测试
   - 但不够专业

2. **域名备案通过后**
   - 按照上面"域名备案通过后的操作"执行
   - 配置域名解析
   - 安装SSL证书
   - 使用 https://域名 访问

3. **软件打包**
   - 如果还没打包软件，下载按钮会404
   - 先上传网站，软件打包好后再上传
   - 上传命令：`scp 文件 root@175.178.121.104:/var/www/damaihelper/downloads/`

4. **安全建议**
   - 定期更新系统：`apt update && apt upgrade`
   - 修改SSH端口（可选）
   - 配置fail2ban防暴力破解（可选）

---

## 🆘 故障排查

### 问题1：无法访问网站
```bash
# 检查Nginx状态
systemctl status nginx

# 如果未运行，启动它
systemctl start nginx

# 检查防火墙
ufw status
```

### 问题2：403 Forbidden
```bash
# 检查文件权限
ls -la /var/www/damaihelper/

# 修复权限
chown -R www-data:www-data /var/www/damaihelper
chmod -R 755 /var/www/damaihelper
```

### 问题3：404 Not Found
```bash
# 检查文件是否存在
ls /var/www/damaihelper/index.html

# 如果不存在，重新上传
```

### 问题4：样式不显示
```bash
# 查看错误日志
tail -f /var/log/nginx/damaihelper_error.log

# 清除浏览器缓存后重试
```

---

## 📞 需要帮助？

如果遇到问题：
1. 查看错误日志：`tail -f /var/log/nginx/error.log`
2. 检查Nginx配置：`nginx -t`
3. 重启服务：`systemctl restart nginx`
4. 联系我获取帮助

---

## ✅ 快速检查脚本

**在服务器上运行，检查所有配置：**

```bash
cat > /root/check.sh << 'EOF'
#!/bin/bash
echo "=== DamaiHelper 部署检查 ==="
echo ""
echo "1. Nginx状态:"
systemctl status nginx | grep Active
echo ""
echo "2. 网站文件:"
ls -lh /var/www/damaihelper/
echo ""
echo "3. 下载文件:"
ls -lh /var/www/damaihelper/downloads/
echo ""
echo "4. 防火墙状态:"
ufw status | grep -E "80|443"
echo ""
echo "5. 访问地址:"
echo "   http://175.178.121.104"
echo ""
EOF

chmod +x /root/check.sh
/root/check.sh
```

---

## 🎉 完成！

按照以上步骤操作后，你的网站应该已经上线了！

**当前访问地址：** http://175.178.121.104

**域名备案通过后：** https://你的域名.com

