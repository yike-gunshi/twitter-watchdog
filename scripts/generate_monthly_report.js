#!/usr/bin/env node

/**
 * Twitter Watchdog 月报生成器
 * 用法: node generate_monthly_report.js [month]
 * month 格式: YYYY-MM
 */

const fs = require('fs');
const path = require('path');

// 配置
const PROJECT_DIR = path.join(__dirname, '..');
const OUTPUT_DIR = path.join(PROJECT_DIR, 'output');
const TEMPLATE_DIR = path.join(PROJECT_DIR, 'templates');
const DAILY_REPORT_DIR = '/var/www/twitter-reports/daily';
const MONTHLY_REPORT_DIR = '/var/www/twitter-reports/monthly';

// 月份参数
const monthParam = process.argv[2] || new Date().toISOString().slice(0, 7);
const [year, month] = monthParam.split('-').map(Number);

// 日期范围
const startDate = new Date(year, month - 1, 1);
const endDate = new Date(year, month, 0);
const daysInMonth = endDate.getDate();

// 确保输出目录存在
if (!fs.existsSync(MONTHLY_REPORT_DIR)) {
    console.error('错误: 月报目录不存在:', MONTHLY_REPORT_DIR);
    console.log('请先运行 setup_web.sh 创建目录');
    process.exit(1);
}

console.log('========================================');
console.log('Twitter Watchdog 月报生成器');
console.log('========================================');
console.log('报告月份:', monthParam);
console.log('日期范围:', startDate.toISOString().split('T')[0], '至', endDate.toISOString().split('T')[0]);
console.log('开始时间:', new Date().toLocaleString('zh-CN'));
console.log('----------------------------------------');

// 读取当月所有日报数据
console.log('正在读取日报数据...');
let allTweets = [];
let dailyReports = [];

for (let day = 1; day <= daysInMonth; day++) {
    const dayStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dailyReportFile = path.join(DAILY_REPORT_DIR, `${dayStr}.html`);

    // 读取日报 HTML 以获取统计信息
    if (fs.existsSync(dailyReportFile)) {
        const html = fs.readFileSync(dailyReportFile, 'utf8');
        const tweetMatch = html.match(/总推文数<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);
        const tweetCount = tweetMatch ? parseInt(tweetMatch[1]) : 0;

        dailyReports.push({
            date: dayStr,
            tweetCount: tweetCount,
            hasReport: true
        });
    } else {
        dailyReports.push({
            date: dayStr,
            tweetCount: 0,
            hasReport: false
        });
    }

    // 读取原始 JSON 数据
    const files = fs.existsSync(OUTPUT_DIR) ? fs.readdirSync(OUTPUT_DIR) : [];
    const jsonFiles = files.filter(f => f.endsWith('.json'));

    jsonFiles.forEach(file => {
        const filePath = path.join(OUTPUT_DIR, file);
        try {
            const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            const tweets = data.tweets || data;

            const dayTweets = tweets.filter(tweet => {
                const tweetDate = tweet.created_at || tweet.time || tweet.date;
                if (!tweetDate) return false;
                return tweetDate.startsWith(dayStr);
            });

            allTweets = allTweets.concat(dayTweets);
        } catch (error) {
            // 忽略读取错误
        }
    });
}

console.log(`找到 ${allTweets.length} 条推文数据`);

// 统计数据
const stats = {
    totalTweets: allTweets.length,
    totalRetweets: 0,
    totalReplies: 0,
    uniqueUsers: new Set(),
    hashtags: {},
    userTweets: {},
    dailyTweets: {},
    daysActive: new Set()
};

// 按天统计
for (let day = 1; day <= daysInMonth; day++) {
    const dayStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    stats.dailyTweets[dayStr] = 0;
}

// 处理推文数据
allTweets.forEach(tweet => {
    const tweetDate = tweet.created_at || tweet.time || tweet.date;
    if (!tweetDate) return;

    const datePart = tweetDate.split('T')[0] || tweetDate.split(' ')[0];
    if (datePart && stats.dailyTweets.hasOwnProperty(datePart)) {
        stats.dailyTweets[datePart]++;
        stats.daysActive.add(datePart);
    }

    // 统计用户
    const username = tweet.username || tweet.user;
    if (username) {
        stats.uniqueUsers.add(username);
        stats.userTweets[username] = (stats.userTweets[username] || 0) + 1;
    }

    // 统计类型
    if (tweet.is_retweet) stats.totalRetweets++;
    if (tweet.is_reply) stats.totalReplies++;

    // 统计话题
    if (tweet.hashtags) {
        tweet.hashtags.forEach(tag => {
            stats.hashtags[tag] = (stats.hashtags[tag] || 0) + 1;
        });
    }
});

// 排序
const topUsers = Object.entries(stats.userTweets)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

const topHashtags = Object.entries(stats.hashtags)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

// 找出最大推文数用于图表
const maxTweetsPerDay = Math.max(...Object.values(stats.dailyTweets), 1);

// 生成每日图表 HTML
const dailyChartHTML = Object.entries(stats.dailyTweets).map(([date, count]) => {
    const day = parseInt(date.split('-')[2]);
    const height = (count / maxTweetsPerDay) * 100;
    return `
        <div class="day-bar">
            <div class="bar" style="height: ${Math.max(height, 5)}%;" data-count="${count}"></div>
            <div class="label">${day}</div>
        </div>
    `;
}).join('');

