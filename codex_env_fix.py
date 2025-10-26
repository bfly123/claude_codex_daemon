#!/usr/bin/env python3
"""
Codex 环境排查与放行工具

功能：
1. 以指定用户身份测试多个目录能否创建/绑定 Unix Socket。
2. 检测 SELinux、AppArmor 的状态，并在需要时给出放行建议。
3. 可选自动执行 AppArmor 放行（aa-complain）、SELinux 临时宽松（setenforce 0）。

使用方式：
  sudo python3 codex_env_fix.py [--user <目标用户>] [--runtime-dir <目录>] [--apply]
"""

import argparse
import os
import pwd
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class BindResult:
    directory: Path
    ok: bool
    stdout: str
    stderr: str
    note: str = ""


def run_cmd(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def ensure_directory(directory: Path, owner: str) -> Tuple[bool, str]:
    """
    尝试创建目录，并将权限设置为 700。如果目录存在且不属于目标用户，则给出提示。
    """
    try:
        target_info = pwd.getpwnam(owner)
        target_uid = target_info.pw_uid
        target_gid = target_info.pw_gid

        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
        stat_info = directory.stat()
        if stat_info.st_uid != target_uid or stat_info.st_gid != target_gid:
            try:
                os.chown(directory, target_uid, target_gid)
            except PermissionError as exc:
                return False, f"无法调整目录所有者: {exc}"
        os.chmod(directory, 0o700)
        return True, "OK"
    except OSError as exc:
        return False, str(exc)


def test_bind_as_user(user: str, directory: Path) -> BindResult:
    """
    使用 runuser/sudo 以指定用户身份测试 Unix Socket 绑定。
    """
    bind_script = rf"""
import os, socket, pathlib, sys
path = r"{(directory / 'codex-test-sock').as_posix()}"
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    sock.bind(path)
    sock.listen(1)
    print("SUCCESS")
finally:
    sock.close()
    p = pathlib.Path(path)
    if p.exists():
        p.unlink()
"""
    cmd = ["runuser", "-u", user, "--", sys.executable, "-c", bind_script]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0 and "SUCCESS" in proc.stdout
    note = ""
    if not ok and "Operation not permitted" in proc.stderr:
        note = "可能被安全策略 (SELinux/AppArmor/seccomp) 拦截"
    return BindResult(directory=directory, ok=ok, stdout=proc.stdout.strip(), stderr=proc.stderr.strip(), note=note)


def selinux_status() -> Tuple[str, Optional[str]]:
    if shutil.which("selinuxenabled") is None:
        return "not_installed", None
    enabled = subprocess.run(["selinuxenabled"])
    if enabled.returncode != 0:
        return "disabled", None
    mode_proc = run_cmd(["getenforce"])
    mode = mode_proc.stdout.strip() if mode_proc.returncode == 0 else "Enforcing"
    return "enabled", mode


def apparmor_profiles() -> Tuple[str, List[str]]:
    if not Path("/sys/kernel/security/apparmor/enabled").exists():
        return "disabled", []
    if shutil.which("aa-status") is None:
        return "missing_utils", []
    status = run_cmd(["aa-status"])
    if status.returncode != 0:
        return "unknown", []

    enforce_profiles: List[str] = []
    capture = False
    for line in status.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("profiles are in enforce mode"):
            capture = True
            continue
        if stripped.startswith("profiles are in complain mode"):
            break
        if capture and stripped:
            enforce_profiles.append(stripped)
    return "enabled", enforce_profiles


def apply_apparmor_complain(profile: str) -> Tuple[bool, str]:
    if shutil.which("aa-complain") is None:
        return False, "aa-complain 不存在，请先安装 apparmor-utils"
    proc = run_cmd(["aa-complain", profile])
    return proc.returncode == 0, proc.stdout.strip() or proc.stderr.strip()


def apply_selinux_permissive() -> Tuple[bool, str]:
    if shutil.which("setenforce") is None:
        return False, "setenforce 不存在，可能未启用 SELinux"
    proc = run_cmd(["setenforce", "0"])
    success = proc.returncode == 0
    output = proc.stdout.strip() or proc.stderr.strip()
    return success, output


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex 守护进程运行环境排查/放行脚本")
    parser.add_argument("--user", help="目标普通用户（默认: sudo 调用者或当前用户）")
    parser.add_argument(
        "--runtime-dir",
        action="append",
        help="额外测试的运行目录，可重复使用该参数添加多个目录"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="自动尝试放宽 AppArmor (aa-complain) / SELinux (setenforce 0)"
    )
    return parser.parse_args()


def main() -> int:
    if os.geteuid() != 0:
        print("❌ 请以 root（sudo）身份运行本脚本。")
        return 1

    args = parse_arguments()
    target_user = args.user or os.environ.get("SUDO_USER") or pwd.getpwuid(os.getuid()).pw_name

    print("=== Codex 守护进程排查工具 ===")
    print(f"目标用户: {target_user}")

    candidate_dirs: List[Path] = [
        Path(f"/tmp/codex-{target_user}"),
        Path.home() / ".codex_runtime",
    ]
    if args.runtime_dir:
        candidate_dirs.extend(Path(p).expanduser() for p in args.runtime_dir)

    results: List[BindResult] = []

    for directory in candidate_dirs:
        directory = directory.resolve()
        print(f"\n[检查目录] {directory}")
        ok, msg = ensure_directory(directory, target_user)
        if ok:
            print("  ✅ 目录可用，正在测试 Unix Socket 绑定…")
        else:
            print(f"  ❌ 目录不可用: {msg}")
            results.append(BindResult(directory, False, "", msg, note="目录不可用"))
            continue
        result = test_bind_as_user(target_user, directory)
        if result.ok:
            print("  ✅ 绑定测试成功")
        else:
            print(f"  ❌ 绑定失败: {result.stderr or '未知错误'}")
            if result.note:
                print(f"     提示: {result.note}")
        results.append(result)

    success_paths = [r.directory for r in results if r.ok]
    if success_paths:
        print("\n=== 结果总结 ===")
        print("以下目录已确认可以绑定 Unix Socket，可用于设置 CODEX_RUNTIME_DIR：")
        for path in success_paths:
            print(f"  export CODEX_RUNTIME_DIR=\"{path}\"")
    else:
        print("\n=== 结果总结 ===")
        print("没有目录成功绑定 Unix Socket，可能被安全策略拦截。")

    # 检测 SELinux/AppArmor 状态
    print("\n=== SELinux 状态 ===")
    se_state, se_mode = selinux_status()
    if se_state == "not_installed":
        print("  未检测到 SELinux。")
    elif se_state == "disabled":
        print("  SELinux 已禁用。")
    else:
        print(f"  SELinux 已启用，当前模式: {se_mode}")
        if args.apply:
            print("  -> 尝试 setenforce 0 …")
            ok, msg = apply_selinux_permissive()
            print(f"     {'✅ 成功' if ok else '❌ 失败'}: {msg}")
        else:
            print("  若需临时放宽，可执行: sudo setenforce 0")

    print("\n=== AppArmor 状态 ===")
    aa_state, profiles = apparmor_profiles()
    if aa_state == "disabled":
        print("  AppArmor 未启用。")
    elif aa_state == "missing_utils":
        print("  未找到 aa-status，请安装 apparmor-utils 再重试。")
    elif aa_state == "unknown":
        print("  无法获取 AppArmor 状态。")
    else:
        if profiles:
            print("  以下 profiles 正在 enforce：")
            for profile in profiles:
                print(f"    - {profile}")
            candidates = [p for p in profiles if "python" in p or "claude" in p or "codex" in p]
            if candidates:
                print("  建议将上述 profile 调整为 complain 模式。")
                if args.apply:
                    for profile in candidates:
                        print(f"  -> 执行 aa-complain {profile} …")
                        ok, msg = apply_apparmor_complain(profile)
                        print(f"     {'✅ 成功' if ok else '❌ 失败'}: {msg}")
                else:
                    for profile in candidates:
                        print(f"    sudo aa-complain \"{profile}\"")
            else:
                print("  尚未检测到与 python/claude 相关的 profile。")
        else:
            print("  未发现处于 enforce 模式的 profile。")

    print("\n=== 后续操作建议 ===")
    if success_paths:
        print("1. 在 shell 环境设置 CODEX_RUNTIME_DIR 为上方的成功目录之一。")
        print("2. 重新执行 `claude-codex` 确认守护进程可以启动。")
    else:
        print("1. 确认 SELinux/AppArmor 已放宽或禁用；如必要可使用 --apply 自动尝试。")
        print("2. 若仍失败，请检查容器/沙箱的 seccomp 配置，确保允许 Unix Socket bind。")
        print("3. 完成调整后重新运行本脚本，直到出现可用目录。")

    return 0 if success_paths else 2


if __name__ == "__main__":
    sys.exit(main())
