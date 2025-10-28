#!/usr/bin/env python3
"""
Codex通信模块 - 实现Claude到Codex的双向通信
支持同步和异步模式
"""

import os
import sys
import json
import time
import signal
import threading
import subprocess
from pathlib import Path
from datetime import datetime

class CodexCommunicator:
    def __init__(self):
        self.session_info = self._load_session_info()
        if not self.session_info:
            raise RuntimeError("❌ 未找到活跃的Codex会话，请先运行 claude-codex-dual")

        self.session_id = self.session_info["session_id"]
        self.runtime_dir = Path(self.session_info["runtime_dir"])
        self.input_fifo = Path(self.session_info["input_fifo"])
        self.output_fifo = Path(self.session_info["output_fifo"])
        self.pending_file = self.runtime_dir / "pending.jsonl"

        # 配置
        env_timeout = os.environ.get("CODEX_SYNC_TIMEOUT")
        try:
            self.timeout = int(env_timeout) if env_timeout else 30
        except ValueError:
            self.timeout = 30
        self.marker_prefix = "ask"

    def _load_session_info(self):
        """加载会话信息"""
        # 优先从环境变量读取
        if "CODEX_SESSION_ID" in os.environ:
            info = {
                "session_id": os.environ["CODEX_SESSION_ID"],
                "runtime_dir": os.environ["CODEX_RUNTIME_DIR"],
                "input_fifo": os.environ["CODEX_INPUT_FIFO"],
                "output_fifo": os.environ["CODEX_OUTPUT_FIFO"]
            }
            daemon_socket = os.environ.get("CODEX_DAEMON_SOCKET")
            if daemon_socket:
                info["daemon_socket"] = daemon_socket
            client_id = os.environ.get("CODEX_CLIENT_ID")
            if client_id:
                info["client_id"] = client_id
            tmux_session = os.environ.get("CODEX_TMUX_SESSION")
            if tmux_session:
                info["tmux_session"] = tmux_session
            tmux_log = os.environ.get("CODEX_TMUX_LOG")
            if tmux_log:
                info["tmux_log"] = tmux_log
            return info

        # 从项目目录读取
        project_session = Path.cwd() / ".codex-session"
        if project_session.exists():
            try:
                with open(project_session, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ 读取会话信息失败: {e}")
                return None

        return None

    def _check_session_health(self):
        """检查会话健康状态"""
        try:
            # 检查运行时目录
            if not self.runtime_dir.exists():
                return False, "运行时目录不存在"

            # 检查PID文件
            codex_pid_file = self.runtime_dir / "codex.pid"
            if not codex_pid_file.exists():
                return False, "Codex进程PID文件不存在"

            # 检查进程存活性
            with open(codex_pid_file, 'r') as f:
                codex_pid = int(f.read().strip())

            try:
                os.kill(codex_pid, 0)  # 发送信号0检测进程
            except OSError:
                return False, f"Codex进程(PID:{codex_pid})已死亡"

            # 检查管道可用性
            if not self.input_fifo.exists() or not self.output_fifo.exists():
                return False, "通信管道不存在"

            return True, "会话正常"

        except Exception as e:
            return False, f"检查失败: {e}"

    def _generate_marker(self):
        """生成唯一消息标记"""
        timestamp = int(time.time())
        pid = os.getpid()
        return f"{self.marker_prefix}-{timestamp}-{pid}"

    def _send_message(self, content, marker=None, expect_response=False):
        """发送消息到Codex"""
        try:
            # 构建消息
            message = {
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "marker": marker or self._generate_marker(),
                "expect_response": expect_response,
            }

            # 写入输入管道
            with open(self.input_fifo, 'w') as f:
                f.write(json.dumps(message, ensure_ascii=False) + '\n')
                f.flush()

            return message["marker"]

        except BrokenPipeError:
            raise RuntimeError("❌ Codex管道断裂，可能Codex窗口已关闭")
        except FileNotFoundError:
            raise RuntimeError("❌ 通信管道不存在")
        except Exception as e:
            raise RuntimeError(f"❌ 发送消息失败: {e}")

    def _wait_for_response(self, marker, timeout=None):
        """等待特定标记的回复"""
        if timeout is None:
            timeout = self.timeout

        start_time = time.time()
        buffer = []

        try:
            # 监控输出管道
            with open(self.output_fifo, 'r', encoding='utf-8') as f:
                while time.time() - start_time < timeout:
                    try:
                        # 设置非阻塞读取
                        line = f.readline()
                        if line:
                            buffer.append(line.strip())

                            # 解析输出行，查找匹配的回复
                            parsed = self._try_parse_json(line.strip())
                            if parsed and parsed.get("marker") == marker:
                                return parsed.get("response") or parsed.get("message")

                            if marker in line:
                                response_content = self._extract_response_content(line, marker)
                                if response_content is not None:
                                    return response_content

                        else:
                            time.sleep(0.1)  # 短暂等待

                    except Exception:
                        time.sleep(0.1)
                        continue

            # 超时
            return None

        except FileNotFoundError:
            raise RuntimeError("❌ 输出管道不存在")
        except Exception as e:
            raise RuntimeError(f"❌ 等待回复失败: {e}")

    def _extract_response_content(self, line, marker):
        """从输出行中提取回复内容"""
        try:
            # 简单的文本提取，实际可能需要更复杂的解析
            if "[" in line and "]" in line:
                # 格式: [时间] 内容 (包含marker)
                time_part, content_part = line.split("]", 1)
                content = content_part.strip()
                if content and marker in content:
                    # 移除marker相关标记
                    clean_content = content.replace(marker, "").strip()
                    return clean_content
            return None
        except Exception:
            return None

    def _try_parse_json(self, line):
        """尝试将输出解析为JSON结构"""
        line = line.strip()
        if not line:
            return None
        if not (line.startswith("{") and line.endswith("}")):
            return None
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def ask_async(self, question):
        """异步模式：发送问题，立即返回"""
        try:
            # 检查会话健康状态
            healthy, status = self._check_session_health()
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            # 发送消息
            marker = self._send_message(question, expect_response=False)
            print(f"✅ 已发送到Codex (标记: {marker[:12]}...)")
            print('提示: 使用 /codex-pending 查看回复')
            return True

        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False

    def ask_sync(self, question, timeout=None):
        """同步模式：发送问题并等待回复"""
        try:
            # 检查会话健康状态
            healthy, status = self._check_session_health()
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            print(f"🔔 发送问题到Codex...")

            # 发送消息
            marker = self._send_message(question, expect_response=True)

            # 等待回复
            print("⏳ 等待Codex回复...")
            response = self._wait_for_response(marker, timeout)

            if response:
                print(f"🤖 Codex回复:")
                print(response)
                return response
            else:
                print(f"⏰ Codex响应超时 ({timeout or self.timeout}秒)")
                return None

        except Exception as e:
            print(f"❌ 同步询问失败: {e}")
            return None

    def consume_pending(self):
        """拉取并展示异步待处理回复"""
        if not self.pending_file.exists():
            print('暂无待处理回复')
            return []

        temp_path = self.pending_file.with_suffix('.tmp')
        try:
            os.replace(self.pending_file, temp_path)
        except FileNotFoundError:
            print('暂无待处理回复')
            return []

        entries = []
        try:
            with temp_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(data)
                    except json.JSONDecodeError:
                        continue
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

        if not entries:
            print('暂无待处理回复')
            return []

        print('待处理回复:')
        for item in entries:
            marker = item.get('marker', '')
            ts = item.get('timestamp', '')
            question = item.get('question', '')
            response = item.get('response', '')
            if ts:
                header = f"-- {ts} ({marker[:12]}...)"
            else:
                header = f"-- {marker[:12]}..."
            print(header)
            if question:
                print(f"问题: {question}")
            if response:
                print(response)
            print()
        return entries

    def ping(self):
        """测试连通性"""
        try:
            healthy, status = self._check_session_health()
            if healthy:
                print(f"✅ Codex连接正常 ({status})")
                return True
            else:
                print(f"❌ Codex连接异常: {status}")
                return False
        except Exception as e:
            print(f"❌ 连通性测试失败: {e}")
            return False

    def get_status(self):
        """获取详细状态信息"""
        try:
            healthy, status = self._check_session_health()

            info = {
                "session_id": self.session_id,
                "runtime_dir": str(self.runtime_dir),
                "healthy": healthy,
                "status": status,
                "input_fifo": str(self.input_fifo),
                "output_fifo": str(self.output_fifo)
            }

            daemon_socket = self.session_info.get("daemon_socket")
            if daemon_socket:
                info["daemon_socket"] = daemon_socket
            client_id = self.session_info.get("client_id")
            if client_id:
                info["client_id"] = client_id
            tmux_session = self.session_info.get("tmux_session")
            if tmux_session:
                info["tmux_session"] = tmux_session
            tmux_log = self.session_info.get("tmux_log")
            if tmux_log:
                info["tmux_log"] = tmux_log

            # 添加进程信息
            codex_pid_file = self.runtime_dir / "codex.pid"
            if codex_pid_file.exists():
                with open(codex_pid_file, 'r') as f:
                    info["codex_pid"] = int(f.read().strip())

            # 添加历史信息
            history_dir = self.runtime_dir / "history"
            if history_dir.exists():
                history_files = list(history_dir.glob("*.jsonl"))
                info["history_files"] = len(history_files)

            if self.pending_file.exists():
                with open(self.pending_file, 'r', encoding='utf-8') as fh:
                    pending_count = sum(1 for line in fh if line.strip())
                info["pending_count"] = pending_count

            return info

        except Exception as e:
            return {"error": str(e)}

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Codex通信工具")
    parser.add_argument("question", nargs="?", help="要发送的问题")
    parser.add_argument("--wait", "-w", action="store_true", help="同步等待回复")
    parser.add_argument("--timeout", type=int, default=15, help="超时时间(秒)")
    parser.add_argument("--ping", action="store_true", help="测试连通性")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--pending", action="store_true", help="查看待处理回复")

    args = parser.parse_args()

    try:
        comm = CodexCommunicator()

        if args.ping:
            comm.ping()
        elif args.status:
            status = comm.get_status()
            print("📊 Codex状态:")
            for key, value in status.items():
                print(f"   {key}: {value}")
        elif args.pending:
            comm.consume_pending()
        elif args.question:
            if args.wait:
                comm.ask_sync(args.question, args.timeout)
            else:
                comm.ask_async(args.question)
        else:
            print("请提供问题或使用 --ping/--status/--pending 选项")
            return 1

        return 0

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
