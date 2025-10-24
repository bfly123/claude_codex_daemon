#!/usr/bin/env python3
import json
import os
import socket
import time
import signal


class CodexProcess:
    def __init__(self, socket_path, instance_id):
        self.socket_path = socket_path
        self.instance_id = instance_id
        self.conversation_history = []
        self.current_profile = "default"
        self.show_reasoning = False
        self.output_format = "final_only"
        self.running = True

        signal.signal(signal.SIGTERM, self._graceful_shutdown)

    def _graceful_shutdown(self, signum, frame):
        self._save_history()
        exit(0)

    def run(self):
        self._load_history_securely()

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(self.socket_path)
        sock.listen(1)
        os.chmod(self.socket_path, 0o600)

        while self.running:
            try:
                conn, addr = sock.accept()
                data = conn.recv(8192).decode()
                if data:
                    request = json.loads(data)
                    response = self.handle_request(request)
                    conn.send(json.dumps(response).encode())
                conn.close()
            except:
                break

        sock.close()

    def handle_request(self, request):
        try:
            validated = self._validate_schema(request)
        except ValueError as e:
            return {
                "instance_id": self.instance_id,
                "type": "error",
                "message": str(e),
                "status": "error",
                "error_code": "VALIDATION_ERROR"
            }

        req_type = validated["type"]
        if req_type == "config":
            return self._handle_config_request(validated)
        elif req_type == "query":
            return self._process_query(validated)
        elif req_type == "restore_history":
            return self._handle_restore_history(validated)
        else:
            return {
                "instance_id": self.instance_id,
                "type": "error",
                "message": f"未知请求类型: {req_type}",
                "status": "error",
                "error_code": "UNKNOWN_REQUEST_TYPE"
            }

    def _validate_schema(self, request):
        required_fields = ["instance_id", "type", "timestamp"]
        for field in required_fields:
            if field not in request:
                raise ValueError(f"缺少必需字段: {field}")

        if request["instance_id"] != self.instance_id:
            raise ValueError("实例ID不匹配")

        request.setdefault("config", {})
        config = request["config"]
        config.setdefault("profile", self.current_profile)
        config.setdefault("show_reasoning", self.show_reasoning)
        config.setdefault("output_format", self.output_format)

        if config["profile"] not in ["high", "low", "default"]:
            config["profile"] = self.current_profile

        return request

    def _handle_config_request(self, request):
        action = request.get("action")
        if action == "set_profile":
            profile = request.get("profile", "default")
            if profile in ["high", "low", "default"]:
                old = self.current_profile
                self.current_profile = profile
                self._log_config_change("profile", old, profile)
                return {
                    "instance_id": self.instance_id,
                    "type": "config_response",
                    "action": action,
                    "profile": profile,
                    "status": "success",
                    "message": f"Profile已更新为{profile}"
                }
            return {
                "instance_id": self.instance_id,
                "type": "error",
                "message": f"无效的profile: {profile}",
                "status": "error",
                "error_code": "INVALID_PROFILE"
            }
        elif action == "set_reasoning":
            new_state = bool(request.get("show_reasoning", False))
            old = self.show_reasoning
            self.show_reasoning = new_state
            self._log_config_change("show_reasoning", old, new_state)
            return {
                "instance_id": self.instance_id,
                "type": "config_response",
                "action": action,
                "show_reasoning": new_state,
                "status": "success",
                "message": f"Show Reasoning 已{'开启' if new_state else '关闭'}"
            }
        elif action == "set_output_format":
            new_format = request.get("output_format", "final_only")
            if new_format not in ["final_only", "final_with_details"]:
                return {
                    "instance_id": self.instance_id,
                    "type": "error",
                    "message": f"无效的输出格式: {new_format}",
                    "status": "error",
                    "error_code": "INVALID_OUTPUT_FORMAT"
                }
            old = self.output_format
            self.output_format = new_format
            self._log_config_change("output_format", old, new_format)
            return {
                "instance_id": self.instance_id,
                "type": "config_response",
                "action": action,
                "output_format": new_format,
                "status": "success",
                "message": f"Output Format 已切换为 {new_format}"
            }
        return {
            "instance_id": self.instance_id,
            "type": "error",
            "message": f"未知配置操作: {action}",
            "status": "error",
            "error_code": "UNKNOWN_CONFIG_ACTION"
        }

    def _process_query(self, request):
        config = request["config"]
        profile = config.get("profile", self.current_profile)
        params = self._get_model_params_for_profile(profile)

        self.conversation_history.append({
            "role": "user",
            "content": request["message"],
            "timestamp": request["timestamp"],
            "profile": profile
        })

        response_text = self._call_codex_with_params(request["message"], params)

        self.conversation_history.append({
            "role": "assistant",
            "content": response_text,
            "timestamp": int(time.time()),
            "profile": profile
        })

        if len(self.conversation_history) > 200:
            self.conversation_history = self.conversation_history[-200:]

        return {
            "instance_id": self.instance_id,
            "type": "response",
            "message": response_text,
            "status": "success",
            "metadata": {
                "context_length": len(self.conversation_history),
                "active_profile": profile,
                "show_reasoning": self.show_reasoning,
                "output_format": self.output_format
            }
        }

    def _handle_restore_history(self, request):
        history = request.get("history", [])
        self.conversation_history = history

        profile = request.get("profile", self.current_profile)
        if profile in ["high", "low", "default"]:
            self.current_profile = profile

        self.show_reasoning = bool(request.get("show_reasoning", self.show_reasoning))
        output_format = request.get("output_format", self.output_format)
        if output_format in ["final_only", "final_with_details"]:
            self.output_format = output_format

        return {
            "instance_id": self.instance_id,
            "type": "restore_response",
            "message": f"已恢复 {len(history)} 条历史，当前profile: {self.current_profile}",
            "status": "success"
        }

    def _log_config_change(self, config_type, old, new):
        print(f"[Codex Config] {config_type}: {old} -> {new}")

    def _get_model_params_for_profile(self, profile):
        mapping = {
            "high": {"temperature": 0.1, "max_tokens": 4000, "top_p": 0.95},
            "low": {"temperature": 0.3, "max_tokens": 1000, "top_p": 0.9},
            "default": {"temperature": 0.2, "max_tokens": 2000, "top_p": 0.92}
        }
        return mapping.get(profile, mapping["default"])

    def _call_codex_with_params(self, message, params):
        depth = params.get("max_tokens", 2000)
        return f"模拟回答({depth} tokens): {message}"

    def _save_history(self):
        history_file = self.socket_path.replace('.sock', '-history.json')
        data = {
            "instance_id": self.instance_id,
            "conversation_history": self.conversation_history,
            "current_profile": self.current_profile,
            "show_reasoning": self.show_reasoning,
            "output_format": self.output_format,
            "saved_at": int(time.time())
        }
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)
        os.chmod(history_file, 0o600)

    def _load_history_securely(self):
        history_file = self.socket_path.replace('.sock', '-history.json')
        if not os.path.exists(history_file):
            return

        file_stat = os.stat(history_file)
        if file_stat.st_uid != os.getuid():
            print("警告：历史文件所有者不正确，跳过加载")
            return

        if file_stat.st_mode & 0o077 != 0:
            print("警告：历史文件权限过于开放，跳过加载")
            return

        try:
            with open(history_file, 'r') as f:
                data = json.load(f)

            if data.get("instance_id") == self.instance_id:
                self.conversation_history = data.get("conversation_history", [])

                profile = data.get("current_profile", "default")
                if profile in ["high", "low", "default"]:
                    self.current_profile = profile

                self.show_reasoning = bool(data.get("show_reasoning", False))
                output_format = data.get("output_format", "final_only")
                if output_format in ["final_only", "final_with_details"]:
                    self.output_format = output_format

                print(f"已恢复profile: {self.current_profile}")
            else:
                print("警告：历史文件instance_id不匹配，跳过加载")
        except Exception as e:
            print(f"警告：加载历史文件失败: {e}")


if __name__ == "__main__":
    if len(os.sys.argv) != 2:
        os.sys.exit(1)

    socket_path = os.sys.argv[1]
    instance_id = socket_path.split('/')[-1].replace('.sock', '').split('-')[-1]

    codex = CodexProcess(socket_path, instance_id)
    codex.run()