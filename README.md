# Claude-Codex 双窗口系统

Claude 与 Codex 双窗口协作工具，支持异步/同步通信和上下文恢复。

## 快速开始

### 安装
```bash
./install.sh install
```

安装后会创建以下命令：
- `claude_codex` - 启动双窗口模式
- `cask` / `cask-w` - 发送问题（异步/同步）
- `cping` - 测试连通性
- `cpend` - 查看最新回复

### 启动
```bash
# 基础启动
claude_codex

# 恢复 Claude 上下文
claude_codex -c

# 恢复 Codex 上下文
claude_codex -C

# 在指定目录启动
claude_codex /path/to/project
```

## 核心命令

在 Claude 窗口中使用：

```bash
cask <问题>         # 异步发送问题
cask-w <问题>       # 同步等待回复
cping               # 测试连通性
cpend               # 查看最新回复
```

### 使用示例

**异步模式（推荐）：**
```bash
cask "写一个快速排序函数"
# 立即返回，继续其他工作
cpend  # 稍后查看结果
```

**同步模式：**
```bash
cask-w "解释快速排序原理"
# 等待并直接显示结果
```

## 系统架构

### 会话管理
- 每次启动生成唯一会话 ID
- 运行时目录：`/tmp/codex-<user>/<session-id>/`
- 项目绑定文件：`.codex-session`

### 通信机制
- FIFO 管道：Claude → Codex 单向控制
- tmux 日志监控：Codex 输出回传
- 消息标记：确保回复匹配

### 文件结构
```
/tmp/codex-<user>/<session-id>/
├── input.fifo          # Claude → Codex 控制管道
├── output.fifo         # Codex 输出监控
├── codex.pid           # Codex 进程 PID
├── claude.pid          # Claude 进程 PID
├── bridge.pid          # 桥接器进程 PID
├── status              # 运行状态
└── bridge_output.log   # tmux 输出日志
```

## 环境变量

```bash
CODEX_SESSION_ID          # 会话标识
CODEX_RUNTIME_DIR         # 运行时目录
CODEX_INPUT_FIFO          # 输入管道路径
CODEX_OUTPUT_FIFO         # 输出管道路径
CODEX_TMUX_SESSION        # tmux 会话名
CODEX_SYNC_TIMEOUT        # 同步超时（默认 30s）
```

## 故障排除

### 检查连通性
```bash
cping
```

### 查看会话信息
```bash
cat .codex-session
```

### 手动清理
```bash
# 查找会话目录
ls /tmp/codex-$(whoami)/

# 清理指定会话
rm -rf /tmp/codex-$(whoami)/dual-<session-id>
```

## 卸载

```bash
./install.sh uninstall
```

## 技术要点

- **Python 3.8+** 和 **tmux** 必须安装
- 支持多种终端：gnome-terminal、konsole、alacritty、xterm
- 自动清理：退出时清理所有临时文件和子进程
- 权限隔离：运行时目录权限 600/644
