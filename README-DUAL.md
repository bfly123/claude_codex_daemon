# Claude-Codex 双窗口模式

全新的Claude与Codex双窗口协作系统，支持单向控制和独立操作。

## 🚀 快速开始

### 启动双窗口模式
```bash
# 基础启动
./claude-codex-dual

# 在项目目录启动
./claude-codex-dual /path/to/project

# 恢复上次会话
./claude-codex-dual --resume
```

### 基本使用
启动后会打开两个窗口：
- **Codex窗口**：独立的AI对话界面
- **Claude窗口**：开发工作界面，可控制Codex

## 📋 可用命令

### 核心控制命令
```bash
/codex-ask <问题>              # 异步发送问题（默认）
/codex-ask --wait <问题>       # 同步等待回复
/codex-ask -w <问题>           # 同步模式简写
```

### 状态查看命令
```bash
/codex-status                  # 查看详细状态
/codex-ping                    # 测试连通性
/codex-history [n]             # 查看对话历史
```

## 🎯 使用场景

### 异步模式（推荐）
```bash
/codex-ask "写一个Python函数计算斐波那契数列"
✅ 已发送到Codex (标记: ask-1704067200-12345...)

# Claude立即返回，可继续其他工作
```

### 同步模式
```bash
/codex-ask --wait "解释一下量子计算的基本原理"
🔔 发送问题到Codex...
⏳ 等待Codex回复...
🤖 Codex回复:
量子计算是一种利用量子力学原理...
```

## 🔧 系统架构

### 会话管理
- **唯一会话ID**：`dual-1704067200-12345`
- **运行时目录**：`/tmp/codex-user/dual-会话ID/`
- **项目绑定**：`./.codex-session`

### 通信机制
- **输入管道**：Claude → Codex控制指令
- **输出管道**：Codex → Claude状态监控
- **消息标记**：确保回复匹配

### 文件结构
```
/tmp/codex-user/dual-{session-id}/
├── input.fifo          # Claude→Codex管道
├── output.fifo         # Codex输出监控
├── codex.pid           # Codex进程PID
├── claude.pid          # Claude进程PID
├── status              # 运行状态
└── history/
    └── session.jsonl   # 对话历史
```

## 💡 高级功能

### 自动恢复
系统会自动检测并恢复异常的连接：
- Codex进程死亡 → 自动重启
- 管道损坏 → 重新创建
- 连接中断 → 自动重连

### 历史记录
- 自动保存所有对话到JSONL文件
- 支持项目级历史同步
- 可按时间查看历史记录

### 配置选项
支持环境变量配置：
```bash
export CODEX_SYNC_TIMEOUT=20    # 同步超时时间
export CODEX_AUTO_RECOVERY=1    # 启用自动恢复
export CODEX_SAVE_HISTORY=1     # 保存历史记录
```

## 🔍 故障排除

### 常见问题

**Q: 启动时提示"未检测到图形终端"**
A: 系统将使用tmux作为备选方案

**Q: Codex窗口无响应**
A: 使用 `/codex-ping` 测试连通性，或重启双窗口模式

**Q: 消息发送失败**
A: 检查管道状态，使用 `/codex-status` 查看详细信息

### 调试命令
```bash
# 检查会话状态
/codex-status

# 测试连通性
/codex-ping

# 查看最近对话
/codex-history 5
```

## 📁 文件说明

### 核心文件
- `claude-codex-dual` - 双窗口启动器
- `codex_comm.py` - 通信核心模块
- `codex-ask` - ask命令入口
- `codex-status` - status命令入口
- `codex-ping` - ping命令入口
- `codex_history.py` - 历史记录查看器

### 配置文件
- `commands/codex-ask.md` - ask命令文档
- `commands/codex-status.md` - status命令文档
- `commands/codex-ping.md` - ping命令文档
- `commands/codex-history.md` - history命令文档

## 🚨 注意事项

1. **终端兼容性**：支持gnome-terminal、konsole、alacritty、xterm等
2. **权限要求**：需要创建/tmp目录下文件的权限
3. **进程管理**：退出时会自动清理所有子进程和临时文件
4. **并发限制**：每个项目只能有一个活跃的双窗口会话

## 🎉 开始使用

1. 启动双窗口模式：
   ```bash
   ./claude-codex-dual
   ```

2. 在Claude窗口中测试：
   ```bash
   /codex-ask "你好，请介绍一下自己"
   ```

3. 查看状态：
   ```bash
   /codex-status
   ```

享受全新的双窗口协作体验！🚀