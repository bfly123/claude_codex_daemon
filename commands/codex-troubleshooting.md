# Codex 故障排除指南

## 常见问题及解决方案

### 1. Claude Code 中启动卡顿

**现象**: 执行命令后长时间无响应，但在终端中正常

**根本原因**: Python 输出缓冲区问题。Claude Code 环境中标准输出使用全缓冲模式，而 Codex 使用异步多线程输出，导致输出在缓冲区中延迟显示。

**关键验证方法**:
1. 检查实际进程状态：`ps aux | grep codex`
2. 查看临时文件：`ls -la /tmp/codex-*/`
3. 如果进程和文件都存在，说明启动成功，只是显示延迟

**解决方案**:

#### 方案A：Python 无缓冲模式（推荐）
```bash
codex-status
```

#### 方案B：stdbuf 强制无缓冲
```bash
stdbuf -o0 -e0 codex-status
```

#### 方案C：Python 代码内配置
```bash
python3 - <<'PY'
import sys, codex_bootstrap
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
print(handle_codex_command('/codex-status'))
PY
```

### 2. 进程冗余和资源占用

**现象**: 系统中出现大量 `node` 和 `codex` 进程，内存占用高

**检查方法**:
```bash
# 查看所有相关进程
ps aux | grep -E "(node|codex)" | grep -v grep

# 统计进程数量
ps aux | grep -E "(node|codex)" | grep -v grep | wc -l
```

**解决方案**:
```bash
# 清理所有相关进程
pkill -f "node.*codex"
pkill -f "python.*codex"

# 清理临时文件
rm -rf /tmp/codex-*/

# 重新启动
claude-codex
```

### 3. Socket 连接失败

**现象**: 提示连接失败或通信错误

**检查方法**:
```bash
# 查看 socket 文件
find /tmp -name "*codex*" -type s

# 检查权限
ls -la /tmp/codex-*/
```

**解决方案**:
```bash
# 完全重建服务
codex-stop
codex-status
# 在终端重新执行 claude-codex 以拉起守护进程
```

### 4. 配置丢失或异常

**现象**: 切换配置后行为异常

**检查方法**:
```bash
codex-status
```

**解决方案**:
```bash
# 重置到默认配置
codex-config default
```

## 预防措施

### 1. 正确关闭流程
结束使用时执行：
```bash
codex-stop
```

### 2. 定期清理
定期检查并清理冗余进程：
```bash
# 查看进程状态
ps aux | grep -E "(node|codex)" | grep -v grep

# 如果发现多余进程，清理后重启
pkill -f "node.*codex" && rm -rf /tmp/codex-*/
```

### 3. 环境适配
在不同环境中使用对应的启动方式：

**终端环境**:
```bash
claude-codex
```

**Claude Code 环境**:
```bash
codex-status
```

## 性能优化

### 1. 资源监控
```bash
# 监控内存使用
watch -n 2 'ps aux | grep -E "(node|codex)" | grep -v grep | awk "{sum+=\$6} END {print \"内存使用: \" sum/1024 \"MB\"}"'

# 监控进程数量
watch -n 2 'ps aux | grep -E "(node|codex)" | grep -v grep | wc -l'
```

### 2. 自动清理脚本
创建定期清理脚本 `cleanup_codex.sh`:
```bash
#!/bin/bash
# 清理超过1小时的僵尸进程和临时文件

# 清理僵尸进程
ps aux | grep -E "(node.*codex)" | grep -v grep | awk '$9 < "'$(date -d '1 hour ago' '+%H:%M')'" {print $2}' | xargs -r kill

# 清理旧的临时文件
find /tmp -name "codex-*" -type d -mtime +1 -exec rm -rf {} +
find /tmp -name "codex-*" -type s -mtime +1 -delete

echo "清理完成"
```

## 手动测试验证步骤

为了确认启动问题是否已解决，请按以下步骤手动测试：

### 步骤1：准备测试环境
```bash
# 清理现有进程
pkill -f "python.*codex" 2>/dev/null || true

# 进入项目目录
cd /home/bfly/运维/基本问题
```

### 步骤2：执行测试命令
```bash
# 启动守护进程并观察输出
claude-codex
```

### 步骤3：验证启动结果
**预期输出应该包含：**
```
[Codex Recovery] 未找到匹配的历史文件
[Codex Recovery] 创建初始历史文件
[Codex Recovery] 创建新会话
[Codex Monitor] 开始监控子进程 PID
[Codex Monitor] 监控线程已启动
✅ Codex服务已启动 (实例ID: xxxxxxxx, 默认Profile: default)
```

### 步骤4：后台验证
```bash
# 检查进程是否运行
ps aux | grep -E "(node|codex)" | grep -v grep

# 检查临时文件
ls -la /tmp/codex-*/

# 检查socket文件
find /tmp -name "*codex*" -type s
```

### 成功标准
- ✅ 命令在 0.1-0.3 秒内完成
- ✅ 显示完整的启动日志信息
- ✅ 最后显示 "✅ Codex服务已启动" 消息
- ✅ 后台有相应的 node 进程运行
- ✅ 创建了 socket 文件和历史文件

## 紧急恢复

如果遇到严重问题，执行以下紧急恢复步骤：

```bash
# 1. 强制终止所有进程
sudo pkill -9 -f "codex"

# 2. 清理所有临时文件
sudo rm -rf /tmp/codex-*

# 3. 检查系统状态
ps aux | grep codex
ls -la /tmp/codex-*/

# 4. 重新启动
claude-codex
```

## 技术细节

### 缓冲区问题详解

- **终端模式**: stdout 是行缓冲的，每行输出立即显示
- **管道模式**: stdout 是全缓冲的，等待缓冲区满（通常是8KB）或程序结束
- **Codex 异步输出**: 多线程和子进程的输出可能在缓冲区中混合，导致显示延迟

### 进程架构

```
Claude Code (父进程)
├── Python3 (子进程)
│   ├── codex_commands.py
│   └── claude_codex_manager.py
└── Node.js (孙进程)
    └── codex (二进制文件)
```

每个组件都有自己的输出流，在非终端环境下容易出现缓冲问题。
