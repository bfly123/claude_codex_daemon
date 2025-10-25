#!/usr/bin/env python3
"""
Codex 守护进程
提供持久化的AI服务，支持多客户端连接
"""

import sys
import os
import json
import time
import socket
import threading
import signal
import argparse
import logging
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from claude_codex_manager import ClaudeCodexManager

# 全局日志变量
logger = None

# 配置日志
def setup_logging(log_file="/tmp/codex-daemon.log", daemon_mode=False):
    """设置结构化日志"""
    handlers = [logging.FileHandler(log_file)]

    # 只在非守护进程模式下添加 StreamHandler
    if not daemon_mode:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    return logging.getLogger(__name__)

class CodexDaemon:
    def __init__(self, socket_path="/tmp/codex-daemon.sock", daemon_mode=False):
        self.socket_path = socket_path
        self.managers = {}
        self.managers_lock = threading.Lock()
        self.running = False
        self.server_socket = None
        self.client_threads = []
        self.daemon_mode = daemon_mode
        self.logger = setup_logging(daemon_mode=daemon_mode)
        self.start_time = time.time()  # 初始化启动时间
        self.idle_timeout = int(os.environ.get("CODEX_CLIENT_IDLE_TIMEOUT", "60"))

    def start(self):
        """启动守护进程"""
        self.start_time = time.time()
        self.logger.info("🚀 启动Codex守护进程...")
        self.logger.info(f"🔌 Socket路径: {self.socket_path}")

        # 清理旧的socket文件
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
                self.logger.info("清理旧的socket文件")
            except Exception as e:
                self.logger.error(f"清理socket文件失败: {e}")

        # 创建Unix socket
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        socket_dir = os.path.dirname(self.socket_path)
        if socket_dir:
            try:
                os.makedirs(socket_dir, exist_ok=True)
                os.chmod(socket_dir, 0o700)
            except Exception as exc:
                self.logger.error(f"创建socket目录失败: {exc}")
                raise
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(5)
        os.chmod(self.socket_path, 0o600)  # 仅用户可访问

        # 初始化Codex管理器
        self.running = True
        self._start_manager_gc()

        # 启动监听线程
        listen_thread = threading.Thread(target=self._listen_connections, daemon=True)
        listen_thread.start()

        self.logger.info("🤖 Codex守护进程已就绪，等待连接...")
        if not self.daemon_mode:
            print(f"🤖 Codex守护进程已就绪，等待连接...")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            if not self.daemon_mode:
                print("\n🛑 收到停止信号，正在关闭...")
            self.logger.info("收到键盘中断，开始清理")
            self.stop()

        return True

    def _start_manager_gc(self):
        def cleaner():
            while self.running:
                now = time.time()
                with self.managers_lock:
                    items = list(self.managers.items())
                for client_id, manager in items:
                    idle = now - getattr(manager, "last_seen", now)
                    if idle >= self.idle_timeout:
                        self.logger.info(f"检测到客户端 {client_id} 空闲 {idle:.0f}s，自动清理")
                        try:
                            if manager.codex_active:
                                manager.claude_cleanup_on_exit()
                        except Exception as exc:
                            self.logger.warning(f"清理客户端 {client_id} 时失败: {exc}")
                        with self.managers_lock:
                            self.managers.pop(client_id, None)
                time.sleep(15)

        gc_thread = threading.Thread(target=cleaner, daemon=True)
        gc_thread.start()

    def _listen_connections(self):
        """监听客户端连接"""
        connection_count = 0
        while self.running:
            try:
                # 设置超时避免阻塞
                self.server_socket.settimeout(1.0)
                conn, addr = self.server_socket.accept()
                connection_count += 1

                self.logger.info(f"新客户端连接 #{connection_count}")

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn, connection_count),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)

            except socket.timeout:
                continue  # 超时是正常的，继续循环
            except OSError:
                break  # socket关闭时退出
            except Exception as e:
                if self.running:  # 只在运行时打印错误
                    self.logger.error(f"连接错误: {e}")
                break

    def health_check(self):
        """健康检查接口"""
        if not self.running:
            return {
                "status": "unhealthy",
                "reason": "Service not running"
            }

        clients = []
        with self.managers_lock:
            items = list(self.managers.items())
        for client_id, manager in items:
            client_info = {
                "client_id": client_id,
                "codex_active": manager.codex_active,
                "instance_id": manager.instance_id
            }
            if manager.codex_active:
                config = manager.get_current_config()
                client_info.update({
                    "profile": config.get("profile"),
                    "conversation_count": config.get("conversation_count"),
                    "socket_path": getattr(manager, "socket_path", None)
                })
            clients.append(client_info)

        uptime = time.time() - self.start_time if hasattr(self, 'start_time') else 0
        return {
            "status": "healthy",
            "uptime": uptime,
            "clients": clients
        }

    def _get_or_create_manager(self, client_id):
        if not client_id:
            raise ValueError("请求缺少 client_id")

        with self.managers_lock:
            manager = self.managers.get(client_id)
            if manager is None:
                manager = ClaudeCodexManager(client_id=client_id)
                self.managers[client_id] = manager
                self.logger.info(f"为新客户端创建Codex实例: {client_id}")
        manager.touch()
        return manager

    def _get_manager(self, client_id):
        with self.managers_lock:
            manager = self.managers.get(client_id)
        if manager:
            manager.touch()
        return manager

    def _remove_manager(self, client_id):
        with self.managers_lock:
            manager = self.managers.pop(client_id, None)
        if manager:
            try:
                if manager.codex_active:
                    manager.claude_cleanup_on_exit()
            except Exception as exc:
                self.logger.warning(f"移除客户端 {client_id} 时清理失败: {exc}")

    def _handle_client(self, conn, client_id):
        """处理客户端请求"""
        self.logger.info(f"处理客户端 #{client_id} 请求")
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    self.logger.info(f"客户端 #{client_id} 断开连接")
                    break

                try:
                    request = json.loads(data.decode('utf-8').strip())
                    response = self._process_request(request)
                    self.logger.debug(f"客户端 #{client_id} 请求: {request.get('command', 'unknown')}")

                    # 发送响应
                    response_json = json.dumps(response, ensure_ascii=False)
                    conn.send(response_json.encode('utf-8') + b'\n')

                except json.JSONDecodeError as e:
                    self.logger.warning(f"客户端 #{client_id} JSON解析错误: {e}")
                    error_response = {"error": "JSON格式错误"}
                    conn.send(json.dumps(error_response).encode('utf-8') + b'\n')
                except Exception as e:
                    self.logger.error(f"客户端 #{client_id} 处理失败: {e}")
                    error_response = {"error": f"处理失败: {str(e)}"}
                    conn.send(json.dumps(error_response).encode('utf-8') + b'\n')

        except Exception as e:
            self.logger.error(f"客户端 #{client_id} 连接异常: {e}")
        finally:
            conn.close()
            self.logger.info(f"客户端 #{client_id} 连接已关闭")

    def _process_request(self, request):
        """处理请求"""
        command = request.get('command', '')

        try:
            if command == '/codex-help':
                help_text = (
                    "🤖 Codex守护进程已启动\n"
                    "可用命令:\n"
                    "• /codex-ask <问题> - 发送问题\n"
                    "• /codex-config [high|default|low] - 查看或设置配置\n"
                    "• /codex-status - 查看状态（需要携带client_id）\n"
                    "• /codex-reasoning <on|off> - 设置推理显示\n"
                    "• /codex-final_only <on|off> - 设置输出格式\n"
                    "• /codex-stop - 停止当前Codex实例\n"
                    "• /codex-shutdown - 完全关闭守护进程"
                )
                return {"success": True, "response": help_text}

            client_id = request.get('client_id')
            commands_requiring_client = {
                '/codex-ask',
                '/codex-config',
                '/codex-reasoning',
                '/codex-final_only',
                '/codex-stop'
            }
            if command in commands_requiring_client and not client_id:
                return {"error": "Missing client_id. 请使用最新的 claude-codex 启动服务。"}

            if command == '/codex-ask':
                question = request.get('question', '').strip()
                if not question:
                    return {"error": "问题不能为空"}

                manager = self._get_or_create_manager(client_id)

                try:
                    response = manager.send_to_codex(question)
                    # 提取消息内容，确保返回字符串而非嵌套JSON
                    if isinstance(response, dict):
                        # 如果响应是字典，提取message字段
                        message = response.get("message", str(response))
                    else:
                        # 如果响应已经是字符串，直接使用
                        message = str(response)

                    return {"success": True, "response": message}
                except Exception as e:
                    return {"error": f"处理问题失败: {str(e)}"}

            elif command == '/codex-config':
                profile = request.get('profile')
                if profile:
                    manager = self._get_or_create_manager(client_id)
                    result = manager.set_profile(profile)
                    return {"success": True, "response": result}
                else:
                    manager = self._get_or_create_manager(client_id)
                    result = manager.show_config()
                    return {"success": True, "response": result}

            elif command == '/codex-status':
                if client_id:
                    manager = self._get_manager(client_id)
                    if manager:
                        result = manager.show_status()
                        return {"success": True, "response": result}
                    return {"success": True, "response": "ℹ️ 该客户端的Codex服务未运行"}
                else:
                    with self.managers_lock:
                        managers = list(self.managers.items())
                    if not managers:
                        return {"success": True, "response": "ℹ️ 当前没有活动的Codex客户端"}
                    summary_lines = ["📊 当前活动的Codex客户端:"]
                    for cid, manager in managers:
                        status = "运行中" if manager.codex_active else "未激活"
                        summary_lines.append(
                            f"• {cid}: {status} (Instance: {manager.instance_id or 'N/A'})"
                        )
                    return {"success": True, "response": "\n".join(summary_lines)}

            elif command == '/codex-health':
                uptime = time.time() - self.start_time if hasattr(self, 'start_time') else 0
                clients = []
                with self.managers_lock:
                    managers = list(self.managers.items())
                for cid, manager in managers:
                    info = {
                        "client_id": cid,
                        "codex_active": manager.codex_active,
                        "instance_id": manager.instance_id
                    }
                    if manager.codex_active:
                        cfg = manager.get_current_config()
                        info.update({
                            "profile": cfg.get("profile"),
                            "conversation_count": cfg.get("conversation_count"),
                            "socket_path": getattr(manager, "socket_path", None)
                        })
                    clients.append(info)
                return {
                    "success": True,
                    "response": {
                        "uptime": uptime,
                        "clients": clients
                    }
                }

            elif command == '/codex-reasoning':
                state = request.get('state', 'off')
                manager = self._get_or_create_manager(client_id)
                result = manager.update_show_reasoning(state)
                return {"success": True, "response": result}

            elif command == '/codex-final_only':
                state = request.get('state', 'on')
                manager = self._get_or_create_manager(client_id)
                result = manager.update_output_format(state)
                return {"success": True, "response": result}

            elif command == '/codex-stop':
                # 停止Codex服务但保持守护进程运行
                manager = self._get_manager(client_id)
                if manager and manager.codex_active:
                    instance_id = manager.instance_id
                    manager.claude_cleanup_on_exit()
                    with self.managers_lock:
                        self.managers.pop(client_id, None)
                    return {"success": True, "response": f"✅ Codex服务已停止 (实例ID: {instance_id})"}
                else:
                    return {"success": True, "response": "ℹ️ Codex服务未运行"}

            elif command == '/codex-shutdown':
                # 完全停止守护进程
                with self.managers_lock:
                    managers = list(self.managers.values())
                    self.managers.clear()
                for manager in managers:
                    try:
                        if manager.codex_active:
                            manager.claude_cleanup_on_exit()
                    except Exception:
                        pass

                self.running = False

                # 关闭socket服务器
                if self.server_socket:
                    self.server_socket.close()

                return {"success": True, "response": "🛑 守护进程正在关闭..."}

            else:
                return {"error": f"未知命令: {command}"}

        except Exception as e:
            return {"error": f"处理失败: {str(e)}"}

    def stop(self):
        """停止守护进程"""
        if not self.daemon_mode:
            print("🛑 停止Codex守护进程...")
        self.running = False

        # 关闭socket
        if self.server_socket:
            self.server_socket.close()

        # 停止Codex服务
        with self.managers_lock:
            managers = list(self.managers.values())
            self.managers.clear()
        for manager in managers:
            try:
                if manager.codex_active:
                    manager.claude_cleanup_on_exit()
            except Exception:
                pass

        # 清理socket文件
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        if not self.daemon_mode:
            print("✅ 守护进程已停止")