// 生成用户卡片 HTML
const generateUserCard = (username, count) => {
    const avatarLetter = username.charAt(0).toUpperCase();
    const retweetCount = Math.floor(count * 0.3); // 估算
    const replyCount = Math.floor(count * 0.2); // 估算
    return `
        <div class="user-card">
            <div class="user-avatar">${avatarLetter}</div>
            <div class="user-name">@${username}</div>
            <div class="user-stats">
                <div class="user-stat-item"><strong>${count}</strong>推文</div>
                <div class="user-stat-item"><strong>${retweetCount}</strong>转推</div>
                <div class="user-stat-item"><strong>${replyCount}</strong>回复</div>
            </div>
        </div>
    `;
};

const topUsersHTML = topUsers.map(([user, count]) => generateUserCard(user, count)).join('');

// 生成话题 HTML
const hashtagsHTML = topHashtags.map(([tag, count]) => {
    const userCount = Math.floor(count / 2); // 估算
    return `
        <div class="hashtag-item">
            <div class="hashtag-name">#${tag}</div>
            <div class="hashtag-stats">
                <span><strong>${count}</strong> 使用</span>
                <span><strong>${userCount}</strong> 用户</span>
            </div>
        </div>
    `;
}).join('');

// 生成日报存档 HTML
const dailyReportsHTML = dailyReports.map(report => {
    if (report.hasReport && report.tweetCount > 0) {
        return `
            <a href="/daily/${report.date}.html" class="daily-link">
                <div class="date">${report.date.slice(5)}</div>
                <div class="count">${report.tweetCount} 条推文</div>
            </a>
        `;
    }
    return '';
}).filter(Boolean).join('');

// 生成数据洞察
const insights = [];
const avgTweetsPerDay = Math.round(stats.totalTweets / daysInMonth);
const avgTweetsPerActiveDay = stats.daysActive.size > 0
    ? Math.round(stats.totalTweets / stats.daysActive.size)
    : 0;

insights.push(`本月共收集 <strong>${stats.totalTweets}</strong> 条推文，平均每天 <strong>${avgTweetsPerDay}</strong> 条`);
if (stats.daysActive.size > 0) {
    insights.push(`活跃天数为 <strong>${stats.daysActive.size}</strong> 天，活跃日平均 <strong>${avgTweetsPerActiveDay}</strong> 条`);
}
insights.push(`<strong>${stats.uniqueUsers.size}</strong> 位用户发布了推文`);
if (topHashtags.length > 0) {
    insights.push(`最热门的话题是 <strong>#${topHashtags[0][0]}</strong>，出现了 <strong>${topHashtags[0][1]}</strong> 次`);
}
if (topUsers.length > 0) {
    insights.push(`最活跃的用户是 <strong>@${topUsers[0][0]}</strong>，发布了 <strong>${topUsers[0][1]}</strong> 条推文`);
}

const insightsHTML = insights.map(insight => `<div class="insight-item">${insight}</div>`).join('');

// 读取模板
const templateFile = path.join(TEMPLATE_DIR, 'monthly.html');
let htmlContent;
if (fs.existsSync(templateFile)) {
    htmlContent = fs.readFileSync(templateFile, 'utf8');
} else {
    console.error('模板文件不存在:', templateFile);
    process.exit(1);
}

// 替换变量
const now = new Date();
const replacements = {
    '{{MONTH}}': monthParam,
    '{{START_DATE}}': startDate.toISOString().split('T')[0],
    '{{END_DATE}}': endDate.toISOString().split('T')[0],
    '{{GENERATED_AT}}': now.toLocaleString('zh-CN'),
    '{{TOTAL_TWEETS}}': stats.totalTweets,
    '{{TOTAL_USERS}}': stats.uniqueUsers.size,
    '{{TOTAL_RETWEETS}}': stats.totalRetweets,
    '{{TOTAL_REPLIES}}': stats.totalReplies,
    '{{TOTAL_HASHTAGS}}': Object.keys(stats.hashtags).length,
    '{{DAYS_ACTIVE}}': stats.daysActive.size,
    '{{DAILY_CHART}}': dailyChartHTML,
    '{{TOP_USERS}}': topUsersHTML,
    '{{HASHTAGS}}': hashtagsHTML,
    '{{DAILY_REPORTS}}': dailyReportsHTML,
    '{{INSIGHTS}}': insightsHTML
};

for (const [key, value] of Object.entries(replacements)) {
    htmlContent = htmlContent.replace(new RegExp(key.replace(/[{}]/g, '\\$&'), 'g'), value);
}

// 写入输出文件
const outputFile = path.join(MONTHLY_REPORT_DIR, `${monthParam}.html`);
fs.writeFileSync(outputFile, htmlContent);

console.log('----------------------------------------');
console.log('统计数据:');
console.log(`  总推文数: ${stats.totalTweets}`);
console.log(`  活跃用户: ${stats.uniqueUsers.size}`);
console.log(`  转推数: ${stats.totalRetweets}`);
console.log(`  回复数: ${stats.totalReplies}`);
console.log(`  话题数: ${Object.keys(stats.hashtags).length}`);
console.log(`  活跃天数: ${stats.daysActive.size}`);
console.log('----------------------------------------');
console.log('✓ 月报生成成功!');
console.log('输出文件:', outputFile);
console.log('========================================');
