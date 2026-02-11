# AI 推文周报 — 02/10 ~ 02/17

## 本期要点

- OpenAI 推出 GPT-5.2 Deep Research 升级和 Codex App，后者首周下载量超 100 万，推动整体用户增长超 60%
- Claude 发布 Windows 版 Cowork 桌面应用，同时 Anthropic 发布 Opus 4.5 安全风险报告，因模型接近 AI Safety Level 4 阈值
- DeepSeek V4 疑似上线（1M 上下文，知识截止 2025 年 5 月），GLM-5 和 Minimax-2.5 正式发布
- Chrome 正在开发 WebMCP 协议，可将网页扫描时间从 3-4 分钟缩短至 3 秒，每个网站将成为 MCP server
- 欧盟批准谷歌 320 亿美元收购网络安全初创公司 Wiz，为 Alphabet 史上最大收购案

## AI 产品与工具

- [Claude Cowork 正式登陆 Windows](https://x.com/claudeai/status/2021384633070584031)。提供与 macOS 一样的功能：文件访问、多任务执行、插件服务和 MCP 支持
- [ChatGPT Deep Research 升级为 GPT-5.2](https://x.com/OpenAI/status/2021299935678026168)。新增内置文档查看器可直接阅读研究报告
- [天工 SkyBot 推出类似 Cowork 的桌面版](https://x.com/yaohui12138/status/2021066655892475990)。支持 Windows 系统,每个助理都有独立虚拟机，可通过 WhatsApp/Telegram 扫码即用
- [Skywork Desktop 桌面版发布](https://x.com/op7418/status/2021069596669903088)。Windows 原生支持，每个助理有独立虚拟机，可读懂文件生成新内容
- [Happycapy Agent 原生计算机](https://x.com/vista8/status/2021595437002858578)。由 Claude Code 和 MiniMax Agent 驱动，为用户独立分配云端沙箱运行环境，提供用户友好的 GUI 操作系统，免费注册使用
- [The Vibe Companion 为 Claude Code 开发 Web 界面](https://x.com/geekbb/status/2021110171511189912)。通过逆向工程 CLI 中未公开的 WebSocket 协议，实现与 Claude Code 的交互，支持多会话并行、独立进程和权限设置
- [Kimi Code Web UI 发布](https://x.com/geekbb/status/2021046451145724236)。为 Kimi Code 提供图形界面
- [CodePilot 桌面端](https://x.com/op7418/status/2021049685482586200)。支持导入 Claude Code 聊天记录、上传图片和文件、快捷添加第三方 API、超级权限模式自动批准 AI 操作，GitHub 一周获得 1.1K Star
- [Obsidian 1.12 发布 CLI 命令行工具](https://x.com/obsdmd/status/2021358580503597360)。支持从终端控制 Obsidian，可进行创建、读取、编辑、删除笔记，搜索 vault 内容，管理任务（列出、标记完成、切换状态）等操作，支持脚本编写和自动化
- [Textream macOS 提词器应用](https://x.com/geekbb/status/2021067497521414528)。免费开源，专为主播、采访者、演讲者和播客设计，贴在屏幕顶部实时高亮朗读进度
- [Seedance 2.0 视频生成工具](https://x.com/op7418/status/2021245204963946917)。在产品宣传片和动效方面表现出色，可根据产品介绍抽象关键词，自动编排节奏和展示逻辑，图片文字能够对应
- [NemoVideo AI 视频编辑 Agent](https://x.com/vista8/status/2021609642837541216)。一键 TikTok 爆款仿剪功能
- [收藏到就是学到 Chrome 插件](https://x.com/JamesAI/status/2021089989136875810)。点击收藏按钮时 AI 自动生成结构化摘要（要点提炼、步骤流程、事实核查评分），支持 GPT/Claude/Kimi 三大模型和五种语言，支持历史记录和指定下载文件夹
- [draw.io 发布官方 MCP 服务](https://x.com/dotey/status/2021342950937297090)。同时分享了使用 Claude Project Instructions 的替代方案
- [杭州博查 AI Agent 信息检索工具](https://x.com/huangyun_122/status/2021163254924574890)。为 OpenClaw 等 AI Agent 提供 web search 服务
- [context-sync 工具](https://x.com/yaohui12138/status/2021551772989575604)。解决多 AI 工具间频繁切换导致的项目背景重复注入问题，60 秒快速部署，支持工具间记忆串联
- [Uber Eats 新增 AI 购物助手](https://x.com/verge/status/2021556075234009413)
- [T-Mobile 实时电话翻译功能](https://x.com/verge/status/2021564762845577478)。无需 App 即可翻译普通电话通话

## AI 模型与技术

- [DeepSeek V4 疑似上线](https://x.com/cellinlab/status/2021513258172359030)。1M 上下文长度，知识截止日期为 2025 年 5 月，需更新手机 App 至 1.7.4 版本体验，前端能力有提升
- [GLM-5 正式上线](https://x.com/geekbb/status/2021568338510610461)。支持天气卡片等功能展示
- [Minimax-2.5 上线](https://x.com/geekbb/status/2021571416991154190)
- [Anthropic 发布 Claude Opus 4.5 安全风险报告](https://x.com/AnthropicAI/status/2021397952791707696)。因未来模型接近 AI Safety Level 4 阈值（自主 AI 研发能力），承诺为未来模型撰写破坏风险报告
- [OpenRouter 上线 Aurora Alpha 模型](https://x.com/geekbb/status/2021055855500853366)
- [Grok-4.1-fast 在 MathArena AIME 2026 评测中得分 95%](https://x.com/billyuchenlin/status/2021069093676384411)。推理成本仅 0.06 美元，名列第二，相比其他领先模型成本更低
- [Isomorphic Labs 药物设计引擎取得突破](https://x.com/demishassabis/status/2021223548744822972)。在预测生物分子结构方面实现了准确性的重大提升，在多个关键基准测试中展示了巨大进步

## AI 开发者生态

- [Chrome 正在开发 WebMCP](https://x.com/wangray/status/2021383503963984006)。网站可以直接给 AI Agent 暴露结构化工具，不用再通过截图→识别→点击流程，预计可将网页扫描时间从 3-4 分钟缩短至 3 秒，每个网站将成为一个 MCP server
- [OpenAI Responses API 引入长时 Agent 运行原语](https://x.com/OpenAIDevs/status/2021286050623373500)。包括服务器端压缩（支持多小时 agent 运行不超上下文限制）和容器化环境
- [Google 开源 LangExtract 文本数据提取工具](https://x.com/GitHub_Daily/status/2021373668778295511)。利用大语言模型从非结构化文档中提取结构化数据，只需几行代码和几个示例，每个提取结果都能精确定位到原文位置
- [MemOS 团队开源 OpenClaw 插件](https://x.com/GitHub_Daily/status/2021217661389242566)。官方实测 Token 消耗下降 72%+，模型调用次数减少 60%
- [Clawra 开源](https://x.com/wangray/status/2021220889790963745)。可让 agent 拥有固定外观，能"自拍"发照片，根据指令生成保持外观一致的图片
- [GitHub 官方开源 Agentic Workflows 项目](https://x.com/GitHub_Daily/status/2021085908200718766)。让 AI Agent 在 GitHub Actions 里自动运行，将传统 CI/CD 升级为"持续 AI"协作
- [Devin 推出 Autofix 功能](https://x.com/cognition/status/2021305038811824210)。当 Devin Review 或 GitHub bot 发现 PR 中的 bug 时，Devin 自动修复 PR，也可处理 CI/lint 问题
- [Vercel 推出 self-driving infrastructure](https://x.com/vercel/status/2021249924906778826)。为 AI Agent 提供安全、可靠、易于审计和维护的生产环境
- [Monty：专为 AI 设计的 Python 解释器](https://x.com/GitHub_Daily/status/2021577650666615032)。基于 Rust 实现，启动速度快且完全隔离主机环境，文件、网络、环境变量通过指定的外部函数调用控制，支持暂停和恢复执行，可序列化存储解释器状态
- [Frappe Drive 开源云存储平台](https://x.com/GitHub_Daily/status/2021140679586611571)。支持大文件分块上传、文件夹批量上传、浏览器预览和视频流式播放，内置实时协作文档编辑器，支持多人编辑、批注讨论、版本控制和 Word 文档导入
- [Agmente 开源项目](https://x.com/Yangyixxxx/status/2021489984637895161)。允许从 iOS 手机操作多个 Coding Agent，支持 Gemini CLI、Claude Code、Qwen 等
- [OpenClaw 浏览器插件支持自动发推](https://x.com/idoubicc/status/2021122348158775781)。需在本地电脑运行（不能云端），浏览器登录 Twitter 后安装插件即可自动写推文和发布
- [Claude Code 音效提醒 Hook](https://x.com/op7418/status/2021059644547006606)。为 Claude Code 添加游戏提示音，方便多开时提醒用户需要操作
- [YouTube 视频剪辑 Skills](https://x.com/op7418/status/2021215381176856917)。可将 agent 变成视频剪辑工具

## AI 行业动态

- [欧盟批准谷歌收购 Wiz](https://x.com/ChineseWSJ/status/2021449153247666355)。320 亿美元收购网络安全初创公司 Wiz 的交易获批，为 Alphabet 史上最大收购案
- [OpenAI Codex App 保留免费用户权限](https://x.com/geekbb/status/2021450880160330046)。推广期结束后仍对免费用户开放，首周下载量超 100 万，整体用户增长超 60%
- [Clemson 大学与 OpenAI 达成协议](https://x.com/ClemsonUniv/status/2021335128774148524)。为学生、教职员工免费提供 ChatGPT Edu 访问权限
- [Meta 新增 PM 面试环节"Product Sense with AI"](https://x.com/lennysan/status/2021257353845486030)。这是 Meta 五年来首次对 PM 面试流程进行重大调整，候选人需要运用 AI 解决产品问题
- [专业 Vibe Coder 成为全职职业](https://x.com/lennysan/status/2021377204790362498)。Lazar Jovanovic 全职从事 vibe coding 工作，构建内部工具和公共产品
- [Theta Network 推出 Theta Intelligence](https://x.com/Theta_Network/status/2021335394688827742)。改变传统客户反馈收集方式（调查、焦点小组、社交监控）的实时性问题
- [Deepsona 收购案](https://x.com/marclou/status/2021519843066106094)。5 周内开发完成，通过 SEO 和 LinkedIn 获得首批客户，最终以 9500 美元被收购
- [TrustMRR Co-Founders 功能](https://x.com/marclou/status/2021604401367130179)。允许创业者激活联合创始人模式，展示经过验证的指标，寻找联合创始人
- [TrustMRR OpenClaw 包装产品专页](https://x.com/marclou/status/2021542995745783844)。汇总 OpenClaw 相关包装服务产品，包括 SetupClaw 上门安装服务（3000 美元）和远程安装（1500 美元）

## AI 研究与观点

- [吴恩达谈 AI 对就业市场的影响](https://x.com/AndrewYNg/status/2021259884709413291)。指出"AI 导致失业"的恐惧被过度夸大，但市场对 AI 技能的需求确实开始引发就业格局转变
- [Matt Shumer 关于 AI 能力临界点的观点](https://x.
