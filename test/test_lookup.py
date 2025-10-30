#!/usr/bin/env python3
"""测试从test目录查找父目录的会话"""

import sys
sys.path.insert(0, '/home/bfly/.local/share/codex-dual')

from pathlib import Path

print(f"当前目录: {Path.cwd()}")
print(f"父目录: {Path.cwd().parent}")

# 测试查找逻辑
current = Path.cwd()
found_sessions = []

for parent in [current] + list(current.parents):
    project_session = parent / ".codex-session"
    if project_session.exists():
        print(f"✅ 找到会话文件: {project_session}")
        try:
            import json
            with open(project_session, "r", encoding="utf-8") as f:
                data = json.load(f)

            active = data.get("active", False)
            runtime_dir = Path(data.get("runtime_dir", ""))
            runtime_exists = runtime_dir.exists()

            print(f"   Active: {active}")
            print(f"   Runtime Dir: {runtime_dir}")
            print(f"   Runtime Exists: {runtime_exists}")

            if active and runtime_exists:
                print(f"   ✅ 有效会话!")
                found_sessions.append(str(project_session))
            else:
                print(f"   ❌ 无效会话")

        except Exception as e:
            print(f"   ❌ 读取失败: {e}")
    else:
        print(f"   ❌ 无会话文件")

print(f"\n找到有效会话: {len(found_sessions)}")
for session in found_sessions:
    print(f"  - {session}")