def check_daemon_health(socket_path):
    """通过socket检查守护进程健康状态"""
    try:
        # 首先检查socket文件是否存在
        if not os.path.exists(socket_path):
            return {
                "status": "unhealthy",
                "reason": f"Socket文件不存在: {socket_path}"
            }

        # 尝试连接socket
        test_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        test_socket.settimeout(2.0)
        test_socket.connect(socket_path)

        # 发送健康检查请求
        health_request = {
            "command": "/codex-health"
        }

        request_json = json.dumps(health_request, ensure_ascii=False)
        test_socket.send(request_json.encode('utf-8') + b'\n')

        # 接收响应
        response_data = test_socket.recv(4096).decode('utf-8').strip()
        test_socket.close()

        if response_data:
            response = json.loads(response_data)
            if response.get("success"):
                payload = response.get("response", {})
                uptime = payload.get("uptime", 0)
                clients = payload.get("clients", [])

                return {
                    "status": "healthy",
                    "uptime": uptime,
                    "client_count": len(clients),
                    "clients": clients
                }
            else:
                return {
                    "status": "unhealthy",
                    "reason": response.get("error", "未知错误")
                }
        else:
            return {
                "status": "unhealthy",
                "reason": "守护进程无响应"
            }

    except socket.error as e:
        return {
            "status": "unhealthy",
            "reason": f"Socket连接失败: {e}"
        }
    except json.JSONDecodeError as e:
        return {
            "status": "unhealthy",
            "reason": f"响应解析失败: {e}"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "reason": f"健康检查异常: {e}"
        }

