#!/bin/bash

# Twitter Watchdog 推送脚本
# 用途: 抓取推文、生成 HTML（包含AI总结和详细报告）、发送到 Telegram

set -e

# 配置
WORK_DIR="/root/.openclaw/workspace/twitter-watchdog"
PUSH_DIR="${WORK_DIR}/push"
OUTPUT_DIR="${WORK_DIR}/output"
NODE_SCRIPT="${WORK_DIR}/scripts/.temp_generate_push.js"
TELEGRAM_BOT_TOKEN="8553585792:AAHORHiabbfd4gkjmkrM499dOHMSTSL2PNs"
TELEGRAM_CHAT_ID="8542554397"

# 默认参数
HOURS_AGO=4

# 解析参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --hours-ago)
      HOURS_AGO="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

# 设置代理
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"

# 进入工作目录
cd "$WORK_DIR"

# 激活虚拟环境
source venv/bin/activate

# 运行 twitter_watchdog.py
echo "抓取最近 ${HOURS_AGO} 小时的推文..."
python3 scripts/twitter_watchdog.py --hours-ago "$HOURS_AGO"

# 获取最新的 JSON 和 Markdown 文件
LATEST_JSON=$(ls -t "$OUTPUT_DIR"/ai_tweets_*.json 2>/dev/null | head -n 1)
LATEST_MD=$(ls -t "$OUTPUT_DIR"/ai_tweets_*.md 2>/dev/null | head -n 1)
LATEST_SUMMARY="$OUTPUT_DIR/latest_summary.md"

if [ -z "$LATEST_JSON" ] || [ -z "$LATEST_MD" ]; then
  echo "错误: 未找到推文数据文件"
  exit 1
fi

echo "使用数据文件: $LATEST_JSON"

# 创建 Node.js 脚本
cat > "$NODE_SCRIPT" << 'NODEEOF'
const fs = require('fs');
const path = require('path');

const jsonFile = process.argv[2];
const mdFile = process.argv[3];
const summaryFile = process.argv[4];
const htmlFile = process.argv[5];

// 读取数据
const data = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
const summaryContent = fs.existsSync(summaryFile) ? fs.readFileSync(summaryFile, 'utf8') : '';

// Markdown to HTML converter
function markdownToHtml(md) {
  let html = md;

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // Lists
  html = html.replace(/^- (.*)$/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

  // Paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';

  return html;
}

const summaryHtml = markdownToHtml(summaryContent);

// 从 followings 中提取所有推文
let allTweets = [];
if (data.followings && Array.isArray(data.followings)) {
  data.followings.forEach(following => {
    if (following.tweets && Array.isArray(following.tweets)) {
      following.tweets.forEach(tweet => {
        // 将 user 信息合并到 tweet 中
        if (following.user) {
          tweet.user = {
            name: following.user.name,
            screen_name: following.user.username
          };
        }
        allTweets.push(tweet);
      });
    }
  });
}

// 生成推文列表HTML
let tweetsHtml = '';
allTweets.forEach(t => {
  const user = t.user || {};
  const name = (user.name || 'Unknown').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const screenName = (user.screen_name || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const text = (t.text || '').replace(/\n/g, ' ').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const url = t.url || t.twitterUrl || '';
  
  const createdAt = t.createdAt || '';
  let tweetTime = '';
  if (createdAt) {
    const date = new Date(createdAt);
    tweetTime = date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'});
  }
  
  tweetsHtml += `<li style="margin: 10px 0;">
    <p><strong>[${text}](${url})</strong>。${text}</p>
    <p style="color: #657786; font-size: 13px;">${tweetTime}</p>
  </li>`;
});

// 生成统计
const users = new Set();
allTweets.forEach(t => {
  if (t.user && t.user.screen_name) {
    users.add(t.user.screen_name);
  }
});

const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });

