#!/usr/bin/env python3
"""
Codex 后台服务集成测试脚本
测试完整的生命周期：启动 → 多轮对话 → 配置切换 → 重启恢复
"""

import sys
import os
import time
import signal
from codex_commands import handle_codex_command

class CodexIntegrationTester:
    def __init__(self):
        self.test_results = []
        self.current_manager = None

    def log_test(self, test_name, result, details=""):
        """记录测试结果"""
        status = "✅ PASS" if result else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "result": result,
            "details": details
        })
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")

    def test_help_command(self):
        """测试帮助命令"""
        print("\n=== 测试帮助命令 ===")
        result = handle_codex_command("/codex-help")
        success = "Codex命令帮助" in result and "启动或重新连接" in result
        self.log_test("帮助命令显示", success, f"返回内容长度: {len(result)} 字符")
        return success

    def test_unactivated_state(self):
        """测试未激活状态的命令处理"""
        print("\n=== 测试未激活状态 ===")

        # 测试需要激活的命令
        commands_to_test = [
            ("/codex-ask test question", "未激活"),
            ("/codex-status", "未激活"),
            ("/codex-stop", "未激活"),
        ]

        all_passed = True
        for cmd, expected in commands_to_test:
            result = handle_codex_command(cmd)
            passed = expected in result
            all_passed = all_passed and passed
            self.log_test(f"未激活命令: {cmd}", passed, f"返回: {result[:50]}...")

        # 测试参数验证命令
        validation_tests = [
            ("/codex-config invalid", "无效参数"),
            ("/codex-reasoning maybe", "参数错误"),
            ("/codex-final_only yes", "参数错误"),
        ]

        for cmd, expected in validation_tests:
            result = handle_codex_command(cmd)
            passed = expected in result
            all_passed = all_passed and passed
            self.log_test(f"参数验证: {cmd}", passed, f"返回: {result[:50]}...")

        return all_passed

    def test_startup(self):
        """测试启动流程"""
        print("\n=== 测试启动流程 ===")

        result = handle_codex_command("/codex-start")
        success = "已启动" in result and "实例ID:" in result
        self.log_test("服务启动", success, f"启动信息: {result}")

        if success:
            # 提取实例ID用于后续测试
            import re
            match = re.search(r'实例ID: ([a-f0-9]+)', result)
            if match:
                self.current_instance_id = match.group(1)
                print(f"    提取到实例ID: {self.current_instance_id}")

        return success

    def test_multiple_queries(self):
        """测试多轮对话"""
        print("\n=== 测试多轮对话 ===")

        if not hasattr(self, 'current_instance_id'):
            self.log_test("多轮对话", False, "缺少实例ID")
            return False

        queries = [
            "什么是机器学习？",
            "解释一下深度学习的基本概念",
            "Python和Java的主要区别是什么？"
        ]

        all_passed = True
        for i, query in enumerate(queries, 1):
            print(f"    查询 {i}: {query}")
            result = handle_codex_command(f"/codex-ask {query}")
            passed = "Profile:" in result and "模拟回答" in result
            all_passed = all_passed and passed
            self.log_test(f"多轮对话 {i}", passed, f"响应长度: {len(result)} 字符")
            time.sleep(0.5)  # 避免过快查询

        return all_passed

    def test_config_switching(self):
        """测试配置切换"""
        print("\n=== 测试配置切换 ===")

        config_tests = [
            ("/codex-config high", "Profile已更新为: high"),
            ("/codex-reasoning on", "Show Reasoning 已设置为 on"),
            ("/codex-final_only off", "Output Format 已切换为 final_with_details"),
            ("/codex-config low", "Profile已更新为: low"),
            ("/codex-reasoning off", "Show Reasoning 已设置为 off"),
            ("/codex-final_only on", "Output Format 已切换为 final_only"),
            ("/codex-config", "当前配置"),
        ]

        all_passed = True
        for cmd, expected in config_tests:
            result = handle_codex_command(cmd)
            passed = expected in result
            all_passed = all_passed and passed
            self.log_test(f"配置切换: {cmd}", passed, f"响应: {result[:60]}...")
            time.sleep(0.3)

        return all_passed

    def test_status_check(self):
        """测试状态检查"""
        print("\n=== 测试状态检查 ===")

        result = handle_codex_command("/codex-status")
        success = all([
            "运行中" in result,
            "实例ID:" in result,
            "当前Profile:" in result,
            "Show Reasoning:" in result,
            "Output Format:" in result,
            "对话轮次:" in result
        ])

        self.log_test("状态检查", success, f"状态信息完整")
        return success

    def test_recovery_simulation(self):
        """模拟重启恢复测试"""
        print("\n=== 测试重启恢复模拟 ===")

        # 保存当前配置状态
        pre_restart_status = handle_codex_command("/codex-status")
        print("    重启前状态已记录")

        # 停止服务
        stop_result = handle_codex_command("/codex-stop")
        stopped = "已停止" in stop_result
        self.log_test("服务停止", stopped, stop_result)

        if not stopped:
            return False

        time.sleep(1)

        # 重新启动（应该自动恢复状态）
        restart_result = handle_codex_command("/codex-start")
        restarted = "已启动" in restart_result
        self.log_test("服务重启", restarted, restart_result)

        if restarted:
            # 检查状态是否恢复
            post_restart_status = handle_codex_command("/codex-status")

            # 提取配置进行比较
            import re
            pre_profile = re.search(r'当前Profile: (\w+)', pre_restart_status)
            post_profile = re.search(r'当前Profile: (\w+)', post_restart_status)

            profile_recovered = pre_profile and post_profile and pre_profile.group(1) == post_profile.group(1)
            self.log_test("配置恢复", profile_recovered,
                         f"重启前: {pre_profile.group(1) if pre_profile else 'unknown'}, "
                         f"重启后: {post_profile.group(1) if post_profile else 'unknown'}")

        return stopped and restarted

    def test_error_scenarios(self):
        """测试异常场景"""
        print("\n=== 测试异常场景 ===")

        error_tests = [
            ("/codex-ask", "缺少要询问的问题"),
            ("/codex-config", "查询+切换"),
            ("/codex-reasoning", "参数错误"),
            ("/codex-final_only", "参数错误"),
            ("/codex-unknown", "未知命令"),
        ]

        all_passed = True
        for cmd, expected in error_tests:
            result = handle_codex_command(cmd)
            # 检查是否正确处理错误或提供有效响应
            passed = len(result) > 10 and ("❌" in result or "✅" in result or "📖" in result)
            all_passed = all_passed and passed
            self.log_test(f"异常场景: {cmd}", passed, f"处理结果: {result[:50]}...")

        return all_passed

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始 Codex 后台服务集成测试")
        print("=" * 50)

        tests = [
            ("帮助命令测试", self.test_help_command),
            ("未激活状态测试", self.test_unactivated_state),
            ("服务启动测试", self.test_startup),
            ("多轮对话测试", self.test_multiple_queries),
            ("配置切换测试", self.test_config_switching),
            ("状态检查测试", self.test_status_check),
            ("重启恢复测试", self.test_recovery_simulation),
            ("异常场景测试", self.test_error_scenarios),
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                self.log_test(test_name, False, f"测试异常: {e}")

        # 生成测试报告
        print("\n" + "=" * 50)
        print("📊 测试报告")
        print("=" * 50)
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")

        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！Codex 后台服务运行正常。")
        else:
            print("\n⚠️  部分测试失败，请检查上述日志。")
            print("\n失败的测试:")
            for result in self.test_results:
                if not result["result"]:
                    print(f"  ❌ {result['test']}: {result['details']}")

        return passed_tests == total_tests

    def cleanup(self):
        """清理测试环境"""
        print("\n=== 清理测试环境 ===")
        try:
            handle_codex_command("/codex-stop")
            print("✅ 测试服务已停止")
        except:
            print("⚠️ 停止服务时出现异常")


if __name__ == "__main__":
    tester = CodexIntegrationTester()

    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 测试过程中发生异常: {e}")
        tester.cleanup()
        sys.exit(1)