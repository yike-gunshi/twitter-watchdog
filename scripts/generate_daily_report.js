#!/usr/bin/env node

/**
 * Twitter Watchdog 日报生成器
 * 用法: node generate_daily_report.js [date]
 */

const fs = require('fs');
const path = require('path');

// 配置
const PROJECT_DIR = path.join(__dirname, '..');
const OUTPUT_DIR = path.join(PROJECT_DIR, 'output');
const TEMPLATE_DIR = path.join(PROJECT_DIR, 'templates');
const REPORT_DIR = '/var/www/twitter-reports/daily';

// 日期参数
const reportDate = process.argv[2] || new Date().toISOString().split('T')[0];
const dateObj = new Date(reportDate);

// 确保输出目录存在
if (!fs.existsSync(REPORT_DIR)) {
    console.error('错误: 报告目录不存在:', REPORT_DIR);
    console.log('请先运行 setup_web.sh 创建目录');
    process.exit(1);
}

console.log('========================================');
console.log('Twitter Watchdog 日报生成器');
console.log('========================================');
console.log('报告日期:', reportDate);
console.log('开始时间:', new Date().toLocaleString('zh-CN'));
console.log('----------------------------------------');

// 读取 output 目录中的所有 JSON 文件
console.log('正在读取数据文件...');
let allTweets = [];
try {
    const files = fs.readdirSync(OUTPUT_DIR);
    const jsonFiles = files.filter(f => f.endsWith('.json'));

    jsonFiles.forEach(file => {
        const filePath = path.join(OUTPUT_DIR, file);
        try {
            const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            const tweets = data.tweets || data;

            // 过滤当日数据
            const dayTweets = tweets.filter(tweet => {
                const tweetDate = tweet.created_at || tweet.time || tweet.date;
                if (!tweetDate) return false;
                return tweetDate.startsWith(reportDate);
            });

            allTweets = allTweets.concat(dayTweets);
        } catch (error) {
            console.warn(`读取文件 ${file} 失败:`, error.message);
        }
    });

    console.log(`找到 ${allTweets.length} 条推文数据`);
} catch (error) {
    console.error('读取数据失败:', error.message);
    process.exit(1);
}

// 时间段分组定义
const timeSlots = [
    { name: '00:00~08:00', start: 0, end: 8 },
    { name: '08:00~12:00', start: 8, end: 12 },
    { name: '12:00~18:00', start: 12, end: 18 },
    { name: '18:00~22:00', start: 18, end: 22 },
    { name: '22:00~02:00', start: 22, end: 32 } // 跨天处理
];

// 统计数据
const stats = {
    totalTweets: allTweets.length,
    totalRetweets: 0,
    totalReplies: 0,
    uniqueUsers: new Set(),
    hashtags: {},
    userTweets: {},
    timeSlotTweets: timeSlots.map(() => [])
};

// 处理推文数据
allTweets.forEach(tweet => {
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

    // 按时间段分组
    const tweetDate = tweet.created_at || tweet.time;
    if (tweetDate) {
        const match = tweetDate.match(/(\d{2}):(\d{2}):?/);
        if (match) {
            const hour = parseInt(match[1]);
            timeSlots.forEach((slot, index) => {
                if (slot.start <= hour && hour < slot.end) {
                    stats.timeSlotTweets[index].push(tweet);
                } else if (slot.start === 22 && (hour >= 22 || hour < 2)) {
                    stats.timeSlotTweets[index].push(tweet);
                }
            });
        }
    }
});

// 排序
const topUsers = Object.entries(stats.userTweets)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

const topHashtags = Object.entries(stats.hashtags)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

// 生成时间段 HTML
const generateTimeSlotHTML = (slot, tweets) => {
    const tweetCount = tweets.length;
    const users = new Set(tweets.map(t => t.username || t.user)).size;
    return `
        <div class="time-slot">
            <div class="time-slot-header">
                <div class="time-slot-title">${slot.name}</div>
                <div class="time-slot-stats">
                    <div class="time-slot-stat">推文: <strong>${tweetCount}</strong></div>
                    <div class="time-slot-stat">用户: <strong>${users}</strong></div>
                </div>
            </div>
        </div>
    `;
};

