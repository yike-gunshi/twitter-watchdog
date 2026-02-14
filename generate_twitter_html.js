const fs = require('fs');
const path = require('path');

// Read the latest markdown file
const outputDir = path.join(__dirname, 'twitter-watchdog', 'output');
const summaryPath = path.join(outputDir, 'latest_summary.md');
const detailPath = path.join(outputDir, 'ai_tweets_20260212_105616.md');

let summaryContent = '';
let detailContent = '';

if (fs.existsSync(summaryPath)) {
  summaryContent = fs.readFileSync(summaryPath, 'utf-8');
}

if (fs.existsSync(detailPath)) {
  detailContent = fs.readFileSync(detailPath, 'utf-8');
}

// Simple Markdown to HTML converter
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

  // Table
  html = html.replace(/^-+\|.*$/gim, ''); // Remove separator row
  html = html.replace(/<ul><li>(.*)<\/li><\/ul>/g, function(match) {
    const lines = match.split('\n').filter(l => l.trim());
    if (lines.length <= 1) return match;
    let tableHtml = '<table style="border-collapse: collapse; width: 100%; margin: 20px 0;">';
    lines.forEach((line, idx) => {
      const content = line.replace(/<\/?li>/g, '').replace(/<\/?ul>/g, '').trim();
      const cols = content.split('|').map(c => c.trim()).filter(c => c);
      if (cols.length >= 2) {
        const rowType = idx === 0 ? 'th' : 'td';
        tableHtml += '<tr>';
        cols.forEach(col => {
          tableHtml += `<${rowType} style="border: 1px solid #ddd; padding: 8px; text-align: left;">${col}</${rowType}>`;
        });
        tableHtml += '</tr>';
      }
    });
    tableHtml += '</table>';
    return tableHtml;
  });

  // Paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';

  return html;
}

const summaryHtml = markdownToHtml(summaryContent);
const detailHtml = markdownToHtml(detailContent);

const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });

const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Twitter AI 推文监控</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 40px 20px;
      line-height: 1.7;
      color: #1a1a1a;
      background: #f5f5f5;
    }
    .container {
      background: white;
      padding: 40px;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    h1 {
      color: #1da1f2;
      border-bottom: 3px solid #1da1f2;
      padding-bottom: 15px;
      margin-bottom: 30px;
    }
    h2 {
      color: #14171a;
      margin-top: 40px;
      margin-bottom: 20px;
    }
    h3 {
      color: #657786;
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
    .meta {
      background: #e8f5fd;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 30px;
    }
    .meta p {
      margin: 5px 0;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 20px 0;
    }
    th, td {
      border: 1px solid #e1e8ed;
      padding: 12px;
      text-align: left;
    }
    th {
      background: #f7f9fa;
      font-weight: 600;
    }
    tr:nth-child(even) {
      background: #f9f9f9;
    }
    ul {
      padding-left: 20px;
    }
    li {
      margin: 10px 0;
    }
    .footer {
      margin-top: 50px;
      padding-top: 20px;
      border-top: 1px solid #e1e8ed;
      color: #657786;
      font-size: 0.9em;
      text-align: center;
    }
    .badge {
      display: inline-block;
      background: #1da1f2;
      color: white;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.85em;
      margin-right: 8px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🐦 Twitter AI 推文监控</h1>

    <div class="meta">
      <p><strong>更新时间:</strong> ${now}</p>
      <p><strong>监控账户:</strong> @rollingrock_1</p>
      <p><strong>项目:</strong> <a href="https://github.com/yike-gunshi/twitter-watchdog" target="_blank">Twitter Watchdog</a></p>
    </div>

    <hr>

    <h2>📊 汇总摘要</h2>
    ${summaryHtml}

    <hr>

    <h2>📝 详细报告</h2>
    ${detailHtml}

    <div class="footer">
      <p>由 Twitter Watchdog 自动生成 | Claude AI 智能筛选</p>
    </div>
  </div>
</body>
</html>`;

// Write HTML file
const outputPath = path.join(__dirname, 'twitter_ai_tweets.html');
fs.writeFileSync(outputPath, htmlContent, 'utf-8');

console.log('✅ 生成成功!');
console.log('📄 文件位置: ' + outputPath);
console.log('');
console.log('可以使用以下命令在浏览器中打开:');
console.log('  open twitter_ai_tweets.html');
console.log('  或');
console.log('  xdg-open twitter_ai_tweets.html');
