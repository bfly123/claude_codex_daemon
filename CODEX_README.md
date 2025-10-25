# Codex 后台服务文档

## 概述

Codex 后台服务是一个基于 Python 的子进程管理系统，提供稳定的 AI 对话服务。该系统通过 Unix Socket 通信，支持会话持久化、自动重启恢复和配置管理。

## 系统架构

```
Claude 主进程
    ├── ClaudeCodexManager (进程管理器)
    │   ├── 自动激活和会话恢复
    │   ├── 子进程监控和自动重启
    │   └── Socket 通信管理
    ├── CodexProcess (子进程服务)
    │   ├── AI 模型调用
    │   ├── 配置动态更新
    │   └── 对话历史管理
    └── codex_commands.py (命令接口)
        ├── 用户命令解析
        ├── 参数验证
        └── 错误处理
```

## 依赖要求

### 系统要求
- Python 3.8+
- Linux/Unix 系统（支持 Unix Socket）
- 至少 512MB 可用内存

### Python 包依赖
```bash
# 无外部依赖，仅使用 Python 标准库
import json
import os
import signal
import socket
import stat
import time
import uuid
import threading
import hashlib
import pwd
import glob
```

## 快速开始

### 1. 基本启动
```python
from codex_commands import handle_codex_command

# 启动服务
result = handle_codex_command('/codex-start')
print(result)  # 输出: ✅ Codex服务已启动 (实例ID: xxx, 默认Profile: default)

# 发送问题
result = handle_codex_command('/codex-ask 什么是Python？')
print(result)
```

### 2. 配置管理
```python
# 查看当前配置
handle_codex_command('/codex-config')

# 切换性能档位
handle_codex_command('/codex-config high')    # 深度分析
handle_codex_command('/codex-config low')     # 简洁快速

# 推理显示控制
handle_codex_command('/codex-reasoning on')   # 显示推理过程
handle_codex_command('/codex-reasoning off')  # 仅输出答案

# 输出格式控制
handle_codex_command('/codex-final_only on')  # 仅最终答案
handle_codex_command('/codex-final_only off') # 包含详细信息
```

### 3. 服务管理
```python
# 查看服务状态
handle_codex_command('/codex-status')

# 停止服务
handle_codex_command('/codex-stop')

# 查看帮助
handle_codex_command('/codex-help')
```

## 配置选项

### Profile 档位设置
| 档位 | 描述 | 适用场景 |
|------|------|----------|
| high | 深度分析 | 复杂问题、代码分析、技术探讨 |
| default | 平衡模式 | 日常问答、一般咨询 |
| low | 简洁快速 | 简单问题、快速查询 |

### Show Reasoning
- **on**: 输出推理过程摘要，帮助理解 AI 思考路径
- **off**: 仅返回最终答案，保持输出简洁

### Output Format
- **final_only**: 仅输出最终答案，减少信息噪音
- **final_with_details**: 包含额外细节和元数据信息

## 核心文件说明

### 主要模块
- `claude_codex_manager.py`: 进程管理器，负责子进程生命周期管理
- `codex_process.py`: 子进程服务，处理 AI 模型调用
- `codex_commands.py`: 命令接口，提供用户友好的命令行接口

### 临时文件
- Socket 文件: `/tmp/codex-{instance_id}-{claude_pid}.sock`
- 历史文件: `/tmp/codex-{instance_id}-history.json`

## 安全特性

### 1. 权限控制
- 所有临时文件权限设置为 0600（仅所有者可读写）
- Socket 文件所有权验证
- 历史文件所有者校验

### 2. 进程隔离
- 基于 Claude PID 的实例隔离
- 每个 Claude 会话独立的实例 ID
- 防止不同会话间的数据泄露

### 3. 异常处理
- 子进程崩溃自动重启
- 通信异常重试机制
- 资源清理保证

## 调试技巧

### 1. 启用调试日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 检查进程状态
```bash
# 查找 codex 进程
ps aux | grep codex

# 检查 socket 文件
ls -la /tmp/codex-*.sock

# 检查历史文件
ls -la /tmp/codex-*history.json
```

### 3. 手动清理
```python
from codex_commands import handle_codex_command
handle_codex_command('/codex-stop')

# 或手动删除临时文件
import os
import glob
for f in glob.glob('/tmp/codex-*test*'):
    try:
        os.unlink(f)
    except:
        pass
```

### 4. 常见问题排查

#### 问题：服务启动失败
```python
# 检查权限
os.access('/tmp', os.W_OK)

# 检查端口占用
import socket
for pid in range(1000, 9999):
    sock_path = f"/tmp/codex-test-{pid}.sock"
    if os.path.exists(sock_path):
        print(f"Socket exists: {sock_path}")
```

#### 问题：通信超时
```python
# 增加超时时间
# 在 send_to_codex 方法中调整超时参数
```

#### 问题：历史恢复失败
```python
# 检查历史文件完整性
import json
with open('/tmp/codex-xxx-history.json', 'r') as f:
    data = json.load(f)
    print(data.keys())
```

## 测试

### 运行完整测试套件
```bash
# 工作流测试
python3 test/test_codex_workflow.py

# 异常场景测试
python3 test/test_codex_exceptions.py
```

### 自定义测试
```python
# 快速连接测试
from codex_commands import handle_codex_command
result = handle_codex_command('/codex-start')
assert '已启动' in result

result = handle_codex_command('/codex-ask 测试')
assert '❌' not in result
```

## 性能优化

### 1. 内存管理
- 定期清理对话历史（超过 1000 条时自动归档）
- 子进程内存使用监控
- Socket 缓冲区大小优化

### 2. 响应时间
- 连接池复用
- 异步请求处理
- 智能预加载机制

### 3. 资源限制
- 最大对话历史数量限制
- 单次响应长度限制
- 并发请求数量控制

## 故障恢复

### 自动恢复机制
1. **子进程崩溃**: 监控线程检测到进程退出后自动重启
2. **会话状态恢复**: 从历史文件恢复对话历史和配置
3. **Socket 重建**: 重启后自动创建新的 Socket 通道

### 手动恢复步骤
1. 停止现有服务: `/codex-stop`
2. 清理残留文件: 删除 `/tmp/codex-*` 相关文件
3. 重新启动: `/codex-start`
4. 验证功能: 发送测试问题

## 扩展开发

### 添加新命令
```python
# 在 codex_commands.py 中添加
def handle_new_command(args):
    if not codex_manager.codex_active:
        return "❌ Codex服务未激活"

    # 实现命令逻辑
    return "✅ 命令执行成功"

# 在 COMMANDS 映射中注册
COMMANDS = {
    # ... 现有命令
    '/codex-new': handle_new_command,
}
```

### 自定义配置选项
```python
# 在 ClaudeCodexManager 中添加新的配置属性
def __init__(self):
    # ... 现有属性
    self.new_config_option = default_value

# 在 _send_config_command 中支持新配置
def update_new_config(self, value):
    # 实现配置更新逻辑
    pass
```

## 版本历史

### v1.0.0
- 基础子进程管理功能
- Unix Socket 通信
- 会话持久化
- 自动重启恢复

### v1.1.0
- 配置动态更新
- 多档位支持
- 推理显示控制
- 输出格式选择

### v1.2.0
- 异常处理优化
- 并发请求支持
- 资源清理改进
- 测试套件完善

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 联系方式

如有问题或建议，请通过以下方式联系：
- 创建 Issue
- 发送邮件
- 技术讨论群