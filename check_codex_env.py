#!/usr/bin/env python3
"""
Codex 运行环境自检脚本

检查常见运行目录是否具备创建/绑定 Unix Socket 的能力，
帮助定位 claude-codex 守护进程启动失败的原因。
"""

import os
import pwd
import socket
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


USER = pwd.getpwuid(os.getuid()).pw_name
HOME = Path.home()

# 常见候选目录
CANDIDATES = [
    Path("/tmp"),
    Path(f"/tmp/codex-{USER}"),
    HOME / ".codex_runtime",
    Path.cwd() / ".codex_runtime_local",
]

# 如果设置了 CODEX_RUNTIME_DIR，放在首位
env_runtime = os.environ.get("CODEX_RUNTIME_DIR")
if env_runtime:
    CANDIDATES.insert(0, Path(env_runtime).expanduser())


def fmt_mode(mode: int) -> str:
    return oct(stat.S_IMODE(mode))


def describe_dir(path: Path) -> str:
    try:
        if not path.exists():
            return "不存在（将尝试创建）"
        st = path.stat()
    except PermissionError as exc:
        return f"无法访问目录信息: {exc}"
    perms = fmt_mode(st.st_mode)
    owner = pwd.getpwuid(st.st_uid).pw_name
    return f"存在，权限 {perms}，所有者 {owner}"


@contextmanager
def bind_test_socket(path: Path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(path))
        sock.listen(1)
        yield True, None
    except OSError as exc:
        yield False, exc
    finally:
        sock.close()
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def ensure_dir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        return True, None
    except OSError as exc:
        return False, exc


def main():
    print("=== Codex 守护进程运行目录自检 ===")
    print(f"当前用户: {USER}")
    print(f"主目录: {HOME}")

    successful_paths = []

    for idx, directory in enumerate(CANDIDATES, 1):
        directory = directory.resolve()
        print(f"\n[{idx}] 目录: {directory}")
        print(f"  情况: {describe_dir(directory)}")

        ok, err = ensure_dir(directory)
        if not ok:
            print(f"  ❌ 创建/修正失败: {err}")
            continue
        else:
            print("  ✅ 创建/权限调整成功或已满足要求")

        test_socket = directory / f"codex-test-{os.getpid()}.sock"
        with bind_test_socket(test_socket) as (success, error):
            if success:
                print("  ✅ Unix Socket 绑定测试成功")
                successful_paths.append(str(directory))
            else:
                print(f"  ❌ Unix Socket 绑定失败: {error}")

    print("\n=== 建议 ===")
    if env_runtime:
        print(f"- 已设置 CODEX_RUNTIME_DIR={env_runtime}，确保守护进程启动前保留该变量即可。")
    elif successful_paths:
        print("- 建议选择以下任一目录作为运行目录，例如：")
        print(f"  export CODEX_RUNTIME_DIR=\"{successful_paths[0]}\"")
    else:
        print("- 未找到可用目录，可尝试手动创建一个目录并赋予 700 权限后重试：")
        print("  mkdir -p $HOME/codex_runtime_manual && chmod 700 $HOME/codex_runtime_manual")
        print("  export CODEX_RUNTIME_DIR=\"$HOME/codex_runtime_manual\"")
    print("- 若所有目录都绑定失败，请检查系统安全策略（SELinux、容器限制、挂载 noexec 等）。")
    print("- 通过测试后，可直接运行 `claude-codex` 验证守护进程能否正常启动。")


if __name__ == "__main__":
    main()
