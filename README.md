# Twitter Watchdog

定时监控 Twitter 关注列表，自动抓取 AI 相关推文，由 Claude 智能筛选并生成结构化日报/周报/月报。

## 它能做什么

1. **日报** — 抓取你 Twitter 关注列表中所有用户的最新推文 + 全网热门 AI 推文，由 Claude 自动判断 AI 相关性，生成 HTML + Markdown 报告
2. **周报** — 基于历史分析数据，自动去重合并，生成结构化周报（本期要点 + 分类整理）
3. **月报** — 基于历史分析数据，自动去重合并，生成结构化月报

## 三层架构

```
Layer 1: scrape          Layer 2: analyze          Layer 3: report
(数据采集)               (AI 分析)                  (报告生成)

┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ twitterapi.io│    │ 读取 raw/*.json   │    │ 读取 analysis/   │
│ 获取关注列表  │    │ 时间窗口切片      │    │ 下载推文配图      │
│ 抓取全量推文  │    │ 关键词预过滤(可选) │    │ 生成 HTML + MD    │
│ 搜索热门推文  │    │ Claude 批量筛选    │    │ 聚合 日/周/月报   │
│ 存 raw JSON  │    │ Claude 批量总结    │    │ 存 reports/       │
└──────┬──────┘    │ 存 analysis JSON   │    └──────────────────┘
       │           └──────────────────┘
       ▼
  raw/*.json     →    analysis/*.json    →    reports/*.{html,md}
```

每一层独立执行，也可串行流水线运行（向后兼容）。

**只需两个 API Key，开箱即用，中国大陆无需 VPN。**

| API | 用途 | 费用 | 说明 |
|-----|------|------|------|
| twitterapi.io | 获取关注列表 + 抓取推文 + 热门搜索 | $0.15/1k tweets | 一个 key 搞定所有 Twitter 数据，国内直连 |
| Claude API | AI 筛选 + 分类总结 + 周报/月报整合 | ~$0.01/次 | 比关键词匹配更准确，能识别语义相关的推文 |
| X Official API | 获取关注列表（可选 fallback） | 免费 | 非必需，仅当 twitterapi.io 不可用时作为备选 |

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/yike-gunshi/twitter-watchdog.git
cd twitter-watchdog

python3 -m venv venv
source venv/bin/activate
pip install requests pyyaml
```

### 2. 配置

```bash
cp config/config.yaml.example config/config.yaml
```

编辑 `config/config.yaml`，填入你的凭证和用户名：

```yaml
# 必填项（只需两个 key）
twitterapi_io:
  api_key: "你的 twitterapi.io Key"

twitter:
  username: "你的 Twitter 用户名"  # 不带 @

ai_summary:
  enabled: true
  api_key: "你的 Claude API Key"
  # base_url: "https://your-proxy.com/api"  # 可选：API 代理地址
```

### 3. 运行

```bash
# 流水线模式（三步串行，最简单）
python3 scripts/twitter_watchdog.py --hours-ago 24

# 或者分层执行
python3 scripts/twitter_watchdog.py --hours-ago 24 scrape     # 只抓取
python3 scripts/twitter_watchdog.py --hours-ago 24 analyze    # 只分析
python3 scripts/twitter_watchdog.py report                     # 只生成报告
```

## 命令行用法

### 子命令

```bash
# Layer 1: 抓取原始推文（不做 AI 过滤，保存全量）
python3 scripts/twitter_watchdog.py [全局参数] scrape

# Layer 2: AI 分析原始数据
python3 scripts/twitter_watchdog.py [全局参数] analyze [--source RAW_FILE]
python3 scripts/twitter_watchdog.py [全局参数] analyze --from "2026-02-12 08:00" --to "2026-02-12 14:00"

# Layer 3: 从分析结果生成报告
python3 scripts/twitter_watchdog.py [全局参数] report [--source ANALYSIS_FILE]
python3 scripts/twitter_watchdog.py [全局参数] report --daily 2026-02-12
python3 scripts/twitter_watchdog.py [全局参数] report --weekly 2026-02-10
python3 scripts/twitter_watchdog.py [全局参数] report --monthly 2026-02

# 流水线（无子命令 = scrape + analyze + report 三步串行，向后兼容）
python3 scripts/twitter_watchdog.py [全局参数]
```

> **注意**：全局参数（如 `--hours-ago`、`--config`）必须放在子命令前面。

### 全局参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config PATH` | 配置文件路径 | `config/config.yaml` |
| `--output-dir PATH` | 输出目录 | 见配置文件 |
| `--hours-ago N` | 时间窗口（小时） | 不限 |
| `--max-followings N` | 关注列表抓取范围（0=全部） | 0 |
| `--tweets-per-user N` | 每个用户最多推文数 | 20 |
| `--trending-count N` | 热门推文最多条数 | 20 |
| `--min-faves N` | 热门推文最低浏览量 | 2000 |
| `--language LANG` | 语言过滤（all/en/zh/ja...） | all |
| `--exclude-users "a,b"` | 排除的用户名 | 无 |
| `--reset-state` | 重置去重状态 | - |
| `--no-trending` | 禁用热门搜索 | - |
| `--no-summary` | 禁用 AI 总结 | - |

