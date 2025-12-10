# Claude-Codex

Claude 与 Codex 双窗口协作工具，支持会话隔离的 tmux 通信。 通过claude发送信息给codex 并从codex读取信息。
目前支持linux系统和mac系统（未测试）。

![Claude 与 Codex 双窗口示意图](figure.png)

## 安装

```bash
./install.sh install
```

## 启动

```bash
claude_codex              # 基础启动
claude_codex -c           # 恢复 Claude 上下文 基于执行目录
claude_codex -C           # 恢复 Codex 上下文 基于执行目录
claude_codex -C -c 
```

## 核心命令

在 Claude 窗口中使用：

```bash
/cask <问题>      # 异步发送问题
/cask-w <问题>    # 同步等待回复
/cpend            # 查看最新回复
/cping            # 测试连通性
```

## 项目结构

```
claude_codex/
├── cask                  # 异步命令转发
├── cask-w                # 同步命令转发
├── cpend                 # 查看回复
├── cping                 # 连通性测试
├── claude_codex          # 主启动器
├── codex_comm.py         # 通信模块
├── codex_dual_bridge.py  # tmux 桥接器
├── commands/             # 命令文档
└── install.sh            # 安装脚本
```

## 核心功能

- 双窗口 Claude-Codex 模式
- 会话隔离（session_id 过滤）
- tmux 命令转发
- 异步/同步通信
- 自动清理临时文件

## 自动化特性

安装后 Claude 会自动识别 Codex 协作意图并调用相应命令：

**触发条件**（任一满足）：
- 提到 codex/Codex 且带有疑问/请求/协作语气
- 想让 Codex 做某事、给建议、帮忙看
- 询问 Codex 的状态或之前的回复

**命令自动选择**：
- 默认使用 `cask`（异步），不阻塞当前会话
- 仅在明确要求等待时使用 `cask-w`
- 查状态用 `cping`，查回复用 `cpend`

**使用示例**：
```
"让 codex 看看这段代码"     → cask（异步）
"codex 有什么建议"          → cask（异步）
"等 codex 回复"             → cask-w（同步等待）
"codex 那边怎么说"          → cpend
"codex 还活着吗"            → cping
```

## 卸载

```bash
./install.sh uninstall
```

## 依赖

- Python 3.8+
- tmux

macOS 可使用 `brew install tmux`，Linux 根据发行版执行如 `sudo apt-get install tmux`、`sudo dnf install tmux`、`sudo pacman -S tmux` 等命令，确保在运行 `./install.sh install` 前已经安装好。

## WSL 支持

- **WSL 2**：完全支持
- **WSL 1**：不支持（FIFO 限制）

升级到 WSL 2：
```powershell
wsl --set-version <distro> 2
```

建议在 WSL 内部文件系统（如 `~/projects`）中运行，避免在 `/mnt/c` 下使用以获得更好的性能。
