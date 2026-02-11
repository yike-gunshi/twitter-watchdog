# Twitter Watchdog

定时监控 Twitter 关注列表，自动抓取 AI 相关推文，由 Claude 智能筛选并生成结构化日报/周报/月报。

## 它能做什么

1. **日报** — 抓取你 Twitter 关注列表中所有用户的最新推文 + 全网热门 AI 推文，由 Claude 自动判断 AI 相关性，生成事实清单
2. **周报** — 基于历史日报数据，自动去重合并，生成结构化周报（本期要点 + 分类整理）
3. **月报** — 基于历史日报数据，自动去重合并，生成结构化月报

## 输出效果

### 日报

```
- [Obsidian 1.12 发布 CLI 命令行工具](https://x.com/...)。支持从终端控制 Obsidian，
  可进行创建、读取、编辑、删除笔记，搜索 vault 内容，管理任务等操作。

- [Chrome 正在开发 WebMCP](https://x.com/...)。网站可以直接给 AI Agent 暴露结构化工具，
  预计可将网页扫描时间从 3-4 分钟缩短至 3 秒。
```

### 周报 / 月报

```markdown
# AI 推文周报 — 02/10 ~ 02/17

## 本期要点

- OpenAI 推出 GPT-5.2 Deep Research 升级和 Codex App，首周下载量超 100 万
- Chrome 正在开发 WebMCP 协议，每个网站将成为 MCP server
- ...

## AI 产品与工具

- [Claude Cowork 正式登陆 Windows](https://x.com/...)。提供与 macOS 一样的功能
- [ChatGPT Deep Research 升级为 GPT-5.2](https://x.com/...)。新增内置文档查看器
- ...

## AI 模型与技术
## AI 开发者生态
## AI 行业动态
## AI 研究与观点
```

完整示例见 [examples/](examples/) 目录。

## 架构

```
┌─────────────────────┐     ┌──────────────────────┐
│  X Official API     │     │   twitterapi.io      │
│  (免费)             │     │   ($0.15/1k tweets)  │
│                     │     │                      │
│  获取关注列表        │     │  抓取用户推文         │
│  (带 24h 本地缓存)  │     │  全网热门 AI 搜索     │
└────────┬────────────┘     └────────┬─────────────┘
         │                           │
         └──────────┬────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   时间窗口过滤       │
         │   去重               │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │   Claude API        │
         │                     │
         │  1. 判断 AI 相关性   │
         │  2. 生成情报清单     │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │  输出报告            │
         │  - JSON 数据        │
         │  - Markdown 日报    │
         │  - 结构化周报/月报   │
         └─────────────────────┘
```

**为什么用混合 API 架构？**

| API | 用途 | 费用 | 原因 |
|-----|------|------|------|
| X Official API | 获取关注列表 | 免费 | 官方 API 免费提供关注列表接口 |
| twitterapi.io | 抓取推文内容 + 热门搜索 | $0.15/1k tweets | X 官方推文 API 需要 $100/月，twitterapi.io 便宜 100 倍 |
| Claude API | AI 筛选 + 总结 + 周报/月报整合 | ~$0.01/次 | 比关键词匹配更准确，能识别语义相关的推文 |

## 网络要求

本工具需要访问以下外部服务：

- `api.twitter.com` — X 官方 API（获取关注列表）
- `api.twitterapi.io` — 第三方推文抓取服务
- Claude API 端点（官方或你配置的代理地址）

**如果你在中国大陆**，需要确保运行环境能访问上述地址。常见方案：

1. **系统代理 / VPN** — 开启全局或规则代理，确保终端流量走代理
2. **终端代理** — 在运行前设置环境变量：
   ```bash
   export https_proxy=http://127.0.0.1:7890
   export http_proxy=http://127.0.0.1:7890
   ```
   其中 `7890` 换成你代理软件的实际端口（Clash 默认 7890，V2Ray 默认 1080 等）
3. **在海外服务器上运行** — 部署到 VPS 后通过 cron 定时执行
4. **Claude API 代理** — 如果只有 Claude API 无法直连，可在 `config.yaml` 的 `ai_summary.base_url` 配置兼容 Anthropic API 的代理地址

> 注意：周报和月报只需要 Claude API（不访问 Twitter），所以如果你已有历史日报数据，生成周报/月报时不需要翻墙。

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/yike-gunshi/twitter-watchdog.git
cd twitter-watchdog

