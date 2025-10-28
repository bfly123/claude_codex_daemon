#!/usr/bin/env python3
"""
Claude-Codex 双窗口模式测试脚本
用于验证基础功能是否正常工作
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path

def test_codex_communicator():
    """测试Codex通信模块"""
    print("🧪 测试Codex通信模块...")

    try:
        # 测试导入
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from codex_comm import CodexCommunicator

        print("✅ codex_comm模块导入成功")

        # 测试无会话情况
        try:
            comm = CodexCommunicator()
            print("❌ 应该在没有会话时失败")
            return False
        except RuntimeError as e:
            if "未找到活跃的Codex会话" in str(e):
                print("✅ 正确处理无会话情况")
            else:
                print(f"❌ 意外的错误: {e}")
                return False

        return True

    except ImportError as e:
        print(f"❌ 导入codex_comm失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_command_scripts():
    """测试命令脚本"""
    print("\n🧪 测试命令脚本...")

    scripts = [
        "codex-ask",
        "codex-status",
        "codex-ping",
        "codex_history.py"
    ]

    results = []
    for script in scripts:
        script_path = Path(__file__).resolve().parent / script
        if script_path.exists() and os.access(script_path, os.X_OK):
            print(f"✅ {script} 存在且可执行")
            results.append(True)
        else:
            print(f"❌ {script} 不存在或不可执行")
            results.append(False)

    return all(results)

def test_dual_launcher():
    """测试双窗口启动器"""
    print("\n🧪 测试双窗口启动器...")

    launcher_path = Path(__file__).resolve().parent / "claude-codex-dual"

    if not launcher_path.exists():
        print("❌ claude-codex-dual 不存在")
        return False

    if not os.access(launcher_path, os.X_OK):
        print("❌ claude-codex-dual 不可执行")
        return False

    print("✅ claude-codex-dual 存在且可执行")

    # 测试帮助信息
    try:
        result = subprocess.run(
            [str(launcher_path), "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and "Claude-Codex 双窗口模式" in result.stdout:
            print("✅ 帮助信息正常显示")
            return True
        else:
            print(f"❌ 帮助信息异常: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ 启动器响应超时")
        return False
    except Exception as e:
        print(f"❌ 测试启动器失败: {e}")
        return False

def test_file_structure():
    """测试文件结构"""
    print("\n🧪 测试文件结构...")

    base_dir = Path(__file__).resolve().parent

    required_files = [
        "claude-codex-dual",
        "codex_comm.py",
        "codex-ask",
        "codex-status",
        "codex-ping",
        "codex_history.py",
        "README-DUAL.md",
        "TODO.md"
    ]

    required_dirs = [
        "commands"
    ]

    results = []

    # 检查文件
    for file_name in required_files:
        file_path = base_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name} 存在")
            results.append(True)
        else:
            print(f"❌ {file_name} 不存在")
            results.append(False)

    # 检查目录
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_name}/ 目录存在")
            results.append(True)
        else:
            print(f"❌ {dir_name}/ 目录不存在")
            results.append(False)

    return all(results)

def test_command_docs():
    """测试命令文档"""
    print("\n🧪 测试命令文档...")

    commands_dir = Path(__file__).resolve().parent / "commands"

    required_docs = [
        "codex-ask.md",
        "codex-status.md",
        "codex-ping.md",
        "codex-history.md"
    ]

    results = []

    for doc_name in required_docs:
        doc_path = commands_dir / doc_name
        if doc_path.exists():
            print(f"✅ {doc_name} 文档存在")
            results.append(True)
        else:
            print(f"❌ {doc_name} 文档不存在")
            results.append(False)

    return all(results)

def main():
    """主测试函数"""
    print("🚀 Claude-Codex 双窗口模式功能测试")
    print("=" * 50)

    tests = [
        ("文件结构", test_file_structure),
        ("命令文档", test_command_docs),
        ("命令脚本", test_command_scripts),
        ("双窗口启动器", test_dual_launcher),
        ("通信模块", test_codex_communicator)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}测试:")
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"✅ {test_name}测试通过")
            else:
                print(f"❌ {test_name}测试失败")
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append(False)

    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")

    passed = sum(results)
    total = len(results)

    for i, (test_name, _) in enumerate(tests):
        status = "✅ 通过" if results[i] else "❌ 失败"
        print(f"   {test_name}: {status}")

    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有测试通过！双窗口模式基础功能正常")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关功能")
        return 1

if __name__ == "__main__":
    sys.exit(main())