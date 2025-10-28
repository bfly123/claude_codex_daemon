#!/usr/bin/env python3
"""
Codex历史记录查看器
读取和显示Claude与Codex的对话历史
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

class CodexHistory:
    def __init__(self):
        self.session_info = self._load_session_info()
        if not self.session_info:
            raise RuntimeError("❌ 未找到活跃的Codex会话")

        self.runtime_dir = Path(self.session_info["runtime_dir"])
        self.history_file = self.runtime_dir / "history" / "session.jsonl"

    def _load_session_info(self):
        """加载会话信息"""
        # 优先从环境变量读取
        if "CODEX_SESSION_ID" in os.environ:
            info = {
                "session_id": os.environ["CODEX_SESSION_ID"],
                "runtime_dir": os.environ["CODEX_RUNTIME_DIR"],
                "input_fifo": os.environ["CODEX_INPUT_FIFO"],
                "output_fifo": os.environ["CODEX_OUTPUT_FIFO"]
            }
            daemon_socket = os.environ.get("CODEX_DAEMON_SOCKET")
            if daemon_socket:
                info["daemon_socket"] = daemon_socket
            client_id = os.environ.get("CODEX_CLIENT_ID")
            if client_id:
                info["client_id"] = client_id
            tmux_session = os.environ.get("CODEX_TMUX_SESSION")
            if tmux_session:
                info["tmux_session"] = tmux_session
            tmux_log = os.environ.get("CODEX_TMUX_LOG")
            if tmux_log:
                info["tmux_log"] = tmux_log
            return info

        # 从项目目录读取
        project_session = Path.cwd() / ".codex-session"
        if project_session.exists():
            try:
                with open(project_session, 'r') as f:
                    return json.load(f)
            except Exception:
                return None

        return None

    def load_history(self, limit=10):
        """加载历史记录"""
        try:
            if not self.history_file.exists():
                return []

            messages = []
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            messages.append(msg)
                        except json.JSONDecodeError:
                            continue

            # 返回最近的limit条记录
            return messages[-limit:] if messages else []

        except Exception as e:
            print(f"❌ 读取历史记录失败: {e}")
            return []

    def format_message(self, msg):
        """格式化消息显示"""
        try:
            timestamp = msg.get('timestamp', '')
            content = msg.get('content', '')
            role = msg.get('role', 'unknown')

            # 解析时间戳
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp[:8]  # 简单截取
            else:
                time_str = '???:???'

            # 确定角色图标
            if role == 'user' or 'claude' in str(content).lower():
                icon = '👤 Claude'
            elif role == 'assistant' or 'codex' in str(content).lower():
                icon = '🤖 Codex'
            else:
                icon = '📝 系统'

            return f"[{time_str}] {icon}: {content}"

        except Exception:
            return f"❌ 消息格式错误: {msg}"

    def show_history(self, limit=10):
        """显示历史记录"""
        messages = self.load_history(limit)

        if not messages:
            print("📝 暂无对话历史记录")
            return

        print(f"📝 对话历史 (最近{len(messages)}条):")
        print("-" * 50)

        for msg in messages:
            formatted = self.format_message(msg)
            print(formatted)

def main():
    parser = argparse.ArgumentParser(description="查看Codex对话历史")
    parser.add_argument("count", nargs="?", type=int, default=10, help="显示记录数量")

    args = parser.parse_args()

    try:
        history = CodexHistory()
        history.show_history(args.count)
        return 0

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
