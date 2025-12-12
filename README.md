# Claude-Codex

Claude 与 Codex 双窗口协作工具 | Dual-pane helper that bridges Claude and Codex over tmux with session isolation. Works on Linux/macOS; Windows is supported via WSL2. 欢迎测试和反馈（v: 710210567）。

![Claude 与 Codex 双窗口示意图](figure.png)

## 简介 / Overview
- CN：通过 Claude 给 Codex 发送指令，并从 Codex 回读结果，保持各自会话隔离。
- EN：Send instructions from Claude to Codex and read responses back, keeping sessions isolated.
- English prompts are supported end-to-end; commands simply forward text and do not depend on language.

## 安装 / Install
```bash
./install.sh install
```

## 启动 / Start
```bash
claude_codex              # 基础启动 / default start
claude_codex -c           # 恢复 Claude 上下文（当前目录）/ resume Claude context for cwd
claude_codex -C           # 恢复 Codex 上下文（当前目录）/ resume Codex context for cwd
claude_codex -C -c        # 同时恢复 / resume both
```

## 核心命令 / Core Commands
- `/cask-w <question>`：同步等待 Codex 回复（默认推荐）  
  `/cask-w <question>`: synchronous; waits for Codex to reply.
- `/cask <question>`：异步发送，不等待  
  `/cask <question>`: async fire-and-forget.
- `/cpend`：查看最新回复  
  `/cpend`: show latest reply.
- `/cping`：测试连通性  
  `/cping`: connectivity check.

## 自动化特性 / Automation
- CN：安装后，Claude 会在检测到 Codex 协作意图时自动调用命令。默认同步使用 `cask-w`，如明确要求异步则用 `cask`，查状态用 `cping`，查回复用 `cpend`。
- EN：After installing the helper rules, Claude will auto-call commands when collaboration intent is detected. Default is synchronous `cask-w`; if you explicitly say “send without waiting”, it uses `cask`. Use `cping` for health, `cpend` to read the latest reply.

## 项目结构 / Project Structure
```
claude_codex/
├── cask                  # 异步命令转发 / async forwarder
├── cask-w                # 同步命令转发 / sync forwarder
├── cpend                 # 查看回复 / show reply
├── cping                 # 连通性测试 / connectivity check
├── claude_codex          # 主启动器 / launcher
├── codex_comm.py         # 通信模块 / comm layer
├── codex_dual_bridge.py  # tmux 桥接器 / tmux bridge
├── commands/             # 命令文档 / command docs
└── install.sh            # 安装脚本 / installer
```

## 核心功能 / Highlights
- 双窗口 Claude-Codex 协作 / dual-pane collaboration.
- 会话隔离（session_id 过滤）/ session isolation via session_id.
- tmux 命令转发 / tmux forwarding.
- 支持异步/同步通信 / async & sync modes.
- 自动清理临时文件 / auto temp cleanup.

## 卸载 / Uninstall
```bash
./install.sh uninstall
```

## 依赖 / Requirements
- Python 3.8+
- tmux

macOS: `brew install tmux`  
Linux: e.g. `sudo apt-get install tmux`, `sudo dnf install tmux`, or `sudo pacman -S tmux` before running the installer.

## WSL 支持 / WSL Support
- WSL2: fully supported  
- WSL1: not supported (FIFO limitation)

升级到 WSL2 / upgrade to WSL2:
```powershell
wsl --set-version <distro> 2
```
建议在 WSL 内部文件系统（如 `~/projects`）中运行，避免 `/mnt/c` 下的性能损失。  
For best performance, work inside the WSL filesystem (e.g., `~/projects`) instead of `/mnt/c`.
