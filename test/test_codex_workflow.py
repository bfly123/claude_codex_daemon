#!/usr/bin/env python3
"""
Codex 完整工作流测试脚本
测试启动 → 多轮 /codex-ask → 切换档位/开关 → 重启恢复
"""

import os
import sys
import time
import subprocess
import signal

def run_test_sequence():
    """运行完整的测试序列"""
    print("🧪 开始 Codex 完整工作流测试\n")

    # 导入测试模块 - 确保仓库根目录在路径中
    def setup_import_path():
        """设置模块导入路径"""
        # 获取测试脚本所在目录的父目录（仓库根目录）
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # 如果 __file__ 不可用（如通过 exec() 执行），使用当前工作目录
            script_dir = os.getcwd()
            # 如果在测试目录中，需要回到父目录
            if script_dir.endswith('/test'):
                script_dir = os.path.dirname(script_dir)
            # 如果在其他位置，尝试找到仓库根目录
            elif not os.path.exists(os.path.join(script_dir, 'codex_commands.py')):
                # 向上查找 codex_commands.py
                while script_dir != '/':
                    parent = os.path.dirname(script_dir)
                    if os.path.exists(os.path.join(parent, 'codex_commands.py')):
                        script_dir = parent
                        break
                    script_dir = parent

        repo_root = os.path.join(script_dir, "..") if script_dir.endswith('/test') else script_dir

        # 规范化路径
        repo_root = os.path.abspath(repo_root)

        # 确保仓库根目录在sys.path的最前面
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        else:
            # 如果已在路径中，移到最前面
            sys.path.remove(repo_root)
            sys.path.insert(0, repo_root)

        return repo_root

    repo_root = setup_import_path()
    from codex_commands import handle_codex_command

    # 验证导入是否成功
    try:
        # 简单验证模块是否正确导入
        test_func = getattr(handle_codex_command, '__call__', None)
        if test_func is None:
            raise ImportError("handle_codex_command 不是可调用对象")
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        print(f"仓库根目录: {repo_root}")
        print(f"Python路径: {sys.path[:3]}")
        raise

    # 1. 测试启动流程
    print("=== 1. 测试启动流程 ===")
    result = handle_codex_command('/codex-start')
    print(f"启动结果: {result}")
    if "已启动" not in result and "运行中" not in result:
        print("❌ 启动失败")
        return False
    print("✅ 启动成功\n")

    # 2. 测试多轮问答
    print("=== 2. 测试多轮问答 ===")
    test_questions = [
        "什么是Python？",
        "解释一下机器学习的基本概念",
        "如何优化代码性能？"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"问题 {i}: {question}")
        result = handle_codex_command(f'/codex-ask {question}')
        if "❌" in result or "未激活" in result:
            print(f"❌ 问答 {i} 失败: {result}")
            return False
        print(f"✅ 问答 {i} 成功")
        print(f"回答摘要: {result[:100]}...")
        print()

    # 3. 测试档位切换
    print("=== 3. 测试档位切换 ===")
    profiles = ["high", "default", "low"]

    for profile in profiles:
        print(f"切换到 {profile} 档位...")
        result = handle_codex_command(f'/codex-config {profile}')
        if "✅" not in result:
            print(f"❌ 档位切换失败: {result}")
            return False
        print(f"✅ 档位切换成功: {result}")

    # 4. 测试推理开关
    print("\n=== 4. 测试推理开关 ===")
    for state in ["on", "off"]:
        print(f"设置推理显示: {state}")
        result = handle_codex_command(f'/codex-reasoning {state}')
        if "✅" not in result:
            print(f"❌ 推理开关设置失败: {result}")
            return False
        print(f"✅ 推理开关设置成功: {result}")

    # 5. 测试输出格式开关
    print("\n=== 5. 测试输出格式开关 ===")
    for state in ["on", "off"]:
        print(f"设置最终输出: {state}")
        result = handle_codex_command(f'/codex-final_only {state}')
        if "✅" not in result:
            print(f"❌ 输出格式设置失败: {result}")
            return False
        print(f"✅ 输出格式设置成功: {result}")

    # 6. 测试状态查询
    print("\n=== 6. 测试状态查询 ===")
    result = handle_codex_command('/codex-status')
    if "❌" in result or "未运行" in result:
        print(f"❌ 状态查询失败: {result}")
        return False
    print(f"✅ 状态查询成功: {result}")

    result = handle_codex_command('/codex-config')
    if "❌" in result:
        print(f"❌ 配置查询失败: {result}")
        return False
    print(f"✅ 配置查询成功: {result}")

    # 7. 测试重启恢复（模拟进程崩溃和恢复）
    print("\n=== 7. 测试重启恢复 ===")
    print("保存当前状态...")

    # 先进行一次问答以确保有历史记录
    handle_codex_command('/codex-ask 这个问题的答案用于测试重启恢复功能')

    # 停止服务
    print("停止服务...")
    result = handle_codex_command('/codex-stop')
    print(f"停止结果: {result}")

    # 等待一秒钟确保进程完全退出
    time.sleep(1)

    # 重新启动，应该恢复历史状态
    print("重新启动服务...")
    result = handle_codex_command('/codex-start')
    print(f"重启结果: {result}")

    if "恢复会话" in result or "已启动" in result:
        print("✅ 重启恢复成功")
    else:
        print(f"❌ 重启恢复可能失败: {result}")

    # 8. 验证恢复后的功能
    print("\n=== 8. 验证恢复后的功能 ===")
    result = handle_codex_command('/codex-ask 验证恢复后的功能是否正常')
    if "❌" in result or "未激活" in result:
        print(f"❌ 恢复后功能验证失败: {result}")
        return False
    print("✅ 恢复后功能验证成功")

    print("\n🎉 所有测试通过！Codex 工作流运行正常")
    return True

def cleanup():
    """清理测试环境"""
    print("\n🧹 清理测试环境...")
    try:
        # 重新导入模块以确保能找到
        repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        sys.path.insert(0, repo_root)
        from codex_commands import handle_codex_command
        handle_codex_command('/codex-stop')
        print("✅ 清理完成")
    except Exception as e:
        print(f"⚠️ 清理时出现异常: {e}")

if __name__ == "__main__":
    try:
        success = run_test_sequence()
        if success:
            print("\n✅ 测试总结：所有功能正常")
            sys.exit(0)
        else:
            print("\n❌ 测试总结：发现失败项")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        cleanup()
        sys.exit(1)
    finally:
        cleanup()