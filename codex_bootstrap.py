"""
Codex Python bootstrap module.

When this module is imported, it makes ``handle_codex_command`` available at the
global builtins level so that simple one-liners like::

    python3 -c "print(handle_codex_command('/codex-config high'))"

work without needing an explicit import statement.
"""

from __future__ import annotations

import builtins


def _inject_handle_codex_command() -> None:
    if getattr(builtins, "handle_codex_command", None) is not None:
        return

    try:
        from codex_commands import handle_codex_command  # type: ignore
    except Exception:
        return

    builtins.handle_codex_command = handle_codex_command
    globals()["handle_codex_command"] = handle_codex_command


_inject_handle_codex_command()
