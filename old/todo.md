## Codex 后台服务落地任务

> 目标：按照最新《方案.md》实现并验证一套稳定的 Codex 子进程后台服务。所有子任务控制在单轮 <30K tokens 内可完成。

### 1. 核心代码同步（每项 ~6K tokens）
- [ ] 清理旧版 `ClaudeCodexManager`/`CodexProcess` 片段，仅保留方案最终骨架。
- [ ] 实现 `ClaudeCodexManager.auto_activate_on_first_use`、`send_to_codex`、子进程监控/重启逻辑。
- [ ] 落地 `_generate_instance_id`、`_generate_secure_socket_path`、`_setup_socket_permissions` 等辅助方法。
- [ ] 确保 `send_to_codex` 请求动态携带 `profile/show_reasoning/output_format`。

### 2. 子进程配置管线（每项 ~6K tokens）
- [ ] 在 `CodexProcess` 中统一处理 `set_profile`、`set_reasoning`、`set_output_format`。
- [ ] 更新响应 `metadata`，返回最新 `active_profile/show_reasoning/output_format`。
- [ ] 整理 `_call_codex_with_params` / `_get_model_params_for_profile`，保持查询路径一致。

### 3. 状态持久化与恢复（每项 ~5K tokens）
- [ ] 历史文件写入 `conversation_history/current_profile/show_reasoning/output_format/saved_at`。
- [ ] `_load_history_securely` 恢复上述字段并执行权限/所有者校验。
- [ ] `_restore_conversation_state` 与 `_handle_restore_history` 双向同步 Claude 端与子进程状态。

### 4. 命令层集成（每项 ~5K tokens）
- [ ] 在 Claude 命令入口实现 `/codex-config`（查询+切换）及参数校验。
- [ ] 实装 `/codex-reasoning`、`/codex-final_only`，并处理未激活提示。
- [ ] `/codex-help` 输出方案描述，注明可用的 Claude `/rewind`、`/clear`。

### 5. 安全与监控（每项 ~4K tokens）
- [ ] Socket/历史文件创建后立即设置 0600 权限并验证所有权。
- [ ] 监控线程处理 `waitpid` 异常，记录自动重启与恢复日志。
- [ ] 配置变更写入日志事件，支持运行期调试。

### 6. 测试与文档（每项 ~4K tokens）
- [ ] 编写脚本/清单：启动 → 多轮 `/codex-ask` → 切换档位/开关 → 重启恢复。
- [ ] 验证异常场景：未激活命令、非法参数、子进程崩溃模拟。
- [ ] 更新 README/方案附录，记录依赖、运行步骤与调试技巧。

> 建议按章节顺序推进，确保单次改动 <300 行代码，便于审阅与回滚。
