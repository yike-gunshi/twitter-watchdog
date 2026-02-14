# 项目清单

> 最后更新：2026-02-14
> 维护者：老大

---

## 项目管理规则

- 所有项目使用 Git 维护
- 每次完成功能点后，提交并推送到 GitHub
- 每个项目在单独文件夹中
- 工作目录：`/root/.openclaw/workspace/`

---

## 活跃项目

### 1. hongbao-cover-store
- **仓库**: https://github.com/yike-gunshi/hongbao-cover-store
- **本地路径**: `/root/.openclaw/workspace/hongbao-cover-store`
- **用途**: 红包封面存储
- **状态**: 活跃维护
- **最近更新**: 2026-02-11

---

### 2. twitter-watchdog
- **仓库**: https://github.com/yike-gunshi/twitter-watchdog
- **本地路径**: `/root/.openclaw/workspace/twitter-watchdog`
- **用途**: Twitter AI 推文监控系统
- **功能**:
  - 定时抓取 Twitter 关注列表推文
  - AI 智能筛选（Claude API）
  - 定时推送到 Telegram
  - 生成日报和月报
  - Web 服务器托管报告
- **状态**: 活跃开发中
- **最近更新**: 2026-02-14
- **最新功能**:
  - ✅ 推送系统（5个时间点自动推送）
  - ✅ HTML 模板（支持明亮/暗黑模式）
  - ✅ AI 智能总结
  - ✅ 日报/月报生成器
  - 📋 待实现：Web 服务器部署、定时任务安装
- **配置文件**:
  - `config/config.yaml` - 主配置文件
  - `config/config.yaml.example` - 配置示例
- **脚本**:
  - `scripts/twitter_watchdog.py` - 主脚本
  - `scripts/push_report.sh` - 推送脚本
  - `scripts/generate_daily_report.js` - 日报生成
  - `scripts/generate_monthly_report.js` - 月报生成
  - `scripts/generate_index.js` - 索引生成
  - `scripts/setup_web.sh` - Web 服务器设置
  - `scripts/install_schedulers.sh` - 定时任务安装
- **模板**:
  - `templates/push.html` - 推送模板（浅色）
  - `templates/push_detailed.html` - 推送模板（详细）
  - `templates/daily.html` - 日报模板
  - `templates/monthly.html` - 月报模板
  - `templates/index.html` - 索引模板
- **输出**:
  - `output/` - 推文数据（JSON/Markdown）
  - `push/` - 推送 HTML 文件
  - `reports/` - 日报/月报报告

---

## 工作流

### 开发新功能

```bash
# 1. 进入项目目录
cd /root/.openclaw/workspace/twitter-watchdog

# 2. 创建功能分支（可选）
git checkout -b feature/new-feature

# 3. 开发功能
# 编写/修改代码...

# 4. 测试功能
./scripts/push_report.sh --hours-ago 4

# 5. 提交代码
git add .
git commit -m "feat: 添加新功能描述"

# 6. 推送到 GitHub
git push origin main
# 或
git push origin feature/new-feature

# 7. 创建 Pull Request（如果用分支）
gh pr create --title "新功能" --body "功能描述"
```

### 更新现有功能

```bash
# 1. 拉取最新代码
cd /root/.openclaw/workspace/twitter-watchdog
git pull origin main

# 2. 修改代码...

# 3. 测试...

# 4. 提交
git add .
git commit -m "fix: 修复问题描述"
git push origin main
```

---

## Git 常用命令

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline -10

# 查看分支
git branch

# 创建分支
git checkout -b feature/name

# 切换分支
git checkout main

# 合并分支
git merge feature/name

# 查看远程
git remote -v

# 拉取最新
git pull origin main

# 推送
git push origin main

# 查看差异
git diff

# 暂存修改
git stash
git stash pop
```

---

## 待办事项

### twitter-watchdog
- [ ] 部署 Web 服务器（`setup_web.sh`）
- [ ] 安装定时任务（`install_schedulers.sh`）
- [ ] 配置域名访问（通过 Cloudflare）
- [ ] 添加可视化图表（二期）
- [ ] 支持英文报告（二期）
- [ ] 数据备份机制

---

## 注意事项

1. **敏感信息**：配置文件包含 API Keys，已加入 `.gitignore`，不会提交到 GitHub
2. **环境变量**：某些配置通过环境变量传递（如代理设置）
3. **日志管理**：定期清理旧的日志文件和生成的报告
4. **备份**：重要配置文件（如 API Keys）应定期备份到安全位置

---

## 快速链接

- GitHub: https://github.com/yike-gunshi?tab=repositories
- Twitter Watchdog 仓库: https://github.com/yike-gunshi/twitter-watchdog
- 红包封面仓库: https://github.com/yike-gunshi/hongbao-cover-store
- 工作区: `/root/.openclaw/workspace/`

---

_此文件会随着项目进展持续更新_
