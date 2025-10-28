#!/usr/bin/env python3
"""
测试Codex窗口启动的简化版本
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def test_simple_codex_start():
    """测试简单的Codex启动"""
    print("🧪 测试简化版Codex窗口启动...")

    try:
        # 简单启动codex
        print("🚀 启动Codex...")
        proc = subprocess.Popen(
            ["codex"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 等待2秒检查是否还在运行
        time.sleep(2)

        if proc.poll() is None:
            print("✅ Codex进程正常运行")
            proc.terminate()
            proc.wait(timeout=5)
            print("✅ 测试完成，已终止测试进程")
            return True
        else:
            stdout, stderr = proc.communicate()
            print(f"❌ Codex进程退出")
            print(f"输出: {stdout}")
            print(f"错误: {stderr}")
            return False

    except FileNotFoundError:
        print("❌ codex命令未找到，请确保已安装codex CLI")
        return False
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def test_codex_version():
    """测试codex版本信息"""
    print("\n🧪 测试Codex版本信息...")

    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"✅ Codex版本信息: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ 获取版本信息失败: {result.stderr}")
            return False

    except FileNotFoundError:
        print("❌ codex命令未找到")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 Codex窗口启动诊断")
    print("=" * 40)

    tests = [
        ("Codex版本检查", test_codex_version),
        ("简化启动测试", test_simple_codex_start)
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

    print(f"📊 诊断结果: {passed}/{total} 项通过")

    if passed == total:
        print("🎉 Codex基础功能正常，问题可能在启动脚本")
    else:
        print("⚠️ Codex基础功能有问题，需要检查安装")

    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())