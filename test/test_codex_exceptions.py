#!/usr/bin/env python3
"""
Codex 异常场景测试脚本
测试未激活命令、非法参数、子进程崩溃模拟等异常情况
"""

import os
import sys
import time
import signal
import subprocess

def run_exception_tests():
    """运行异常场景测试"""
    print("🧪 开始 Codex 异常场景测试\n")

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
    from codex_commands import handle_codex_command, get_codex_manager

    # 验证导入是否成功
    try:
        # 验证 handle_codex_command
        test_func = getattr(handle_codex_command, '__call__', None)
        if test_func is None:
            raise ImportError("handle_codex_command 不是可调用对象")

        # 验证 get_codex_manager
        test_manager = get_codex_manager()
        if not hasattr(test_manager, 'codex_active'):
            raise ImportError("get_codex_manager 返回的对象不正确")

    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        print(f"仓库根目录: {repo_root}")
        print(f"Python路径: {sys.path[:3]}")
        raise

    test_results = []

    # 1. 测试未激活状态下的命令
    print("=== 1. 测试未激活状态下的命令 ===")

    # 确保服务未激活
    handle_codex_command('/codex-stop')
    time.sleep(0.5)

    commands_should_fail = [
        '/codex-ask 测试问题',
        '/codex-status',
        '/codex-config high',
        '/codex-reasoning on',
        '/codex-final_only off',
    ]

    for cmd in commands_should_fail:
        print(f"测试命令: {cmd}")
        result = handle_codex_command(cmd)
        if "❌" in result or "未激活" in result or "未运行" in result:
            print(f"✅ 正确拒绝: {result[:50]}...")
            test_results.append(True)
        else:
            print(f"❌ 应该拒绝但接受了: {result[:50]}...")
            test_results.append(False)

    # 2. 测试非法参数
    print("\n=== 2. 测试非法参数 ===")

    # 先启动服务
    handle_codex_command('/codex-start')
    time.sleep(0.5)

    invalid_params = [
        ('/codex-config invalid_profile', '无效的profile参数'),
        ('/codex-reasoning maybe', '无效的reasoning参数'),
        ('/codex-final_only maybe', '无效的final_only参数'),
        ('/codex-ask', '缺少问题参数'),
    ]

    for cmd, description in invalid_params:
        print(f"测试: {description}")
        try:
            result = handle_codex_command(cmd)
            if "❌" in result or "无效" in result or "参数错误" in result:
                print(f"✅ 正确拒绝非法参数")
                test_results.append(True)
            else:
                print(f"❌ 应该拒绝但接受了: {result[:50]}...")
                test_results.append(False)
        except Exception as e:
            print(f"✅ 正确抛出异常: {e}")
            test_results.append(True)

    # 3. 测试命令格式错误
    print("\n=== 3. 测试命令格式错误 ===")

    invalid_commands = [
        '/invalid-command',
        '/codex-unknown',
        '/codex-ask',  # 缺少参数
        'codex-ask test',  # 缺少前斜杠
        # '/codex-config',  # 这是有效命令（查看配置），移除
    ]

    for cmd in invalid_commands:
        print(f"测试无效命令: {cmd}")
        try:
            result = handle_codex_command(cmd)
            # 如果返回了错误信息，这是正确的
            if "❌" in result or "未知" in result or "无效" in result or "参数" in result:
                print(f"✅ 正确处理无效命令")
                test_results.append(True)
            else:
                print(f"⚠️ 意外接受无效命令: {result[:50]}...")
                test_results.append(False)
        except Exception as e:
            print(f"✅ 正确抛出异常: {e}")
            test_results.append(True)

    # 4. 测试子进程崩溃模拟
    print("\n=== 4. 测试子进程崩溃模拟 ===")

    # 启动服务
    result = handle_codex_command('/codex-start')
    print(f"启动服务: {result[:50]}...")

    # 进行一次问答确保服务正常
    result = handle_codex_command('/codex-ask 崩溃前测试')
    if "❌" not in result:
        print("✅ 服务启动正常")
        test_results.append(True)
    else:
        print("❌ 服务启动失败")
        test_results.append(False)

    # 获取当前codex进程PID并模拟崩溃
    from codex_commands import get_codex_manager
    manager = get_codex_manager()
    if manager.codex_active and manager.codex_pid:
        pid_to_kill = manager.codex_pid
        print(f"准备终止进程: {pid_to_kill}")

        try:
            # 发送SIGTERM信号模拟崩溃
            os.kill(pid_to_kill, signal.SIGTERM)
            print(f"✅ 已发送终止信号给进程 {pid_to_kill}")
            test_results.append(True)

            # 等待进程退出和自动重启（需要更长时间）
            print("等待自动重启...")
            time.sleep(3)  # 给监控线程足够时间检测并重启

            # 验证服务是否恢复
            status_result = handle_codex_command('/codex-status')
            if "运行中" in status_result:
                print("✅ 服务已自动重启")
                test_results.append(True)

                # 再次尝试使用服务
                result = handle_codex_command('/codex-ask 崩溃后测试')
                if "❌" not in result:
                    print("✅ 崩溃后自动恢复功能正常")
                    test_results.append(True)
                else:
                    print(f"⚠️ 重启后服务响应异常: {result[:50]}...")
                    test_results.append(False)
            else:
                print(f"❌ 服务未能自动重启: {status_result[:50]}...")
                test_results.append(False)
                test_results.append(False)  # 恢复测试也失败

        except ProcessLookupError:
            print("✅ 进程已经退出（符合预期）")
            test_results.append(True)
        except Exception as e:
            print(f"⚠️ 模拟崩溃时出现异常: {e}")
            test_results.append(False)
    else:
        print("⚠️ 无法获取codex进程PID，跳过崩溃测试")
        test_results.append(False)

    # 5. 测试并发请求
    print("\n=== 5. 测试并发请求 ===")

    import threading
    import queue

    results_queue = queue.Queue()

    def send_concurrent_request(question_id):
        try:
            result = handle_codex_command(f'/codex-ask 并发测试问题 {question_id}')
            results_queue.put((question_id, "❌" not in result))
        except Exception as e:
            results_queue.put((question_id, False, str(e)))

    # 启动多个并发请求
    threads = []
    for i in range(5):
        thread = threading.Thread(target=send_concurrent_request, args=(i,))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join(timeout=10)

    # 收集结果
    success_count = 0
    total_count = 0
    while not results_queue.empty():
        total_count += 1
        result = results_queue.get()
        if len(result) == 2:
            question_id, success = result
            if success:
                success_count += 1
                print(f"✅ 并发请求 {question_id} 成功")
            else:
                print(f"❌ 并发请求 {question_id} 失败")
        else:
            question_id, success, error = result
            print(f"❌ 并发请求 {question_id} 异常: {error}")

    if success_count >= 3:  # 至少一半成功
        print(f"✅ 并发测试通过 ({success_count}/{total_count})")
        test_results.append(True)
    else:
        print(f"❌ 并发测试失败 ({success_count}/{total_count})")
        test_results.append(False)

    # 6. 测试资源清理
    print("\n=== 6. 测试资源清理 ===")

    # 检查临时文件
    import glob
    temp_files = glob.glob('/tmp/codex-*.sock') + glob.glob('/tmp/codex-*history.json')
    print(f"发现临时文件: {len(temp_files)} 个")

    # 正常停止服务
    result = handle_codex_command('/codex-stop')
    if "已停止" in result:
        print("✅ 服务正常停止")
        test_results.append(True)
    else:
        print(f"❌ 服务停止异常: {result[:50]}...")
        test_results.append(False)

    # 清理测试文件
    cleaned_count = 0
    for temp_file in temp_files:
        try:
            if 'test' in temp_file or 'session' in temp_file:
                os.unlink(temp_file)
                cleaned_count += 1
        except:
            pass

    print(f"✅ 清理了 {cleaned_count} 个测试临时文件")

    # 总结测试结果
    passed = sum(test_results)
    total = len(test_results)

    print(f"\n📊 测试结果总结:")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")

    if passed >= total * 0.8:  # 80%通过率
        print("🎉 异常场景测试通过！")
        return True
    else:
        print("❌ 异常场景测试失败，需要改进错误处理")
        return False

def cleanup():
    """清理测试环境"""
    print("\n🧹 清理异常测试环境...")
    try:
        # 重新导入模块以确保能找到
        repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        sys.path.insert(0, repo_root)
        from codex_commands import handle_codex_command
        handle_codex_command('/codex-stop')

        # 清理测试相关的临时文件
        import glob
        temp_files = glob.glob('/tmp/codex-*test*.sock') + glob.glob('/tmp/codex-*test*.json')
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

        print("✅ 清理完成")
    except Exception as e:
        print(f"⚠️ 清理时出现异常: {e}")

if __name__ == "__main__":
    try:
        success = run_exception_tests()
        if success:
            print("\n✅ 异常测试总结：错误处理机制正常")
            sys.exit(0)
        else:
            print("\n❌ 异常测试总结：发现需要改进的错误处理")
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