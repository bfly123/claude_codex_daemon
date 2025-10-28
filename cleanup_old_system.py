#!/usr/bin/env python3
"""
清理旧系统，避免与新双窗口模式冲突
"""

import os
import sys
import shutil
from pathlib import Path

def cleanup_old_system():
    """清理旧的claude-codex系统"""
    print("🧹 开始清理旧系统文件...")

    local_bin = Path("/home/bfly/.local/bin")
    old_install_dir = Path("/home/bfly/.local/share/claude-codex-lock")

    removed_files = []
    failed_files = []

    # 清理全局符号链接
    codex_links = [
        "claude-codex",
        "claude-codex-install",
        "codex-ask",
        "codex-cli",
        "codex-config",
        "codex-final_only",
        "codex-reasoning",
        "codex-status",
        "codex-stop"
    ]

    for link in codex_links:
        link_path = local_bin / link
        if link_path.exists():
            try:
                link_path.unlink()
                removed_files.append(str(link_path))
                print(f"✅ 删除: {link_path}")
            except Exception as e:
                failed_files.append(f"{link_path}: {e}")
                print(f"❌ 删除失败: {link_path} - {e}")

    # 备份旧安装目录（重命名而不是删除）
    if old_install_dir.exists():
        backup_dir = old_install_dir.parent / "claude-codex-lock-backup"
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(str(old_install_dir), str(backup_dir))
            removed_files.append(f"{old_install_dir} -> {backup_dir}")
            print(f"✅ 备份旧安装目录: {old_install_dir} -> {backup_dir}")
        except Exception as e:
            failed_files.append(f"{old_install_dir}: {e}")
            print(f"❌ 备份失败: {old_install_dir} - {e}")

    return removed_files, failed_files

def setup_new_system_aliases():
    """为新系统创建别名"""
    print("\n🔧 为新系统创建使用别名...")

    current_dir = Path("/home/bfly/运维/基本问题").resolve()

    aliases = [
        ("dual-codex", f"{current_dir}/claude-codex-dual"),
        ("dual-ask", f"{current_dir}/codex-ask"),
        ("dual-status", f"{current_dir}/codex-status"),
        ("dual-ping", f"{current_dir}/codex-ping")
    ]

    print("建议添加以下别名到 ~/.bashrc 或 ~/.zshrc:")
    print()
    for alias, cmd in aliases:
        print(f"alias {alias}='{cmd}'")

    print()
    print("或者直接使用完整路径:")
    for alias, cmd in aliases:
        print(f"{cmd}  # 对应 {alias}")

def verify_cleanup():
    """验证清理结果"""
    print("\n🔍 验证清理结果...")

    local_bin = Path("/home/bfly/.local/bin")
    remaining_links = []

    codex_links = ["codex-ask", "codex-status", "codex-ping", "claude-codex"]

    for link in codex_links:
        link_path = local_bin / link
        if link_path.exists():
            remaining_links.append(str(link_path))

    if remaining_links:
        print("⚠️ 仍有未清理的链接:")
        for link in remaining_links:
            print(f"   {link}")
        return False
    else:
        print("✅ 全局命令清理完成")
        return True

def main():
    """主函数"""
    print("🚀 Claude-Codex 系统清理工具")
    print("目的: 清理旧系统，为新双窗口模式让路")
    print("=" * 60)

    # 清理旧系统
    removed, failed = cleanup_old_system()

    print(f"\n📊 清理结果:")
    print(f"✅ 成功处理: {len(removed)} 项")
    for item in removed:
        print(f"   {item}")

    if failed:
        print(f"❌ 处理失败: {len(failed)} 项")
        for item in failed:
            print(f"   {item}")

    # 验证清理
    success = verify_cleanup()

    # 设置新系统别名
    setup_new_system_aliases()

    print("\n" + "=" * 60)
    if success and not failed:
        print("🎉 清理完成！现在可以使用新的双窗口模式")
        print("\n🚀 启动命令:")
        print("   /home/bfly/运维/基本问题/claude-codex-dual")
        print("\n📝 或者添加别名后使用:")
        print("   dual-codex")
        return 0
    else:
        print("⚠️ 清理部分完成，可能需要手动处理剩余项目")
        return 1

if __name__ == "__main__":
    sys.exit(main())