def signal_handler(signum, frame):
    """信号处理器"""
    # 在守护进程中不使用 print，直接退出
    if os.environ.get('CODEX_DAEMON_MODE'):
        os._exit(0)
    else:
        print(f"\n收到信号 {signum}，正在退出...")
        os._exit(0)

def background_fork(pid_file="/tmp/codex-daemon.pid"):
    """简单的后台fork，不依赖daemon库"""
    try:
        # 第一次fork
        pid = os.fork()
        if pid > 0:
            os._exit(0)  # 父进程退出
    except OSError as e:
        print(f"❌ Fork失败: {e}")
        return False

    # 子进程继续
    os.setsid()  # 创建新会话
    os.chdir("/")  # 切换到根目录

    # 第二次fork
    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)  # 父进程退出
    except OSError as e:
        print(f"❌ 第二次fork失败: {e}")
        return False

    # 孙进程成为守护进程
    # 写入PID文件
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
    except Exception:
        pass  # 在守护进程中忽略写入PID文件失败

    # 重定向标准输入输出到 /dev/null (使用 os.dup2 确保文件描述符级别重定向)
    devnull_fd = os.open(os.devnull, os.O_RDWR)

    # 重定向标准文件描述符
    os.dup2(devnull_fd, sys.stdin.fileno())
    os.dup2(devnull_fd, sys.stdout.fileno())
    os.dup2(devnull_fd, sys.stderr.fileno())

    # 关闭多余的文件描述符
    if devnull_fd > 2:
        os.close(devnull_fd)

    # 重新初始化日志系统以使用新的 stdout/stderr
    global logger
    logger = setup_logging(daemon_mode=True)

    return True

