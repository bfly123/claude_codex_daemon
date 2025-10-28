#!/usr/bin/env python3
"""
Codex 双窗口桥接器 - 基于 tmux 的常驻 Codex CLI 控制
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

BEGIN_MARK = "[[CLAUDE-BEGIN]]"
END_MARK = "[[CLAUDE-END]]"
ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ANSI_OSC_RE = re.compile(r"\x1b][^\x07]*\x07")
ANSI_SIMPLE_RE = re.compile(r"\x1b[@-~]")


class TmuxCodexSession:
    """通过 tmux 会话与 Codex CLI 进行交互"""

    def __init__(self, session_name: str, log_path: Path, prompt_token: str = "codex>"):
        self.session_name = session_name
        self.log_path = log_path
        self.prompt_token = prompt_token
        self.lock = threading.Lock()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)
        self._ensure_pipe()

    def fire_and_forget(self, question: str) -> None:
        """发送异步请求，不等待结果"""
        with self.lock:
            self._send_to_tmux(question)

    def ask(self, question: str, marker: str, timeout: float = 60.0) -> str:
        """发送同步请求并等待 Codex 输出结束"""
        with self.lock:
            baseline_offset = self._current_log_size()
            command = self._send_to_tmux(question)
            ticket = {
                "marker": marker,
                "command": command,
                "offset": baseline_offset,
                "deadline": time.time() + timeout,
            }
            return self._collect_response(ticket)

    def _send_to_tmux(self, text: str) -> str:
        """格式化为 ask 指令并注入到 tmux """
        command = self._normalize_question(text)
        payload = command.encode("utf-8")
        buffer_name = f"claude-{os.getpid()}-{int(time.time() * 1000)}"
        self._run_tmux(["load-buffer", "-b", buffer_name, "-"], input_data=payload)
        self._run_tmux(["paste-buffer", "-t", self.session_name, "-b", buffer_name])
        self._run_tmux(["delete-buffer", "-b", buffer_name])
        time.sleep(0.05)
        self._run_tmux(["send-keys", "-t", self.session_name, "C-m"])
        return command

    def _normalize_question(self, text: str) -> str:
        """规范化提问内容，保留原意同时方便匹配"""
        sanitized = text.replace("\r", " ").replace("\n", " ").strip()
        return sanitized

    def _collect_response(self, ticket: Dict[str, Any]) -> str:
        """从日志文件读取 Codex 输出并解析回复"""
        deadline = ticket["deadline"]
        command = ticket["command"].strip()
        offset = ticket["offset"]

        buffer_lines: list[str] = []
        remainder = ""

        with self.log_path.open("r", encoding="utf-8", errors="ignore") as handle:
            handle.seek(offset)
            while time.time() < deadline:
                chunk = handle.read()
                if chunk:
                    text = remainder + chunk
                    lines = text.splitlines()
                    remainder = ""
                    if not text.endswith("\n"):
                        remainder = lines.pop() if lines else ""
                    buffer_lines.extend(lines)
                    response = self._try_extract(buffer_lines, command)
                    if response is not None:
                        return response
                else:
                    time.sleep(0.1)

        raise TimeoutError(f"等待 Codex 响应超时 (marker={ticket['marker']})")

    def _current_log_size(self) -> int:
        try:
            return self.log_path.stat().st_size
        except FileNotFoundError:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.touch()
            return 0

    def _ensure_pipe(self) -> None:
        target = shlex.quote(str(self.log_path))
        cmd = [
            "tmux",
            "pipe-pane",
            "-o",
            "-t",
            self.session_name,
            f"cat >> {target}",
        ]
        subprocess.run(cmd, check=False, capture_output=True)

    def _strip_ansi(self, text: str) -> str:
        text = ANSI_OSC_RE.sub("", text)
        text = ANSI_CSI_RE.sub("", text)
        text = ANSI_SIMPLE_RE.sub("", text)
        return text

    def _is_noise(self, clean: str) -> bool:
        noise_keywords = [
            "Working",
            "context left",
            "Thinking",
            "Reasoning",
            "Plan:",
            "Plans:",
            "途中推理",
            "思考中",
            "Summarize",
            "Press enter to",
            "Select Model",
            "Select Reasoning",
            "choose what model",
            "choose what Codex",
            "list configured MCP",
            "/model",
            "/compact",
            "/mention",
        ]
        if not clean:
            return True
        if clean.startswith("› "):
            return True
        if clean.startswith("Cnsidering") or clean.startswith("Considering"):
            return True
        return any(keyword in clean for keyword in noise_keywords)

    def _try_extract(self, lines: list[str], command_line: str) -> Optional[str]:
        meaningful: list[str] = []
        for raw in lines:
            clean = self._strip_ansi(raw).strip()
            if not clean or clean == command_line:
                continue
            if clean.startswith("─ Worked"):
                if meaningful:
                    break
                continue
            if self._is_noise(clean):
                continue
            if clean.startswith("•"):
                content = clean.lstrip("•").strip()
                if content:
                    meaningful.append(content)
                continue
            meaningful.append(clean)

        if meaningful:
            return "\n".join(meaningful).strip()
        return None

    def _run_tmux(self, args: list[str], input_data: Optional[bytes] = None) -> None:
        cmd = ["tmux"] + args
        if input_data is None:
            result = subprocess.run(cmd, capture_output=True, text=True)
            stdout, stderr = result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, input=input_data, capture_output=True, text=False)
            stdout = result.stdout.decode("utf-8", "ignore") if result.stdout else ""
            stderr = result.stderr.decode("utf-8", "ignore") if result.stderr else ""

        if result.returncode != 0:
            raise RuntimeError(
                f"tmux 命令失败: {' '.join(cmd)}\nstdout: {stdout}\nstderr: {stderr}"
            )


class DualBridge:
    """Claude ↔ Codex 桥接主流程"""

    def __init__(self, runtime_dir: Path, session_id: str):
        self.runtime_dir = runtime_dir
        self.session_id = session_id
        self.input_fifo = self.runtime_dir / "input.fifo"
        self.output_fifo = self.runtime_dir / "output.fifo"
        self.history_dir = self.runtime_dir / "history"
        self.history_file = self.history_dir / "session.jsonl"
        self.bridge_log = self.runtime_dir / "bridge.log"
        self.pending_file = self.runtime_dir / "pending.jsonl"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        tmux_session = os.environ.get("CODEX_TMUX_SESSION")
        tmux_log = os.environ.get("CODEX_TMUX_LOG")
        if not tmux_session or not tmux_log:
            raise RuntimeError("缺少 tmux 会话信息，请检查 CODEX_TMUX_SESSION 与 CODEX_TMUX_LOG 环境变量")

        prompt_token = os.environ.get("CODEX_PROMPT_TOKEN", "codex>")
        self.codex_session = TmuxCodexSession(tmux_session, Path(tmux_log), prompt_token)

        self._running = True
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, _: Any) -> None:
        self._running = False
        self._log_console(f"⚠️ 收到信号 {signum}，准备退出...")

    def run(self) -> int:
        self._log_console("🔌 Codex桥接器已启动，等待Claude指令...")
        while self._running:
            try:
                payload = self._read_request()
                if payload is None:
                    time.sleep(0.1)
                    continue
                self._process_request(payload)
            except KeyboardInterrupt:
                self._running = False
            except Exception as exc:
                self._log_console(f"❌ 处理消息失败: {exc}")
                self._log_bridge(f"error: {exc}")
                time.sleep(0.5)

        self._log_console("👋 Codex桥接器已退出")
        return 0

    def _read_request(self) -> Optional[Dict[str, Any]]:
        if not self.input_fifo.exists():
            return None
        try:
            with self.input_fifo.open("r", encoding="utf-8") as fifo:
                line = fifo.readline()
                if not line:
                    return None
                return json.loads(line)
        except json.JSONDecodeError as exc:
            self._log_console(f"⚠️ 无法解析JSON: {exc}")
            return None

    def _process_request(self, payload: Dict[str, Any]) -> None:
        content = payload.get("content", "")
        marker = payload.get("marker") or self._generate_marker()
        expect_response = bool(payload.get("expect_response", False))

        timestamp = self._timestamp()
        self._log_bridge(json.dumps({"marker": marker, "question": content, "time": timestamp}, ensure_ascii=False))
        self._append_history("claude", content, marker)

        try:
            answer = self.codex_session.ask(content, marker)
            self._append_history("codex", answer, marker)
            if expect_response:
                self._send_response({"marker": marker, "response": answer, "timestamp": timestamp})
            else:
                self._record_pending(marker, content, answer, timestamp)
        except TimeoutError as exc:
            msg = f"⏰ Codex 响应超时: {exc}"
            self._append_history("codex", msg, marker)
            if expect_response:
                self._send_response({"marker": marker, "response": msg, "timestamp": timestamp})
            else:
                self._record_pending(marker, content, msg, timestamp)
        except Exception as exc:
            msg = f"❌ Codex 会话异常: {exc}"
            self._append_history("codex", msg, marker)
            if expect_response:
                self._send_response({"marker": marker, "response": msg, "timestamp": timestamp})
            else:
                self._record_pending(marker, content, msg, timestamp)

    def _record_pending(self, marker: str, question: str, response: str, timestamp: str) -> None:
        entry = {
            "marker": marker,
            "question": question,
            "response": response,
            "timestamp": timestamp,
        }
        try:
            with open(self.pending_file, 'a', encoding='utf-8') as fh:
                json.dump(entry, fh, ensure_ascii=False)
                fh.write('\n')
        except Exception as exc:
            self._log_console(f"⚠️ 写入待处理回复失败: {exc}")

    def _send_response(self, response: Dict[str, Any]) -> None:
        if not self.output_fifo.exists():
            return
        try:
            with self.output_fifo.open("w", encoding="utf-8") as fifo:
                fifo.write(json.dumps(response, ensure_ascii=False) + "\n")
                fifo.flush()
        except Exception as exc:
            self._log_console(f"⚠️ 写入输出管道失败: {exc}")

    def _append_history(self, role: str, content: str, marker: str) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "marker": marker,
            "content": content,
        }
        try:
            with self.history_file.open("a", encoding="utf-8") as handle:
                json.dump(entry, handle, ensure_ascii=False)
                handle.write("\n")
        except Exception as exc:
            self._log_console(f"⚠️ 写入历史失败: {exc}")

    def _log_bridge(self, message: str) -> None:
        try:
            with self.bridge_log.open("a", encoding="utf-8") as handle:
                handle.write(f"{self._timestamp()} {message}\n")
        except Exception:
            pass

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _generate_marker() -> str:
        return f"ask-{int(time.time())}-{os.getpid()}"

    @staticmethod
    def _log_console(message: str) -> None:
        print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Claude-Codex tmux 桥接器")
    parser.add_argument("--runtime-dir", required=True, help="运行目录")
    parser.add_argument("--session-id", required=True, help="会话ID")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_dir = Path(args.runtime_dir)
    bridge = DualBridge(runtime_dir, args.session_id)
    return bridge.run()


if __name__ == "__main__":
    raise SystemExit(main())
