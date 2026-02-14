# Telegram 通道配置记录 - 2026-02-11

## 概览
- **时间：** 2026-02-11 21:16 ~ 23:30 CST
- **目标：** 配置 Telegram 通道并确保与飞书通道共存正常工作

---

## 操作步骤

### 1. 配置 Telegram Bot Token
- 在 `/root/.openclaw/.env` 中填入 `TELEGRAM_BOT_TOKEN`
- Token 来自 @BotFather 创建的 `@hahaha_working_bot`

### 2. 启用 Telegram 通道
- 运行 `openclaw doctor --fix` 自动启用 Telegram 插件
- 在 `openclaw.json` 的 `channels` 中添加 `telegram: { enabled: true }`

### 3. 解决网络问题（关键）
**问题：** 服务器无法直连 `api.telegram.org`（被墙），日志报错：
```
telegram setMyCommands failed: Network request for 'setMyCommands' failed!
Telegram: failed (unknown) - This operation was aborted
```

**解决方案：** 部署 Clash 代理，仅代理 Telegram 流量

- 订阅配置下载后提取节点信息
- 创建精简 Clash 配置 `/root/.config/clash/config.yaml`
  - 仅包含 4 个节点（HK/JP/SG），使用 fallback 策略组
  - 规则：只代理 Telegram 域名和 IP 段，其余全部 DIRECT
  - Telegram 域名：`telegram.org`, `t.me`, `telegram.me`, `telegra.ph`, `telegram.dog`, `telesco.pe`
  - Telegram IP 段：`91.108.4.0/22` ~ `91.108.56.0/22`, `149.154.160.0/20`, `185.76.151.0/24`
- Clash 注册为 systemd 服务 `/etc/systemd/system/clash.service`，开机自启
- 在 `openclaw.json` 中配置 `channels.telegram.proxy: "http://127.0.0.1:7890"`

### 4. Telegram 配对审批
- 私聊策略为 `pairing` 模式（默认），陌生人需配对审批
- 用户发消息后 Bot 返回配对码
- 通过 `openclaw pairing approve telegram <code>` 审批
- 已审批用户 ID：`8542554397`

### 5. 解决飞书无回复问题（关键）
**问题：** 添加 Telegram 后，飞书发消息不返回回复（一直 typing 后无响应）

**根因：** 默认 `session.dmScope` 为 `main`，所有通道的私聊共用同一个 session（`test2-1770805619`）。Telegram 和飞书消息混入同一会话，Agent 回复可能发到了错误的通道。日志表现为飞书侧 `dispatch complete (queuedFinal=false, replies=0)`。

**解决方案：** 在 `openclaw.json` 中添加：
```json
"session": {
  "dmScope": "per-channel-peer"
}
```
这使每个通道+每个用户拥有独立 session：
- 飞书 → `agent:main:feishu:dm:<userId>`
- Telegram → `agent:main:telegram:dm:<userId>`

---

## 最终配置文件变更

### `/root/.openclaw/.env`
```
TELEGRAM_BOT_TOKEN=8553585792:AAHORHiabbfd4gkjmkrM499dOHMSTSL2PNs
```

### `/root/.openclaw/openclaw.json` 新增/修改
```json
{
  "session": {
    "dmScope": "per-channel-peer"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "proxy": "http://127.0.0.1:7890"
    }
  },
  "plugins": {
    "entries": {
      "telegram": { "enabled": true }
    }
  }
}
```

### 新增文件
- `/root/.config/clash/config.yaml` — Clash 精简配置（仅代理 Telegram）
- `/etc/systemd/system/clash.service` — Clash systemd 服务

---

## 排查经验总结

| 问题 | 症状 | 排查方式 | 解决 |
|------|------|----------|------|
| 网络不通 | Bot 启动失败，`setMyCommands failed` | `curl api.telegram.org` 测试连通性 | 部署 Clash 代理 + `channels.telegram.proxy` |
| 飞书无回复 | typing 后无响应，`replies=0` | 查日志发现共用 `sessionId`，`dispatch complete` 均为 `replies=0` | `session.dmScope: "per-channel-peer"` |
| 日志位置 | `journalctl` 无输出 | OpenClaw 日志不走 systemd journal | 查看 `/tmp/openclaw/openclaw-2026-MM-DD.log` |

## 相关命令速查
```bash
# Telegram 配对管理
openclaw pairing list telegram
openclaw pairing approve telegram <code>

# 日志查看
grep -i "telegram\|feishu\|error" /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | tail -20

# Clash 管理
systemctl status clash
systemctl restart clash

# Gateway 管理
openclaw gateway restart
openclaw doctor --fix
```