### analyze 子命令参数

| 参数 | 说明 |
|------|------|
| `--source PATH` | 指定 raw JSON 文件路径（默认取最新） |
| `--from "YYYY-MM-DD HH:MM"` | 起始时间 |
| `--to "YYYY-MM-DD HH:MM"` | 结束时间 |

### report 子命令参数

| 参数 | 说明 |
|------|------|
| `--source PATH` | 指定 analysis JSON 文件路径（默认取最新） |
| `--daily YYYY-MM-DD` | 生成日报（聚合当天所有 analysis） |
| `--weekly YYYY-MM-DD` | 生成周报（从指定日期起 7 天） |
| `--monthly YYYY-MM` | 生成月报 |

## 输出目录结构

```
output/
├── raw/                          # Layer 1: 原始抓取数据
│   ├── 20260212_080000.json
│   └── 20260212_140000.json
├── analysis/                     # Layer 2: AI 分析结果
│   ├── 20260212_083000.json
│   └── 20260212_143000.json
└── reports/                      # Layer 3: 最终报告
    ├── 20260212_083000.html
    ├── 20260212_083000.md
    ├── daily_20260212.html       # 日报
    ├── weekly_20260210.html      # 周报
    ├── monthly_202602.html       # 月报
    ├── latest.html               # → 最新报告
    └── images/                   # 推文配图
```

### 数据格式示例

见 [examples/](examples/) 目录：
- `raw_sample.json` — Layer 1 原始数据示例
- `analysis_sample.json` — Layer 2 分析结果示例

## 工作原理

### Layer 1: scrape（数据采集）

1. **获取关注列表** — twitterapi.io 获取你的关注用户（带 24h 本地缓存）
2. **抓取推文** — 每个用户的最新推文（`--hours-ago` 控制分页深度）
3. **全网热门搜索** — twitterapi.io 搜索全网 AI 相关热门推文
4. **去重保存** — 自动去重后存入 `output/raw/YYYYMMDD_HHMMSS.json`

关键：**不做任何 AI/关键词过滤**，保存全量原始数据，方便后续重新分析。

### Layer 2: analyze（AI 分析）

1. **读取 raw JSON** — 支持 `--source` 指定文件、`--from/--to` 时间范围、`--hours-ago` 窗口
2. **时间窗口过滤** — 按时间切片
3. **关键词预过滤** — 当 `ai_filter: false` 时生效，`ai_filter: true` 时跳过（交给 Claude）
4. **Claude AI 筛选** — 发送全量推文，让 Claude 判断哪些与 AI 相关
5. **Claude 生成总结** — 结构化分类情报清单
6. **保存分析结果** — 存入 `output/analysis/YYYYMMDD_HHMMSS.json`

### Layer 3: report（报告生成）

1. **读取 analysis JSON** — 支持单文件或多文件聚合
2. **聚合处理** — 日报/周报/月报：解析条目 → URL 去重 → Claude 整合
3. **下载图片** — 推文配图自动下载到 `reports/images/`
4. **生成报告** — HTML（自包含页面，暗色模式，导航栏）+ Markdown

## 调度策略

推荐通过 cron、launchd 定时执行，覆盖全天：

| 时间 (UTC+8) | 命令 | 覆盖区间 |
|--------------|------|----------|
| 08:00 | `python3 twitter_watchdog.py --hours-ago 8 scrape` | 00:00 ~ 08:00 |
| 12:00 | `python3 twitter_watchdog.py --hours-ago 4 scrape` | 08:00 ~ 12:00 |
| 18:00 | `python3 twitter_watchdog.py --hours-ago 6 scrape` | 12:00 ~ 18:00 |
| 00:00 | `python3 twitter_watchdog.py --hours-ago 6 scrape` | 18:00 ~ 00:00 |

分析和报告可以独立调度，也可以在每次抓取后串行：

```bash
# 抓取 + 分析 + 报告（流水线）
python3 scripts/twitter_watchdog.py --hours-ago 8

# 或者分开调度
python3 scripts/twitter_watchdog.py --hours-ago 8 scrape
python3 scripts/twitter_watchdog.py --hours-ago 8 analyze
python3 scripts/twitter_watchdog.py report

# 每周一生成周报
python3 scripts/twitter_watchdog.py report --weekly $(date -v-7d +%Y-%m-%d)

# 每月 1 号生成月报
python3 scripts/twitter_watchdog.py report --monthly $(date -v-1m +%Y-%m)
```

## 费用估算

以 100 个关注用户、每天运行 4 次为例：

| 项目 | 单次费用 | 每日费用 | 每月费用 |
|------|----------|----------|----------|
| twitterapi.io（~100 次 API 调用） | ~$0.02 | ~$0.08 | ~$2.4 |
| Claude API — 分析（~30k input + ~3k output tokens） | ~$0.01 | ~$0.04 | ~$1.2 |
| Claude API — 周报/月报（按需生成） | ~$0.02/次 | - | ~$0.1 |
| **合计** | - | **~$0.12** | **~$3.7** |

## License

MIT