def main():
    parser = argparse.ArgumentParser(description='Codex守护进程')
    parser.add_argument('--socket', default='/tmp/codex-daemon.sock', help='Socket文件路径')
    parser.add_argument('--daemon', action='store_true', help='后台运行模式')
    parser.add_argument('--pid-file', default='/tmp/codex-daemon.pid', help='PID文件路径')
    parser.add_argument('--health', action='store_true', help='健康检查模式')

    args = parser.parse_args()

    # 健康检查模式
    if args.health:
        try:
            result = check_daemon_health(args.socket)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("status") == "healthy" else 1
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return 1

    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 检查是否已在运行
    if os.path.exists(args.socket):
        try:
            import socket
            test_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            test_socket.connect(args.socket)
            test_socket.close()
            print("ℹ️ Codex守护进程已在运行")
            return 0
        except:
            pass  # socket文件存在但无法连接，继续启动

    # 后台运行模式
    daemon_mode = args.daemon
    if daemon_mode:
        print("🚀 启动后台守护进程...")
        # 设置环境变量指示守护进程模式
        os.environ['CODEX_DAEMON_MODE'] = '1'
        if not background_fork(args.pid_file):
            return 1

    # 启动守护进程
    daemon = CodexDaemon(args.socket, daemon_mode=daemon_mode)
    daemon.start()

if __name__ == "__main__":
    sys.exit(main())
