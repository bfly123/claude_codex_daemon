<div align="center">

# Claude Code Bridge (ccb) v2.0 alpha

**🌍 Cross-Platform Multi-AI Collaboration: Claude + Codex + Gemini**

**Windows | macOS | Linux — One Tool, All Platforms**

[![Version](https://img.shields.io/badge/version-2.0_alpha-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)]()

[English](#english) | [中文](#中文)

<img src="assets/demo.webp" alt="Dual-pane demo (animated)" width="900">

<p>
  <a href="https://github.com/bfly123/claude_code_bridge/releases/tag/2.0">Full demo video (GitHub Release)</a>
</p>

</div>

---

## 🎉 What's New in v2.0

> **🪟 Full Windows Support via [WezTerm](https://wezfurlong.org/wezterm/)**
> WezTerm is now the recommended terminal for all platforms. It's a powerful, cross-platform terminal with native split-pane support. Linux/macOS users: give it a try! tmux remains supported.

- **⚡ Faster Response** — Optimized send/receive latency, significantly faster than MCP
- **🐛 macOS Fixes** — Fixed session resume and various login issues
- **🔄 Easy Updates** — Run `ccb update` instead of re-cloning

> Found a bug? Run `claude` in the project directory to debug, then share your `git diff` with the maintainer!

---

# English

## Why This Project?

Traditional MCP calls treat Codex as a **stateless executor**—Claude must feed full context every time.

**ccb (Claude Code Bridge)** establishes a **persistent, lightweight channel** for sending/receiving small messages while each AI maintains its own context.

### Division of Labor

| Role | Responsibilities |
|------|------------------|
| **Claude Code** | Requirements analysis, architecture planning, code refactoring |
| **Codex** | Algorithm implementation, bug hunting, code review |
| **Gemini** | Research, alternative perspectives, verification |
| **ccb** | Session management, context isolation, communication bridge |

### Official MCP vs Persistent Dual-Pane

| Aspect | MCP (Official) | Persistent Dual-Pane |
|--------|----------------|----------------------|
| Codex State | Stateless | Persistent session |
| Context | Passed from Claude | Self-maintained |
| Token Cost | 5k-20k/call | 50-200/call (much faster) |
| Work Mode | Master-slave | Parallel |
| Recovery | Not possible | Supported (`-r`) |
| Multi-AI | Single target | Multiple backends |

> **Prefer MCP?** Check out [CodexMCP](https://github.com/GuDaStudio/codexmcp) — a more powerful MCP implementation with session context and multi-turn support.

<details>
<summary><b>Token Savings Explained</b></summary>

```
MCP approach:
  Claude → [full code + history + instructions] → Codex
  Cost: 5,000-20,000 tokens/call

Dual-pane approach (only sends/receives small messages):
  Claude → "optimize utils.py" → Codex
  Cost: 50-200 tokens/call
  (Codex reads the file itself)
```

</details>

## Install

```bash
git clone https://github.com/bfly123/claude_code_bridge.git
cd claude_code_bridge
./install.sh install
```

### Windows

- **WSL2 (recommended):** run the same commands inside WSL.
- **Native Windows (PowerShell/CMD):** use the wrappers:
  - `install.cmd install`
  - or `powershell -ExecutionPolicy Bypass -File .\\install.ps1 install`
- **WezTerm-only (no tmux):** run `ccb` inside WezTerm, or set `CCB_TERMINAL=wezterm` (and if needed `CODEX_WEZTERM_BIN` to `wezterm.exe`).

## Start

```bash
ccb up codex            # Start with Codex
ccb up gemini           # Start with Gemini
ccb up codex gemini     # Start both
ccb up codex -r         # Resume previous session
ccb up codex -a         # Full permissions mode
```

### Session Management

```bash
ccb status              # Check backend status
ccb kill codex          # Terminate session
ccb restore codex       # Attach to running session
ccb update              # Update to latest version
```

> `-a` enables `--dangerously-skip-permissions` for Claude and `--full-auto` for Codex.  
> `-r` resumes based on local dotfiles in the current directory (`.claude-session`, `.codex-session`, `.gemini-session`); delete them to reset.

## Usage Examples

### Practical Workflows
- "Have Codex review my code changes"
- "Ask Gemini for alternative approaches"
- "Codex plans the refactoring, supervises while I implement"
- "Codex writes backend API, I handle frontend"

### Fun & Creative

> **🎴 Featured: AI Poker Night!**
> ```
> "Let Claude, Codex and Gemini play Dou Di Zhu (斗地主)!
>  You deal the cards, everyone plays open hand!"
>
>  🃏 Claude (Landlord)  vs  🎯 Codex + 💎 Gemini (Farmers)
> ```

- "Play Gomoku with Codex"
- "Debate: tabs vs spaces"
- "Codex writes a function, Claude finds the bugs"

### Advanced
- "Codex designs architecture, Claude implements modules"
- "Parallel code review from different angles"
- "Codex implements, Gemini reviews, Claude coordinates"

## Commands (For Developers)

> Most users don't need these—Claude auto-detects collaboration intent.

**Codex:**

| Command | Description |
|---------|-------------|
| `cask-w <msg>` | Sync: wait for reply |
| `cask <msg>` | Async: fire-and-forget |
| `cpend` | Show latest reply |
| `cping` | Connectivity check |

**Gemini:**

| Command | Description |
|---------|-------------|
| `gask-w <msg>` | Sync: wait for reply |
| `gask <msg>` | Async: fire-and-forget |
| `gpend` | Show latest reply |
| `gping` | Connectivity check |

## Requirements

- Python 3.8+
- tmux or WezTerm (at least one; WezTerm recommended)

## Uninstall

```bash
./install.sh uninstall
```

---

# 中文

## 🎉 v2.0 新特性

> **🪟 全面支持 Windows — 通过 [WezTerm](https://wezfurlong.org/wezterm/)**
> WezTerm 现已成为所有平台的推荐终端。它是一个强大的跨平台终端，原生支持分屏。Linux/macOS 用户也推荐使用！当然短期tmux仍然支持。

- **⚡ 响应更快** — 优化了发送/接收延迟，显著快于 MCP
- **🐛 macOS 修复** — 修复了会话恢复和各种登录问题
- **🔄 一键更新** — 运行 `ccb update` 即可更新，无需重新拉取安装

> 发现 bug？在项目目录运行 `claude` 调试，然后将 `git diff` 发给作者更新到主分支！

---

## 界面截图

<div align="center">
  <img src="assets/figure.png" alt="双窗口协作界面" width="900">
</div>

<div align="center">
  <img src="assets/demo.webp" alt="动图预览" width="900">
</div>

<div align="center">
  <a href="https://github.com/bfly123/claude_code_bridge/releases/tag/2.0">完整演示视频（GitHub Release）</a>
</div>

---

## 为什么需要这个项目？

传统 MCP 调用把 Codex 当作**无状态执行器**——Claude 每次都要传递完整上下文。

**ccb (Claude Code Bridge)** 建立**持久通道** 轻量级发送和抓取信息， AI间各自维护独立上下文。

### 分工协作

| 角色 | 职责 |
|------|------|
| **Claude Code** | 需求分析、架构规划、代码重构 |
| **Codex** | 算法实现、bug 定位、代码审查 |
| **Gemini** | 研究、多角度分析、验证 |
| **ccb** | 会话管理、上下文隔离、通信桥接 |

### 官方 MCP vs 持久双窗口

| 维度 | MCP（官方方案） | 持久双窗口 |
|------|----------------|-----------|
| Codex 状态 | 无记忆 | 持久会话 |
| 上下文 | Claude 传递 | 各自维护 |
| Token 消耗 | 5k-20k/次 | 50-200/次（速度显著提升） |
| 工作模式 | 主从 | 并行协作 |
| 会话恢复 | 不支持 | 支持 (`-r`) |
| 多AI | 单目标 | 多后端 |

> **偏好 MCP？** 推荐 [CodexMCP](https://github.com/GuDaStudio/codexmcp) — 更强大的 MCP 实现，支持会话上下文和多轮对话。

<details>
<summary><b>Token 节省原理</b></summary>

```
MCP 方式：
  Claude → [完整代码 + 历史 + 指令] → Codex
  消耗：5,000-20,000 tokens/次

双窗口方式（每次仅发送和抓取少量信息）：
  Claude → "优化 utils.py" → Codex
  消耗：50-200 tokens/次
  (Codex 自己读取文件)
```

</details>

## 安装

```bash
git clone https://github.com/bfly123/claude_code_bridge.git
cd claude_code_bridge
./install.sh install
```

### Windows

- **推荐 WSL2：** 在 WSL 内执行上面的命令即可。
- **原生 Windows（PowerShell/CMD）：** 使用包装脚本：
  - `install.cmd install`
  - 或 `powershell -ExecutionPolicy Bypass -File .\\install.ps1 install`
- **仅 WezTerm（无 tmux）：** 建议在 WezTerm 中运行 `ccb`，或设置 `CCB_TERMINAL=wezterm`（必要时设置 `CODEX_WEZTERM_BIN=wezterm.exe`）。




## 启动

```bash
ccb up codex            # 启动 Codex
ccb up gemini           # 启动 Gemini
ccb up codex gemini     # 同时启动
ccb up codex -r         # 恢复上次会话
ccb up codex -a         # 最高权限模式
```

### 会话管理

```bash
ccb status              # 检查后端状态
ccb kill codex          # 终止会话
ccb restore codex       # 连接到运行中的会话
ccb update              # 更新到最新版本
```

> `-a` 为 Claude 启用 `--dangerously-skip-permissions`，Codex 启用 `--full-auto`。  
> `-r` 基于当前目录下的本地文件恢复（`.claude-session/.codex-session/.gemini-session`）；删除这些文件即可重置。

## 使用示例

### 实用场景
- "让 Codex 审查我的代码修改"
- "问问 Gemini 有没有其他方案"
- "Codex 规划重构方案，我来实现它监督"
- "Codex 写后端 API，我写前端"

### 趣味玩法

> **🎴 特色玩法：AI 棋牌之夜！**
> ```
> "让 Claude、Codex 和 Gemini 来一局斗地主！
>  你来发牌，大家明牌玩！"
>
>  🃏 Claude (地主)  vs  🎯 Codex + 💎 Gemini (农民)
> ```

- "和 Codex 下五子棋"
- "辩论：Tab vs 空格"
- "Codex 写函数，Claude 找 bug"

### 进阶工作流
- "Codex 设计架构，Claude 实现各模块"
- "两个 AI 从不同角度并行 Code Review"
- "Codex 实现，Gemini 审查，Claude 协调"

## 命令（开发者使用）

> 普通用户无需使用这些命令——Claude 会自动检测协作意图。

**Codex:**

| 命令 | 说明 |
|------|------|
| `cask-w <消息>` | 同步：等待回复 |
| `cask <消息>` | 异步：发送即返回 |
| `cpend` | 查看最新回复 |
| `cping` | 测试连通性 |

**Gemini:**

| 命令 | 说明 |
|------|------|
| `gask-w <消息>` | 同步：等待回复 |
| `gask <消息>` | 异步：发送即返回 |
| `gpend` | 查看最新回复 |
| `gping` | 测试连通性 |

## 依赖

- Python 3.8+
- tmux 或 WezTerm（至少安装一个），强烈推荐wezterm


## 卸载

```bash
./install.sh uninstall
```

---

<div align="center">

**WSL2 supported** | WSL1 not supported (FIFO limitation)

</div>
