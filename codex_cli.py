#!/usr/bin/env python3
"""命令行入口，通过 handle_codex_command 调用 Codex 守护进程。"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _resolve_command_alias(argv: Sequence[str]) -> list[str]:
    tool_name = Path(sys.argv[0]).name
    alias_map = {
        "codex-ask": ["ask"],
        "codex-status": ["status"],
        "codex-stop": ["stop"],
        "codex-config": ["config"],
        "codex-reasoning": ["reasoning"],
        "codex-final_only": ["final-only"],
    }
    if tool_name in alias_map and tool_name != "codex-cli":
        return alias_map[tool_name] + list(argv)
    return list(argv)


def _candidate_runtime_dirs() -> list[Path]:
    dirs: list[Path] = []
    env_dir = os.environ.get("CODEX_RUNTIME_DIR")
    if env_dir:
        dirs.append(Path(env_dir).expanduser())
    dirs.append(Path("/tmp") / f"codex-{getpass.getuser()}")
    dirs.append(Path.home() / ".codex_runtime")
    return dirs


def _load_default_client_id() -> str | None:
    for base in _candidate_runtime_dirs():
        file_path = base / "active_client_id"
        try:
            data = file_path.read_text(encoding="utf-8").strip()
            if data:
                return data
        except OSError:
            continue
    return None


def _handle_command(command: str) -> str:
    from codex_commands import handle_codex_command

    result = handle_codex_command(command)
    if isinstance(result, str):
        return result
    return str(result)


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = _resolve_command_alias(argv or sys.argv[1:])

    parser = argparse.ArgumentParser(prog="codex-cli", description="Codex 命令行工具")
    parser.add_argument(
        "--client-id",
        dest="client_id",
        help="指定要复用的 CODEX_CLIENT_ID；默认读取环境变量",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="向 Codex 提问")
    ask_parser.add_argument("question", nargs="+", help="要询问的问题内容")

    status_parser = subparsers.add_parser("status", help="查看当前状态")

    stop_parser = subparsers.add_parser("stop", help="停止当前实例")

    config_parser = subparsers.add_parser("config", help="查看或设置性能模式")
    config_parser.add_argument("profile", nargs="?", choices=["high", "default", "low"], help="目标性能档位")

    reasoning_parser = subparsers.add_parser("reasoning", help="切换推理展示开关")
    reasoning_parser.add_argument("state", choices=["on", "off"], help="on 或 off")

    final_parser = subparsers.add_parser("final-only", help="切换输出详细程度")
    final_parser.add_argument("state", choices=["on", "off"], help="on 返回纯最终答案，off 包含额外细节")

    args = parser.parse_args(raw_argv)

    client_id = args.client_id or os.environ.get("CODEX_CLIENT_ID") or _load_default_client_id()
    if client_id:
        os.environ["CODEX_CLIENT_ID"] = client_id
        if os.environ.get("CODEX_CLI_VERBOSE"):
            print(f"[codex-cli] 使用 CODEX_CLIENT_ID={client_id}", file=sys.stderr)
    else:
        if os.environ.get("CODEX_CLI_VERBOSE"):
            print("[codex-cli] 未找到有效的 CODEX_CLIENT_ID，将以临时会话执行", file=sys.stderr)

    if args.command == "ask":
        payload = " ".join(args.question)
        response = _handle_command(f"/codex-ask {payload}")
    elif args.command == "status":
        response = _handle_command("/codex-status")
    elif args.command == "stop":
        response = _handle_command("/codex-stop")
    elif args.command == "config":
        if args.profile:
            response = _handle_command(f"/codex-config {args.profile}")
        else:
            response = _handle_command("/codex-config")
    elif args.command == "reasoning":
        response = _handle_command(f"/codex-reasoning {args.state}")
    elif args.command == "final-only":
        response = _handle_command(f"/codex-final_only {args.state}")
    else:
        parser.error("未知命令")
        return 1

    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
