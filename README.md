# Claude-Codex

Claude 与 Codex 双窗口协作工具，支持会话隔离的 tmux 通信。 通过claude发送信息给codex 并从codex读取信息。
目前支持linux系统和mac系统（未测试）。

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
cask <问题>      # 异步发送问题
cask-w <问题>    # 同步等待回复
cpend            # 查看最新回复
cping            # 测试连通性
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

## 卸载

```bash
./install.sh uninstall
```

## 依赖

- Python 3.8+
- tmux

macOS 可使用 `brew install tmux`，Linux 根据发行版执行如 `sudo apt-get install tmux`、`sudo dnf install tmux`、`sudo pacman -S tmux` 等命令，确保在运行 `./install.sh install` 前已经安装好。