const timeSlotsHTML = stats.timeSlotTweets
    .map((tweets, index) => generateTimeSlotHTML(timeSlots[index], tweets))
    .join('');

// 生成用户卡片 HTML
const generateUserCard = (username, count) => {
    const avatarLetter = username.charAt(0).toUpperCase();
    return `
        <div class="user-card">
            <div class="user-avatar">${avatarLetter}</div>
            <div class="user-name">@${username}</div>
            <div class="user-stats">${count} 条推文</div>
        </div>
    `;
};

const topUsersHTML = topUsers.map(([user, count]) => generateUserCard(user, count)).join('');

// 生成话题 HTML
const hashtagsHTML = topHashtags.map(([tag, count]) =>
    `<div class="hashtag-item">#${tag} <span class="count">${count}</span></div>`
).join('');

// 生成最新推文 HTML
const generateTweetPreview = (tweet) => {
    const username = tweet.username || tweet.user;
    const avatarLetter = username ? username.charAt(0).toUpperCase() : 'U';
    const time = (tweet.created_at || tweet.time || '').split(' ').slice(1).join(' ') || '';
    return `
        <div class="tweet-preview">
            <div class="tweet-preview-header">
                <div class="tweet-preview-avatar">${avatarLetter}</div>
                <div class="tweet-preview-user">
                    <div class="tweet-preview-name">@${username}</div>
                </div>
                <div class="tweet-preview-time">${time}</div>
            </div>
            <div class="tweet-preview-content">${tweet.text || tweet.content || ''}</div>
        </div>
    `;
};

const recentTweets = allTweets.slice(0, 5);
const recentTweetsHTML = recentTweets.length > 0
    ? recentTweets.map(generateTweetPreview).join('')
    : '<div class="no-data">暂无推文</div>';

// 读取模板
const templateFile = path.join(TEMPLATE_DIR, 'daily.html');
let htmlContent;
if (fs.existsSync(templateFile)) {
    htmlContent = fs.readFileSync(templateFile, 'utf8');
} else {
    console.error('模板文件不存在:', templateFile);
    process.exit(1);
}

// 替换变量
const currentMonth = dateObj.toISOString().slice(0, 7);
const now = new Date();
const replacements = {
    '{{DATE}}': reportDate,
    '{{DATA_SOURCE}}': 'Twitter Watchdog',
    '{{GENERATED_AT}}': now.toLocaleString('zh-CN'),
    '{{TOTAL_TWEETS}}': stats.totalTweets,
    '{{ACTIVE_USERS}}': stats.uniqueUsers.size,
    '{{TOTAL_RETWEETS}}': stats.totalRetweets,
    '{{TOTAL_REPLIES}}': stats.totalReplies,
    '{{TOTAL_HASHTAGS}}': Object.keys(stats.hashtags).length,
    '{{TIME_SLOTS}}': timeSlotsHTML,
    '{{TOP_USERS}}': topUsersHTML,
    '{{HASHTAGS}}': hashtagsHTML,
    '{{RECENT_TWEETS}}': recentTweetsHTML,
    '{{CURRENT_MONTH}}': currentMonth
};

for (const [key, value] of Object.entries(replacements)) {
    htmlContent = htmlContent.replace(new RegExp(key.replace(/[{}]/g, '\\$&'), 'g'), value);
}

// 写入输出文件
const outputFile = path.join(REPORT_DIR, `${reportDate}.html`);
fs.writeFileSync(outputFile, htmlContent);

console.log('----------------------------------------');
console.log('统计数据:');
console.log(`  总推文数: ${stats.totalTweets}`);
console.log(`  活跃用户: ${stats.uniqueUsers.size}`);
console.log(`  转推数: ${stats.totalRetweets}`);
console.log(`  回复数: ${stats.totalReplies}`);
console.log(`  话题数: ${Object.keys(stats.hashtags).length}`);
console.log('----------------------------------------');
console.log('✓ 日报生成成功!');
console.log('输出文件:', outputFile);
console.log('========================================');
