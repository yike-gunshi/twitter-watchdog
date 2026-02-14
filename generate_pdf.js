const fs = require('fs');
const path = require('path');

// Read the HTML file
const htmlPath = path.join(__dirname, 'ai_news.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf-8');

// For this environment, we'll create a simple text-based PDF-like document
// In a full setup, you would use a library like puppeteer or pdfkit

const outputPath = path.join(__dirname, 'ai_news.txt');
fs.writeFileSync(outputPath, htmlContent.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' '));

console.log('Generated: ai_news.txt');
console.log('Note: Full PDF generation requires browser/puppeteer setup.');
console.log('The HTML file is available at: ai_news.html');
