# Twitter Watchdog 使用指南

## 一、启动服务

### 1.1 启动后端（API 服务）

```bash
cd /Users/dbwu/ai_project/twitter-watchdog-repo/backend
/Users/dbwu/.claude/skills/twitter-watchdog/venv/bin/python3 -m uvicorn app.main:app --port 8000
```

启动后：
- API 地址：http://localhost:8000
- Swagger 文档：http://localhost:8000/docs

### 1.2 启动前端（Web 界面）

```bash
cd /Users/dbwu/ai_project/twitter-watchdog-repo/frontend
npm run dev
```

启动后打开浏览器访问：http://localhost:3000

---

## 二、页面功能

### 2.1 控制台（首页 `/`）

控制台是主操作入口，提供四个快捷操作按钮：

| 按钮 | 功能 | 说明 |
|------|------|------|
| **完整流水线** | scrape → analyze → report | 一键完成抓取、分析、生成报告 |
| **数据采集** | 仅抓取推文 | 从关注列表 + 热门搜索获取原始数据 |
| **AI 分析** | 仅做 AI 筛选和总结 | 基于已有原始数据进行分析 |
| **生成报告** | 仅生成报告 | 基于已有分析结果生成 HTML/MD 报告 |

**每个按钮点击后会弹出参数配置弹窗**，可以自定义本次执行的参数（设置页只是默认值）。

首页还展示：
- 最近 5 条任务的执行状态
- 最新 3 份报告的预览

### 2.2 设置页（`/settings`）

设置页配置**默认参数**，每次执行任务时的弹窗会预填这些值。

#### 信息源
- **Twitter 用户名**：你的主账号（用于获取关注列表）
- **自定义账号**：额外监控的账号（标签式添加/删除）
- **采集时间范围**：默认回看多少小时

#### 分析风格
- **精简**（concise）：每条推文一句话摘要，适合快速浏览
- **标准**（standard）：1-2 句说明，包含来源和事实
- **详细**（advanced）：标准 + "为什么重要"分析

#### 自定义提示词
追加到 AI 分析 prompt 末尾的指令，例如：
- "重点关注 AI Agent 和 MCP 方向"
- "忽略纯营销内容"
- "增加对中文推文的关注"

#### 过滤规则
- **关键词列表**：AI 相关关键词（默认已配置，可增删）
- **最低互动量**：过滤低互动推文

#### Telegram 推送
配置 Bot Token 和 Chat ID，启用后流水线完成会自动推送摘要。

### 2.3 任务页（`/jobs`）

管理所有执行记录：

- **任务列表**：按时间倒序展示，包含类型、状态、耗时
- **状态标识**：
  - 灰色 = 等待中（pending）
  - 蓝色+动画 = 运行中（running）
  - 绿色 = 已完成（completed）
  - 红色 = 失败（failed）
  - 橙色 = 已取消（cancelled）
- **操作**：
  - 运行中 → 点击"取消"停止任务
  - 已结束 → 点击"删除"清理记录
- **任务详情**：点击任务查看实时运行日志（每 3 秒自动刷新）

### 2.4 报告页（`/reports`）

浏览所有生成的报告：

- **类型筛选**：全部 / 单次 / 日报 / 周报 / 月报
- **报告卡片**：显示类型、时间、推文数量
- **报告详情**：点击后直接在页面内渲染 HTML 报告
- **删除报告**：鼠标悬停显示删除按钮

---

## 三、执行参数详解

### 3.1 数据采集（Scrape）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 采集时间范围 | 回看最近 N 小时的推文 | 8 小时 |
| 热门推文上限 | 全网热门搜索最多返回条数 | 50 |
| 最低浏览量 | 热门推文的浏览量门槛 | 1000 |

采集流程：
1. 获取你的关注列表（~100 人）
2. 逐个抓取每个账号的最近推文
3. 合并 custom_accounts 中的额外账号
4. 执行 6 组关键词 × 2 种排序（Top + Latest）的全网热门搜索
5. 合并去重，保存原始数据到 `output/raw/`

### 3.2 AI 分析（Analyze）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 数据源 | 选择要分析的 raw 文件 | 最新 |
| 时间范围 | 按时间窗口过滤推文 | 8 小时 |
| 分析风格 | concise / standard / advanced | standard |
| 自定义提示词 | 追加指令 | 空 |

分析流程：
1. 读取 raw 数据文件
2. 按时间窗口过滤
3. Claude AI 批量判断每条推文是否 AI 相关
4. 标记紧急推文（🔴 突发 / 常规）
5. Claude AI 生成分类总结报告
6. 保存分析结果到 `output/analysis/`

### 3.3 生成报告（Report）

| 参数 | 说明 |
|------|------|
| 报告类型 | 单次报告 / 日报 / 周报 / 月报 |
| 数据源 | 单次：选择 analysis 文件；日报：选日期；周报：选周一日期；月报：选月份 |

