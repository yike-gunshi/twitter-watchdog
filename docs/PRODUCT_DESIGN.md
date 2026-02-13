# Twitter Watchdog — MVP 产品设计文档

## 1. 产品讨论历史

### 1.1 产品化方向探讨（2026-02-12）

**背景**：twitter_watchdog.py 完成三层架构重构（scrape → analyze → report），具备完整的 Twitter AI 新闻监控能力。讨论如何将其包装为可对外提供服务的产品。

**两条商业化路径**：
- **SaaS 工具**：面向个人/团队的信息监控服务
- **嵌入式引擎**：提供 API/SDK 给其他产品集成

**当时识别的 5 项缺失能力**：
1. 多用户支持（账户体系、配额管理）
2. 主题可定制（不限于 AI，支持自定义领域）
3. 推送/分发（邮件、Telegram、Slack、微信）
4. 数据源扩展（Reddit、公众号、arXiv 等）
5. 交互式报告（收藏、标记、反馈）

### 1.2 用户的三层个性化模型

用户提出了核心产品理念——**零配置即可用 + 渐进式个性化**：

**Layer 1 — 源头个性化**：
- 默认支持多源信息（Twitter、Reddit、公众号、即刻、arXiv 等）
- 默认按 AI/经济/政治/加密货币等领域维护和抓取
- 用户可以不配置任何东西，直接查看预置信息源的聚合结果
- 也可以给出自己账号（获取关注列表），或直接指定感兴趣的账号
- **个性化代价**：只需输入账号 ID 或关注列表

**Layer 2 — 处理个性化**：
- 允许用户选择信息加工方式，或输入自定义 prompt
- 简洁版：信息一句话
- 标准版：信息源头和事实说明
- 进阶版：增加 AI 解读
- **个性化代价**：选择风格，或输入一句话 prompt

**Layer 3 — 身份个性化**：
- 用户上传个人关键信息（产品经理/国企员工/开发者等）
- AI 基于个人特征给出信息用途建议
- 核心理念："每个人获取信息，目的都是为己所用"
- **个性化代价**：选择或输入自己的领域/目的

**用户的关键洞察**：个性化的代价极低——用户只需输入账号 ID 或关注列表、选择领域、输入获取信息的目的，就能获得高度定制化的信息流。

### 1.3 我的反馈与建议

**Layer 1 反馈**：
- 数据源稳定性是关键风险（微信公众号尤其难抓）
- 建议从 2-3 个高质量源起步，不要一开始做太多
- Twitter 关注列表作为信息源效果好（Nuzzel 已验证）

**Layer 2 反馈**：
- 最可落地的一层
- 建议增加"视角维度"与 Layer 3 联动

**Layer 3 反馈**：
- 风险最高——泛化的角色建议容易变成废话
- **建议 MVP 不做**，改为通过收藏/标记等行为数据积累用户偏好
- 等有足够行为数据后，再做个性化推荐

**新增概念 — 信息紧急度分级**：
- 🔴 实时推送：重大发布、安全事件
- 🟡 日报汇总：新产品、新模型
- 🟢 周报趋势：观点、分析、教程

**达成共识的 MVP 范围**：
- Layer 1：源头可配置（关注列表 + 自定义账号）
- Layer 2：处理风格可选（concise/standard/advanced + custom_prompt）
- Layer 3：MVP 不做，先积累行为数据

---

## 2. 竞品研究（2026-02-13）

### 2.1 直接竞品

| 产品 | 状态 | 核心模式 | 关键启示 |
|------|------|---------|---------|
| **Nuzzel** | 已关闭（2021） | 社交图谱过滤——"你关注的人在看什么" | 最被怀念的模式，Twitter 上目前无替代品 |
| **Artifact** | 已关闭（2024） | AI 推荐 + 去标题党 | 独立新闻 App 市场太小；加功能失焦致死 |
| **Feedly AI** | 运营中 | RSS + AI 去重/优先级 | 去重减少 30-40% 噪音，这是杀手功能 |
| **Perplexity Tasks** | 运营中 | 定时 AI 搜索 + 邮件推送 | Tasks 灵活但需要用户写好 prompt |
| **Particle News** | 运营中 | 多源综合 + 偏见分析 | 事件级聚合（不是文章级）是好方向 |
| **Sill** | 运营中 | Nuzzel 精神续作 | 只支持 Bluesky/Mastodon，不支持 Twitter |
| **Readwise Reader** | 运营中 | 统一阅读器 + AI 辅助 | 处理已找到的内容，不是发现工具 |
| **即刻** | 运营中 | 兴趣推送 → 社区 | "订阅话题→推送通知"就是 watchdog 模式原型 |

### 2.2 Newsletter 类产品

| 产品 | 核心模式 | 关键启示 |
|------|---------|---------|
| **TLDR** | 人工精选 8-10 条 + 2-3 句摘要 | 零个性化也能 100 万+ 订阅，简洁就是力量 |
| **Morning Brew** | 语气和声音是一切 | 同样的新闻换个包装就能爆发 |
| **The Batch / Import AI** | 专家策展 | 垂直领域中策展人信誉 > AI 个性化 |
| **通往AGI之路** | 结构化知识库 | 中文 AI 社区价值在于结构化整理 |

### 2.3 关键结论

**信息过载的解法排序**：
1. 去重 + 聚合（Feedly：减 30-40% 噪音）— 我们已有
2. 激进筛选（TLDR：每天只给 8-10 条）— 可通过 prompt 控制
3. 社交证明（Nuzzel：多人分享的才推）— 关注列表天然具备
4. 摘要化（Particle：多源综合为一段话）— Claude 已在做
5. 时间承诺（"5 分钟读完"）— 报告已做到