// 生成HTML
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Twitter AI 推文监控</title>
  <style>
    @media (prefers-color-scheme: light) {
      body {
        background: #f5f5f5;
        color: #1a1a1a;
      }
      .container {
        background: white;
      }
      h1 { color: #1da1f2; }
      h2 { color: #14171a; }
      h3 { color: #657786; }
    }
    @media (prefers-color-scheme: dark) {
      body {
        background: #15202b;
        color: #ffffff;
      }
      .container {
        background: #192734;
      }
      h1 { color: #1da1f2; }
      h2 { color: #ffffff; }
      h3 { color: #8899a6; }
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px;
      line-height: 1.7;
    }
    .container {
      padding: 40px;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    .meta {
      background: #e8f5fe;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 30px;
    }
    .meta p {
      margin: 5px 0;
    }
    h1 {
      font-size: 28px;
      border-bottom: 3px solid #1da1f2;
      padding-bottom: 15px;
      margin-bottom: 30px;
    }
    h2 {
      font-size: 20px;
      margin-top: 40px;
      margin-bottom: 20px;
    }
    h3 {
      font-size: 16px;
      margin-top: 25px;
      margin-bottom: 15px;
    }
    a {
      color: #1da1f2;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    hr {
      border: none;
      border-top: 1px solid #e1e8ed;
      margin: 30px 0;
    }
    ul {
      padding-left: 20px;
    }
    .footer {
      margin-top: 50px;
      padding-top: 20px;
      border-top: 1px solid #e1e8ed;
      text-align: center;
      font-size: 0.9em;
      color: #657786;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🐦 Twitter AI 推文监控</h1>

    <div class="meta">
      <p><strong>更新时间:</strong> ${now}</p>
      <p><strong>监控账户:</strong> @rollingrock_1</p>
      <p><strong>推文数量:</strong> ${allTweets.length}</p>
      <p><strong>活跃用户:</strong> ${users.size}</p>
    </div>

    <hr>

    <h2>📊 AI 智能总结</h2>
    ${summaryHtml}

    <hr>

    <h2>📝 详细报告</h2>
    <ul>
      ${tweetsHtml}
    </ul>

    <div class="footer">
      <p>由 Twitter Watchdog 自动生成 | Claude AI 智能筛选</p>
    </div>
  </div>
</body>
</html>`;

// 确保目录存在
const dir = path.dirname(htmlFile);
if (!fs.existsSync(dir)) {
  fs.mkdirSync(dir, { recursive: true });
}

// 写入文件
fs.writeFileSync(htmlFile, html, 'utf8');

console.log('TWEET_COUNT=' + allTweets.length);
console.log('USER_COUNT=' + users.size);
NODEEOF

# 生成输出文件名
OUTPUT_FILE="${PUSH_DIR}/push-$(date '+%Y%m%d-%H%M').html"

# 运行 Node.js 脚本生成 HTML
echo "生成 HTML..."
eval $(node "$NODE_SCRIPT" "$LATEST_JSON" "$LATEST_MD" "$LATEST_SUMMARY" "$OUTPUT_FILE")

# 获取统计值
TWEET_COUNT=$(echo "$TWEET_COUNT" | sed 's/TWEET_COUNT=//')
USER_COUNT=$(echo "$USER_COUNT" | sed 's/USER_COUNT=//')

echo "推文数: $TWEET_COUNT, 用户数: $USER_COUNT"
echo "生成推送文件: $OUTPUT_FILE"

# 清理临时脚本
rm -f "$NODE_SCRIPT"

# 发送到 Telegram
echo "发送到 Telegram..."

# 获取文件路径
FILE_PATH=$(realpath "$OUTPUT_FILE")

# 使用 curl 发送文件
RESPONSE=$(curl -s -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" \
  -F "chat_id=${TELEGRAM_CHAT_ID}" \
  -F "document=@${FILE_PATH}" \
  -F "caption=🐦 Twitter AI 推文监控 · ${TWEET_COUNT}条推文")

# 检查响应
if echo "$RESPONSE" | grep -q '"ok":true'; then
  echo "✅ 推送成功"
else
  echo "❌ 推送失败"
  echo "$RESPONSE"
  exit 1
fi

echo "完成!"
