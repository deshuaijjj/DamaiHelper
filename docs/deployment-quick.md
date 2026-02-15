# 腾讯云部署快速指南

## 🚀 超简化版（给不懂技术的人）

### 第一步：备案（必须，15-20天）

1. **登录腾讯云** → 搜索"网站备案" → 点击"开始备案"
2. **填写信息**：
   - 姓名、身份证、手机号
   - 网站名称：写"个人技术博客"（不要写抢票相关）
   - 上传身份证照片
3. **视频核验**：按提示录视频（1分钟）
4. **等待审核**：10-20天
5. **收到备案号**：短信通知

### 第二步：一键部署（10分钟）

**在你的Mac上：**

```bash
# 1. 连接到服务器
ssh root@你的服务器IP
# 输入密码

# 2. 下载部署脚本
curl -O https://raw.githubusercontent.com/yourusername/DamaiHelper/main/scripts/deploy.sh

# 3. 运行脚本
bash deploy.sh
# 输入你的域名，等待完成

# 4. 上传网站文件（新开一个终端）
cd /Users/zhangyuxin/Desktop/DamaiHelper
scp website/index.html root@你的服务器IP:/var/www/damaihelper/

# 5. 上传软件（打包后）
scp electron/dist/*.dmg root@你的服务器IP:/var/www/damaihelper/downloads/
scp electron/dist/*.exe root@你的服务器IP:/var/www/damaihelper/downloads/
```

### 第三步：配置域名（5分钟）

1. **腾讯云控制台** → "域名管理" → 点击你的域名 → "解析"
2. **添加记录**：
   - 记录类型：A
   - 主机记录：@
   - 记录值：你的服务器IP
   - 点击"保存"

### 第四步：安装HTTPS（5分钟）

```bash
# 在服务器上运行
curl -O https://raw.githubusercontent.com/yourusername/DamaiHelper/main/scripts/install-ssl.sh
bash install-ssl.sh
# 输入域名和邮箱
```

### 完成！

访问：`https://你的域名`

---

## 📋 详细步骤（给懂技术的人）

详见：[完整部署文档](deployment.md)

---

## ⚡ 命令速查表

### 连接服务器
```bash
ssh root@服务器IP
```

### 上传文件
```bash
# 上传单个文件
scp 本地文件 root@服务器IP:/远程路径

# 上传整个目录
scp -r 本地目录 root@服务器IP:/远程路径
```

### 查看日志
```bash
# Nginx访问日志
tail -f /var/log/nginx/damaihelper_access.log

# Nginx错误日志
tail -f /var/log/nginx/damaihelper_error.log
```

### 重启服务
```bash
# 重启Nginx
systemctl restart nginx

# 查看Nginx状态
systemctl status nginx
```

### 检查证书
```bash
# 查看证书信息
certbot certificates

# 手动续期
certbot renew
```

---

## 🎯 时间线

```
Day 1:    购买域名 + 提交备案
Day 2-20: 等待备案审核（什么都不用做）
Day 21:   备案通过
Day 21:   部署网站（30分钟）
Day 21:   配置域名（5分钟）
Day 21:   安装SSL（5分钟）
Day 21:   网站上线！🎉
```

---

## 💰 费用预算

- 域名：50-100元/年
- 服务器：你已经买了（轻量应用服务器）
- SSL证书：免费（Let's Encrypt）
- 备案：免费

**总计：50-100元/年**

---

## ⚠️ 重要提醒

### 备案注意事项
1. ❌ 不要在备案信息中提到"抢票"、"大麦"
2. ✅ 网站名称写"个人技术博客"或"开源工具分享"
3. ✅ 所有信息必须真实
4. ✅ 保持手机畅通（可能接到核实电话）

### 网站内容注意
1. ✅ 强调"学习研究用途"
2. ✅ 显眼位置放免责声明
3. ✅ 不要宣传"100%成功"
4. ✅ 不要收费

### 法律风险
1. 这是灰色地带，有一定风险
2. 强调开源、学习性质
3. 不要商业化运营
4. 随时准备下线

---

## 🆘 遇到问题？

### 问题1：备案被拒绝
- 查看拒绝原因
- 修改网站名称（去掉敏感词）
- 重新提交

### 问题2：网站打不开
```bash
# 检查Nginx
systemctl status nginx

# 检查防火墙
ufw status

# 查看错误日志
tail -f /var/log/nginx/error.log
```

### 问题3：域名解析不生效
- 等待5-10分钟
- 检查解析记录是否正确
- 使用 `ping 域名` 测试

### 问题4：SSL证书申请失败
- 确认域名已解析到服务器
- 确认80端口开放
- 检查Nginx配置

---

## 📞 获取帮助

- 查看完整文档：`docs/deployment.md`
- GitHub Issues：提交问题
- 腾讯云工单：技术支持

---

## ✅ 部署检查清单

**部署前：**
- [ ] 域名已购买
- [ ] 备案已通过（有备案号）
- [ ] 服务器已购买
- [ ] 软件已打包（.dmg 和 .exe）
- [ ] 网站文件已准备

**部署后：**
- [ ] 网站可以访问
- [ ] HTTPS正常（绿色小锁）
- [ ] 软件可以下载
- [ ] 手机端显示正常
- [ ] 备案号已显示在页面底部

---

## 🎉 恭喜！

如果一切顺利，你现在拥有：
- ✅ 一个专业的官网
- ✅ HTTPS加密
- ✅ 合法备案
- ✅ 用户可以下载软件

**下一步：**
1. 分享给朋友测试
2. 收集反馈
3. 持续改进
4. 建立社区

加油！🚀

