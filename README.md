# Claude Codex Lock

为 Claude Code 提供持久、隔离的 Codex 后台服务。该工具在本地启动一个守护进程，为每个终端或窗口分配独立的 Codex 实例，并自动处理生命周期、日志及历史记录。

## 关键特性

- **多客户端隔离**：每个 `claude-codex` 会话都会生成独立的 `CODEX_CLIENT_ID`，守护进程按客户端维护专属的 `ClaudeCodexManager` 与子进程，互不干扰。
- **自动恢复**：历史记录与配置保存在 `/tmp/codex-<instance>-history.json`，同一客户端重连时会自动恢复上下文。
- **真实 Codex 调用**：守护进程子进程通过 `codex exec --json` 调用 Codex CLI，解析流式输出并返回最终答案。
- **健壮通信**：Unix Socket + 超时重试，单次请求默认 180 秒超时，并自动截断响应换行。
- **运行洞察**：提供 `/codex-status` 与 `/codex-health` 命令/接口，可同时查看单客户端与全局运行概况。
- **自动清理**：当客户端 60 秒无活动时，对应 Codex 子进程会自动关闭，可通过 `CODEX_CLIENT_IDLE_TIMEOUT` 环境变量调整。

## 组件概览

```
claude-codex (脚本)
  └─ 设置 CODEX_CLIENT_ID、启动 codex_daemon.py、拉起 Claude Code

codex_daemon.py (守护进程)
  ├─ 监听 /tmp/codex-daemon.sock
  ├─ 按 client_id 懒加载 ClaudeCodexManager
  └─ 代理 /codex-* 命令至对应 Codex 实例

claude_codex_manager.py
  ├─ 生成/恢复 instance_id、管理历史文件
  ├─ fork CodexProcess 子进程
  └─ 监控子进程并自动重启

codex_process.py
  ├─ 接收查询/配置请求
  ├─ 构造提示词并调用 `codex exec --json`
  └─ 保持对话历史、配置状态
```

## 快速开始

1. **准备环境**
   - Python ≥ 3.8
   - 已安装 Codex CLI (`codex --version`)
   - Linux 或 macOS（需要 Unix socket 支持）

2. **安装 / 卸载**
   ```bash
   git clone <项目地址>
   cd claude_codex_lock
   ./install.sh install        # 安装

   # 卸载（任选其一）
   ./install.sh uninstall
   claude-codex-install uninstall
   ```
   默认会将项目安装到 `~/.local/share/claude-codex-lock`，并创建以下链接：
   - `~/.local/bin/claude-codex`：一键启动守护进程 + Claude Code
   - `~/.local/bin/claude-codex-install`：全局安装/卸载入口
   - `~/.claude/commands/codex`（如不存在则自动创建）：在 Claude 中可直接使用 `/codex-*` 命令

   可通过环境变量定制：
   - `CODEX_INSTALL_PREFIX`：安装目录
   - `CODEX_BIN_DIR`：bin 目录
   - `CODEX_CLAUDE_COMMAND_DIR`：Claude 命令目录

3. **启动守护进程并运行 Claude Code**
   ```bash
   claude-codex
   ```
   - 守护进程默认使用 `~/.codex_runtime/codex-daemon.sock`，适配多数受限环境。
   - 首次启动会分配一个随机 `CODEX_CLIENT_ID` 并写入子进程环境。
   - 如需自定义，可在运行前设置 `CODEX_CLIENT_ID=my-session claude-codex`。

4. **在 Claude Code 中使用命令**
   ```
   /codex-ask …          # 提问
   /codex-config …       # 切换 high/default/low
   /codex-reasoning on   # 控制推理展示
   /codex-final_only on  # 控制输出格式
   /codex-status         # 查看当前客户端状态
   /codex-stop           # 关闭当前客户端实例
   ```

## 多客户端使用

- 每个终端/窗口运行 `claude-codex` 都会携带独立 `CODEX_CLIENT_ID`。
- 守护进程按 `client_id` 存储历史、配置和 socket，确保上下文不会串线。
- 同一客户端再次启动会尝试复用其历史文件并恢复 conversation context。
- 每个客户端若超过 60 秒无请求，会被守护进程自动清理以释放资源，可通过 `CODEX_CLIENT_IDLE_TIMEOUT=<秒>` 调整阈值。

### 查看全局状态

```bash
python3 codex_daemon.py --health
```

