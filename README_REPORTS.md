# Twitter Watchdog 报告系统

完整的 Twitter 监控与自动化报告生成系统。

## 项目结构

```
twitter-watchdog/
├── scripts/                    # 脚本目录
│   ├── push_report.sh         # 推送报告脚本
│   ├── generate_daily_report.js    # 日报生成器
│   ├── generate_monthly_report.js  # 月报生成器
│   ├── generate_index.js      # 索引页面生成器
│   ├── setup_web.sh           # Web 服务器设置
│   └── install_schedulers.sh  # 调度安装脚本
├── templates/                  # HTML 模板目录
│   ├── push.html              # 精简版推送模板
│   ├── push_detailed.html     # 详细版推送模板
│   ├── daily.html             # 日报模板
│   ├── monthly.html           # 月报模板
│   └── index.html             # 索引页模板
├── output/                     # 数据输出目录
└── push/                       # 推送报告临时目录
```

## 配置

- **Telegram Bot Token**: 8553585792:AAHORHiabbfd4gkjmkrM499dOHMSTSL2PNs
- **Chat ID**: 8542554397
- **主题色**: #1da1f2 (Twitter 蓝)
- **语言**: 中文

## 快速开始

### 1. 设置 Web 服务器

```bash
sudo ./scripts/setup_web.sh
```

这将：
- 创建 `/var/www/twitter-reports` 目录结构
- 安装 systemd 服务（端口 8080）
- 启用开机自启

访问地址: http://localhost:8080

### 2. 安装定时任务

```bash
./scripts/install_schedulers.sh
```

这将安装以下定时任务：

**推送报告**:
- 08:00 - 过去 8 小时精简报告
- 12:00 - 过去 4 小时精简报告
- 18:00 - 过去 6 小时精简报告
- 22:00 - 过去 4 小时精简报告
- 02:00 - 过去 4 小时精简报告

**报告生成**:
- 23:55 - 生成当天日报
- 00:05 - 生成前一天日报
- 每月 1 号 00:10 - 生成月报
- 每小时 - 更新索引页

## 手动使用

### 推送报告

```bash
# 精简版
./scripts/push_report.sh --hours-ago 4 --format simple

# 详细版
./scripts/push_report.sh --hours-ago 24 --format detailed
```

### 生成日报

```bash
# 生成今天的日报
node ./scripts/generate_daily_report.js

# 生成指定日期的日报
node ./scripts/generate_daily_report.js 2026-02-12
```

### 生成月报

```bash
# 生成当前月报
node ./scripts/generate_monthly_report.js

# 生成指定月份的月报
node ./scripts/generate_monthly_report.js 2026-02
```

### 更新索引页

```bash
node ./scripts/generate_index.js
```

## 报告说明

### 推送报告

- **精简版**: 显示基本统计和推文列表
- **详细版**: 包含完整统计、热门话题和详细推文信息

### 日报

包含以下内容：
- 总体统计（推文数、用户数、转推数、回复数等）
- 时间段分布（00:00~08:00, 08:00~12:00 等）
- 最活跃用户
- 热门话题
- 最新推文

### 月报

包含以下内容：
- 月度总体统计
- 每日推文趋势图
- 月度最活跃用户 TOP 10
- 热门话题 TOP 10
- 数据洞察分析
- 日报存档链接

### 索引页

- 快速统计概览
- 最新日报列表
- 月度报告列表
- 详细数据统计

## 服务管理

### Web 服务

```bash
# 查看状态
systemctl status twitter-watchdog-web

# 启动/停止/重启
systemctl start twitter-watchdog-web
systemctl stop twitter-watchdog-web
systemctl restart twitter-watchdog-web

# 查看日志
journalctl -u twitter-watchdog-web -f
```

### 定时任务

```bash
# 查看已安装的任务
crontab -l

# 查看日志
tail -f /var/log/twitter-watchdog/push.log
tail -f /var/log/twitter-watchdog/daily.log
tail -f /var/log/twitter-watchdog/monthly.log
tail -f /var/log/twitter-watchdog/index.log
```

## 日志

所有日志存储在 `/var/log/twitter-watchdog/` 目录：
- `push.log` - 推送报告日志
- `daily.log` - 日报生成日志
- `monthly.log` - 月报生成日志
- `index.log` - 索引更新日志

## 故障排除

### 推送报告失败

1. 检查 `twitter_watchdog.py` 是否存在
2. 检查 Telegram Bot Token 是否正确
3. 检查网络连接

### Web 服务无法访问

1. 检查服务状态: `systemctl status twitter-watchdog-web`
2. 检查防火墙规则
3. 查看服务日志: `journalctl -u twitter-watchdog-web -n 50`

### 报告生成失败

1. 检查 output 目录是否有数据
2. 检查 `/var/www/twitter-reports` 目录权限
3. 查看对应日志文件

## 卸载

### 卸载定时任务

编辑 crontab 并删除 Twitter Watchdog 相关任务：
```bash
crontab -e
```

### 停止并卸载 Web 服务

```bash
systemctl stop twitter-watchdog-web
systemctl disable twitter-watchdog-web
rm /etc/systemd/system/twitter-watchdog-web.service
systemctl daemon-reload
```

## 许可证

MIT License
