#!/usr/bin/env python3
"""
Gemini 通信模块
支持 tmux 和 WezTerm 终端发送请求，从 ~/.gemini/tmp/<hash>/chats/session-*.json 读取回复
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from terminal import get_backend_for_session, get_pane_id_from_session
from ccb_config import apply_backend_env

apply_backend_env()

GEMINI_ROOT = Path(os.environ.get("GEMINI_ROOT") or (Path.home() / ".gemini" / "tmp")).expanduser()


def _get_project_hash(work_dir: Optional[Path] = None) -> str:
    """计算项目目录的哈希值（与 gemini-cli 的 Storage.getFilePathHash 一致）"""
    path = work_dir or Path.cwd()
    # gemini-cli 使用的是 Node.js 的 path.resolve()（不会 realpath 解析符号链接），
    # 因此这里使用 absolute() 而不是 resolve()，避免在 WSL/Windows 场景下 hash 不一致。
    try:
        normalized = str(path.expanduser().absolute())
    except Exception:
        normalized = str(path)
    return hashlib.sha256(normalized.encode()).hexdigest()


class GeminiLogReader:
    """读取 ~/.gemini/tmp/<hash>/chats 内的 Gemini 会话文件"""

    def __init__(self, root: Path = GEMINI_ROOT, work_dir: Optional[Path] = None):
        self.root = Path(root).expanduser()
        self.work_dir = work_dir or Path.cwd()
        forced_hash = os.environ.get("GEMINI_PROJECT_HASH", "").strip()
        self._project_hash = forced_hash or _get_project_hash(self.work_dir)
        self._preferred_session: Optional[Path] = None
        try:
            poll = float(os.environ.get("GEMINI_POLL_INTERVAL", "0.05"))
        except Exception:
            poll = 0.05
        self._poll_interval = min(0.5, max(0.02, poll))
        # Some filesystems only update mtime at 1s granularity. When waiting for a reply,
        # force a read periodically to avoid missing in-place updates that keep size/mtime unchanged.
        try:
            force = float(os.environ.get("GEMINI_FORCE_READ_INTERVAL", "1.0"))
        except Exception:
            force = 1.0
        self._force_read_interval = min(5.0, max(0.2, force))

    def _chats_dir(self) -> Optional[Path]:
        chats = self.root / self._project_hash / "chats"
        return chats if chats.exists() else None

    def _scan_latest_session_any_project(self) -> Optional[Path]:
        """在所有 projectHash 下扫描最新 session 文件（用于 Windows/WSL 路径哈希不一致的兜底）"""
        if not self.root.exists():
            return None
        try:
            sessions = sorted(
                (p for p in self.root.glob("*/chats/session-*.json") if p.is_file() and not p.name.startswith(".")),
                key=lambda p: p.stat().st_mtime,
            )
        except OSError:
            return None
        return sessions[-1] if sessions else None

    def _scan_latest_session(self) -> Optional[Path]:
        chats = self._chats_dir()
        try:
            if chats:
                sessions = sorted(
                    (p for p in chats.glob("session-*.json") if p.is_file() and not p.name.startswith(".")),
                    key=lambda p: p.stat().st_mtime,
                )
            else:
                sessions = []
        except OSError:
            sessions = []

        if sessions:
            return sessions[-1]

        # fallback: projectHash 可能因路径规范化差异（Windows/WSL、符号链接等）而不匹配
        return self._scan_latest_session_any_project()

    def _latest_session(self) -> Optional[Path]:
        if self._preferred_session and self._preferred_session.exists():
            return self._preferred_session
        latest = self._scan_latest_session()
        if latest:
            self._preferred_session = latest
            try:
                # 若是 fallback 扫描到的 session，则反向绑定 projectHash，后续避免全量扫描
                project_hash = latest.parent.parent.name
                if project_hash:
                    self._project_hash = project_hash
            except Exception:
                pass
        return latest

    def set_preferred_session(self, session_path: Optional[Path]) -> None:
        if not session_path:
            return
        try:
            candidate = session_path if isinstance(session_path, Path) else Path(str(session_path)).expanduser()
        except Exception:
            return
        if candidate.exists():
            self._preferred_session = candidate

    def current_session_path(self) -> Optional[Path]:
        return self._latest_session()

    def capture_state(self) -> Dict[str, Any]:
        """记录当前会话文件和消息数量"""
        session = self._latest_session()
        msg_count = 0
        mtime = 0.0
        mtime_ns = 0
        size = 0
        last_gemini_id: Optional[str] = None
        last_gemini_hash: Optional[str] = None
        if session and session.exists():
            try:
                stat = session.stat()
                mtime = stat.st_mtime
                mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
                size = stat.st_size
                with session.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                msg_count = len(data.get("messages", []))
                last = self._extract_last_gemini(data)
                if last:
                    last_gemini_id, content = last
                    last_gemini_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "session_path": session,
            "msg_count": msg_count,
            "mtime": mtime,
            "mtime_ns": mtime_ns,
            "size": size,
            "last_gemini_id": last_gemini_id,
            "last_gemini_hash": last_gemini_hash,
        }

    def wait_for_message(self, state: Dict[str, Any], timeout: float) -> Tuple[Optional[str], Dict[str, Any]]:
        """阻塞等待新的 Gemini 回复"""
        return self._read_since(state, timeout, block=True)

    def try_get_message(self, state: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        """非阻塞读取回复"""
        return self._read_since(state, timeout=0.0, block=False)

    def latest_message(self) -> Optional[str]:
        """直接获取最新一条 Gemini 回复"""
        session = self._latest_session()
        if not session or not session.exists():
            return None
        try:
            with session.open("r", encoding="utf-8") as f:
                data = json.load(f)
            messages = data.get("messages", [])
            for msg in reversed(messages):
                if msg.get("type") == "gemini":
                    return msg.get("content", "").strip()
        except (OSError, json.JSONDecodeError):
            pass
        return None

    def _read_since(self, state: Dict[str, Any], timeout: float, block: bool) -> Tuple[Optional[str], Dict[str, Any]]:
        deadline = time.time() + timeout
        prev_count = state.get("msg_count", 0)
        prev_mtime = state.get("mtime", 0.0)
        prev_mtime_ns = state.get("mtime_ns")
        if prev_mtime_ns is None:
            prev_mtime_ns = int(float(prev_mtime) * 1_000_000_000)
        prev_size = state.get("size", 0)
        prev_session = state.get("session_path")
        prev_last_gemini_id = state.get("last_gemini_id")
        prev_last_gemini_hash = state.get("last_gemini_hash")
        # 允许短 timeout 场景下也能扫描到新 session 文件（gask-w 默认 1s/次）
        rescan_interval = min(2.0, max(0.2, timeout / 2.0))
        last_rescan = time.time()
        last_forced_read = time.time()

        while True:
            # 定期重新扫描，检测是否有新会话文件
            if time.time() - last_rescan >= rescan_interval:
                latest = self._scan_latest_session()
                if latest and latest != self._preferred_session:
                    self._preferred_session = latest
                    # 新会话文件，重置计数
                    if latest != prev_session:
                        prev_count = 0
                        prev_mtime = 0.0
                        prev_size = 0
                        prev_last_gemini_id = None
                        prev_last_gemini_hash = None
                last_rescan = time.time()

            session = self._latest_session()
            if not session or not session.exists():
                if not block:
                    return None, {
                        "session_path": None,
                        "msg_count": 0,
                        "mtime": 0.0,
                        "size": 0,
                        "last_gemini_id": prev_last_gemini_id,
                        "last_gemini_hash": prev_last_gemini_hash,
                    }
                time.sleep(self._poll_interval)
                if time.time() >= deadline:
                    return None, state
                continue

            try:
                stat = session.stat()
                current_mtime = stat.st_mtime
                current_mtime_ns = getattr(stat, "st_mtime_ns", int(current_mtime * 1_000_000_000))
                current_size = stat.st_size
                # Windows/WSL 场景下文件 mtime 可能是秒级精度，单靠 mtime 会漏掉快速写入的更新；
                # 因此同时用文件大小作为变化信号。
                if block and current_mtime_ns <= prev_mtime_ns and current_size == prev_size:
                    if time.time() - last_forced_read < self._force_read_interval:
                        time.sleep(self._poll_interval)
                        if time.time() >= deadline:
                            return None, {
                                "session_path": session,
                                "msg_count": prev_count,
                                "mtime": prev_mtime,
                                "mtime_ns": prev_mtime_ns,
                                "size": prev_size,
                                "last_gemini_id": prev_last_gemini_id,
                                "last_gemini_hash": prev_last_gemini_hash,
                            }
                        continue
                    # fallthrough: forced read

                with session.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                last_forced_read = time.time()
                messages = data.get("messages", [])
                current_count = len(messages)

                if current_count > prev_count:
                    for msg in messages[prev_count:]:
                        if msg.get("type") == "gemini":
                            content = msg.get("content", "").strip()
                            if content:
                                new_state = {
                                    "session_path": session,
                                    "msg_count": current_count,
                                    "mtime": current_mtime,
                                    "mtime_ns": current_mtime_ns,
                                    "size": current_size,
                                    "last_gemini_id": msg.get("id"),
                                    "last_gemini_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                                }
                                return content, new_state
                else:
                    # 有些版本会先写入空的 gemini 消息，再“原地更新 content”，消息数不变。
                    last = self._extract_last_gemini(data)
                    if last:
                        last_id, content = last
                        if content:
                            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                            if last_id != prev_last_gemini_id or current_hash != prev_last_gemini_hash:
                                new_state = {
                                    "session_path": session,
                                    "msg_count": current_count,
                                    "mtime": current_mtime,
                                    "mtime_ns": current_mtime_ns,
                                    "size": current_size,
                                    "last_gemini_id": last_id,
                                    "last_gemini_hash": current_hash,
                                }
                                return content, new_state

                prev_mtime = current_mtime
                prev_mtime_ns = current_mtime_ns
                prev_count = current_count
                prev_size = current_size
                last = self._extract_last_gemini(data)
                if last:
                    prev_last_gemini_id, content = last
                    prev_last_gemini_hash = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else prev_last_gemini_hash

            except (OSError, json.JSONDecodeError):
                pass

            if not block:
                return None, {
                    "session_path": session,
                    "msg_count": prev_count,
                    "mtime": prev_mtime,
                    "mtime_ns": prev_mtime_ns,
                    "size": prev_size,
                    "last_gemini_id": prev_last_gemini_id,
                    "last_gemini_hash": prev_last_gemini_hash,
                }

            time.sleep(self._poll_interval)
            if time.time() >= deadline:
                return None, {
                    "session_path": session,
                    "msg_count": prev_count,
                    "mtime": prev_mtime,
                    "mtime_ns": prev_mtime_ns,
                    "size": prev_size,
                    "last_gemini_id": prev_last_gemini_id,
                    "last_gemini_hash": prev_last_gemini_hash,
                }

    @staticmethod
    def _extract_last_gemini(payload: dict) -> Optional[Tuple[Optional[str], str]]:
        messages = payload.get("messages", []) if isinstance(payload, dict) else []
        if not isinstance(messages, list):
            return None
        for msg in reversed(messages):
            if not isinstance(msg, dict):
                continue
            if msg.get("type") != "gemini":
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            return msg.get("id"), content.strip()
        return None


class GeminiCommunicator:
    """通过终端与 Gemini 通信，并从会话文件读取回复"""

    def __init__(self):
        self.session_info = self._load_session_info()
        if not self.session_info:
            raise RuntimeError("❌ 未找到活跃的 Gemini 会话，请先运行 ccb up gemini")

        self.session_id = self.session_info["session_id"]
        self.runtime_dir = Path(self.session_info["runtime_dir"])
        self.terminal = self.session_info.get("terminal", "tmux")
        self.pane_id = get_pane_id_from_session(self.session_info)
        self.timeout = int(os.environ.get("GEMINI_SYNC_TIMEOUT", "60"))
        work_dir_hint = self.session_info.get("work_dir")
        log_work_dir = Path(work_dir_hint) if isinstance(work_dir_hint, str) and work_dir_hint else None
        self.log_reader = GeminiLogReader(work_dir=log_work_dir)
        preferred_session = self.session_info.get("gemini_session_path") or self.session_info.get("session_path")
        if preferred_session:
            self.log_reader.set_preferred_session(Path(str(preferred_session)))
        self.project_session_file = self.session_info.get("_session_file")
        self.backend = get_backend_for_session(self.session_info)

        healthy, msg = self._check_session_health()
        if not healthy:
            raise RuntimeError(f"❌ 会话不健康: {msg}\n提示: 请运行 ccb up gemini")

        self._prime_log_binding()

    def _prime_log_binding(self) -> None:
        session_path = self.log_reader.current_session_path()
        if not session_path:
            return
        self._remember_gemini_session(session_path)

    def _load_session_info(self):
        if "GEMINI_SESSION_ID" in os.environ:
            terminal = os.environ.get("GEMINI_TERMINAL", "tmux")
            # 根据终端类型获取正确的 pane_id
            if terminal == "wezterm":
                pane_id = os.environ.get("GEMINI_WEZTERM_PANE", "")
            elif terminal == "iterm2":
                pane_id = os.environ.get("GEMINI_ITERM2_PANE", "")
            else:
                pane_id = ""
            return {
                "session_id": os.environ["GEMINI_SESSION_ID"],
                "runtime_dir": os.environ["GEMINI_RUNTIME_DIR"],
                "terminal": terminal,
                "tmux_session": os.environ.get("GEMINI_TMUX_SESSION", ""),
                "pane_id": pane_id,
                "_session_file": None,
            }

        project_session = Path.cwd() / ".gemini-session"
        if not project_session.exists():
            return None

        try:
            with open(project_session, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or not data.get("active", False):
                return None

            runtime_dir = Path(data.get("runtime_dir", ""))
            if not runtime_dir.exists():
                return None

            data["_session_file"] = str(project_session)
            return data

        except Exception:
            return None

    def _check_session_health(self) -> Tuple[bool, str]:
        return self._check_session_health_impl(probe_terminal=True)

    def _check_session_health_impl(self, probe_terminal: bool) -> Tuple[bool, str]:
        try:
            if not self.runtime_dir.exists():
                return False, "运行时目录不存在"
            if not self.pane_id:
                return False, "未找到会话 ID"
            if probe_terminal and self.backend and not self.backend.is_alive(self.pane_id):
                return False, f"{self.terminal} 会话 {self.pane_id} 不存在"
            return True, "会话正常"
        except Exception as exc:
            return False, f"检查失败: {exc}"

    def _send_via_terminal(self, content: str) -> bool:
        if not self.backend or not self.pane_id:
            raise RuntimeError("未配置终端会话")
        self.backend.send_text(self.pane_id, content)
        return True

    def ask_async(self, question: str) -> bool:
        try:
            healthy, status = self._check_session_health_impl(probe_terminal=False)
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            self._send_via_terminal(question)
            print(f"✅ 已发送到 Gemini")
            print("提示: 使用 gpend 查看回复")
            return True
        except Exception as exc:
            print(f"❌ 发送失败: {exc}")
            return False

    def ask_sync(self, question: str, timeout: Optional[int] = None) -> Optional[str]:
        try:
            healthy, status = self._check_session_health_impl(probe_terminal=False)
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            print("🔔 发送问题到 Gemini...")
            self._send_via_terminal(question)
            # Capture state after sending to reduce "question → send" latency.
            state = self.log_reader.capture_state()

            wait_timeout = self.timeout if timeout is None else int(timeout)
            if wait_timeout == 0:
                print("⏳ 等待 Gemini 回复 (无超时，Ctrl-C 可中断)...")
                start_time = time.time()
                last_hint = 0
                while True:
                    message, new_state = self.log_reader.wait_for_message(state, timeout=30.0)
                    state = new_state if new_state else state
                    session_path = (new_state or {}).get("session_path") if isinstance(new_state, dict) else None
                    if isinstance(session_path, Path):
                        self._remember_gemini_session(session_path)
                    if message:
                        print("🤖 Gemini 回复:")
                        print(message)
                        return message
                    elapsed = int(time.time() - start_time)
                    if elapsed >= last_hint + 30:
                        last_hint = elapsed
                        print(f"⏳ 仍在等待... ({elapsed}s)")

            print(f"⏳ 等待 Gemini 回复 (超时 {wait_timeout} 秒)...")
            message, new_state = self.log_reader.wait_for_message(state, float(wait_timeout))
            session_path = (new_state or {}).get("session_path") if isinstance(new_state, dict) else None
            if isinstance(session_path, Path):
                self._remember_gemini_session(session_path)
            if message:
                print("🤖 Gemini 回复:")
                print(message)
                return message

            print("⏰ Gemini 未在限定时间内回复，可稍后执行 gpend 获取答案")
            return None
        except Exception as exc:
            print(f"❌ 同步询问失败: {exc}")
            return None

    def consume_pending(self, display: bool = True):
        session_path = self.log_reader.current_session_path()
        if isinstance(session_path, Path):
            self._remember_gemini_session(session_path)
        message = self.log_reader.latest_message()
        if not message:
            if display:
                print("暂无 Gemini 回复")
            return None
        if display:
            print(message)
        return message

    def _remember_gemini_session(self, session_path: Path) -> None:
        if not session_path or not self.project_session_file:
            return
        project_file = Path(self.project_session_file)
        if not project_file.exists():
            return

        try:
            with project_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return

        updated = False
        session_path_str = str(session_path)
        if data.get("gemini_session_path") != session_path_str:
            data["gemini_session_path"] = session_path_str
            updated = True

        try:
            project_hash = session_path.parent.parent.name
        except Exception:
            project_hash = ""
        if project_hash and data.get("gemini_project_hash") != project_hash:
            data["gemini_project_hash"] = project_hash
            updated = True

        session_id = ""
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("sessionId"), str):
                session_id = payload["sessionId"]
        except Exception:
            session_id = ""
        if session_id and data.get("gemini_session_id") != session_id:
            data["gemini_session_id"] = session_id
            updated = True

        if not updated:
            return

        tmp_file = project_file.with_suffix(".tmp")
        try:
            with tmp_file.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_file, project_file)
        except PermissionError as e:
            print(f"⚠️  无法更新 {project_file.name}: {e}", file=sys.stderr)
            print(f"💡 尝试: sudo chown $USER:$USER {project_file}", file=sys.stderr)
            try:
                if tmp_file.exists():
                    tmp_file.unlink(missing_ok=True)
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️  更新 {project_file.name} 失败: {e}", file=sys.stderr)
            try:
                if tmp_file.exists():
                    tmp_file.unlink(missing_ok=True)
            except Exception:
                pass

    def ping(self, display: bool = True) -> Tuple[bool, str]:
        healthy, status = self._check_session_health()
        msg = f"✅ Gemini 连接正常 ({status})" if healthy else f"❌ Gemini 连接异常: {status}"
        if display:
            print(msg)
        return healthy, msg

    def get_status(self) -> Dict[str, Any]:
        healthy, status = self._check_session_health()
        return {
            "session_id": self.session_id,
            "runtime_dir": str(self.runtime_dir),
            "terminal": self.terminal,
            "pane_id": self.pane_id,
            "healthy": healthy,
            "status": status,
        }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Gemini 通信工具")
    parser.add_argument("question", nargs="*", help="要发送的问题")
    parser.add_argument("--wait", "-w", action="store_true", help="同步等待回复")
    parser.add_argument("--timeout", type=int, default=60, help="同步超时时间(秒)")
    parser.add_argument("--ping", action="store_true", help="测试连通性")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--pending", action="store_true", help="查看待处理回复")

    args = parser.parse_args()

    try:
        comm = GeminiCommunicator()

        if args.ping:
            comm.ping()
        elif args.status:
            status = comm.get_status()
            print("📊 Gemini 状态:")
            for key, value in status.items():
                print(f"   {key}: {value}")
        elif args.pending:
            comm.consume_pending()
        elif args.question:
            question_text = " ".join(args.question).strip()
            if not question_text:
                print("❌ 请提供问题内容")
                return 1
            if args.wait:
                comm.ask_sync(question_text, args.timeout)
            else:
                comm.ask_async(question_text)
        else:
            print("请提供问题或使用 --ping/--status/--pending 选项")
            return 1
        return 0
    except Exception as exc:
        print(f"❌ 执行失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
