#!/usr/bin/env python3
"""
Codex客户端命令处理器
连接到外部的Codex守护进程，处理所有codex相关命令
"""

import socket
import json
import os
from typing import Dict, Any, Optional

class CodexClient:
    def __init__(self, socket_path: Optional[str] = None):
        if socket_path is None:
            socket_path = os.environ.get("CODEX_DAEMON_SOCKET", "/tmp/codex-daemon.sock")
        self.socket_path = socket_path
        self.max_retries = 3
        self.base_timeout = 5  # 减少基础超时时间
        self.response_timeout = 180  # 默认请求超时时间（秒）
        self.client_id = self._resolve_client_id()

    def _resolve_client_id(self) -> str:
        """确定当前客户端的唯一标识"""
        env_id = os.environ.get("CODEX_CLIENT_ID")
        if env_id:
            return env_id

        hostname = os.uname().nodename if hasattr(os, "uname") else "unknown-host"
        return f"codex-client-{hostname}-{os.getppid()}-{os.getpid()}"

    def _connect_with_retry(self) -> socket.socket:
        """带重试机制的连接"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

                # 指数退避策略
                timeout = self.base_timeout * (2 ** attempt)
                client_socket.settimeout(timeout)

                client_socket.connect(self.socket_path)
                return client_socket

            except socket.error as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)  # 指数等待
                    import time
                    time.sleep(wait_time)

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 0.5 * (2 ** attempt)
                    import time
                    time.sleep(wait_time)

        # 所有重试失败后抛出异常
        if last_error:
            if hasattr(last_error, 'errno'):
                if last_error.errno == 2:  # No such file or directory
                    raise ConnectionError("❌ Codex守护进程未运行，请先启动 claude_codex")
                elif last_error.errno == 111:  # Connection refused
                    raise ConnectionError("❌ 无法连接到Codex守护进程，服务可能异常")
            raise ConnectionError(f"❌ 连接Codex守护进程失败（已重试{self.max_retries}次）: {last_error}")

        raise ConnectionError("❌ 连接失败: 未知错误")

    def _connect(self) -> socket.socket:
        """连接到Codex守护进程（已弃用，使用_connect_with_retry）"""
        return self._connect_with_retry()

    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到守护进程"""
        client_socket = None
        try:
            client_socket = self._connect_with_retry()
            client_socket.settimeout(self.response_timeout)

            # 发送请求
            request_json = json.dumps(request, ensure_ascii=False)
            client_socket.send(request_json.encode('utf-8'))

            # 接收响应
            response_chunks = []
            while True:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                response_chunks.append(chunk)
                if b'\n' in chunk:
                    break

            if not response_chunks:
                raise ConnectionError("❌ 服务器连接断开")

            response_data = b"".join(response_chunks).decode('utf-8').strip()
            response = json.loads(response_data)
            return response

        except json.JSONDecodeError as e:
            return {"error": f"❌ 服务器响应格式错误: {e}"}
        except socket.timeout:
            return {"error": "❌ 请求处理超时（服务器可能繁忙）"}
        except ConnectionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"❌ 通信错误: {e}"}
        finally:
            if client_socket:
                client_socket.close()

    def handle_command(self, command: str) -> str:
        """统一命令处理入口"""
        command = command.strip()

        alias_map = {
            "/cask-w": "/codex-ask --wait",
            "/cask": "/codex-ask",
            "/cpend": "/codex-pending",
            "/cping": "/codex-ping",
        }
        for alias, target in alias_map.items():
            if command.startswith(alias):
                command = target + command[len(alias):]
                break

        if not command.startswith("/codex-"):
            return None

        parts = command.split()
        cmd_type = parts[0]

        if cmd_type == "/codex-ask":
            if len(parts) == 1:
                return "❌ 请提供要询问的问题，用法: /cask <你的问题>"
            wait_mode = False
            args_tail = parts[1:]
            if args_tail and args_tail[0] in {"--wait", "-w"}:
                wait_mode = True
                args_tail = args_tail[1:]
            question = " ".join(args_tail) if args_tail else ""
            if not question:
                return "❌ 请提供要询问的问题，用法: /cask <你的问题>"

            try:
                from codex_comm import CodexCommunicator
            except ImportError as exc:
                return f"❌ 无法导入 CodexCommunicator: {exc}"

            try:
                comm = CodexCommunicator()
            except Exception as exc:
                return f"❌ 无法连接到 Codex: {exc}"

            if wait_mode:
                result = comm.ask_sync(question)
                return result or "⏰ 请稍后使用 /cpend 查看最新回复"
            else:
                comm.ask_async(question)
                return ""

        if cmd_type == "/codex-pending":
            try:
                from codex_comm import CodexCommunicator
            except ImportError as exc:
                return f"❌ 无法读取待处理消息: {exc}"
            comm = CodexCommunicator()
            output = comm.consume_pending(display=False)
            return output or "暂无 Codex 回复"

        if cmd_type == "/codex-ping":
            try:
                from codex_comm import CodexCommunicator
            except ImportError as exc:
                return f"❌ 无法执行 ping: {exc}"
            comm = CodexCommunicator()
            _, msg = comm.ping(display=False)
            return msg

        return "❌ 不支持的命令"

# 全局客户端实例
_client = None

def get_client() -> CodexClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = CodexClient()
    return _client

def handle_codex_command(command: str) -> str:
    """对外接口：处理Codex相关命令"""
    command = command.strip()

    # 废弃 codex-start 相关命令，返回提示信息
    if command.startswith("/codex-start"):
        return 'ℹ️ 守护进程由 claude_codex 自动管理，无需执行此命令。'

    client = get_client()
    return client.handle_command(command)

# 为了向后兼容，保留一些辅助函数
def get_codex_manager():
    """向后兼容函数，现在返回None"""
    return None

if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        result = handle_codex_command(" ".join(sys.argv[1:]))
        print(result)
    else:
        print("用法: python3 codex_commands.py <command>")
        print("例如: python3 codex_commands.py /codex-help")
