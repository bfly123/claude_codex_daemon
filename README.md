<div align="center">

# Claude-Codex v1.0

**Persistent multi-AI collaboration: Claude + Codex + Gemini**

[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20WSL2-lightgrey.svg)]()

[English](#english) | [中文](#中文)

<img src="figure.png" alt="Dual-pane diagram" width="600">

</div>

---

# English

## Why This Project?

Traditional MCP calls treat Codex as a **stateless executor**—Claude must feed full context every time.

**claude_codex** establishes a **persistent channel** where both AIs maintain independent contexts.

### Division of Labor

| Role | Responsibilities |
|------|------------------|
| **Claude Code** | Requirements analysis, architecture planning, code refactoring |
| **Codex** | Algorithm implementation, bug hunting, code review |
| **Gemini** | Research, alternative perspectives, verification |
| **claude_codex** | Session management, context isolation, communication bridge |

### Official MCP vs Persistent Dual-Pane

| Aspect | MCP (Official) | Persistent Dual-Pane |
|--------|----------------|----------------------|
| Codex State | Stateless | Persistent session |
| Context | Passed from Claude | Self-maintained |
| Token Cost | 5k-20k/call | 50-200/call |
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

Dual-pane approach:
  Claude → "optimize utils.py" → Codex
  Cost: 50-200 tokens/call
  (Codex reads the file itself)
```

**Estimated savings: 70-90%**

</details>

## Install

```bash
git clone https://github.com/bfly123/claude_codex.git
cd claude_codex
./install.sh install
```

## Start

### New Unified Launcher (v1.0)

```bash
claude_ai up codex            # Start with Codex
claude_ai up gemini           # Start with Gemini
claude_ai up codex gemini     # Start both
claude_ai up codex -r         # Resume previous session
claude_ai up codex -a         # Full permissions mode
```

### Session Management

```bash
claude_ai status              # Check backend status
claude_ai kill codex          # Terminate session
claude_ai restore codex       # Attach to running session
```

### Legacy Command (Still Supported)

```bash
claude_codex              # default start
claude_codex -c           # resume Claude context
claude_codex -C           # resume Codex context
claude_codex -a           # full permissions mode
```

> `-a` enables `--dangerously-skip-permissions` for Claude and `--full-auto` for Codex.

## Usage Examples

### Practical Workflows
- "Have Codex review my code changes"
- "Ask Gemini for alternative approaches"
- "Codex plans the refactoring, supervises while I implement"
- "Codex writes backend API, I handle frontend"

### Fun & Creative
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
- tmux (`brew install tmux` / `apt install tmux`)

## Uninstall

```bash
./install.sh uninstall
```

---

# 中文

## 为什么需要这个项目？

传统 MCP 调用把 Codex 当作**无状态执行器**——Claude 每次都要传递完整上下文。

**claude_codex** 建立**持久通道**，两个 AI 各自维护独立上下文。

### 分工协作

| 角色 | 职责 |
|------|------|
| **Claude Code** | 需求分析、架构规划、代码重构 |
| **Codex** | 算法实现、bug 定位、代码审查 |
| **Gemini** | 研究、多角度分析、验证 |
| **claude_codex** | 会话管理、上下文隔离、通信桥接 |

### 官方 MCP vs 持久双窗口

| 维度 | MCP（官方方案） | 持久双窗口 |
|------|----------------|-----------|
| Codex 状态 | 无记忆 | 持久会话 |
| 上下文 | Claude 传递 | 各自维护 |
| Token 消耗 | 5k-20k/次 | 50-200/次 |
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

双窗口方式：
  Claude → "优化 utils.py" → Codex
  消耗：50-200 tokens/次
  (Codex 自己读取文件)
```

**预估节省：70-90%**

</details>

## 安装

```bash
git clone https://github.com/bfly123/claude_codex.git
cd claude_codex
./install.sh install
```

## 启动

### 新版统一启动器 (v1.0)

```bash
claude_ai up codex            # 启动 Codex
claude_ai up gemini           # 启动 Gemini
claude_ai up codex gemini     # 同时启动
claude_ai up codex -r         # 恢复上次会话
claude_ai up codex -a         # 最高权限模式
```

### 会话管理

```bash
claude_ai status              # 检查后端状态
claude_ai kill codex          # 终止会话
claude_ai restore codex       # 连接到运行中的会话
```

### 旧版命令（仍支持）

```bash
claude_codex              # 默认启动
claude_codex -c           # 恢复 Claude 上下文
claude_codex -C           # 恢复 Codex 上下文
claude_codex -a           # 最高权限模式
```

> `-a` 为 Claude 启用 `--dangerously-skip-permissions`，Codex 启用 `--full-auto`。

## 使用示例

### 实用场景
- "让 Codex 审查我的代码修改"
- "问问 Gemini 有没有其他方案"
- "Codex 规划重构方案，我来实现它监督"
- "Codex 写后端 API，我写前端"

### 趣味玩法
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
- tmux（`brew install tmux` / `apt install tmux`）

## 卸载

```bash
./install.sh uninstall
```

---

<div align="center">

**WSL2 supported** | WSL1 not supported (FIFO limitation)

</div>