报告类型说明：
- **单次报告**：基于一个 analysis 文件生成
- **日报**：聚合当天所有 analysis 文件，去重合并
- **周报**：聚合 7 天的 analysis 文件，Claude 重新整合
- **月报**：聚合整月 analysis 文件，Claude 重新整合

报告输出到 `output/reports/`，同时生成 HTML 和 Markdown 两种格式。

### 3.4 完整流水线（Pipeline）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 采集时间范围 | 同 Scrape | 8 小时 |
| 分析风格 | 同 Analyze | standard |
| 自定义提示词 | 同 Analyze | 空 |

流水线 = Scrape → Analyze → Report 三步串行执行。

---

## 四、热门搜索机制

系统使用 6 组关键词覆盖不同维度的 AI 话题：

| 组别 | 关键词 | 最低点赞 |
|------|--------|----------|
| 通用 AI | AI, artificial intelligence, AGI, ASI | 100 |
| 模型/产品 | LLM, GPT, ChatGPT, Claude, Gemini, DeepSeek, Grok | 100 |
| 公司 | OpenAI, Anthropic, DeepMind, Mistral | 100 |
| 开发工具 | AI agent, MCP, cursor, copilot, vibe coding | 50 |
| 技术概念 | transformer, diffusion, fine-tuning, RAG, prompt engineering | 50 |
| 中文 | 大模型, 人工智能, 机器学习, 深度学习 | 30 |

每组同时搜索 **Top**（热门排序）和 **Latest**（最新排序），合并去重后按浏览量排序。

---

## 五、典型使用场景

### 场景 1：每日快速了解 AI 动态

1. 打开控制台，点击"完整流水线"
2. 弹窗中设置 `采集时间 = 8`，风格选"标准"
3. 点击执行，等待完成（通常 3-5 分钟）
4. 到报告页查看最新报告

### 场景 2：深度分析特定时段

1. 先执行"数据采集"，设置较长时间范围（如 24 小时）
2. 再执行"AI 分析"，选择刚才的 raw 文件，风格选"详细"
3. 添加自定义提示词："重点关注 AI Agent 框架和工具链"
4. 最后执行"生成报告"

### 场景 3：生成周报

1. 确保过去一周每天都执行过采集和分析（建议配合 cron 定时任务）
2. 点击"生成报告"，类型选"周报"
3. 选择本周一的日期
4. 系统自动聚合 7 天的分析数据并生成综合报告

### 场景 4：添加新的监控账号

1. 到设置页，在"自定义账号"中添加新账号（如 `@AnthropicAI`）
2. 保存配置
3. 下次执行采集时会自动包含该账号

---

## 六、定时任务（可选）

配合 macOS launchd 或 cron 实现自动运行：

```bash
# 每天 8:00、14:00、20:00 自动执行流水线
0 8,14,20 * * * cd /Users/dbwu/ai_project/twitter-watchdog-repo/backend && \
  curl -s -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"type":"pipeline","params":{"hours_ago":8}}'
```

前提：后端服务需要保持运行。

---

## 七、API 速查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/config` | 获取配置 |
| PUT | `/api/config` | 更新配置 |
| POST | `/api/jobs` | 创建任务 |
| GET | `/api/jobs` | 任务列表 |
| GET | `/api/jobs/{id}` | 任务详情 |
| POST | `/api/jobs/{id}/cancel` | 取消任务 |
| DELETE | `/api/jobs/{id}` | 删除任务 |
| GET | `/api/reports` | 报告列表 |
| GET | `/api/reports/{id}` | 报告详情 |
| GET | `/api/reports/{id}/html` | 报告 HTML |
| DELETE | `/api/reports/{id}` | 删除报告 |
| GET | `/api/data/raw-files` | 原始数据文件列表 |
| GET | `/api/data/analysis-files` | 分析数据文件列表 |

---

## 八、目录结构

```
twitter-watchdog-repo/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 入口
│   │   ├── api/               # 路由（config, jobs, reports, data）
│   │   ├── models/            # 数据库模型 + Pydantic schema
│   │   ├── services/          # 引擎封装层
│   │   └── tasks/             # 后台任务执行器
│   └── data/                  # SQLite 数据库
├── frontend/                   # Next.js 前端
│   └── src/
│       ├── app/               # 页面（控制台、任务、报告、设置）
│       ├── components/        # UI 组件
│       └── lib/               # API 调用层
├── engine/                     # 核心引擎
│   └── twitter_watchdog.py    # 三层架构 CLI 工具
├── config/
│   └── config.yaml.example    # 配置模板
├── docs/
│   ├── PRODUCT_DESIGN.md      # 产品设计文档
│   └── USAGE_GUIDE.md         # 本使用指南
└── output/                     # 数据输出（通过 config 指定实际路径）
    ├── raw/                   # Layer 1 原始抓取
    ├── analysis/              # Layer 2 AI 分析
    └── reports/               # Layer 3 报告文件
```
