#!/usr/bin/env python3
import re
from claude_codex_manager import ClaudeCodexManager


class CodexCommandHandler:
    def __init__(self):
        self.codex_manager = ClaudeCodexManager()
        self.codex_active = self.codex_manager.codex_active

    def _validate_command_parameters(self, cmd_type, command):
        """验证命令参数，返回错误信息或None"""
        parts = command.split()

        if cmd_type == "/codex-config":
            if len(parts) > 2:
                return """❌ 参数错误
用法:
• /codex-config            # 查看当前配置
• /codex-config <high|default|low>  # 切换模型强度"""
            elif len(parts) == 2:
                target_profile = parts[1].lower()
                if target_profile not in {"high", "default", "low", "medium", "mid", "normal", "balanced"}:
                    return "❌ 无效参数，请使用: high、default、low"

        elif cmd_type == "/codex-reasoning":
            if len(parts) != 2:
                return """❌ 参数错误
用法: /codex-reasoning <on|off>
• on: 在Claude中展示推理摘要（可能暴露细节）
• off: 仅展示最终答案（推荐）"""
            elif parts[1] not in ["on", "off"]:
                return "❌ 参数错误，使用 on 或 off"

        elif cmd_type == "/codex-final_only":
            if len(parts) != 2:
                return """❌ 参数错误
用法: /codex-final_only <on|off>
• on: 仅返回最终答案（推荐）
• off: 返回最终答案及额外细节（用于调试）"""
            elif parts[1] not in ["on", "off"]:
                return "❌ 参数错误，使用 on 或 off"

        elif cmd_type == "/codex-ask":
            if len(parts) == 1:
                return "❌ 请提供要询问的问题，用法: /codex-ask <你的问题>"

        return None  # 参数验证通过

    def handle_command(self, command):
        """统一命令处理入口"""
        command = command.strip()
        if not command.startswith("/codex-"):
            return None

        # 提取命令类型
        parts = command.split()
        cmd_type = parts[0]

        # 无需激活状态的命令
        no_activation_commands = {"/codex-start", "/codex-help"}
        # 需要激活状态的命令
        activation_required_commands = {"/codex-ask", "/codex-status", "/codex-stop"}

        # 首先检查需要激活状态的命令
        if cmd_type in activation_required_commands and not self.codex_manager.codex_active:
            return "❌ Codex服务未激活，请先运行 /codex-start 或输入 /codex-help 查看指引"

        # 对于配置相关命令，先进行参数验证（无需激活状态）
        if cmd_type in {"/codex-config", "/codex-reasoning", "/codex-final_only"}:
            validation_result = self._validate_command_parameters(cmd_type, command)
            if validation_result:
                return validation_result

            # 配置命令在参数验证通过后，检查是否需要激活
            if not self.codex_manager.codex_active:
                return "❌ Codex服务未激活，请先运行 /codex-start 或输入 /codex-help 查看指引"

        # 命令路由
        if cmd_type == "/codex-start":
            return self._handle_start()
        elif cmd_type == "/codex-ask":
            return self._handle_ask(command)
        elif cmd_type == "/codex-stop":
            return self._handle_stop()
        elif cmd_type == "/codex-status":
            return self._handle_status()
        elif cmd_type == "/codex-config":
            return self._handle_config(parts)
        elif cmd_type == "/codex-reasoning":
            return self._handle_reasoning(parts)
        elif cmd_type == "/codex-final_only":
            return self._handle_final_only(parts)
        elif cmd_type == "/codex-help":
            return self._handle_help()
        else:
            return f"❌ 未知命令: {cmd_type}"

    def _handle_start(self):
        """处理启动命令"""
        if not self.codex_manager.codex_active:
            try:
                self.codex_manager.auto_activate_on_first_use()
                self.codex_active = True
                return f"✅ Codex服务已启动 (实例ID: {self.codex_manager.instance_id}, 默认Profile: {self.codex_manager.current_profile})"
            except Exception as e:
                return f"❌ 启动失败: {str(e)}"
        else:
            self.codex_active = True
            return f"ℹ️ Codex服务已在运行 (Profile: {self.codex_manager.current_profile})"

    def _handle_ask(self, command):
        """处理询问命令"""
        if command == "/codex-ask":
            return "❌ 请提供要询问的问题，用法: /codex-ask <你的问题>"

        question = command.replace("/codex-ask ", "").strip()
        if not question:
            return "❌ 问题内容不能为空"

        try:
            response = self.codex_manager.send_to_codex(question)
            metadata = response.get("metadata", {})
            profile = metadata.get("active_profile", "default")
            return f"🤖 [Profile: {profile}]\n{response['message']}"
        except Exception as e:
            return f"❌ 请求失败: {str(e)}"

    def _handle_stop(self):
        """处理停止命令"""
        if self.codex_manager.codex_active:
            instance_id = self.codex_manager.instance_id
            self.codex_manager.claude_cleanup_on_exit()
            self.codex_active = False
            return f"✅ Codex服务已停止 (实例ID: {instance_id})"
        else:
            self.codex_active = False
            return "ℹ️ Codex服务未运行"

    def _handle_status(self):
        """处理状态查询命令"""
        return self.codex_manager.show_status()

    def _handle_config(self, parts):
        """处理配置命令"""
        if len(parts) == 1:
            return self.codex_manager.show_config()

        if len(parts) != 2:
            return """❌ 参数错误
用法:
• /codex-config            # 查看当前配置
• /codex-config <high|default|low>  # 切换模型强度"""

        target_profile = parts[1].lower()
        aliases = {
            "high": "high",
            "default": "default",
            "low": "low",
            "medium": "default",
            "mid": "default",
            "normal": "default",
            "balanced": "default",
        }

        if target_profile not in aliases:
            return "❌ 无效参数，请使用: high、default、low"

        resolved = aliases[target_profile]
        return self.codex_manager.set_profile(resolved)

    def _handle_reasoning(self, parts):
        """处理推理开关命令"""
        if len(parts) != 2:
            return """❌ 参数错误
用法: /codex-reasoning <on|off>
• on: 在Claude中展示推理摘要（可能暴露细节）
• off: 仅展示最终答案（推荐）"""

        state_token = parts[1]
        if state_token not in ["on", "off"]:
            return "❌ 参数错误，使用 on 或 off"

        result = self.codex_manager.update_show_reasoning(state_token)
        advice = "（建议关闭以保持输出纯净）" if state_token == "off" else "（建议开启以获取推理过程）"
        return f"{result} {advice}"

    def _handle_final_only(self, parts):
        """处理输出格式命令"""
        if len(parts) != 2:
            return """❌ 参数错误
用法: /codex-final_only <on|off>
• on: 仅返回最终答案（推荐）
• off: 返回最终答案及额外细节（用于调试）"""

        state_token = parts[1]
        if state_token not in ["on", "off"]:
            return "❌ 参数错误，使用 on 或 off"

        result = self.codex_manager.update_output_format(state_token)
        advice = "（推荐开启以避免额外噪音）" if state_token == "on" else "（将返回额外细节信息）"
        return f"{result} {advice}"

    def _handle_help(self):
        """处理帮助命令"""
        return (
            "📖 Codex命令帮助（Claude内置）\n"
            "• /codex-start\n"
            "  - 说明: 启动或重新连接Codex进程，自动生成专属socket和实例ID\n"
            "  - 使用: 首次对话前执行一次即可，如已运行会返回当前档位\n"
            "• /codex-ask <问题>\n"
            "  - 说明: 向当前Codex实例发起提问，自动携带当前模型强度/输出配置\n"
            "  - 使用: `/codex-ask 解释一下数据库分片`\n"
            "• /codex-config [high|default|low]\n"
            "  - 说明: 不带参数查看档位和开关；附带参数可切换模型强度\n"
            "  - 建议: 详细模式用 high，快速问答用 low，default 保持平衡\n"
            "• /codex-reasoning <on|off>\n"
            "  - 说明: 控制是否在Claude侧展示推理摘要，on 仅影响展示不影响真实推理\n"
            "  - 建议: 默认为 off 以保持回答纯净，除非调试需要\n"
            "• /codex-final_only <on|off>\n"
            "  - 说明: on 时仅返回最终答案；off 时附带额外细节或中间说明\n"
            "  - 建议: 生产使用保持 on，调试场景可临时关闭\n"
            "• /codex-status\n"
            "  - 说明: 查看实例ID、当前profile、推理/输出开关、进程PID等运行信息\n"
            "• /codex-stop\n"
            "  - 说明: 手动停止当前Codex子进程并清理socket，Claude退出时会自动调用\n"
            "• /codex-help\n"
            "  - 说明: 显示本帮助信息\n"
            "\n"
            "⚙️ 维护建议:\n"
            "1. 需要撤回最近一轮或清理上下文时，可结合 Claude 的 /rewind 或 /clear。\n"
            "2. 切换档位后如遇回答异常，优先执行 `/codex-config` 查看当前状态。\n"
            "3. 若长时间未用，建议 `/codex-stop` 后再 `/codex-start` 以释放资源。"
        )


# 全局命令处理器实例
command_handler = CodexCommandHandler()


def handle_codex_command(command):
    """对外接口：处理Codex相关命令"""
    return command_handler.handle_command(command)


def get_codex_manager():
    """获取全局的 Codex 管理器实例（用于测试和调试）"""
    return command_handler.codex_manager