python3 -m venv venv
source venv/bin/activate
pip install requests pyyaml
```

### 2. 获取 API 凭证

你需要准备三组凭证：

**a) X Official API（免费）**

1. 前往 [developer.twitter.com](https://developer.twitter.com/) 创建开发者账号
2. 创建一个 App，获取 Consumer Key 和 Consumer Secret
3. 只需要 App-only 认证（Bearer Token），不需要用户级别 OAuth

**b) twitterapi.io（按量付费）**

1. 前往 [twitterapi.io](https://twitterapi.io/) 注册
2. 获取 API Key
3. 费用：$0.15/1000 条推文

**c) Claude API（推荐）**

1. 前往 [console.anthropic.com](https://console.anthropic.com/) 获取 API Key
2. 或使用兼容 Anthropic API 的第三方代理服务（在 `base_url` 中配置）
3. 也可通过环境变量 `ANTHROPIC_API_KEY` 设置

### 3. 配置

```bash
cp config/config.yaml.example config/config.yaml
```

编辑 `config/config.yaml`，填入你的凭证和用户名：

```yaml
# 必填项
twitter_api:
  consumer_key: "你的 Consumer Key"
  consumer_secret: "你的 Consumer Secret"

twitterapi_io:
  api_key: "你的 twitterapi.io Key"

twitter:
  username: "你的 Twitter 用户名"  # 不带 @

ai_summary:
  enabled: true
  api_key: "你的 Claude API Key"
  # base_url: "https://your-proxy.com/api"  # 可选：API 代理地址
```

### 4. 运行

```bash
# 抓取最近 24 小时的 AI 推文（日报）
python3 scripts/twitter_watchdog.py --hours-ago 24

# 抓取最近 4 小时
python3 scripts/twitter_watchdog.py --hours-ago 4

# 生成周报（从指定日期起 7 天）
python3 scripts/twitter_watchdog.py --weekly 2026-02-10

# 生成月报
python3 scripts/twitter_watchdog.py --monthly 2026-02

# 指定输出目录
python3 scripts/twitter_watchdog.py --hours-ago 8 --output-dir ./my_output
```

## 命令行参数

### 日报参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--hours-ago N` | 只保留最近 N 小时内的推文 | 不限 |
| `--max-followings N` | 关注列表抓取范围（0=全部） | 0 |
| `--tweets-per-user N` | 每个用户最多推文数 | 20 |
| `--trending-count N` | 热门推文最多条数 | 20 |
| `--trending-query "..."` | 热门搜索关键词（Twitter 搜索语法） | 见配置文件 |
| `--min-faves N` | 热门推文最低浏览量 | 2000 |
| `--language LANG` | 语言过滤（all/en/zh/ja...） | all |
| `--exclude-users "a,b"` | 排除的用户名（逗号分隔） | 无 |
| `--output-dir PATH` | 输出目录 | 见配置文件 |
| `--reset-state` | 重置去重状态，重新拉取全量 | - |
| `--no-trending` | 禁用热门搜索（只看关注列表） | - |
| `--no-summary` | 禁用 AI 总结（只抓取原始推文） | - |

### 周报 / 月报参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--weekly YYYY-MM-DD` | 生成从指定日期起 7 天的周报 | `--weekly 2026-02-10` |
| `--monthly YYYY-MM` | 生成指定月份的月报 | `--monthly 2026-02` |

周报和月报基于 output 目录中的历史 `ai_tweets_*.json` 文件生成，**不需要 Twitter API 凭证**，只需要 Claude API。

所有参数都会覆盖 `config.yaml` 中的对应配置。

## 工作原理

### 日报流程

1. **获取关注列表** — X 官方 API 获取你的关注用户（免费，带 24h 本地缓存）
2. **抓取推文** — twitterapi.io 抓取每个用户的最新推文 + 全网热门 AI 搜索
3. **时间窗口过滤** — 根据 `--hours-ago` 过滤，自动去重
4. **AI 智能筛选** — Claude 判断每条推文是否与 AI 相关（ai_filter 模式）
5. **生成情报清单** — Claude 生成结构化的事实清单，每条附原文链接
6. **保存报告** — 输出 JSON + Markdown 日报到 output 目录

### 周报 / 月报流程

