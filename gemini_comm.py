#!/usr/bin/env python3
"""
Gemini 通信模块
通过 tmux 发送请求，从 ~/.gemini/tmp/<hash>/chats/session-*.json 读取回复
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

GEMINI_ROOT = Path.home() / ".gemini" / "tmp"


def _get_project_hash(work_dir: Optional[Path] = None) -> str:
    """计算项目目录的哈希值（与 gemini-cli 一致）"""
    path = work_dir or Path.cwd()
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()


class GeminiLogReader:
    """读取 ~/.gemini/tmp/<hash>/chats 内的 Gemini 会话文件"""

    def __init__(self, root: Path = GEMINI_ROOT, work_dir: Optional[Path] = None):
        self.root = Path(root).expanduser()
        self.work_dir = work_dir or Path.cwd()
        self._project_hash = _get_project_hash(self.work_dir)
        self._preferred_session: Optional[Path] = None

    def _chats_dir(self) -> Optional[Path]:
        chats = self.root / self._project_hash / "chats"
        return chats if chats.exists() else None

    def _scan_latest_session(self) -> Optional[Path]:
        chats = self._chats_dir()
        if not chats:
            return None
        try:
            sessions = sorted(
                (p for p in chats.glob("session-*.json") if p.is_file() and not p.name.startswith(".")),
                key=lambda p: p.stat().st_mtime,
            )
        except OSError:
            return None
        return sessions[-1] if sessions else None

    def _latest_session(self) -> Optional[Path]:
        if self._preferred_session and self._preferred_session.exists():
            return self._preferred_session
        latest = self._scan_latest_session()
        if latest:
            self._preferred_session = latest
        return latest

    def current_session_path(self) -> Optional[Path]:
        return self._latest_session()

    def capture_state(self) -> Dict[str, Any]:
        """记录当前会话文件和消息数量"""
        session = self._latest_session()
        msg_count = 0
        mtime = 0.0
        if session and session.exists():
            try:
                mtime = session.stat().st_mtime
                with session.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                msg_count = len(data.get("messages", []))
            except (OSError, json.JSONDecodeError):
                pass
        return {"session_path": session, "msg_count": msg_count, "mtime": mtime}

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
        prev_session = state.get("session_path")
        rescan_interval = 2.0
        last_rescan = time.time()

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
                last_rescan = time.time()

            session = self._latest_session()
            if not session or not session.exists():
                if not block:
                    return None, {"session_path": None, "msg_count": 0, "mtime": 0.0}
                time.sleep(0.2)
                if time.time() >= deadline:
                    return None, state
                continue

            try:
                current_mtime = session.stat().st_mtime
                if current_mtime <= prev_mtime and block:
                    time.sleep(0.2)
                    if time.time() >= deadline:
                        return None, {"session_path": session, "msg_count": prev_count, "mtime": prev_mtime}
                    continue

                with session.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                messages = data.get("messages", [])
                current_count = len(messages)

                if current_count > prev_count:
                    for msg in messages[prev_count:]:
                        if msg.get("type") == "gemini":
                            content = msg.get("content", "").strip()
                            if content:
                                new_state = {"session_path": session, "msg_count": current_count, "mtime": current_mtime}
                                return content, new_state

                prev_mtime = current_mtime
                prev_count = current_count

            except (OSError, json.JSONDecodeError):
                pass

            if not block:
                return None, {"session_path": session, "msg_count": prev_count, "mtime": prev_mtime}

            time.sleep(0.2)
            if time.time() >= deadline:
                return None, {"session_path": session, "msg_count": prev_count, "mtime": prev_mtime}


class GeminiCommunicator:
    """通过 tmux 与 Gemini 通信，并从会话文件读取回复"""

    def __init__(self):
        self.session_info = self._load_session_info()
        if not self.session_info:
            raise RuntimeError("❌ 未找到活跃的 Gemini 会话，请先运行 claude_ai up gemini")

        self.session_id = self.session_info["session_id"]
        self.runtime_dir = Path(self.session_info["runtime_dir"])
        self.tmux_session = self.session_info.get("tmux_session", "")
        self.timeout = int(os.environ.get("GEMINI_SYNC_TIMEOUT", "60"))
        self.log_reader = GeminiLogReader()
        self.project_session_file = self.session_info.get("_session_file")

        healthy, msg = self._check_session_health()
        if not healthy:
            raise RuntimeError(f"❌ 会话不健康: {msg}\n提示: 请运行 claude_ai up gemini")

    def _load_session_info(self):
        if "GEMINI_SESSION_ID" in os.environ:
            return {
                "session_id": os.environ["GEMINI_SESSION_ID"],
                "runtime_dir": os.environ["GEMINI_RUNTIME_DIR"],
                "tmux_session": os.environ.get("GEMINI_TMUX_SESSION", ""),
                "_session_file": None,
            }

        project_session = Path.cwd() / ".gemini-session"
        if not project_session.exists():
            return None

        try:
            with open(project_session, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return None

            if not data.get("active", False):
                return None

            runtime_dir = Path(data.get("runtime_dir", ""))
            if not runtime_dir.exists():
                return None

            data["_session_file"] = str(project_session)
            return data

        except Exception:
            return None

    def _check_session_health(self) -> Tuple[bool, str]:
        try:
            if not self.runtime_dir.exists():
                return False, "运行时目录不存在"

            if self.tmux_session:
                import subprocess
                result = subprocess.run(
                    ["tmux", "has-session", "-t", self.tmux_session],
                    capture_output=True
                )
                if result.returncode != 0:
                    return False, f"tmux 会话 {self.tmux_session} 不存在"

            return True, "会话正常"
        except Exception as exc:
            return False, f"检查失败: {exc}"

    def _send_via_tmux(self, content: str) -> bool:
        if not self.tmux_session:
            raise RuntimeError("未配置 tmux 会话")
        import subprocess
        import tempfile

        marker = f"gemini-ask-{int(time.time())}-{os.getpid()}"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            subprocess.run(
                ["tmux", "load-buffer", "-b", marker, tmp_path],
                check=True, capture_output=True
            )
            subprocess.run(
                ["tmux", "paste-buffer", "-t", self.tmux_session, "-b", marker],
                check=True, capture_output=True
            )
            subprocess.run(
                ["tmux", "send-keys", "-t", self.tmux_session, "Enter"],
                check=True, capture_output=True
            )
            subprocess.run(
                ["tmux", "delete-buffer", "-b", marker],
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"tmux 发送失败: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def ask_async(self, question: str) -> bool:
        try:
            healthy, status = self._check_session_health()
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            self._send_via_tmux(question)
            print(f"✅ 已发送到 Gemini")
            print("提示: 使用 gpend 查看回复")
            return True
        except Exception as exc:
            print(f"❌ 发送失败: {exc}")
            return False

    def ask_sync(self, question: str, timeout: Optional[int] = None) -> Optional[str]:
        try:
            healthy, status = self._check_session_health()
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            state = self.log_reader.capture_state()
            print("🔔 发送问题到 Gemini...")
            self._send_via_tmux(question)

            wait_timeout = timeout or self.timeout
            print(f"⏳ 等待 Gemini 回复 (超时 {wait_timeout} 秒)...")

            message, _ = self.log_reader.wait_for_message(state, wait_timeout)
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
        message = self.log_reader.latest_message()
        if not message:
            if display:
                print("暂无 Gemini 回复")
            return None
        if display:
            print(message)
        return message

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
            "tmux_session": self.tmux_session,
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
