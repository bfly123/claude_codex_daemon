#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import platform
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    return platform.system() == "Windows"


def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _is_windows_wezterm() -> bool:
    """检测 WezTerm 是否运行在 Windows 上"""
    override = os.environ.get("CODEX_WEZTERM_BIN") or os.environ.get("WEZTERM_BIN")
    if override and "/mnt/c/" in override:
        return True
    if is_wsl():
        candidates = [
            "/mnt/c/Program Files/WezTerm/wezterm.exe",
            "/mnt/c/Program Files (x86)/WezTerm/wezterm.exe",
        ]
        for c in candidates:
            if Path(c).exists():
                return True
    return False


def _default_shell() -> tuple[str, str]:
    # WSL + Windows WezTerm: pane 在 Windows 环境运行，需用 PowerShell
    if is_wsl() and _is_windows_wezterm():
        return "powershell.exe", "-Command"
    if is_windows():
        for shell in ["pwsh", "powershell"]:
            if shutil.which(shell):
                return shell, "-Command"
        return "powershell", "-Command"
    return "bash", "-c"


def get_shell_type() -> str:
    shell, _ = _default_shell()
    if shell in ("pwsh", "powershell"):
        return "powershell"
    return "bash"


class TerminalBackend(ABC):
    @abstractmethod
    def send_text(self, pane_id: str, text: str) -> None: ...
    @abstractmethod
    def is_alive(self, pane_id: str) -> bool: ...
    @abstractmethod
    def kill_pane(self, pane_id: str) -> None: ...
    @abstractmethod
    def activate(self, pane_id: str) -> None: ...
    @abstractmethod
    def create_pane(self, cmd: str, cwd: str, direction: str = "right", percent: int = 50, parent_pane: Optional[str] = None) -> str: ...