1. **扫描历史数据** — 读取 output 目录中指定日期范围的 `ai_tweets_*.json` 文件
2. **提取新闻条目** — 从每个 JSON 的 `ai_summary` 字段解析出新闻条目
3. **本地去重** — 按 URL 去重，保留描述最详细的版本
4. **Claude 整合** — 发送给 Claude 进行最终整合：生成"本期要点" + 分类整理
5. **保存报告** — 输出 `weekly_report_YYYY_MM_DD.md` 或 `monthly_report_YYYY_MM.md`

> 周报/月报的质量取决于历史日报数据的完整性。建议通过定时任务每天运行 3~5 次日报，确保数据覆盖全天。

## AI 筛选模式

配置 `ai_summary.ai_filter: true` 后（默认开启），工作流变为：

1. **抓取全量推文** — 不做关键词预过滤，收集关注列表所有推文
2. **发送给 Claude** — 一次性发送所有推文，让 Claude 判断哪些与 AI 相关
3. **Claude 返回两部分** — 结构化的情报清单 + AI 相关推文 ID 列表
4. **过滤数据** — 根据 Claude 返回的 ID 过滤原始数据，只保留 AI 相关推文
5. **生成报告** — 基于过滤后的数据生成 Markdown/JSON 报告

如果设为 `false`，则退回关键词匹配模式（使用 `filters.keywords.include` 列表）。

## 输出文件

### 日报（每次运行生成）

| 文件 | 说明 |
|------|------|
| `ai_tweets_YYYYMMDD_HHMMSS.json` | 完整数据，含所有推文原始字段和 AI 总结文本（供周报/月报使用） |
| `ai_tweets_YYYYMMDD_HHMMSS.md` | Markdown 详细报告，含 AI 总结 + 每条推文详情 |
| `latest_summary.md` | 汇总摘要，每次覆盖更新，适合快速查看 |

### 周报 / 月报

| 文件 | 说明 |
|------|------|
| `weekly_report_YYYY_MM_DD.md` | 结构化周报（本期要点 + 5 大分类） |
| `monthly_report_YYYY_MM.md` | 结构化月报（本期要点 + 5 大分类） |

周报/月报的分类包含：AI 产品与工具、AI 模型与技术、AI 开发者生态、AI 行业动态、AI 研究与观点。按重要性从高到低排列，无内容的分类自动省略。

## 调度策略

推荐通过 cron、launchd 或其他调度工具定时执行日报，覆盖全天。日报数据会自动累积在 output 目录，是生成周报/月报的数据来源。

| 时间 (UTC+8) | 命令 | 覆盖区间 |
|--------------|------|----------|
| 08:00 | `python3 twitter_watchdog.py --hours-ago 8` | 00:00 ~ 08:00 |
| 12:00 | `python3 twitter_watchdog.py --hours-ago 4` | 08:00 ~ 12:00 |
| 18:00 | `python3 twitter_watchdog.py --hours-ago 6` | 12:00 ~ 18:00 |
| 21:00 | `python3 twitter_watchdog.py --hours-ago 3` | 18:00 ~ 21:00 |
| 00:00 | `python3 twitter_watchdog.py --hours-ago 3` | 21:00 ~ 00:00 |

每周/每月可额外加一条周报/月报任务：

```bash
# 每周一 09:00 生成上周周报（上周一日期）
0 9 * * 1 cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --weekly $(date -v-7d +\%Y-\%m-\%d)

# 每月 1 号 09:00 生成上月月报
0 9 1 * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --monthly $(date -v-1m +\%Y-\%m)
```

### macOS launchd

```bash
# 安装定时任务
bash scripts/install.sh

# 查看状态
launchctl list | grep twitter-watchdog

# 停止
launchctl unload ~/Library/LaunchAgents/com.user.twitter-watchdog.plist

# 重启
launchctl load ~/Library/LaunchAgents/com.user.twitter-watchdog.plist
```

### crontab

```bash
crontab -e

# 日报（根据你的路径调整）
0 8 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 8
0 12 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 4
0 18 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 6
0 21 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 3
0 0 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 3
```

## 费用估算

以 100 个关注用户、每天运行 5 次为例：

| 项目 | 单次费用 | 每日费用 | 每月费用 |
|------|----------|----------|----------|
| twitterapi.io（~100 次 API 调用） | ~$0.02 | ~$0.10 | ~$3 |
| Claude API — 日报（~30k input + ~3k output tokens） | ~$0.01 | ~$0.05 | ~$1.5 |
| Claude API — 周报/月报（按需生成） | ~$0.02/次 | - | ~$0.1 |
| **合计** | - | **~$0.15** | **~$4.6** |

## License

MIT
