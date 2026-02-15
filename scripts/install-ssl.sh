#!/bin/bash

# SSL证书自动安装脚本

set -e

echo "================================"
echo "SSL证书自动安装脚本"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用root用户运行此脚本${NC}"
    exit 1
fi

# 获取域名
echo -e "${YELLOW}请输入你的域名（例如：damaihelper.com）：${NC}"
read DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}域名不能为空！${NC}"
    exit 1
fi

# 获取邮箱
echo -e "${YELLOW}请输入你的邮箱（用于接收证书到期提醒）：${NC}"
read EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}邮箱不能为空！${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}开始安装SSL证书...${NC}"
echo ""

# 1. 安装Certbot
echo -e "${YELLOW}[1/4] 安装Certbot...${NC}"
apt update
apt install certbot python3-certbot-nginx -y

# 2. 申请证书
echo -e "${YELLOW}[2/4] 申请SSL证书...${NC}"
certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email --redirect

# 3. 设置自动续期
echo -e "${YELLOW}[3/4] 设置自动续期...${NC}"
certbot renew --dry-run

# 添加定时任务
(crontab -l 2>/dev/null; echo "0 2 * * * certbot renew --quiet") | crontab -

# 4. 重启Nginx
echo -e "${YELLOW}[4/4] 重启Nginx...${NC}"
systemctl restart nginx

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}SSL证书安装完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}现在可以通过HTTPS访问你的网站：${NC}"
echo "   ${GREEN}https://$DOMAIN${NC}"
echo ""
echo -e "${YELLOW}证书信息：${NC}"
certbot certificates
echo ""
echo -e "${YELLOW}证书将在到期前自动续期${NC}"
echo ""

