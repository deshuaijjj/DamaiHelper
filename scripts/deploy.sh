#!/bin/bash

# DamaiHelper 一键部署脚本
# 适用于腾讯云轻量应用服务器（Ubuntu）

set -e

echo "================================"
echo "DamaiHelper 网站一键部署脚本"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root用户运行此脚本${NC}"
    echo "使用命令: sudo bash deploy.sh"
    exit 1
fi

# 获取域名
echo -e "${YELLOW}请输入你的域名（例如：damaihelper.com）：${NC}"
read DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}域名不能为空！${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}开始部署，域名：$DOMAIN${NC}"
echo ""

# 1. 更新系统
echo -e "${YELLOW}[1/8] 更新系统...${NC}"
apt update && apt upgrade -y

# 2. 安装Nginx
echo -e "${YELLOW}[2/8] 安装Nginx...${NC}"
apt install nginx -y

# 3. 创建网站目录
echo -e "${YELLOW}[3/8] 创建网站目录...${NC}"
mkdir -p /var/www/damaihelper/downloads

# 4. 配置Nginx
echo -e "${YELLOW}[4/8] 配置Nginx...${NC}"
cat > /etc/nginx/sites-available/damaihelper << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    root /var/www/damaihelper;
    index index.html;
    
    # 网站主页
    location / {
        try_files \$uri \$uri/ =404;
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

# 5. 启用站点
echo -e "${YELLOW}[5/8] 启用站点...${NC}"
ln -sf /etc/nginx/sites-available/damaihelper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
nginx -t

# 6. 设置权限
echo -e "${YELLOW}[6/8] 设置文件权限...${NC}"
chown -R www-data:www-data /var/www/damaihelper
chmod -R 755 /var/www/damaihelper

# 7. 配置防火墙
echo -e "${YELLOW}[7/8] 配置防火墙...${NC}"
ufw allow 'Nginx Full'
ufw allow OpenSSH
echo "y" | ufw enable

# 8. 重启Nginx
echo -e "${YELLOW}[8/8] 重启Nginx...${NC}"
systemctl restart nginx
systemctl enable nginx

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}基础部署完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}下一步操作：${NC}"
echo ""
echo "1. 上传网站文件："
echo "   ${GREEN}scp index.html root@服务器IP:/var/www/damaihelper/${NC}"
echo ""
echo "2. 上传软件安装包："
echo "   ${GREEN}scp *.dmg root@服务器IP:/var/www/damaihelper/downloads/${NC}"
echo "   ${GREEN}scp *.exe root@服务器IP:/var/www/damaihelper/downloads/${NC}"
echo ""
echo "3. 配置域名解析（在腾讯云控制台）："
echo "   - 记录类型：A"
echo "   - 主机记录：@"
echo "   - 记录值：$(curl -s ifconfig.me)"
echo ""
echo "4. 等待域名解析生效后，安装SSL证书："
echo "   ${GREEN}apt install certbot python3-certbot-nginx -y${NC}"
echo "   ${GREEN}certbot --nginx -d $DOMAIN -d www.$DOMAIN${NC}"
echo ""
echo -e "${YELLOW}临时访问地址：${NC}"
echo "   http://$(curl -s ifconfig.me)"
echo ""
echo -e "${YELLOW}域名解析后访问：${NC}"
echo "   http://$DOMAIN"
echo ""

