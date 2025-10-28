#!/usr/bin/env python3
"""
测试简化的双窗口启动
"""

import os
import sys
import tempfile
import subprocess
import time
from pathlib import Path

def test_codex_terminal_launch():
    """测试Codex在真实终端中启动"""
    print("🧪 测试Codex在终端中启动...")

    script_dir = Path(__file__).resolve().parent

    # 创建简化的测试脚本
    test_script = f'''#!/bin/bash
echo "🤖 测试Codex启动..."
echo "Session ID: test-session-123"
echo "Runtime dir: {script_dir}/test_runtime"
mkdir -p {script_dir}/test_runtime
echo $$ > {script_dir}/test_runtime/codex.pid
echo "✅ 测试脚本启动成功"
# 启动codex（但这里我们用sleep代替来避免实际启动）
sleep 3
echo "👋 测试结束"
'''

    # 写入测试脚本
    test_file = script_dir / "test_codex.sh"
    with open(test_file, 'w') as f:
        f.write(test_script)
    os.chmod(test_file, 0o755)

    try:
        # 测试gnome-terminal
        if subprocess.run(["which", "gnome-terminal"], capture_output=True).returncode == 0:
            print("🖥️ 测试gnome-terminal启动...")
            proc = subprocess.Popen([
                "gnome-terminal", "--title", "Test Codex",
                "--", str(test_file)
            ])

            # 等待脚本运行
            time.sleep(2)

            if proc.poll() is None:
                print("✅ gnome-terminal测试成功")
                proc.terminate()
                proc.wait(timeout=5)
                return True
            else:
                print("❌ gnome-terminal进程已退出")
                return False

        # 测试xterm作为备选
        elif subprocess.run(["which", "xterm"], capture_output=True).returncode == 0:
            print("🖥️ 测试xterm启动...")
            proc = subprocess.Popen([
                "xterm", "-title", "Test Codex",
                "-e", str(test_file)
            ])

            time.sleep(2)

            if proc.poll() is None:
                print("✅ xterm测试成功")
                proc.terminate()
                proc.wait(timeout=5)
                return True
            else:
                print("❌ xterm进程已退出")
                return False

        else:
            print("❌ 未找到可用的终端")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

    finally:
        # 清理测试文件
        try:
            test_file.unlink()
            test_runtime = script_dir / "test_runtime"
            if test_runtime.exists():
                test_runtime.rmdir()
        except:
            pass

def main():
    """主测试函数"""
    print("🔍 简化双窗口启动测试")
    print("=" * 40)

    success = test_codex_terminal_launch()

    print("\n" + "=" * 40)
    if success:
        print("🎉 终端启动测试通过！")
        print("💡 建议现在尝试完整启动:")
        print("   python3 claude-codex-dual")
    else:
        print("⚠️ 终端启动测试失败")
        print("💡 可能需要检查终端配置或使用tmux模式")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())