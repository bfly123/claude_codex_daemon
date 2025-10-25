#!/usr/bin/env python3
import errno
import getpass
import json
import os
import platform
import signal
import socket
import stat
import sys
import tempfile
import threading
import time
import uuid

# 守护进程安全的打印函数
def dprint(*args, **kwargs):
    """守护进程安全的打印函数"""
    if not os.environ.get('CODEX_DAEMON_MODE'):
        print(*args, **kwargs)


class ClaudeCodexManager:
    def __init__(self, client_id=None):
        self.client_id = client_id
        self.runtime_dir = self._initialize_runtime_dir()
        self.ipc_mode = None
        self.instance_id = None
        self.socket_path = None
        self.request_pipe = None
        self.response_pipe = None
        self.codex_pid = None
        self.history_file = None
        self.codex_active = False
        self.current_profile = "default"
        self.show_reasoning = False
        self.output_format = "final_only"
        self.start_time = 0  # 初始化为0，避免None
        self.last_seen = time.time()
        self.ipc_mode = self._determine_ipc_mode()

    def touch(self):
        self.last_seen = time.time()

    def _initialize_runtime_dir(self):
        system = platform.system()
        if system not in {"Linux", "Darwin"}:
            raise RuntimeError("Codex服务目前仅支持 Linux 或 macOS")

        candidate_dirs = []

        override_dir = os.environ.get("CODEX_RUNTIME_DIR")
        if override_dir:
            candidate_dirs.append(os.path.abspath(os.path.expanduser(override_dir)))

        default_dir = os.path.join(tempfile.gettempdir(), f"codex-{getpass.getuser()}")
        if default_dir not in candidate_dirs:
            candidate_dirs.append(default_dir)

        home_dir = os.path.join(os.path.expanduser("~"), ".codex_runtime")
        if home_dir not in candidate_dirs:
            candidate_dirs.append(home_dir)

        errors = []
        for runtime_dir in candidate_dirs:
            try:
                os.makedirs(runtime_dir, mode=0o700, exist_ok=True)
                directory_stat = os.stat(runtime_dir)
                if directory_stat.st_uid != os.getuid():
                    raise PermissionError("运行目录所有者与当前用户不匹配")
                current_mode = stat.S_IMODE(directory_stat.st_mode)
                if current_mode != 0o700:
                    os.chmod(runtime_dir, 0o700)
                return runtime_dir
            except Exception as exc:
                errors.append((runtime_dir, exc))

        error_message = "; ".join(f"{path}: {exc}" for path, exc in errors)
        raise RuntimeError(f"无法创建运行目录: {error_message}")

    def _determine_ipc_mode(self):
        test_path = os.path.join(self.runtime_dir, f"codex-ipc-test-{os.getpid()}.sock")
        try:
            test_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            test_socket.bind(test_path)
            test_socket.listen(1)
            test_socket.close()
            if os.path.exists(test_path):
                os.unlink(test_path)
            return "socket"
        except OSError as exc:
            if os.path.exists(test_path):
                try:
                    os.unlink(test_path)
                except OSError:
                    pass

            fallback_errno = {errno.EPERM, errno.EACCES, errno.EOPNOTSUPP, errno.ENOTSUP}
            if getattr(exc, "errno", None) in fallback_errno:
                dprint("[Codex Manager] 当前环境禁止Unix Socket，切换FIFO通信模式")
                return "fifo"

            # 某些环境会返回通用错误码，此时也允许回退
            if getattr(exc, "errno", None) == errno.EPROTONOSUPPORT:
                dprint("[Codex Manager] 当前环境不支持Unix Socket协议，切换FIFO通信模式")
                return "fifo"

            raise

    def _candidate_socket_paths(self, instance_id, claude_pid):
        # 优先使用runtime_dir (应该是 /tmp/codex-{user})
        primary = os.path.join(self.runtime_dir, f"codex-{instance_id}-{claude_pid}.sock")
        candidates = [primary]

        # 检查其他可能的位置
        legacy_dir = "/tmp"
        legacy_path = os.path.join(legacy_dir, f"codex-{instance_id}-{claude_pid}.sock")
        if legacy_path != primary:
            candidates.append(legacy_path)

        # 检查是否在用户目录下的其他位置
        user_dir = f"/tmp/codex-{getpass.getuser()}"
        user_path = os.path.join(user_dir, f"codex-{instance_id}-{claude_pid}.sock")
        if user_path != primary and user_path not in candidates:
            candidates.append(user_path)

        return candidates

    def _generate_fifo_paths(self, instance_id, claude_pid):
        base = os.path.join(self.runtime_dir, f"codex-{instance_id}-{claude_pid}")
        request_path = f"{base}.req"
        response_path = f"{base}.resp"
        return request_path, response_path

    def _ensure_fifo(self, path):
        try:
            if os.path.exists(path):
                info = os.lstat(path)
                if not stat.S_ISFIFO(info.st_mode):
                    os.unlink(path)
                else:
                    if info.st_uid != os.getuid():
                        raise PermissionError("FIFO文件所有者不正确")
                    current_mode = stat.S_IMODE(info.st_mode)
                    if current_mode != 0o600:
                        os.chmod(path, 0o600)
                    return
            os.mkfifo(path, 0o600)
        except FileExistsError:
            return
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
        return self._candidate_socket_paths(instance_id, claude_pid)[0]

    def _generate_socket_path_for_instance(self, instance_id):
        """为指定的instance_id生成socket路径"""
        claude_pid = os.getppid()
        return self._candidate_socket_paths(instance_id, claude_pid)[0]

    def _create_initial_history_file(self):
        """创建初始历史文件以锁定instance_id"""
        try:
            claude_parent_pid = os.getppid()
            data = {
                "instance_id": self.instance_id,
                "claude_parent_pid": claude_parent_pid,
                "socket_path": self.socket_path,
                "client_id": self.client_id,
                "ipc_mode": self.ipc_mode,
                "request_pipe": self.request_pipe,
                "response_pipe": self.response_pipe,
                "conversation_history": [],
                "current_profile": self.current_profile,
                "show_reasoning": self.show_reasoning,
                "output_format": self.output_format,
                "saved_at": int(time.time()),
                "created_at": int(time.time())
            }

            # 安全写入初始历史文件
            fd = os.open(self.history_file, os.O_NOFOLLOW | os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
            file_stat = os.fstat(fd)
            if not stat.S_ISREG(file_stat.st_mode):
                os.close(fd)
                raise Exception("目标不是普通文件")
            if file_stat.st_uid != os.getuid():
                os.close(fd)
                raise Exception("文件所有者不正确")

            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                # fsync在慢盘上可能很慢，默认关闭，可通过环境变量启用
                if os.environ.get('CODEX_SYNC_HISTORY', '').lower() in ('1', 'true', 'yes'):
                    os.fsync(fd)  # 强制同步到磁盘

            dprint(f"[Codex Recovery] 创建初始历史文件: {self.history_file}")

        except Exception as e:
            dprint(f"[Codex Recovery] 创建初始历史文件失败: {e}")
            # 如果创建失败，尝试删除可能存在的文件
            try:
                if os.path.exists(self.history_file):
                    os.unlink(self.history_file)
            except:
                pass

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
        """尝试恢复现有的会话状态 - 优化版：早返回机制"""
        import glob
        import os
        import socket

        current_claude_pid = os.getppid()
        user_id = os.getuid()
        history_files = []
        runtime_pattern = os.path.join(self.runtime_dir, "codex-*-history.json")
        history_files.extend(glob.glob(runtime_pattern))

        legacy_dir = "/tmp"
        if self.runtime_dir != legacy_dir:
            history_files.extend(glob.glob(os.path.join(legacy_dir, "codex-*-history.json")))

        # 去重保持顺序
        seen = set()
        unique_history_files = []
        for file_path in history_files:
            if file_path not in seen:
                seen.add(file_path)
                unique_history_files.append(file_path)

        # 过滤出属于当前用户的文件，并按修改时间排序
        user_files = []
        for file_path in unique_history_files:
            try:
                file_stat = os.stat(file_path)
                if (file_stat.st_uid == user_id and
                    file_stat.st_mode & 0o077 == 0):
                    user_files.append((file_path, file_stat.st_mtime))
            except:
                continue

        # 按修改时间降序排列，取最近的 - 早返回优化
        user_files.sort(key=lambda x: x[1], reverse=True)

        # 轻量级检查：先检查文件名是否包含当前PID，如果有则优先处理
        pid_pattern = f"codex-*-{current_claude_pid}-history.json"
        current_pid_files = []
        other_pid_files = []

        for file_path, mtime in user_files:
            if f"-{current_claude_pid}-" in file_path:
                current_pid_files.append((file_path, mtime))
            else:
                other_pid_files.append((file_path, mtime))

        # 优先检查当前PID的文件
        for file_path, mtime in current_pid_files:
            result = self._check_and_recover_session_file(file_path, current_claude_pid)
            if result:
                return result

        # 再检查其他文件
        for file_path, mtime in other_pid_files:
            result = self._check_and_recover_session_file(file_path, current_claude_pid)
            if result:
                return result

        dprint(f"[Codex Recovery] 未找到匹配的历史文件 (Claude PID: {current_claude_pid})")
        return None

    def _check_and_recover_session_file(self, file_path, current_claude_pid):
        """检查并恢复单个会话文件"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # 跳过空的或无对话历史的文件
            if not data.get("conversation_history"):
                return None

            # 检查文件是否太旧（超过24小时则不恢复）
            file_stat = os.stat(file_path)
            file_age = time.time() - file_stat.st_mtime
            if file_age > 24 * 3600:  # 24小时
                return None

            # 检查Claude父进程ID是否匹配（关键：实例隔离）
            saved_claude_pid = data.get("claude_parent_pid")
            if saved_claude_pid and saved_claude_pid != current_claude_pid:
                dprint(f"[Codex Recovery] 跳过文件 {file_path}: Claude PID不匹配 "
                      f"(保存: {saved_claude_pid}, 当前: {current_claude_pid})")
                return None

            saved_client_id = data.get("client_id")
            if self.client_id:
                if saved_client_id and saved_client_id != self.client_id:
                    dprint(f"[Codex Recovery] 跳过文件 {file_path}: client_id不匹配")
                    return None
                if not saved_client_id:
                    data["client_id"] = self.client_id
                    try:
                        with open(file_path, 'w') as f:
                            json.dump(data, f, indent=2)
                    except Exception as e:
                        dprint(f"[Codex Recovery] 更新历史文件client_id失败: {e}")

            # 提取完整的会话状态
            instance_id = data.get("instance_id")
            if not instance_id:
                return None

            current_profile = data.get("current_profile", "default")
            if current_profile not in ["high", "low", "default"]:
                current_profile = "default"

            show_reasoning = bool(data.get("show_reasoning", False))
            output_format = data.get("output_format", "final_only")
            if output_format not in ["final_only", "final_with_details"]:
                output_format = "final_only"

            dprint(f"[Codex Recovery] 找到匹配的历史文件: {file_path} "
                  f"(Claude PID: {current_claude_pid})")

            return {
                "instance_id": instance_id,
                "history_file": file_path,
                "current_profile": current_profile,
                "show_reasoning": show_reasoning,
                "output_format": output_format,
                "conversation_count": len(data.get("conversation_history", [])),
                "socket_path": data.get("socket_path"),
                "ipc_mode": data.get("ipc_mode", "socket"),
                "request_pipe": data.get("request_pipe"),
                "response_pipe": data.get("response_pipe")
            }
        except Exception as e:
            dprint(f"[Codex Recovery] 尝试恢复会话文件 {file_path} 失败: {e}")
            return None

    def auto_activate_on_first_use(self):
        if not self.codex_active:
            self.touch()
            # 首先尝试恢复现有的历史文件
            recovered_state = self._recover_existing_session()

            if recovered_state:
                # 使用恢复的instance_id和历史文件路径
                self.instance_id = recovered_state["instance_id"]
                self.history_file = recovered_state["history_file"]
                self.current_profile = recovered_state["current_profile"]
                self.show_reasoning = recovered_state["show_reasoning"]
                self.output_format = recovered_state["output_format"]
                dprint(f"[Codex Recovery] 恢复会话: instance_id={self.instance_id}, 历史文件={self.history_file}")

                # 检查socket是否已存在并可用（避免双重启动）
                socket_candidates = self._candidate_socket_paths(self.instance_id, os.getppid())
                for candidate in socket_candidates:
                    if os.path.exists(candidate):
                        try:
                            test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                            test_sock.connect(candidate)
                            test_sock.close()
                            self.socket_path = candidate
                            dprint(f"[Codex Recovery] 发现已存在的socket，跳过子进程创建")
                            self.codex_active = True
                            self._setup_child_monitor()
                            return
                        except:
                            dprint(f"[Codex Recovery] Socket {candidate} 已存在但不可用，继续创建新进程")
            else:
                # 生成新的会话ID并立即持久化
                self.instance_id = self._generate_instance_id()
                self.history_file = os.path.join(self.runtime_dir, f"codex-{self.instance_id}-history.json")
                self.socket_path = self._generate_socket_path_for_instance(self.instance_id)

                # 立即创建空的历史文件以锁定这个instance_id
                self._create_initial_history_file()
                dprint(f"[Codex Recovery] 创建新会话: instance_id={self.instance_id}")

            if not self.socket_path:
                self.socket_path = self._generate_socket_path_for_instance(self.instance_id)
            self.history_file = self.history_file or os.path.join(
                self.runtime_dir, f"codex-{self.instance_id}-history.json"
            )
            self.start_time = time.time()
            self.touch()

            self.codex_pid = os.fork()
            if self.codex_pid == 0:
                try:
                    self._run_codex_child_process()
                finally:
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
                self.touch()
                return response
            except Exception as exc:
                if attempt == 2:
                    raise RuntimeError(f"与Codex通信失败: {exc}")
                time.sleep(0.1)

    def _run_codex_child_process(self):
        from codex_process import CodexProcess
        codex = CodexProcess(self.socket_path, self.instance_id, client_id=self.client_id)
        codex.run()

    def _setup_child_monitor(self):
        def monitor_child():
            dprint(f"[Codex Monitor] 开始监控子进程 PID: {self.codex_pid}")
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
                        dprint(f"[Codex Monitor] 子进程 PID:{pid} 已退出，退出码: {exit_code}")
                        dprint("[Codex Monitor] 正在重新启动Codex服务...")
                        self._restart_codex_process()
                        break
                except OSError as e:
                    dprint(f"[Codex Monitor] 检测到异常: {e}")
                    dprint("[Codex Monitor] Codex进程异常退出，正在重新启动...")
                    self._restart_codex_process()
                    break
                except Exception as e:
                    dprint(f"[Codex Monitor] 监控线程异常: {e}")
                    break
                time.sleep(2)

        monitor_thread = threading.Thread(target=monitor_child, daemon=True)
        monitor_thread.start()
        dprint(f"[Codex Monitor] 监控线程已启动，实例ID: {self.instance_id}")

    def _restart_codex_process(self):
        dprint(f"[Codex Restart] 开始重启Codex实例 {self.instance_id}...")

        old_state = {}
        if os.path.exists(self.history_file):
            try:
                dprint(f"[Codex Restart] 正在读取历史文件: {self.history_file}")
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
                        dprint(f"[Codex Restart] 已恢复状态: {conversation_count}条对话, Profile={self.current_profile}")
                    else:
                        dprint(f"[Codex Restart] 历史文件instance_id不匹配，跳过状态恢复")
            except Exception as e:
                dprint(f"[Codex Restart] 读取历史文件失败: {e}")
        else:
            dprint(f"[Codex Restart] 历史文件不存在，将使用默认配置")

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
                dprint(f"已恢复 {history_count} 条对话历史，Profile: {profile}, ShowReasoning: {reasoning}, OutputFormat: {output_format}")
            else:
                dprint("状态恢复失败")
        except Exception as e:
            dprint(f"恢复状态时出错: {e}")

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
            if not self.history_file:
                return []
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
            self.touch()
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
            self.touch()
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
            self.touch()
            return f"✅ Output Format 已切换为 {target}"
        return f"❌ 设置失败: {response.get('message', '未知错误')}"

    def show_config(self):
        cfg = self.get_current_config()
        reasoning_flag = "on" if cfg["show_reasoning"] else "off"
        output_flag = cfg["output_format"]
        output_desc = "final_only" if output_flag == "final_only" else "final_with_details"
        self.touch()
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
        self.touch()
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
                self.touch()
            except:
                pass
