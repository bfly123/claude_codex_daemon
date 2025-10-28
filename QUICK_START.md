# 🚀 快速开始指南

## ✅ 系统已就绪

旧系统已清理，新双窗口模式命令已全局可用！

---

## 🎯 立即开始

### 1. 启动双窗口模式
```bash
/home/bfly/运维/基本问题/claude-codex-dual
```

### 2. 测试连接（启动后在Claude窗口中使用）
```bash
/codex-ping        # 测试连通性
/codex-status      # 查看状态
```

### 3. 开始对话
```bash
/codex-ask "你好，请介绍一下自己"              # 异步模式
/codex-ask --wait "解释一下Python装饰器"     # 同步模式
```

---

## 📋 可用命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/codex-ask <问题>` | 异步发送问题 | `/codex-ask "写一个函数"` |
| `/codex-ask --wait <问题>` | 同步等待回复 | `/codex-ask -w "解释代码"` |
| `/codex-status` | 查看连接状态 | `/codex-status` |
| `/codex-ping` | 测试连通性 | `/codex-ping` |
| `/codex-history [n]` | 查看对话历史 | `/codex-history 5` |

---

## 💡 重要提示

1. **先启动双窗口模式**，再使用控制命令
2. **异步模式**适合发送问题后继续工作
3. **同步模式**适合需要立即结果的重要查询
4. **保持两个窗口开启**确保通信正常

---

## 🎉 享受双窗口协作体验！

现在可以同时使用Claude的开发功能和Codex的AI对话能力了！

---
*快速开始指南 - Claude-Codex 双窗口模式*