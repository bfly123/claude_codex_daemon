#!/usr/bin/env python3
import json
import os
import socket
import time
import uuid
import signal
import threading


class ClaudeCodexManager:
    def __init__(self):
        self.instance_id = None
        self.socket_path = None
        self.codex_pid = None
        self.history_file = None
        self.codex_active = False
        self.current_profile = "default"
        self.show_reasoning = False
        self.output_format = "final_only"
        self.start_time = None

    def _generate_instance_id(self):
        user_id = os.getuid()
        import hashlib
        import pwd
        import uuid
        import time

        # 每个会话生成唯一的instance_id，但包含时间戳以支持历史恢复
        username = pwd.getpwuid(user_id).pw_name
        timestamp = int(time.time() // 60)  # 分钟级时间戳，确保重启后短期内能找到历史
        unique_id = str(uuid.uuid4())[:8]
        stable_string = f"codex-{username}-{user_id}-{timestamp}-{unique_id}"
        instance_id = hashlib.md5(stable_string.encode()).hexdigest()[:8]

        return instance_id

    def _generate_secure_socket_path(self):
        claude_pid = os.getppid()
        instance_id = self._generate_instance_id()
        # 添加进程ID以避免socket冲突，但保持instance_id稳定
        socket_path = f"/tmp/codex-{instance_id}-{claude_pid}.sock"
        return socket_path

    def _setup_socket_permissions(self, socket_path):
        if os.path.exists(socket_path):
            os.chmod(socket_path, 0o600)

            file_stat = os.stat(socket_path)
            if file_stat.st_uid != os.getuid():
                raise Exception("Socket文件所有者不正确")

            file_mode = file_stat.st_mode & 0o777
            if file_mode != 0o600:
                os.chmod(socket_path, 0o600)

    def _wait_for_socket_ready(self):
        for i in range(10):
            if os.path.exists(self.socket_path):
                try:
                    test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    test_sock.connect(self.socket_path)
                    test_sock.close()
                    return
                except:
                    pass
            time.sleep(0.1)
        raise RuntimeError("Socket启动超时")

    def _recover_existing_session(self):
        """尝试恢复现有的会话状态"""
        import glob
        import os

        user_id = os.getuid()
        pattern = f"/tmp/codex-*-history.json"
        history_files = glob.glob(pattern)

        # 过滤出属于当前用户的文件，并按修改时间排序
        user_files = []
        for file_path in history_files:
            try:
                file_stat = os.stat(file_path)
                if (file_stat.st_uid == user_id and
                    file_stat.st_mode & 0o077 == 0):
                    user_files.append((file_path, file_stat.st_mtime))
            except:
                continue

        # 按修改时间降序排列，取最近的
        user_files.sort(key=lambda x: x[1], reverse=True)

        for file_path, mtime in user_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # 跳过空的或无对话历史的文件
                if not data.get("conversation_history"):
                    continue

                # 检查文件是否太旧（超过24小时则不恢复）
                file_age = time.time() - mtime
                if file_age > 24 * 3600:  # 24小时
                    continue

                # 提取完整的会话状态
                instance_id = data.get("instance_id")
                if not instance_id:
                    continue

                current_profile = data.get("current_profile", "default")
                if current_profile not in ["high", "low", "default"]:
                    current_profile = "default"

                show_reasoning = bool(data.get("show_reasoning", False))
                output_format = data.get("output_format", "final_only")
                if output_format not in ["final_only", "final_with_details"]:
                    output_format = "final_only"

                return {
                    "instance_id": instance_id,
                    "history_file": file_path,
                    "current_profile": current_profile,
                    "show_reasoning": show_reasoning,
                    "output_format": output_format,
                    "conversation_count": len(data.get("conversation_history", []))
                }
            except Exception as e:
                print(f"[Codex Recovery] 尝试恢复会话文件 {file_path} 失败: {e}")
                continue

        return None

    def _load_existing_config(self):
        """在启动时加载已保存的配置状态（已弃用，使用 _recover_existing_session）"""
        pass

    def auto_activate_on_first_use(self):
        if not self.codex_active:
            # 首先尝试恢复现有的历史文件
            recovered_state = self._recover_existing_session()

            if recovered_state:
                # 使用恢复的instance_id和历史文件路径
                self.instance_id = recovered_state["instance_id"]
                self.history_file = recovered_state["history_file"]
                self.current_profile = recovered_state["current_profile"]
                self.show_reasoning = recovered_state["show_reasoning"]
                self.output_format = recovered_state["output_format"]
                print(f"[Codex Recovery] 恢复会话: instance_id={self.instance_id}, 历史文件={self.history_file}")
            else:
                # 生成新的会话ID
                self.instance_id = self._generate_instance_id()
                self.history_file = f"/tmp/codex-{self.instance_id}-history.json"
                print(f"[Codex Recovery] 创建新会话: instance_id={self.instance_id}")

            self.socket_path = self._generate_secure_socket_path()
            self.start_time = time.time()

            self.codex_pid = os.fork()
            if self.codex_pid == 0:
                self._run_codex_child_process()
                os._exit(0)
            else:
                self._wait_for_socket_ready()
                self._setup_socket_permissions(self.socket_path)
                self.codex_active = True
                self._setup_child_monitor()

    def send_to_codex(self, message):
        if not self.codex_active:
            self.auto_activate_on_first_use()

        request = {
            "instance_id": self.instance_id,
            "type": "query",
            "message": message,
            "config": {
                "profile": self.current_profile,
                "show_reasoning": self.show_reasoning,
                "output_format": self.output_format
            },
            "timestamp": int(time.time())
        }

        for attempt in range(3):
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self.socket_path)
                sock.send(json.dumps(request).encode())
                response = json.loads(sock.recv(8192).decode())
                sock.close()
                if response.get("instance_id") != self.instance_id:
                    raise RuntimeError("实例ID不匹配")
                return response
            except Exception as exc:
                if attempt == 2:
                    raise RuntimeError(f"与Codex通信失败: {exc}")
                time.sleep(0.1)

    def _run_codex_child_process(self):
        from codex_process import CodexProcess
        codex = CodexProcess(self.socket_path, self.instance_id)
        codex.run()

    def _setup_child_monitor(self):
        def monitor_child():
            print(f"[Codex Monitor] 开始监控子进程 PID: {self.codex_pid}")
            while self.codex_active:
                try:
                    # 检查子进程状态
                    pid, status = os.waitpid(self.codex_pid, os.WNOHANG)
                    if pid == 0:
                        # 子进程正常运行
                        pass
                    else:
                        # 子进程已退出
                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else "异常"
                        print(f"[Codex Monitor] 子进程 PID:{pid} 已退出，退出码: {exit_code}")
                        print("[Codex Monitor] 正在重新启动Codex服务...")
                        self._restart_codex_process()
                        break
                except OSError as e:
                    print(f"[Codex Monitor] 检测到异常: {e}")
                    print("[Codex Monitor] Codex进程异常退出，正在重新启动...")
                    self._restart_codex_process()
                    break
                except Exception as e:
                    print(f"[Codex Monitor] 监控线程异常: {e}")
                    break
                time.sleep(2)

        monitor_thread = threading.Thread(target=monitor_child, daemon=True)
        monitor_thread.start()
        print(f"[Codex Monitor] 监控线程已启动，实例ID: {self.instance_id}")

    def _restart_codex_process(self):
        print(f"[Codex Restart] 开始重启Codex实例 {self.instance_id}...")

        old_state = {}
        if os.path.exists(self.history_file):
            try:
                print(f"[Codex Restart] 正在读取历史文件: {self.history_file}")
                with open(self.history_file, 'r') as f:
                    old_data = json.load(f)
                    if old_data.get("instance_id") == self.instance_id:
                        conversation_count = len(old_data.get("conversation_history", []))
                        old_state = {
                            "conversation_history": old_data.get("conversation_history", []),
                            "current_profile": old_data.get("current_profile", "default"),
                            "show_reasoning": old_data.get("show_reasoning", False),
                            "output_format": old_data.get("output_format", "final_only")
                        }
                        self.current_profile = old_state["current_profile"]
                        self.show_reasoning = old_state["show_reasoning"]
                        self.output_format = old_state["output_format"]
                        print(f"[Codex Restart] 已恢复状态: {conversation_count}条对话, Profile={self.current_profile}")
                    else:
                        print(f"[Codex Restart] 历史文件instance_id不匹配，跳过状态恢复")
            except Exception as e:
                print(f"[Codex Restart] 读取历史文件失败: {e}")
        else:
            print(f"[Codex Restart] 历史文件不存在，将使用默认配置")

        self.codex_pid = os.fork()
        if self.codex_pid == 0:
            self._run_codex_child_process()
            os._exit(0)
        else:
            self._setup_child_monitor()

        self._wait_for_socket_ready()
        self._setup_socket_permissions(self.socket_path)
        self._restore_conversation_state(old_state)

    def _restore_conversation_state(self, state):
        if not state:
            return

        try:
            restore_request = {
                "instance_id": self.instance_id,
                "type": "restore_history",
                "history": state.get("conversation_history", []),
                "profile": state.get("current_profile", "default"),
                "show_reasoning": state.get("show_reasoning", False),
                "output_format": state.get("output_format", "final_only"),
                "timestamp": int(time.time())
            }

            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.send(json.dumps(restore_request).encode())
            response = json.loads(sock.recv(4096).decode())
            sock.close()

            if response.get("status") == "success":
                history_count = len(state.get("conversation_history", []))
                profile = state.get("current_profile", "default")
                reasoning = state.get("show_reasoning", False)
                output_format = state.get("output_format", "final_only")
                print(f"已恢复 {history_count} 条对话历史，Profile: {profile}, ShowReasoning: {reasoning}, OutputFormat: {output_format}")
            else:
                print("状态恢复失败")
        except Exception as e:
            print(f"恢复状态时出错: {e}")

    def get_detailed_status(self):
        if not self.codex_active:
            return {}

        uptime = int(time.time()) - getattr(self, 'start_time', time.time())
        conversation_count = len(self._load_conversation_count())

        return {
            "instance_id": self.instance_id,
            "current_profile": self.current_profile,
            "show_reasoning": self.show_reasoning,
            "output_format": self.output_format,
            "conversation_count": conversation_count,
            "uptime": uptime,
            "socket_path": self.socket_path,
            "codex_pid": self.codex_pid
        }

    def get_current_config(self):
        return {
            "profile": self.current_profile,
            "instance_id": self.instance_id,
            "show_reasoning": self.show_reasoning,
            "output_format": self.output_format,
            "conversation_count": len(self._load_conversation_count())
        }

    def _load_conversation_count(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    return data.get("conversation_history", [])
        except:
            pass
        return []

    def _send_config_command(self, payload):
        if not self.codex_active:
            return {"status": "error", "message": "Codex未激活"}

        command = {
            "instance_id": self.instance_id,
            "type": "config",
            "timestamp": int(time.time())
        }
        command.update(payload)

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.send(json.dumps(command).encode())
            response = json.loads(sock.recv(4096).decode())
            sock.close()
            return response
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def set_profile(self, new_profile):
        normalized = new_profile.lower()
        aliases = {"high": "high", "default": "default", "low": "low"}
        if normalized not in aliases:
            return "❌ 无效参数，请使用: high、default、low"

        if not self.codex_active:
            return "❌ Codex服务未激活，请先运行 /codex-start"

        response = self._send_config_command(
            {"action": "set_profile", "profile": aliases[normalized]}
        )
        if response.get("status") == "success":
            self.current_profile = aliases[normalized]
            return f"✅ Profile已更新为: {self.current_profile}"
        return f"❌ Profile更新失败: {response.get('message', '未知错误')}"

    def update_show_reasoning(self, state_token):
        if state_token not in ["on", "off"]:
            return "❌ 参数错误，使用 on 或 off"

        if not self.codex_active:
            return "❌ Codex服务未激活，请先运行 /codex-start"

        target = state_token == "on"
        response = self._send_config_command(
            {"action": "set_reasoning", "show_reasoning": target}
        )
        if response.get("status") == "success":
            self.show_reasoning = target
            label = "on" if target else "off"
            return f"✅ Show Reasoning 已设置为 {label}"
        return f"❌ 设置失败: {response.get('message', '未知错误')}"

    def update_output_format(self, state_token):
        if state_token not in ["on", "off"]:
            return "❌ 参数错误，使用 on 或 off"

        if not self.codex_active:
            return "❌ Codex服务未激活，请先运行 /codex-start"

        target = "final_only" if state_token == "on" else "final_with_details"
        response = self._send_config_command(
            {"action": "set_output_format", "output_format": target}
        )
        if response.get("status") == "success":
            self.output_format = target
            return f"✅ Output Format 已切换为 {target}"
        return f"❌ 设置失败: {response.get('message', '未知错误')}"

    def show_config(self):
        cfg = self.get_current_config()
        reasoning_flag = "on" if cfg["show_reasoning"] else "off"
        output_flag = cfg["output_format"]
        output_desc = "final_only" if output_flag == "final_only" else "final_with_details"
        return (
            "📋 当前配置:\n"
            f"• Profile: {cfg['profile']} ({self._describe_profile(cfg['profile'])})\n"
            f"• Instance ID: {cfg.get('instance_id') or '尚未创建（服务未激活）'}\n"
            f"• Show Reasoning: {reasoning_flag}  (on=输出推理摘要；off=仅内部使用)\n"
            f"• Output Format: {output_desc}  (final_only=只输出最终答案)\n"
            f"• 历史轮次: {cfg['conversation_count']}"
        )

    def show_status(self):
        if not self.codex_active:
            return "❌ Codex服务未运行"

        status = self.get_detailed_status()
        return (
            "✅ Codex服务运行中:\n"
            f"• 实例ID: {status['instance_id']}\n"
            f"• 当前Profile: {status['current_profile']}\n"
            f"• Show Reasoning: {'on' if status['show_reasoning'] else 'off'}\n"
            f"• Output Format: {status['output_format']}\n"
            f"• 对话轮次: {status['conversation_count']}\n"
            f"• 进程PID: {status['codex_pid']}\n"
            f"• Socket: {status['socket_path']}"
        )

    def _describe_profile(self, profile):
        mapping = {
            "high": "深度分析",
            "default": "平衡模式",
            "low": "简洁快速"
        }
        return mapping.get(profile, "平衡模式")

    def claude_cleanup_on_exit(self):
        if self.codex_active and self.codex_pid:
            try:
                os.kill(self.codex_pid, signal.SIGTERM)
                os.waitpid(self.codex_pid, 0)

                if os.path.exists(self.socket_path):
                    os.unlink(self.socket_path)

                self.codex_active = False
            except:
                pass