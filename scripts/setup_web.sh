#!/bin/bash

# Twitter Watchdog Web 服务器设置脚本
# 创建目录结构并设置 systemd 服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Twitter Watchdog Web 服务器设置"
echo "========================================"

# 配置
WWW_ROOT="/var/www/twitter-reports"
PORT=8080
SERVICE_NAME="twitter-watchdog-web"

# 检查是否以 root 权限运行
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}错误: 此脚本需要 root 权限运行${NC}"
    echo "请使用: sudo $0"
    exit 1
fi

# 创建目录结构
echo -e "${YELLOW}创建目录结构...${NC}"
mkdir -p "$WWW_ROOT/daily"
mkdir -p "$WWW_ROOT/monthly"

# 设置权限
chown -R www-data:www-data "$WWW_ROOT" 2>/dev/null || chown -R $(whoami):$(whoami) "$WWW_ROOT"
chmod -R 755 "$WWW_ROOT"

echo -e "${GREEN}✓ 目录创建完成${NC}"
echo "  - $WWW_ROOT/daily"
echo "  - $WWW_ROOT/monthly"

# 创建 Python HTTP 服务器脚本
echo -e "${YELLOW}创建 HTTP 服务器脚本...${NC}"
cat > /usr/local/bin/twitter-watchdog-server << 'EOF'
#!/usr/bin/env python3
"""
Twitter Watchdog 简单 HTTP 服务器
"""
import http.server
import socketserver
import os
import sys

# 配置
PORT = 8080
DIRECTORY = "/var/www/twitter-reports"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # 添加 CORS 头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"Twitter Watchdog Web Server 运行在端口 {PORT}")
        print(f"文档根目录: {DIRECTORY}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            sys.exit(0)

if __name__ == "__main__":
    main()
EOF

chmod +x /usr/local/bin/twitter-watchdog-server
echo -e "${GREEN}✓ HTTP 服务器脚本创建完成${NC}"

# 创建 systemd 服务文件
echo -e "${YELLOW}创建 systemd 服务...${NC}"
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Twitter Watchdog Web Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/bin/python3 /usr/local/bin/twitter-watchdog-server
Restart=always
RestartSec=10

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/www/twitter-reports

[Install]
WantedBy=multi-user.target
EOF

# 如果 www-data 用户不存在，使用当前用户
if ! id www-data &>/dev/null; then
    echo -e "${YELLOW}www-data 用户不存在，使用当前用户${NC}"
    sed -i 's/User=www-data/User=root/' /etc/systemd/system/${SERVICE_NAME}.service
    sed -i 's/Group=www-data/Group=root/' /etc/systemd/system/${SERVICE_NAME}.service
    sed -i 's|ReadWritePaths=/var/www/twitter-reports|ReadWritePaths=/var/www/twitter-reports\nReadWritePaths=/var/www|' /etc/systemd/system/${SERVICE_NAME}.service
fi

echo -e "${GREEN}✓ systemd 服务创建完成${NC}"

# 重载 systemd
echo -e "${YELLOW}重载 systemd...${NC}"
systemctl daemon-reload

# 启用服务
echo -e "${YELLOW}启用服务开机自启...${NC}"
systemctl enable ${SERVICE_NAME}

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
systemctl start ${SERVICE_NAME}

# 检查服务状态
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}✓ 服务启动成功${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "查看日志: journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi

# 配置防火墙 (如果存在)
if command -v ufw &> /dev/null; then
    echo -e "${YELLOW}配置防火墙...${NC}"
    ufw allow ${PORT}/tcp &> /dev/null || true
    echo -e "${GREEN}✓ 防火墙规则已添加${NC}"
elif command -v firewall-cmd &> /dev/null; then
    echo -e "${YELLOW}配置防火墙...${NC}"
    firewall-cmd --permanent --add-port=${PORT}/tcp &> /dev/null || true
    firewall-cmd --reload &> /dev/null || true
    echo -e "${GREEN}✓ 防火墙规则已添加${NC}"
fi

# 创建示例索引页
echo -e "${YELLOW}创建示例索引页...${NC}"
cat > "$WWW_ROOT/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Twitter Watchdog 报告中心</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f0f3f5;
            color: #14171a;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 50px auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #1da1f2;
            font-size: 28px;
        }
        .message {
            background: #e8f5fe;
            border-left: 4px solid #1da1f2;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .message strong {
            color: #0c85d0;
        }
        .info {
            color: #657786;
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Twitter Watchdog 报告中心</h1>
        </div>
        <div class="message">
            <strong>欢迎！</strong> 报告正在准备中...
        </div>
        <div class="info">
            请运行日报和月报生成器来创建报告
        </div>
    </div>
</body>
</html>
EOF

echo -e "${GREEN}✓ 示例索引页创建完成${NC}"

# 完成
echo ""
echo "========================================"
echo -e "${GREEN}✓ Web 服务器设置完成！${NC}"
echo "========================================"
echo ""
echo "服务信息:"
echo "  端口: ${PORT}"
echo "  访问地址: http://localhost:${PORT}"
echo "  服务名称: ${SERVICE_NAME}"
echo "  报告目录: $WWW_ROOT"
echo ""
echo "常用命令:"
echo "  查看状态: systemctl status ${SERVICE_NAME}"
echo "  启动服务: systemctl start ${SERVICE_NAME}"
echo "  停止服务: systemctl stop ${SERVICE_NAME}"
echo "  重启服务: systemctl restart ${SERVICE_NAME}"
echo "  查看日志: journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "========================================"
