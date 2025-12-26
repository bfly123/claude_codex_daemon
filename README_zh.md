<div align="center">

# Claude Code Bridge (ccb) v2.3

**基于终端分屏的 Claude & Codex & Gemini 丝滑协作工具**

**打造真实的大模型专家协作团队，给 Claude Code / Codex / Gemini 配上"不会遗忘"的搭档**

[![Version](https://img.shields.io/badge/version-2.3-orange.svg)]()
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)]()

[English](README.md) | **中文**

<img src="assets/demo.webp" alt="双窗口协作演示" width="900">

</div>

---

**简介：** 多模型协作能够有效避免模型偏见、认知漏洞和上下文限制，然而 MCP、Skills 等直接调用 API 方式存在诸多局限性。本项目打造了一套新的方案。

## ⚡ 核心优势

| 特性 | 价值 |
| :--- | :--- |
| **🖥️ 可见可控** | 多模型分屏 CLI 挂载，所见即所得，完全掌控。 |
| **🧠 持久上下文** | 每个 AI 独立记忆，关闭后可随时恢复（`-r` 参数）。 |
| **📉 节省 Token** | 仅发送轻量级指令，而非整个代码库历史 (~20k tokens)。 |
| **🪟 原生终端体验** | 直接集成于 **WezTerm** (推荐) 或 tmux，无需配置复杂的服务器。 |

---

## 🚀 快速开始

**第一步：** 安装 [WezTerm](https://wezfurlong.org/wezterm/)（Windows 请安装原生 `.exe` 版本）

**第二步：** 根据你的环境选择安装脚本：

<details>
<summary><b>Linux / macOS</b></summary>

```bash
git clone https://github.com/bfly123/claude_code_bridge.git
cd claude_code_bridge
./install.sh install
```

</details>

<details>
<summary><b>WSL (Windows 子系统)</b></summary>

> 如果你的 Claude/Codex/Gemini 运行在 WSL 中，请使用此方式。

```bash
# 在 WSL 终端中运行
git clone https://github.com/bfly123/claude_code_bridge.git
cd claude_code_bridge
./install.sh install
```

</details>

<details>
<summary><b>Windows 原生</b></summary>

> 如果你的 Claude/Codex/Gemini 运行在 Windows 原生环境，请使用此方式。

```powershell
git clone https://github.com/bfly123/claude_code_bridge.git
cd claude_code_bridge
powershell -ExecutionPolicy Bypass -File .\install.ps1 install
```

</details>

### 启动
```bash
ccb up codex            # 启动 Codex
ccb up gemini           # 启动 Gemini
ccb up codex gemini     # 同时启动两个
```

### 常用参数
| 参数 | 说明 | 示例 |
| :--- | :--- | :--- |
| `-r` | 恢复上次会话上下文 | `ccb up codex -r` |
| `-a` | 全自动模式，跳过权限确认 | `ccb up codex -a` |
| `-h` | 查看详细帮助信息 | `ccb -h` |
| `-v` | 查看当前版本和检测更新 | `ccb -v` |

### 后续更新
```bash
ccb update              # 更新 ccb 到最新版本
```

---

## 🗣️ 使用场景

安装完成后，直接用自然语言与 Claude 对话即可，它会自动检测并分派任务。

**常见用法：**

- **代码审查**：*"让 Codex 帮我 Review 一下 `main.py` 的改动。"*
- **多维咨询**：*"问问 Gemini 有没有更好的实现方案。"*
- **结对编程**：*"Codex 负责写后端逻辑，我来写前端。"*
- **架构设计**：*"让 Codex 先设计一下这个模块的结构。"*
- **信息交互**：*"调取 Codex 3 轮对话，并加以总结"*

### 🎴 趣味玩法：AI 棋牌之夜！

> *"让 Claude、Codex 和 Gemini 来一局斗地主！你来发牌，大家明牌玩！"*
>
> 🃏 Claude (地主) vs 🎯 Codex + 💎 Gemini (农民)

> **提示：** 底层命令 (`cask`, `cping` 等) 通常由 Claude 自动调用，需要显式调用见命令详情。

---

## 📝 命令详情

### Codex 命令

| 命令 | 说明 |
| :--- | :--- |
| `/cask <消息>` | 后台模式：提交任务给 Codex，前台释放可继续其他任务（推荐） |
| `/cask-w <消息>` | 前台模式：提交任务并等待返回，响应更快但会阻塞 |
| `cpend [N]` | 调取当前 Codex 会话的对话记录，N 控制轮数（默认 1） |
| `cping` | 测试 Codex 连通性 |

### Gemini 命令

| 命令 | 说明 |
| :--- | :--- |
| `/gask <消息>` | 后台模式：提交任务给 Gemini |
| `/gask-w <消息>` | 前台模式：提交任务并等待返回 |
| `gpend [N]` | 调取当前 Gemini 会话的对话记录 |
| `gping` | 测试 Gemini 连通性 |

---

## 🖥️ 编辑器集成：Neovim + 多模型代码审查

<img src="assets/nvim.png" alt="Neovim 集成多模型代码审查" width="900">

> 结合 **Neovim** 等编辑器，实现无缝的代码编辑与多模型审查工作流。在你喜欢的编辑器中编写代码，AI 助手实时审查并提供改进建议。

---

## 📋 环境要求

- **Python 3.10+**
- **终端软件：** [WezTerm](https://wezfurlong.org/wezterm/) (强烈推荐) 或 tmux

---

## 🗑️ 卸载

```bash
./install.sh uninstall
```

---

<div align="center">

**Windows 完全支持** (WSL + 原生 Windows 均通过 WezTerm)

---

**测试用户群，欢迎加入**

<img src="assets/wechat.png" alt="微信群" width="300">

</div>
