# 🎯 Claude-Codex 双窗口模式 - 使用指南

## ✅ 系统已清理完成

旧系统已成功清理，新双窗口模式现在可以正常使用！

---

## 🚀 立即开始使用

### 方法1: 使用完整路径（推荐）
```bash
# 启动双窗口模式
/home/bfly/运维/基本问题/claude-codex-dual

# 检查系统状态
/home/bfly/运维/基本问题/test_dual_mode.py
```

### 方法2: 添加别名到shell
编辑 `~/.bashrc` 或 `~/.zshrc`，添加：
```bash
# Claude-Codex 双窗口模式别名
alias dual-codex='/home/bfly/运维/基本问题/claude-codex-dual'
alias dual-ask='/home/bfly/运维/基本问题/codex-ask'
alias dual-status='/home/bfly/运维/基本问题/codex-status'
alias dual-ping='/home/bfly/运维/基本问题/codex-ping'
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

---

## 🎮 完整使用流程

### 1. 启动双窗口模式
```bash
# 使用完整路径
/home/bfly/运维/基本问题/claude-codex-dual

# 或使用别名（如果已配置）
dual-codex
```

**预期输出**：
```
🚀 Claude-Codex 双窗口模式
📅 启动时间: 2025-10-27 16:30:00
🆔 会话ID: dual-1761553800-123456
==================================================
🔧 创建通信管道...
✅ 管道创建完成:
   输入: /tmp/codex-bfly/dual-1761553800-123456/input.fifo
   输出: /tmp/codex-bfly/dual-1761553800-123456/output.fifo
🚀 启动Codex窗口...
✅ 检测到终端: gnome-terminal
✅ Codex窗口已启动 (PID: 12345)
🚀 启动Claude窗口...
✅ Claude窗口就绪

🎯 可用命令:
   /codex-ask <问题>              - 异步发送问题
   /codex-ask --wait <问题>       - 同步等待回复
   /codex-status                  - 查看连接状态
   /codex-ping                    - 测试连通性
```

### 2. 在Claude窗口中发送指令
```bash
# 异步模式（推荐，立即返回）
/codex-ask "写一个Python函数计算斐波那契数列"

# 同步模式（等待回复）
/codex-ask --wait "解释一下量子计算的基本原理"
/codex-ask -w "帮我想一个算法解决方案"
```

### 3. 检查连接状态
```bash
# 查看详细状态
/codex-status

# 测试连通性
/codex-ping

# 查看对话历史
/codex-history 5
```

---

## 📋 可用命令清单

### 启动命令
| 命令 | 功能 | 示例 |
|------|------|------|
| `claude-codex-dual` | 启动双窗口模式 | `./claude-codex-dual` |
| `claude-codex-dual --resume` | 恢复上次会话 | `./claude-codex-dual --resume` |
| `claude-codex-dual /path/to/project` | 在项目目录启动 | `./claude-codex-dual ~/my-project` |

### 控制命令（在Claude窗口中使用）
| 命令 | 功能 | 模式 | 示例 |
|------|------|------|------|
| `/codex-ask <问题>` | 异步发送问题 | 异步 | `/codex-ask "写一个排序算法"` |
| `/codex-ask --wait <问题>` | 同步等待回复 | 同步 | `/codex-ask -w "解释这段代码"` |
| `/codex-status` | 查看连接状态 | - | `/codex-status` |
| `/codex-ping` | 测试连通性 | - | `/codex-ping` |
| `/codex-history [n]` | 查看对话历史 | - | `/codex-history 10` |

---

## 💡 使用技巧

### 异步 vs 同步模式
- **异步模式**：发送问题后立即返回，适合继续其他工作
- **同步模式**：等待Codex回复，适合需要立即结果的重要查询

### 最佳实践
1. **启动后先测试**：使用 `/codex-ping` 确认连接正常
2. **异步模式优先**：大部分情况使用异步模式提高效率
3. **重要查询用同步**：需要立即反馈的关键问题使用同步模式
4. **定期查看历史**：使用 `/codex-history` 回顾之前的对话

### 工作流程示例
```bash
# 1. 启动双窗口
dual-codex

# 2. 测试连接
/codex-ping

# 3. 批量发送问题（异步）
/codex-ask "分析这个算法的时间复杂度"
/codex-ask "提供优化建议"
/codex-ask "写出改进后的代码"

# 4. 继续在Claude中工作...

# 5. 查看状态和历史
/codex-status
/codex-history 5

# 6. 重要问题同步等待
/codex-ask --wait "这个方案是否可行？"
```

---

## 🔧 故障排除

### 常见问题

**Q: 启动时提示终端未找到**
```bash
A: 系统会自动使用tmux作为备选方案，这是正常的
```

**Q: /codex-ask 命令提示会话异常**
```bash
A: 确保已启动双窗口模式，先运行 claude-codex-dual
```

**Q: Codex窗口无响应**
```bash
A: 使用 /codex-ping 测试连通性，如果失败重启双窗口模式
```

**Q: 管道创建失败**
```bash
A: 检查 /tmp 目录权限，确保有写权限
```

### 调试命令
```bash
# 检查系统状态
/home/bfly/运维/基本问题/test_dual_mode.py

# 查看详细帮助
/home/bfly/运维/基本问题/claude-codex-dual --help

# 查看使用示例
/home/bfly/运维/基本问题/example_usage.py
```

---

## 📁 文件位置说明

### 核心文件
```
/home/bfly/运维/基本问题/
├── claude-codex-dual          # 双窗口启动器
├── codex_comm.py              # 通信核心模块
├── codex-ask                  # ask命令入口
├── codex-status               # status命令入口
├── codex-ping                 # ping命令入口
├── codex_history.py           # 历史查看器
├── README-DUAL.md             # 完整文档
├── USAGE_GUIDE.md             # 使用指南（本文件）
└── commands/                  # 命令文档目录
```

### 运行时文件
```
/tmp/codex-bfly/dual-{session-id}/
├── input.fifo                 # Claude→Codex管道
├── output.fifo                # 输出监控管道
├── codex.pid                  # Codex进程PID
├── claude.pid                 # Claude进程PID
└── status                     # 运行状态文件
```

### 项目文件
```
./.codex-session               # 项目会话信息（自动生成）
```

---

## 🎊 享受新体验

现在你已经完全准备好使用全新的Claude-Codex双窗口协作模式了！

**主要优势**：
- 🚀 **双窗口独立** - Claude和Codex各自独立工作
- 🔄 **灵活控制** - 单向控制通道，互不干扰
- ⚡ **高效协作** - 异步模式提高工作效率
- 💾 **智能管理** - 自动会话管理和资源清理

**立即开始**：
```bash
/home/bfly/运维/运维基本问题/claude-codex-dual
```

祝您使用愉快！🎉

---
*使用指南更新时间: 2024-01-27*
*适用版本: 双窗口模式 v1.0*