class TmuxBackend(TerminalBackend):
    def send_text(self, session: str, text: str) -> None:
        sanitized = text.replace("\r", "").strip()
        if not sanitized:
            return
        # Fast-path for typical short, single-line commands (fewer tmux subprocess calls).
        if "\n" not in sanitized and len(sanitized) <= 200:
            subprocess.run(["tmux", "send-keys", "-t", session, "-l", sanitized], check=True)
            subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], check=True)
            return

        buffer_name = f"tb-{os.getpid()}-{int(time.time() * 1000)}"
        encoded = (sanitized + "\n").encode("utf-8")
        subprocess.run(["tmux", "load-buffer", "-b", buffer_name, "-"], input=encoded, check=True)
        subprocess.run(["tmux", "paste-buffer", "-t", session, "-b", buffer_name, "-p"], check=True)
        time.sleep(0.02)
        subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], check=True)
        subprocess.run(["tmux", "delete-buffer", "-b", buffer_name], stderr=subprocess.DEVNULL)

    def is_alive(self, session: str) -> bool:
        result = subprocess.run(["tmux", "has-session", "-t", session], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0

    def kill_pane(self, session: str) -> None:
        subprocess.run(["tmux", "kill-session", "-t", session], stderr=subprocess.DEVNULL)

    def activate(self, session: str) -> None:
        subprocess.run(["tmux", "attach", "-t", session])

    def create_pane(self, cmd: str, cwd: str, direction: str = "right", percent: int = 50, parent_pane: Optional[str] = None) -> str:
        session_name = f"ai-{int(time.time()) % 100000}-{os.getpid()}"
        subprocess.run(["tmux", "new-session", "-d", "-s", session_name, "-c", cwd, cmd], check=True)
        return session_name


class WeztermBackend(TerminalBackend):
    _wezterm_bin: Optional[str] = None

    @classmethod
    def _cli_base_args(cls) -> list[str]:
        args = [cls._bin(), "cli"]
        wezterm_class = os.environ.get("CODEX_WEZTERM_CLASS") or os.environ.get("WEZTERM_CLASS")
        if wezterm_class:
            args.extend(["--class", wezterm_class])
        if os.environ.get("CODEX_WEZTERM_PREFER_MUX", "").lower() in {"1", "true", "yes", "on"}:
            args.append("--prefer-mux")
        if os.environ.get("CODEX_WEZTERM_NO_AUTO_START", "").lower() in {"1", "true", "yes", "on"}:
            args.append("--no-auto-start")
        return args

    @classmethod
    def _bin(cls) -> str:
        if cls._wezterm_bin:
            return cls._wezterm_bin
        override = os.environ.get("CODEX_WEZTERM_BIN") or os.environ.get("WEZTERM_BIN")
        if override:
            cls._wezterm_bin = override
            return override
        found = shutil.which("wezterm") or shutil.which("wezterm.exe")
        if not found and is_wsl():
            # Common Windows install locations (WSL interop may not expose Windows PATH).
            candidates = [
                "/mnt/c/Program Files/WezTerm/wezterm.exe",
                "/mnt/c/Program Files (x86)/WezTerm/wezterm.exe",
            ]
            for candidate in candidates:
                if Path(candidate).exists():
                    found = candidate
                    break
        cls._wezterm_bin = found or "wezterm"
        return cls._wezterm_bin

    def send_text(self, pane_id: str, text: str) -> None:
        sanitized = text.replace("\r", "").strip()
        if not sanitized:
            return
        # tmux 可单独发 Enter 键；wezterm cli 没有 send-key，只能用 send-text 发送控制字符。
        # 经验上，很多交互式 CLI 在“粘贴/多行输入”里不会自动执行；这里将文本和 Enter 分两次发送更可靠。
        subprocess.run(
            [*self._cli_base_args(), "send-text", "--pane-id", pane_id, "--no-paste"],
            input=sanitized.encode("utf-8"),
            check=True,
        )
        # 给 TUI 一点时间退出“粘贴/突发输入”路径，再发送 Enter 更像真实按键
        time.sleep(0.01)
        try:
            subprocess.run(
                [*self._cli_base_args(), "send-text", "--pane-id", pane_id, "--no-paste"],
                input=b"\r",
                check=True,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                [*self._cli_base_args(), "send-text", "--pane-id", pane_id, "--no-paste"],
                input=b"\n",
                check=True,
            )

    def is_alive(self, pane_id: str) -> bool:
        try:
            result = subprocess.run([*self._cli_base_args(), "list", "--format", "json"], capture_output=True, text=True)
            if result.returncode != 0:
                return False
            panes = json.loads(result.stdout)
            return any(str(p.get("pane_id")) == str(pane_id) for p in panes)
        except Exception:
            return False

    def kill_pane(self, pane_id: str) -> None:
        subprocess.run([*self._cli_base_args(), "kill-pane", "--pane-id", pane_id], stderr=subprocess.DEVNULL)

    def activate(self, pane_id: str) -> None:
        subprocess.run([*self._cli_base_args(), "activate-pane", "--pane-id", pane_id])

    def create_pane(self, cmd: str, cwd: str, direction: str = "right", percent: int = 50, parent_pane: Optional[str] = None) -> str:
        args = [*self._cli_base_args(), "split-pane", "--cwd", cwd]
        if direction == "right":
            args.append("--right")
        elif direction == "bottom":
            args.append("--bottom")
        args.extend(["--percent", str(percent)])
        if parent_pane:
            args.extend(["--pane-id", parent_pane])
        shell, flag = _default_shell()
        args.extend(["--", shell, flag, cmd])
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout.strip()


_backend_cache: Optional[TerminalBackend] = None


def detect_terminal() -> Optional[str]:
    if os.environ.get("WEZTERM_PANE"):
        return "wezterm"
    if os.environ.get("TMUX"):
        return "tmux"
    override = os.environ.get("CODEX_WEZTERM_BIN") or os.environ.get("WEZTERM_BIN")
    if override and Path(override).expanduser().exists():
        return "wezterm"
    if shutil.which("wezterm") or shutil.which("wezterm.exe"):
        return "wezterm"
    if shutil.which("tmux") or shutil.which("tmux.exe"):
        return "tmux"
    return None


def get_backend(terminal_type: Optional[str] = None) -> Optional[TerminalBackend]:
    global _backend_cache
    if _backend_cache:
        return _backend_cache
    t = terminal_type or detect_terminal()
    if t == "wezterm":
        _backend_cache = WeztermBackend()
    elif t == "tmux":
        _backend_cache = TmuxBackend()
    return _backend_cache


def get_backend_for_session(session_data: dict) -> Optional[TerminalBackend]:
    terminal = session_data.get("terminal", "tmux")
    if terminal == "wezterm":
        return WeztermBackend()
    return TmuxBackend()


def get_pane_id_from_session(session_data: dict) -> Optional[str]:
    terminal = session_data.get("terminal", "tmux")
    if terminal == "wezterm":
        return session_data.get("pane_id")
    return session_data.get("tmux_session")
