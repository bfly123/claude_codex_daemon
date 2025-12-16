#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Optional


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
        buffer_name = f"tb-{os.getpid()}-{int(time.time() * 1000)}"
        encoded = (sanitized + "\n").encode("utf-8")
        subprocess.run(["tmux", "load-buffer", "-b", buffer_name, "-"], input=encoded, check=True)
        subprocess.run(["tmux", "paste-buffer", "-t", session, "-b", buffer_name, "-p"], check=True)
        time.sleep(0.05)
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
    def send_text(self, pane_id: str, text: str) -> None:
        sanitized = text.replace("\r", "").strip()
        if not sanitized:
            return
        subprocess.run(["wezterm", "cli", "send-text", "--pane-id", pane_id, "--no-paste"], input=(sanitized + "\n").encode("utf-8"), check=True)

    def is_alive(self, pane_id: str) -> bool:
        try:
            result = subprocess.run(["wezterm", "cli", "list", "--format", "json"], capture_output=True, text=True)
            if result.returncode != 0:
                return False
            panes = json.loads(result.stdout)
            return any(str(p.get("pane_id")) == str(pane_id) for p in panes)
        except Exception:
            return False

    def kill_pane(self, pane_id: str) -> None:
        subprocess.run(["wezterm", "cli", "kill-pane", "--pane-id", pane_id], stderr=subprocess.DEVNULL)

    def activate(self, pane_id: str) -> None:
        subprocess.run(["wezterm", "cli", "activate-pane", "--pane-id", pane_id])

    def create_pane(self, cmd: str, cwd: str, direction: str = "right", percent: int = 50, parent_pane: Optional[str] = None) -> str:
        args = ["wezterm", "cli", "split-pane", "--cwd", cwd]
        if direction == "right":
            args.append("--right")
        elif direction == "bottom":
            args.append("--bottom")
        args.extend(["--percent", str(percent)])
        if parent_pane:
            args.extend(["--pane-id", parent_pane])
        args.extend(["--", "bash", "-c", cmd])
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return result.stdout.strip()


_backend_cache: Optional[TerminalBackend] = None


def detect_terminal() -> Optional[str]:
    if os.environ.get("WEZTERM_PANE"):
        return "wezterm"
    if os.environ.get("TMUX"):
        return "tmux"
    if subprocess.run(["which", "wezterm"], capture_output=True).returncode == 0:
        return "wezterm"
    if subprocess.run(["which", "tmux"], capture_output=True).returncode == 0:
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
