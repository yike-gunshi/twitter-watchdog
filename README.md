# Twitter Watchdog

定时监控 Twitter 关注列表，自动抓取 AI 相关推文，由 Claude 智能筛选并生成结构化情报清单。

## 它能做什么

1. 抓取你 Twitter 关注列表中所有用户的最新推文
2. 搜索全网热门 AI 推文（按浏览量筛选）
3. 由 Claude 自动判断哪些推文与 AI 相关（不依赖关键词匹配）
4. 生成扁平化的事实清单，每条附原文链接，方便快速跳转

## 输出效果

```
- [Obsidian 1.12 发布 CLI 命令行工具](https://x.com/...)。支持从终端控制 Obsidian，
  可进行创建、读取、编辑、删除笔记，搜索 vault 内容，管理任务等操作。

- [Chrome 正在开发 WebMCP](https://x.com/...)。网站可以直接给 AI Agent 暴露结构化工具，
  预计可将网页扫描时间从 3-4 分钟缩短至 3 秒。

- [Google 开源 LangExtract 文本数据提取工具](https://x.com/...)。利用大语言模型从
  非结构化文档中提取结构化数据，只需几行代码和几个示例。
```

完整示例见 [examples/latest_summary.md](examples/latest_summary.md)。

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
         │  - Markdown 详情    │
         │  - JSON 数据        │
         │  - 汇总摘要         │
         │  - macOS 通知       │
         └─────────────────────┘
```

**为什么用混合 API 架构？**

| API | 用途 | 费用 | 原因 |
|-----|------|------|------|
| X Official API | 获取关注列表 | 免费 | 官方 API 免费提供关注列表接口 |
| twitterapi.io | 抓取推文内容 + 热门搜索 | $0.15/1k tweets | X 官方推文 API 需要 $100/月，twitterapi.io 便宜 100 倍 |
| Claude API | AI 筛选 + 总结 | ~$0.01/次 | 比关键词匹配更准确，能识别语义相关的推文 |

## 快速开始

### 1. 安装依赖

```bash
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

**c) Claude API（可选，推荐）**

1. 前往 [console.anthropic.com](https://console.anthropic.com/) 获取 API Key
2. 或使用兼容 Anthropic API 的第三方代理服务
3. 环境变量：`ANTHROPIC_API_KEY` 或在配置文件中填写

### 3. 配置

```bash
cp config/config.yaml.example config/config.yaml
```

编辑 `config/config.yaml`，填入你的凭证和用户名。

### 4. 运行

```bash
# 抓取最近 24 小时的 AI 推文
python3 scripts/twitter_watchdog.py --hours-ago 24

# 抓取最近 4 小时
python3 scripts/twitter_watchdog.py --hours-ago 4

# 指定输出目录
python3 scripts/twitter_watchdog.py --hours-ago 8 --output-dir ./my_output

# 禁用热门搜索（只看关注列表）
python3 scripts/twitter_watchdog.py --hours-ago 4 --no-trending

# 禁用 AI 总结（只抓取原始推文）
python3 scripts/twitter_watchdog.py --hours-ago 4 --no-summary
```

## 命令行参数

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
| `--no-trending` | 禁用热门搜索 | - |
| `--no-summary` | 禁用 AI 总结 | - |

所有参数都会覆盖 `config.yaml` 中的对应配置。

## AI 筛选模式

配置 `ai_summary.ai_filter: true` 后（默认开启），工作流变为：

1. **抓取全量推文** — 不做关键词预过滤，收集关注列表所有推文
2. **发送给 Claude** — 一次性发送所有推文，让 Claude 判断哪些与 AI 相关
3. **Claude 返回两部分** — 结构化的情报清单 + AI 相关推文 ID 列表
4. **过滤数据** — 根据 Claude 返回的 ID 过滤原始数据，只保留 AI 相关推文
5. **生成报告** — 基于过滤后的数据生成 Markdown/JSON 报告

如果设为 `false`，则退回关键词匹配模式（使用 `filters.keywords.include` 列表）。

## 调度策略

推荐通过 cron、launchd 或其他调度工具定时执行，覆盖全天：

| 时间 (UTC+8) | 命令 | 覆盖区间 |
|--------------|------|----------|
| 08:00 | `python3 twitter_watchdog.py --hours-ago 8` | 00:00 ~ 08:00 |
| 12:00 | `python3 twitter_watchdog.py --hours-ago 4` | 08:00 ~ 12:00 |
| 18:00 | `python3 twitter_watchdog.py --hours-ago 6` | 12:00 ~ 18:00 |
| 21:00 | `python3 twitter_watchdog.py --hours-ago 3` | 18:00 ~ 21:00 |
| 00:00 | `python3 twitter_watchdog.py --hours-ago 3` | 21:00 ~ 00:00 |

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
# 编辑 crontab
crontab -e

# 添加以下行（根据你的路径调整）
0 8 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 8
0 12 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 4
0 18 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 6
0 21 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 3
0 0 * * * cd /path/to/twitter-watchdog && venv/bin/python3 scripts/twitter_watchdog.py --hours-ago 3
```

## 输出文件

每次运行生成三个文件：

| 文件 | 说明 |
|------|------|
| `ai_tweets_YYYYMMDD_HHMMSS.json` | 完整数据，含所有推文原始字段、AI 总结文本 |
| `ai_tweets_YYYYMMDD_HHMMSS.md` | Markdown 详细报告，含 AI 总结 + 每条推文详情 |
| `latest_summary.md` | 汇总摘要，每次覆盖更新，适合快速查看 |

## 费用估算

以 100 个关注用户、每天运行 5 次为例：

| 项目 | 单次费用 | 每日费用 | 每月费用 |
|------|----------|----------|----------|
| twitterapi.io（~100 次 API 调用） | ~$0.02 | ~$0.10 | ~$3 |
| Claude API（~30k input + ~3k output tokens） | ~$0.01 | ~$0.05 | ~$1.5 |
| **合计** | **~$0.03** | **~$0.15** | **~$4.5** |

## License

MIT
