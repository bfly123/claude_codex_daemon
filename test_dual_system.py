#!/usr/bin/env python3
"""
测试简化的双窗口系统
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def test_dual_commands():
    """测试双窗口命令"""
    print("🧪 测试双窗口命令...")

    script_dir = Path(__file__).resolve().parent
    commands = [
        ("dual-ask", f"{script_dir}/dual-ask"),
        ("dual-ping", f"{script_dir}/dual-ping"),
        ("dual-status", f"{script_dir}/dual-status")
    ]

    results = []

    for name, cmd in commands:
        try:
            result = subprocess.run([cmd, "--help"], capture_output=True, text=True, timeout=5)
            # 命令应该因为没有会话而失败，但这是预期的
            if "未找到活动会话" in result.stdout or "请提供问题内容" in result.stdout:
                print(f"✅ {name}: 命令正常响应")
                results.append(True)
            else:
                print(f"❌ {name}: 意外响应 - {result.stdout}")
                results.append(False)
        except subprocess.TimeoutExpired:
            print(f"⚠️ {name}: 响应超时")
            results.append(False)
        except Exception as e:
            print(f"❌ {name}: 执行失败 - {e}")
            results.append(False)

    return all(results)

def test_tmux_availability():
    """测试tmux可用性"""
    print("\n🧪 测试tmux可用性...")

    try:
        result = subprocess.run(["tmux", "list-sessions"], capture_output=True, text=True, timeout=5)
        print("✅ tmux命令可用")
        return True
    except FileNotFoundError:
        print("❌ tmux未安装")
        print("💡 安装命令: sudo apt install tmux (Ubuntu/Debian)")
        return False
    except Exception as e:
        print(f"❌ tmux测试失败: {e}")
        return False

def test_codex_availability():
    """测试codex可用性"""
    print("\n🧪 测试codex可用性...")

    try:
        result = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ codex可用: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ codex版本检查失败: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ codex命令未找到")
        return False
    except Exception as e:
        print(f"❌ codex测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 双窗口系统测试")
    print("=" * 40)

    tests = [
        ("tmux可用性", test_tmux_availability),
        ("codex可用性", test_codex_availability),
        ("双窗口命令", test_dual_commands)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name}异常: {e}")
            results.append(False)

    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)

    print(f"📊 测试结果: {passed}/{total} 项通过")

    if passed == total:
        print("\n🎉 系统测试通过！")
        print("\n🚀 现在可以启动双窗口模式:")
        print("   python3 /home/bfly/运维/基本问题/claude-codex-dual-simple")
        print("\n📝 使用命令:")
        print("   /home/bfly/运维/基本问题/dual-ping")
        print("   /home/bfly/运维/基本问题/dual-status")
        print("   /home/bfly/运维/基本问题/dual-ask \"你的问题\"")
    else:
        print("\n⚠️ 部分测试失败，请检查相关组件")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())