响应示例：
```json
{
  "status": "healthy",
  "uptime": 125.3,
  "client_count": 2,
  "clients": [
    {"client_id": "clientA", "codex_active": true, "instance_id": "0e6f9e42"},
    {"client_id": "clientB", "codex_active": false, "instance_id": null}
  ]
}
```

也可以直接向 socket 查询：
```bash
python3 - <<'PY'
import socket, json
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/tmp/codex-daemon.sock')
sock.send(json.dumps({"command": "/codex-status"}).encode('utf-8'))
print(sock.recv(4096).decode())
PY
```

## 关闭服务

- **当前客户端**：在 Claude 中执行 `/codex-stop`，只停止对应 Codex 实例。
- **全部客户端/守护进程**：执行 `/codex-shutdown`，或在 shell 中发送同等请求。
  ```bash
  python3 - <<'PY'
  import socket, json
  sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  sock.connect('/tmp/codex-daemon.sock')
  sock.send(json.dumps({"command": "/codex-shutdown"}).encode('utf-8'))
  print(sock.recv(4096).decode())
  PY
  ```
- **紧急终止**（不推荐）：`pkill -f codex_daemon.py`，可能遗留 socket/历史文件。

## 调试与日志

- 守护进程日志：`/tmp/codex-daemon.log`
- 子进程日志：`/tmp/codex-<instance>-debug.log`
- 历史文件：`/tmp/codex-<instance>-history.json`
- 守护进程健康校验：`python3 codex_daemon.py --health`
- 若 `codex exec` 命令缺失或超时，子进程会返回明确的错误提示。
- 如需手动清理，可删除 `~/.codex_runtime/codex-daemon.sock`、`~/.codex_runtime/codex-daemon.pid`。

若系统策略禁止在 `/tmp` 创建 Unix Socket，可在启动前改用自定义路径（程序会自动尝试 `~/.codex_runtime/`，仍不行时退回 `/tmp/codex-$USER/`）：

```bash
export CODEX_DAEMON_SOCKET="$HOME/.codex_runtime/codex-daemon.sock"
export CODEX_DAEMON_PID="$HOME/.codex_runtime/codex-daemon.pid"
claude-codex
```

摘掉这些环境变量即可恢复默认行为。

若 `~/.codex_runtime` 目录曾以 root 身份创建，请先 `chmod -R 700 ~/.codex_runtime && chown -R $USER ~/.codex_runtime` 或直接删除后再运行，避免因权限导致守护进程不断退回其他路径。

## 开发提示

### 项目技术介绍
- 采用 Python 3 编写的守护进程 + 子进程架构，`codex_daemon.py` 负责长连接管理，`claude_codex_manager.py` 负责实例生命周期，`codex_process.py` 处理实际 Codex 调用。
- 通过 Unix Domain Socket/FIFO 作为主通信通道，结合结构化 JSON 协议，实现 CLI 与守护进程之间的双向指令流。
- 历史记录、安全写入与恢复逻辑集中在 `ClaudeCodexManager`，利用 0600 权限、`O_NOFOLLOW` 防止符号链接攻击，并提供分钟级实例恢复。
- Slash 命令通过 `codex_commands.py` 与 `commands/codex` 脚本嵌入 Claude CLI，保持与前端互动时的统一体验。

### 核心技术特点
- **多客户端复用**：基于 `client_id` 的懒加载管理器，动态分配 Codex 子进程并复用历史。
- **健壮通信链路**：内建重试、超时控制以及健康检查接口，降低短暂抖动导致的失败。
- **自动清理与守护**：守护线程检测空闲会话，触发 `claude_cleanup_on_exit` 进行资源回收，减少僵尸进程风险。
- **安全运行环境**：运行目录权限检查、套接字所有者校验以及可配置的 runtime 目录，适配多种受限环境。
- **扩展友好**：明确的模块划分与辅助方法（如 `_handle_config_request`、`get_current_config`），便于新增配置项或接入更多命令。

- 多客户端行为已在 `codex_daemon.py` 与 `claude_codex_manager.py` 内复用，新增特性时请确保保持 `client_id` 传递。
- 对话历史默认保留最近 200 轮，可在 `codex_process.py` 内调整。
- `_save_history` 使用安全写入策略（`O_NOFOLLOW`、权限 0600），修改时注意保持安全性。
- 所有 CLI 调用默认 `--sandbox read-only`，如需写权限请在调用层扩展。

---

欢迎根据自身工作流扩展命令或加入更详细的监控。如发现问题，可通过守护进程日志与健康接口快速定位。祝使用愉快！***
