#!/usr/bin/env python3
"""
session_utils.py - Session 文件权限检查工具
"""
from __future__ import annotations
import os
import stat
from pathlib import Path
from typing import Tuple, Optional


def check_session_writable(session_file: Path) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    检查 session 文件是否可写

    Returns:
        (可写, 错误原因, 解决建议)
    """
    session_file = Path(session_file)
    parent = session_file.parent

    # 1. 检查父目录是否存在且可进入
    if not parent.exists():
        return False, f"目录不存在: {parent}", f"mkdir -p {parent}"

    if not os.access(parent, os.X_OK):
        return False, f"目录无法访问(缺少x权限): {parent}", f"chmod +x {parent}"

    # 2. 检查父目录是否可写
    if not os.access(parent, os.W_OK):
        return False, f"目录不可写: {parent}", f"chmod u+w {parent}"

    # 3. 如果文件不存在，目录可写就行
    if not session_file.exists():
        return True, None, None

    # 4. 检查是否是普通文件
    if session_file.is_symlink():
        target = session_file.resolve()
        return False, f"是符号链接指向 {target}", f"rm -f {session_file}"

    if session_file.is_dir():
        return False, "是目录而非文件", f"rmdir {session_file} 或 rm -rf {session_file}"

    if not session_file.is_file():
        return False, "不是普通文件", f"rm -f {session_file}"

    # 5. 检查文件归属
    try:
        file_stat = session_file.stat()
        file_uid = file_stat.st_uid
        current_uid = os.getuid()

        if file_uid != current_uid:
            import pwd
            try:
                owner_name = pwd.getpwuid(file_uid).pw_name
            except KeyError:
                owner_name = str(file_uid)
            current_name = pwd.getpwuid(current_uid).pw_name
            return False, f"文件归属为 {owner_name} (当前用户: {current_name})", \
                   f"sudo chown {current_name}:{current_name} {session_file}"
    except Exception:
        pass

    # 6. 检查文件是否可写
    if not os.access(session_file, os.W_OK):
        mode = stat.filemode(session_file.stat().st_mode)
        return False, f"文件不可写 (权限: {mode})", f"chmod u+w {session_file}"

    return True, None, None


def safe_write_session(session_file: Path, content: str) -> Tuple[bool, Optional[str]]:
    """
    安全写入 session 文件，失败时返回友好错误

    Returns:
        (成功, 错误信息)
    """
    session_file = Path(session_file)

    # 预检查
    writable, reason, fix = check_session_writable(session_file)
    if not writable:
        return False, f"❌ 无法写入 {session_file.name}: {reason}\n💡 解决方案: {fix}"

    # 尝试原子写入
    tmp_file = session_file.with_suffix(".tmp")
    try:
        tmp_file.write_text(content, encoding="utf-8")
        os.replace(tmp_file, session_file)
        return True, None
    except PermissionError as e:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
        return False, f"❌ 无法写入 {session_file.name}: {e}\n💡 尝试: rm -f {session_file} 后重试"
    except Exception as e:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
        return False, f"❌ 写入失败: {e}"


def print_session_error(msg: str, to_stderr: bool = True) -> None:
    """输出 session 相关错误"""
    import sys
    output = sys.stderr if to_stderr else sys.stdout
    print(msg, file=output)
