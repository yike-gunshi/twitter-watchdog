#!/bin/bash

# Twitter Watchdog 调度安装脚本
# 安装 crontab 任务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Twitter Watchdog 调度安装"
echo "========================================"

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH_SCRIPT="$SCRIPT_DIR/push_report.sh"
DAILY_REPORT_SCRIPT="$SCRIPT_DIR/generate_daily_report.js"
MONTHLY_REPORT_SCRIPT="$SCRIPT_DIR/generate_monthly_report.js"
INDEX_SCRIPT="$SCRIPT_DIR/generate_index.js"

# 检查脚本是否存在
check_script() {
    if [[ ! -f "$1" ]]; then
        echo -e "${RED}错误: 脚本不存在 $1${NC}"
        exit 1
    fi
}

check_script "$PUSH_SCRIPT"
check_script "$DAILY_REPORT_SCRIPT"
check_script "$MONTHLY_REPORT_SCRIPT"
check_script "$INDEX_SCRIPT"

echo -e "${GREEN}✓ 所有脚本检查通过${NC}"
echo ""

# 临时文件保存 crontab
TEMP_CRON=$(mktemp)

# 导出当前 crontab（如果存在）
crontab -l > "$TEMP_CRON" 2>/dev/null || true

# 检查是否已安装 Twitter Watchdog 任务
if grep -q "Twitter Watchdog" "$TEMP_CRON" 2>/dev/null; then
    echo -e "${YELLOW}检测到已安装的 Twitter Watchdog 任务${NC}"
    read -p "是否要覆盖现有任务? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消安装"
        rm -f "$TEMP_CRON"
        exit 0
    fi
    # 删除旧的 Twitter Watchdog 任务
    grep -v "Twitter Watchdog" "$TEMP_CRON" > "$TEMP_CRON.tmp" 2>/dev/null || true
    mv "$TEMP_CRON.tmp" "$TEMP_CRON" 2>/dev/null || true
fi

# 添加注释
cat >> "$TEMP_CRON" << 'CRON_EOF'

# ========================================
# Twitter Watchdog 自动任务
# ========================================

# 推送报告 - 每天 5 个时间点
CRON_EOF

# 添加推送报告任务
echo "添加推送报告任务..."

# 08:00 - 推送过去 8 小时的精简报告
echo "0 8 * * * $PUSH_SCRIPT --hours-ago 8 --format simple >> /var/log/twitter-watchdog/push.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 08:00 - push_report.sh --hours-ago 8 --format simple${NC}"

# 12:00 - 推送过去 4 小时的精简报告
echo "0 12 * * * $PUSH_SCRIPT --hours-ago 4 --format simple >> /var/log/twitter-watchdog/push.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 12:00 - push_report.sh --hours-ago 4 --format simple${NC}"

# 18:00 - 推送过去 6 小时的精简报告
echo "0 18 * * * $PUSH_SCRIPT --hours-ago 6 --format simple >> /var/log/twitter-watchdog/push.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 18:00 - push_report.sh --hours-ago 6 --format simple${NC}"

# 22:00 - 推送过去 4 小时的精简报告
echo "0 22 * * * $PUSH_SCRIPT --hours-ago 4 --format simple >> /var/log/twitter-watchdog/push.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 22:00 - push_report.sh --hours-ago 4 --format simple${NC}"

# 02:00 - 推送过去 4 小时的精简报告
echo "0 2 * * * $PUSH_SCRIPT --hours-ago 4 --format simple >> /var/log/twitter-watchdog/push.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 02:00 - push_report.sh --hours-ago 4 --format simple${NC}"

echo ""
echo "添加日报生成任务..."

# 23:55 - 生成当天日报
echo "55 23 * * * node $DAILY_REPORT_SCRIPT >> /var/log/twitter-watchdog/daily.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 23:55 - generate_daily_report.js${NC}"

# 00:05 - 生成前一天日报（确保完整）
echo "5 0 * * * node $DAILY_REPORT_SCRIPT >> /var/log/twitter-watchdog/daily.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 00:05 - generate_daily_report.js${NC}"

echo ""
echo "添加月报生成任务..."

# 每月 1 号 00:10 - 生成上个月报告
echo "10 0 1 * * node $MONTHLY_REPORT_SCRIPT >> /var/log/twitter-watchdog/monthly.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 每月 1 号 00:10 - generate_monthly_report.js${NC}"

echo ""
echo "添加索引更新任务..."

# 每小时更新索引页
echo "0 * * * * node $INDEX_SCRIPT >> /var/log/twitter-watchdog/index.log 2>&1" >> "$TEMP_CRON"
echo -e "${GREEN}✓ 每小时 - generate_index.js${NC}"

# 创建日志目录
echo ""
echo -e "${YELLOW}创建日志目录...${NC}"
mkdir -p /var/log/twitter-watchdog
chmod 755 /var/log/twitter-watchdog

# 安装 crontab
echo ""
echo -e "${YELLOW}安装 crontab...${NC}"
crontab "$TEMP_CRON"

# 清理临时文件
rm -f "$TEMP_CRON"

# 显示当前 crontab
echo ""
echo "========================================"
echo -e "${GREEN}✓ 调度任务安装完成！${NC}"
echo "========================================"
echo ""
echo "已安装的任务:"
echo ""
echo "推送报告:"
echo "  08:00  - push_report.sh --hours-ago 8 --format simple"
echo "  12:00  - push_report.sh --hours-ago 4 --format simple"
echo "  18:00  - push_report.sh --hours-ago 6 --format simple"
echo "  22:00  - push_report.sh --hours-ago 4 --format simple"
echo "  02:00  - push_report.sh --hours-ago 4 --format simple"
echo ""
echo "日报生成:"
echo "  23:55  - generate_daily_report.js"
echo "  00:05  - generate_daily_report.js"
echo ""
echo "月报生成:"
echo "  每月 1 号 00:10 - generate_monthly_report.js"
echo ""
echo "索引更新:"
echo "  每小时 - generate_index.js"
echo ""
echo "日志目录: /var/log/twitter-watchdog/"
echo ""
echo "查看 crontab: crontab -l"
echo "查看日志: tail -f /var/log/twitter-watchdog/push.log"
echo ""
echo "========================================"
