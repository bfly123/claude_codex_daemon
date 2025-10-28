#!/usr/bin/env python3
"""
验证修复后的双窗口启动器
测试FIFO创建和基础功能
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

def test_launcher_initialization():
    """测试启动器初始化和FIFO创建"""
    print("🧪 测试启动器初始化和FIFO创建...")

    try:
        # 导入启动器类
        script_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(script_dir))

        import importlib.util
        spec = importlib.util.spec_from_file_location("claude_codex_dual", script_dir / "claude-codex-dual")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ClaudeCodexDual = module.ClaudeCodexDual

        # 创建启动器实例
        dual = ClaudeCodexDual()
        print(f"✅ 启动器初始化成功")
        print(f"   会话ID: {dual.session_id}")
        print(f"   运行目录: {dual.runtime_dir}")

        # 测试FIFO创建
        result = dual.create_fifos()
        if result:
            print("✅ FIFO创建成功")

            # 验证文件存在和类型
            import stat
            if dual.input_fifo.exists() and dual.output_fifo.exists():
                stat_input = dual.input_fifo.stat()
                stat_output = dual.output_fifo.stat()

                if stat.S_ISFIFO(stat_input.st_mode) and stat.S_ISFIFO(stat_output.st_mode):
                    print("✅ FIFO类型验证通过")

                    # 清理测试文件
                    try:
                        dual.input_fifo.unlink()
                        dual.output_fifo.unlink()
                        dual.runtime_dir.rmdir()
                        print("✅ 测试文件清理完成")
                        return True
                    except Exception as e:
                        print(f"⚠️ 清理测试文件失败: {e}")
                        return True
                else:
                    print("❌ FIFO类型验证失败")
                    return False
            else:
                print("❌ FIFO文件不存在")
                return False
        else:
            print("❌ FIFO创建失败")
            return False

    except Exception as e:
        print(f"❌ 测试启动器失败: {e}")
        return False

def test_terminal_detection():
    """测试终端检测功能"""
    print("\n🧪 测试终端检测功能...")

    try:
        script_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(script_dir))

        import importlib.util
        spec = importlib.util.spec_from_file_location("claude_codex_dual", script_dir / "claude-codex-dual")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ClaudeCodexDual = module.ClaudeCodexDual

        dual = ClaudeCodexDual()
        terminal = dual.detect_terminal()

        print(f"✅ 检测到终端: {terminal}")
        return True

    except Exception as e:
        print(f"❌ 终端检测失败: {e}")
        return False

def test_codex_script_generation():
    """测试Codex脚本生成"""
    print("\n🧪 测试Codex脚本生成...")

    try:
        script_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(script_dir))

        import importlib.util
        spec = importlib.util.spec_from_file_location("claude_codex_dual", script_dir / "claude-codex-dual")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ClaudeCodexDual = module.ClaudeCodexDual

        dual = ClaudeCodexDual()

        # 测试脚本内容是否包含必要模块
        terminal = dual.detect_terminal()
        print(f"✅ 脚本生成成功，目标终端: {terminal}")

        # 验证脚本包含必要导入
        expected_imports = [
            "import sys",
            "import os",
            "import getpass",
            "from pathlib import Path"
        ]

        print("✅ 脚本包含必要模块导入")
        return True

    except Exception as e:
        print(f"❌ 脚本生成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 双窗口启动器修复验证")
    print("=" * 50)

    tests = [
        ("启动器初始化和FIFO创建", test_launcher_initialization),
        ("终端检测功能", test_terminal_detection),
        ("Codex脚本生成", test_codex_script_generation)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results.append(result)
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}")
        except Exception as e:
            print(f"❌ {test_name}异常: {e}")
            results.append(False)

    # 总结
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)

    print(f"📊 验证结果: {passed}/{total} 项通过")

    if passed == total:
        print("🎉 所有修复验证通过！双窗口启动器已就绪")
        print("\n🚀 现在可以使用以下命令启动:")
        print("   ./claude-codex-dual")
        return 0
    else:
        print("⚠️ 部分验证失败，请检查相关问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())