#!/usr/bin/env python3
"""
测试FIFO管道创建功能
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# 添加脚本目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

def test_fifo_creation():
    """测试FIFO管道创建"""
    print("🧪 测试FIFO管道创建...")

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="codex-test-")
    print(f"📁 临时目录: {temp_dir}")

    try:
        # 测试管道路径
        input_fifo = Path(temp_dir) / "input.fifo"
        output_fifo = Path(temp_dir) / "output.fifo"

        # 创建输入管道
        if not input_fifo.exists():
            os.mkfifo(input_fifo)
            print("✅ 输入管道创建成功")
        else:
            print("⚠️ 输入管道已存在")

        # 设置权限
        os.chmod(input_fifo, 0o600)
        print("✅ 输入管道权限设置完成")

        # 创建输出管道
        if not output_fifo.exists():
            os.mkfifo(output_fifo)
            print("✅ 输出管道创建成功")
        else:
            print("⚠️ 输出管道已存在")

        # 设置权限
        os.chmod(output_fifo, 0o644)
        print("✅ 输出管道权限设置完成")

        # 验证管道类型
        import stat
        stat_input = input_fifo.stat()
        stat_output = output_fifo.stat()

        if stat.S_ISFIFO(stat_input.st_mode):  # 检查是否为FIFO
            print("✅ 输入管道类型正确")
        else:
            print("❌ 输入管道类型错误")
            return False

        if stat.S_ISFIFO(stat_output.st_mode):  # 检查是否为FIFO
            print("✅ 输出管道类型正确")
        else:
            print("❌ 输出管道类型错误")
            return False

        print("✅ FIFO管道创建测试通过")
        return True

    except Exception as e:
        print(f"❌ FIFO管道创建失败: {e}")
        return False

    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
            print("🧹 临时目录清理完成")
        except Exception as e:
            print(f"⚠️ 清理临时目录失败: {e}")

def test_dual_launcher_fifo():
    """测试双窗口启动器的FIFO创建功能"""
    print("\n🧪 测试双窗口启动器FIFO创建...")

    try:
        # 导入启动器类
        script_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(script_dir))

        # 导入模块
        import importlib.util
        spec = importlib.util.spec_from_file_location("claude_codex_dual", script_dir / "claude-codex-dual")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        ClaudeCodexDual = module.ClaudeCodexDual

        # 创建实例（但不启动）
        dual = ClaudeCodexDual()

        # 测试创建FIFO
        result = dual.create_fifos()

        if result:
            print("✅ 双窗口启动器FIFO创建成功")

            # 验证文件存在
            if dual.input_fifo.exists() and dual.output_fifo.exists():
                print("✅ 管道文件存在验证通过")

                # 手动清理测试文件
                try:
                    dual.input_fifo.unlink()
                    dual.output_fifo.unlink()
                    dual.runtime_dir.rmdir()
                    print("🧹 测试文件清理完成")
                except Exception as e:
                    print(f"⚠️ 清理测试文件失败: {e}")

                return True
            else:
                print("❌ 管道文件不存在")
                return False
        else:
            print("❌ 双窗口启动器FIFO创建失败")
            return False

    except ImportError as e:
        print(f"❌ 导入启动器失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试启动器FIFO创建失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 FIFO管道创建功能测试")
    print("=" * 50)

    tests = [
        ("基础FIFO创建", test_fifo_creation),
        ("启动器FIFO创建", test_dual_launcher_fifo)
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

    print(f"📊 测试结果: {passed}/{total} 项通过")

    if passed == total:
        print("🎉 所有FIFO创建测试通过！")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())