**推送留存关键**：
- 邮件/消息日报 > App 内浏览
- 固定时间 + 固定格式 = 用户习惯
- 突发推送必须极度克制，否则用户关通知

**市场空白**：
- Twitter/X 上没有 Nuzzel 替代品
- "你关注的聪明人在讨论什么"这个需求完全未被满足

---

## 3. 代码库能力分析

### 3.1 现有架构

```
Layer 1: scrape          Layer 2: analyze          Layer 3: report
(数据采集)               (AI 分析)                  (报告生成)

raw/*.json        →    analysis/*.json      →    reports/*.{html,md}
```

- **2297 行** Python 代码
- 三层完全解耦，各层可独立执行
- CLI subparsers 支持 scrape / analyze / report / 流水线
- 配置驱动（YAML + CLI 参数覆盖）

### 3.2 可直接复用的模块

| 模块 | 代码行 | 复用方式 |
|------|--------|---------|
| `get_following()` | 294-336 | 不变 |
| `get_tweets()` | 355-417 | 不变 |
| `search_trending_ai()` | 495-512 | 不变 |
| 去重系统 | 185-217 | 不变 |
| AI 批量筛选 | 753-834 | 改 prompt |
| AI 总结生成 | 552-651 | 改 prompt |
| 分批 + 重试 + 合并 | 688-703, 930-957 | 不变 |
| HTML 报告模板 | 1596-1909 | 不变 |
| 日/周/月报聚合 | 2063-2187 | 不变 |

### 3.3 硬编码限制（MVP 中需改动的）

| 限制 | 影响 | 改动量 |
|------|------|--------|
| AI prompt 中 5 个固定分类 | 无法定制报告结构 | 改 prompt 模板 |
| 只能抓 username 的关注列表 | 无法指定额外账号 | 加 custom_accounts |
| 无推送能力 | 必须手动打开报告 | 加 Telegram 推送 |
| 无信息紧急度概念 | 所有信息同等对待 | 改 AI 筛选 prompt |

---

## 4. MVP 设计方案

### 4.1 约束

- 目标用户：开发者本人（单用户）
- 领域：仅 AI
- 信息源：仅 Twitter
- 基于现有代码改造，不引入新框架/新依赖
- 只改 `twitter_watchdog.py` + `config.yaml`

### 4.2 五项改动

#### 改动 1：源头个性化（~15 行）

在 config.yaml 增加 `custom_accounts` 列表，`run_scrape()` 中与关注列表合并去重后抓取。

```yaml
twitter:
  username: "rollingrock_1"
  custom_accounts: ["AnthropicAI", "OpenAI", "GoogleDeepMind"]
```

#### 改动 2：处理个性化（~55 行）

在 `ai_summary` 中增加 `style` 和 `custom_prompt`：

```yaml
ai_summary:
  style: "standard"        # concise / standard / advanced
  custom_prompt: ""         # 追加到 AI prompt 末尾
```

- **concise**：每条一句话摘要，只保留核心事实
- **standard**：当前默认（不变）
- **advanced**：standard + 每条增加"为什么重要"分析

`custom_prompt` 直接追加到系统 prompt 末尾。

#### 改动 3：紧急度分级（~25 行）

修改 `_filter_batch_robust()` 的 AI prompt，让 Claude 返回：

```json
{"ai_tweet_ids": ["id1", ...], "urgent_ids": ["id2", ...]}
```

🔴 `urgent_ids` 中的推文触发即时推送（如果 push 已启用）。

#### 改动 4：Telegram 推送（~50 行）

新增 `push_summary()` 方法，用 `requests.post()` 调用 Telegram Bot API。

```yaml
push:
  enabled: true
  telegram:
    bot_token: "..."
    chat_id: "..."
```

- `run_report()` 结束后自动调用
- 🔴 突发推文立即推送
- 日报推送"本期要点"摘要

#### 改动 5：push 子命令（~20 行）

```bash
python twitter_watchdog.py push [--source analysis/xxx.json]
python twitter_watchdog.py push --test
```

### 4.3 不做的事情

| 不做 | 原因 |
|------|------|
| Web UI | 单用户不需要，CLI + config.yaml 足够 |
| 数据库 | JSON 文件对单用户完全够用 |
| 多用户 | MVP 只有一个用户 |
| 多信息源 | 仅 Twitter，不加 Reddit/公众号 |
| 用户身份/角色系统 | 用 custom_prompt 代替 |
| 独立 App | Artifact 教训 |

### 4.4 改动总量

约 **180 行**代码变更，0 个新依赖。

### 4.5 使用场景

```bash
# 日常（cron 每天 3 次）
0 8,14,20 * * * python3 twitter_watchdog.py --hours-ago 8 --config config.yaml
# → 自动抓取 + 分析 + 报告 + 推送到 Telegram

# 突发新闻
# Claude 检测到 🔴 突发 → 立即推 Telegram
# "🔴 OpenAI 发布 GPT-5 https://x.com/..."

# 调整关注点
# 编辑 config.yaml: custom_prompt: "重点关注 AI Agent 和 MCP"
# 下次运行时 AI 会重点筛选这些方向
```

---

## 5. 后续演进方向（MVP 之后）

1. **行为数据积累**：在 Telegram 中加收藏/标记按钮，积累用户偏好
2. **多信息源**：Reddit、arXiv 等
3. **多领域**：支持 AI 之外的领域
4. **多用户**：加用户体系
5. **Web 界面**：报告浏览 + 配置管理
