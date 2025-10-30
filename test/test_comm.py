#!/usr/bin/env python3
"""测试从子目录发送消息到 Codex"""

import sys
from pathlib import Path

sys.path.insert(0, '/home/bfly/.local/share/codex-dual')

print("=" * 50)
print("测试从子目录发送消息")
print("=" * 50)
print(f"当前目录: {Path.cwd()}")
print(f"父目录: {Path.cwd().parent}")

try:
    from codex_comm import CodexCommunicator

    print("\n1. 尝试加载会话...")
    comm = CodexCommunicator()
    print(f"✅ 会话加载成功")
    print(f"   Session ID: {comm.session_id}")
    print(f"   Runtime Dir: {comm.runtime_dir}")
    print(f"   Input FIFO: {comm.input_fifo}")

    print("\n2. 检查会话健康状态...")
    healthy, msg = comm._check_session_health()
    if healthy:
        print(f"✅ {msg}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)

    print("\n3. 测试发送消息（异步）...")
    result = comm.ask_async("测试消息：1+1")
    print(f"✅ 发送成功: {result}")

    print("\n✅ 所有测试通过！")

except Exception as e:
    import traceback
    print(f"\n❌ 测试失败: {e}")
    traceback.print_exc()
    sys.exit(1)
