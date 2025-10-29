#!/usr/bin/env python3
"""
Codex 通信模块（日志驱动版本）
通过 FIFO 发送请求，并从 ~/.codex/sessions 下的官方日志解析回复。
"""

from __future__ import annotations

import json
import os
import time
import shlex
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

SESSION_ROOT = Path.home() / ".codex" / "sessions"


class CodexLogReader:
    """读取 ~/.codex/sessions 内的 Codex 官方日志"""

    def __init__(self, root: Path = SESSION_ROOT):
        self.root = root

    def _latest_log(self) -> Optional[Path]:
        if not self.root.exists():
            return None
        logs = sorted(self.root.glob("**/*.jsonl"), key=lambda p: p.stat().st_mtime)
        return logs[-1] if logs else None

    def current_log_path(self) -> Optional[Path]:
        return self._latest_log()

    def capture_state(self) -> Dict[str, Any]:
        """记录当前日志与偏移"""
        log = self._latest_log()
        offset = log.stat().st_size if log and log.exists() else 0
        return {"log_path": log, "offset": offset}

    def wait_for_message(self, state: Dict[str, Any], timeout: float) -> Tuple[Optional[str], Dict[str, Any]]:
        """阻塞等待新的回复"""
        return self._read_since(state, timeout, block=True)

    def try_get_message(self, state: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        """非阻塞读取回复"""
        return self._read_since(state, timeout=0.0, block=False)

    def latest_message(self) -> Optional[str]:
        """直接获取最新一条回复"""
        log_path = self._latest_log()
        if not log_path:
            return None
        try:
            with log_path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                buffer = bytearray()
                position = handle.tell()
                while position > 0 and len(buffer) < 1024 * 256:
                    read_size = min(4096, position)
                    position -= read_size
                    handle.seek(position)
                    buffer = handle.read(read_size) + buffer
                    if buffer.count(b"\n") >= 50:
                        break
                lines = buffer.decode("utf-8", errors="ignore").splitlines()
        except OSError:
            return None

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = self._extract_message(entry)
            if message:
                return message
        return None

    def _read_since(self, state: Dict[str, Any], timeout: float, block: bool) -> Tuple[Optional[str], Dict[str, Any]]:
        deadline = time.time() + timeout
        current_path = state.get("log_path")
        offset = state.get("offset", 0)

        def ensure_log() -> Path:
            log = current_path
            if log is None or not log.exists():
                log = self._latest_log()
            if log is None:
                raise FileNotFoundError("未找到 Codex session 日志")
            return log

        while True:
            try:
                log_path = ensure_log()
            except FileNotFoundError:
                if not block:
                    return None, {"log_path": None, "offset": 0}
                time.sleep(0.1)
                continue

            with log_path.open("r", encoding="utf-8", errors="ignore") as fh:
                fh.seek(offset)
                while True:
                    if block and time.time() >= deadline:
                        return None, {"log_path": log_path, "offset": offset}
                    line = fh.readline()
                    if not line:
                        break
                    offset = fh.tell()
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = self._extract_message(entry)
                    if message is not None:
                        return message, {"log_path": log_path, "offset": offset}

            latest = self._latest_log()
            if latest and latest != log_path:
                current_path = latest
                try:
                    offset = latest.stat().st_size
                except OSError:
                    offset = 0
                if not block:
                    return None, {"log_path": current_path, "offset": offset}
                time.sleep(0.05)
                continue

            if not block:
                return None, {"log_path": log_path, "offset": offset}

            time.sleep(0.1)
            if time.time() >= deadline:
                return None, {"log_path": log_path, "offset": offset}

    @staticmethod
    def _extract_message(entry: dict) -> Optional[str]:
        if entry.get("type") != "response_item":
            return None
        payload = entry.get("payload", {})
        if payload.get("type") != "message":
            return None

        content = payload.get("content") or []
        texts = [item.get("text", "") for item in content if item.get("type") == "output_text"]
        if texts:
            return "\n".join(filter(None, texts)).strip()

        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        return None


class CodexCommunicator:
    """通过 FIFO 与 Codex 桥接器通信，并使用日志读取回复"""

    def __init__(self):
        self.session_info = self._load_session_info()
        if not self.session_info:
            raise RuntimeError("❌ 未找到活跃的Codex会话，请先运行 claude_codex")

        self.session_id = self.session_info["session_id"]
        self.runtime_dir = Path(self.session_info["runtime_dir"])
        self.input_fifo = Path(self.session_info["input_fifo"])

        self.timeout = int(os.environ.get("CODEX_SYNC_TIMEOUT", "30"))
        self.marker_prefix = "ask"
        self.log_reader = CodexLogReader()
        self.project_session_file = Path.cwd() / ".codex-session"

    def _load_session_info(self):
        if "CODEX_SESSION_ID" in os.environ:
            return {
                "session_id": os.environ["CODEX_SESSION_ID"],
                "runtime_dir": os.environ["CODEX_RUNTIME_DIR"],
                "input_fifo": os.environ["CODEX_INPUT_FIFO"],
                "output_fifo": os.environ.get("CODEX_OUTPUT_FIFO", ""),
            }

        project_session = Path.cwd() / ".codex-session"
        if project_session.exists():
            try:
                with open(project_session, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _check_session_health(self):
        try:
            if not self.runtime_dir.exists():
                return False, "运行时目录不存在"

            codex_pid_file = self.runtime_dir / "codex.pid"
            if not codex_pid_file.exists():
                return False, "Codex进程PID文件不存在"

            with open(codex_pid_file, "r", encoding="utf-8") as f:
                codex_pid = int(f.read().strip())
            try:
                os.kill(codex_pid, 0)
            except OSError:
                return False, f"Codex进程(PID:{codex_pid})已退出"

            if not self.input_fifo.exists():
                return False, "通信管道不存在"

            return True, "会话正常"
        except Exception as exc:
            return False, f"检查失败: {exc}"

    def _send_message(self, content: str) -> Tuple[str, Dict[str, Any]]:
        marker = self._generate_marker()
        message = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "marker": marker,
        }

        state = self.log_reader.capture_state()

        with open(self.input_fifo, "w", encoding="utf-8") as fifo:
            fifo.write(json.dumps(message, ensure_ascii=False) + "\n")
            fifo.flush()

        return marker, state

    def _generate_marker(self) -> str:
        return f"{self.marker_prefix}-{int(time.time())}-{os.getpid()}"

    def ask_async(self, question: str) -> bool:
        try:
            healthy, status = self._check_session_health()
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            marker, state = self._send_message(question)
            self._remember_codex_session(state.get("log_path"))
            print(f"✅ 已发送到Codex (标记: {marker[:12]}...)")
            print("提示: 使用 /cpend 查看最新回复")
            return True
        except Exception as exc:
            print(f"❌ 发送失败: {exc}")
            return False

    def ask_sync(self, question: str, timeout: Optional[int] = None) -> Optional[str]:
        try:
            healthy, status = self._check_session_health()
            if not healthy:
                raise RuntimeError(f"❌ 会话异常: {status}")

            print("🔔 发送问题到Codex...")
            marker, state = self._send_message(question)
            wait_timeout = timeout or self.timeout
            print(f"⏳ 等待Codex回复 (超时 {wait_timeout} 秒)...")

            message, new_state = self.log_reader.wait_for_message(state, wait_timeout)
            if message:
                print("🤖 Codex回复:")
                print(message)
                self._remember_codex_session(new_state.get("log_path"))
                return message

            print("⏰ Codex未在限定时间内回复，可稍后执行 /cpend 获取最新答案")
            return None
        except Exception as exc:
            print(f"❌ 同步询问失败: {exc}")
            return None

    def consume_pending(self, display: bool = True):
        message = self.log_reader.latest_message()
        if not message:
            if display:
                print("暂无 Codex 回复")
            return None
        self._remember_codex_session(self.log_reader.current_log_path())
        if display:
            print(message)
        return message

    def ping(self, display: bool = True) -> Tuple[bool, str]:
        healthy, status = self._check_session_health()
        msg = f"✅ Codex连接正常 ({status})" if healthy else f"❌ Codex连接异常: {status}"
        if display:
            print(msg)
        return healthy, msg

    def get_status(self) -> Dict[str, Any]:
        healthy, status = self._check_session_health()
        info = {
            "session_id": self.session_id,
            "runtime_dir": str(self.runtime_dir),
            "healthy": healthy,
            "status": status,
            "input_fifo": str(self.input_fifo),
        }

        codex_pid_file = self.runtime_dir / "codex.pid"
        if codex_pid_file.exists():
            with open(codex_pid_file, "r", encoding="utf-8") as f:
                info["codex_pid"] = int(f.read().strip())

        return info

    def _remember_codex_session(self, log_path: Optional[Path]) -> None:
        if not log_path:
            return
        project_file = self.project_session_file
        if not project_file.exists():
            return
        try:
            with project_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return

        path_str = str(log_path)
        session_id = self._extract_session_id(log_path)
        resume_cmd = f"codex resume {session_id}" if session_id else None
        updated = False

        if data.get("codex_session_path") != path_str:
            data["codex_session_path"] = path_str
            updated = True
        if session_id and data.get("codex_session_id") != session_id:
            data["codex_session_id"] = session_id
            updated = True
        if resume_cmd:
            if data.get("codex_start_cmd") != resume_cmd:
                data["codex_start_cmd"] = resume_cmd
                updated = True
        elif data.get("codex_start_cmd", "").startswith("codex resume "):
            # keep existing command if we cannot derive a better one
            pass
        if data.get("active") is False:
            data["active"] = True
            updated = True

        if not updated:
            return

        tmp_file = project_file.with_suffix(".tmp")
        try:
            with tmp_file.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_file, project_file)
        except Exception:
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

    @staticmethod
    def _extract_session_id(log_path: Path) -> Optional[str]:
        stem = log_path.stem
        # Expect pattern rollout-...-<uuid>
        parts = stem.split("-")
        if len(parts) < 2:
            return None
        candidate = "-".join(parts[-5:]) if len(parts) >= 5 else parts[-1]
        # Validate UUID-like structure (versionless)
        if len(candidate) == 36 and candidate.count("-") == 4:
            return candidate
        try:
            # Fallback to reading the first line session_meta
            with log_path.open("r", encoding="utf-8") as handle:
                first_line = handle.readline()
        except OSError:
            return None
        try:
            entry = json.loads(first_line)
            payload = entry.get("payload", {})
            session_meta_id = payload.get("id")
            if isinstance(session_meta_id, str):
                return session_meta_id
        except Exception:
            return None
        return None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Codex 通信工具（日志驱动）")
    parser.add_argument("question", nargs="*", help="要发送的问题")
    parser.add_argument("--wait", "-w", action="store_true", help="同步等待回复")
    parser.add_argument("--timeout", type=int, default=30, help="同步超时时间(秒)")
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
            tokens = list(args.question)
            if tokens and tokens[0].lower() == "ask":
                tokens = tokens[1:]
            question_text = " ".join(tokens).strip()
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
