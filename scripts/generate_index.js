#!/usr/bin/env node

/**
 * Twitter Watchdog 索引页面生成器
 * 扫描 daily 和 monthly 目录，生成历史索引页面
 */

const fs = require('fs');
const path = require('path');

// 配置
const PROJECT_DIR = path.join(__dirname, '..');
const TEMPLATE_DIR = path.join(PROJECT_DIR, 'templates');
const DAILY_REPORT_DIR = '/var/www/twitter-reports/daily';
const MONTHLY_REPORT_DIR = '/var/www/twitter-reports/monthly';
const INDEX_FILE = '/var/www/twitter-reports/index.html';

console.log('========================================');
console.log('Twitter Watchdog 索引页面生成器');
console.log('========================================');
console.log('开始时间:', new Date().toLocaleString('zh-CN'));
console.log('----------------------------------------');

// 读取日报
console.log('正在扫描日报...');
let dailyReports = [];
if (fs.existsSync(DAILY_REPORT_DIR)) {
    const files = fs.readdirSync(DAILY_REPORT_DIR)
        .filter(f => f.endsWith('.html'))
        .sort()
        .reverse();

    files.forEach(file => {
        const filePath = path.join(DAILY_REPORT_DIR, file);
        try {
            const html = fs.readFileSync(filePath, 'utf8');
            const tweetMatch = html.match(/总推文数<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);
            const userMatch = html.match(/活跃用户<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);

            dailyReports.push({
                date: file.replace('.html', ''),
                tweets: tweetMatch ? parseInt(tweetMatch[1]) : 0,
                users: userMatch ? parseInt(userMatch[1]) : 0,
                file: file
            });
        } catch (error) {
            console.warn('读取日报失败:', file, error.message);
        }
    });
}

console.log(`找到 ${dailyReports.length} 份日报`);

// 读取月报
console.log('正在扫描月报...');
let monthlyReports = [];
if (fs.existsSync(MONTHLY_REPORT_DIR)) {
    const files = fs.readdirSync(MONTHLY_REPORT_DIR)
        .filter(f => f.endsWith('.html'))
        .sort()
        .reverse();

    files.forEach(file => {
        const filePath = path.join(MONTHLY_REPORT_DIR, file);
        try {
            const html = fs.readFileSync(filePath, 'utf8');
            const tweetMatch = html.match(/总推文数<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);
            const userMatch = html.match(/活跃用户<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);
            const retweetMatch = html.match(/转推数<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);
            const replyMatch = html.match(/回复数<\/div>[\s\S]*?<div class="value">(\d+)<\/div>/);

            monthlyReports.push({
                month: file.replace('.html', ''),
                tweets: tweetMatch ? parseInt(tweetMatch[1]) : 0,
                users: userMatch ? parseInt(userMatch[1]) : 0,
                retweets: retweetMatch ? parseInt(retweetMatch[1]) : 0,
                replies: replyMatch ? parseInt(replyMatch[1]) : 0,
                file: file
            });
        } catch (error) {
            console.warn('读取月报失败:', file, error.message);
        }
    });
}

console.log(`找到 ${monthlyReports.length} 份月报`);

// 统计总数据
const totalTweets = [...dailyReports, ...monthlyReports].reduce((sum, r) => sum + r.tweets, 0);
const totalUsers = Math.max(...dailyReports.map(r => r.users), 0);
const recentDaily = dailyReports.slice(0, 8);

// 生成最新日报 HTML
const recentDailyHTML = recentDaily.length > 0
    ? recentDaily.map(report => `
        <a href="/daily/${report.file}" class="report-card">
            <div class="date">${report.date}</div>
            <div class="stats">
                <span>📝 ${report.tweets}</span>
                <span>👥 ${report.users}</span>
            </div>
        </a>
    `).join('')
    : '<div class="empty-state"><div class="icon">📭</div>暂无日报</div>';

// 生成月报 HTML
const monthlyHTML = monthlyReports.length > 0
    ? monthlyReports.map(report => `
        <div class="monthly-card">
            <div class="month">${report.month}</div>
            <div class="stats-grid">
                <div class="stat-item"><strong>${report.tweets}</strong>推文</div>
                <div class="stat-item"><strong>${report.users}</strong>用户</div>
                <div class="stat-item"><strong>${report.retweets}</strong>转推</div>
                <div class="stat-item"><strong>${report.replies}</strong>回复</div>
            </div>
            <a href="/monthly/${report.file}" class="view-btn">查看详情 →</a>
        </div>
    `).join('')
    : '<div class="empty-state"><div class="icon">📭</div>暂无月报</div>';

// 生成详细统计 HTML
let statsDetailHTML = '<div class="report-grid">';
if (dailyReports.length > 0) {
    // 本月推文
    const thisMonth = new Date().toISOString().slice(0, 7);
    const thisMonthReports = dailyReports.filter(r => r.date.startsWith(thisMonth));
    const thisMonthTweets = thisMonthReports.reduce((sum, r) => sum + r.tweets, 0);

    statsDetailHTML += `
        <div class="report-card">
            <div class="date">本月推文</div>
            <div class="stats"><span>${thisMonthTweets}</span></div>
        </div>
    `;

    // 平均每日推文
    const avgTweets = thisMonthReports.length > 0
        ? Math.round(thisMonthTweets / thisMonthReports.length)
        : 0;
    statsDetailHTML += `
        <div class="report-card">
            <div class="date">日均推文</div>
            <div class="stats"><span>${avgTweets}</span></div>
        </div>
    `;

    // 最活跃的一天
    if (thisMonthReports.length > 0) {
        const mostActive = thisMonthReports.reduce((max, r) => r.tweets > max.tweets ? r : max);
        statsDetailHTML += `
            <div class="report-card">
                <div class="date">最活跃日</div>
                <div class="stats"><span>${mostActive.date}</span></div>
            </div>
        `;
    }
}
statsDetailHTML += '</div>';

// 读取模板
const templateFile = path.join(TEMPLATE_DIR, 'index.html');
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
    '{{LAST_UPDATE}}': now.toLocaleString('zh-CN'),
    '{{TOTAL_DAILY_REPORTS}}': dailyReports.length,
    '{{TOTAL_MONTHLY_REPORTS}}': monthlyReports.length,
    '{{TOTAL_TWEETS}}': totalTweets,
    '{{TOTAL_USERS}}': totalUsers,
    '{{RECENT_DAILY}}': recentDailyHTML,
    '{{MONTHLY_REPORTS}}': monthlyHTML,
    '{{STATS_DETAIL}}': statsDetailHTML,
    '{{GENERATED_AT}}': now.toLocaleString('zh-CN')
};

for (const [key, value] of Object.entries(replacements)) {
    htmlContent = htmlContent.replace(new RegExp(key.replace(/[{}]/g, '\\$&'), 'g'), value);
}

// 写入输出文件
fs.writeFileSync(INDEX_FILE, htmlContent);

console.log('----------------------------------------');
console.log('统计信息:');
console.log(`  日报总数: ${dailyReports.length}`);
console.log(`  月报总数: ${monthlyReports.length}`);
console.log(`  总推文数: ${totalTweets}`);
console.log('----------------------------------------');
console.log('✓ 索引页面生成成功!');
console.log('输出文件:', INDEX_FILE);
console.log('========================================');
