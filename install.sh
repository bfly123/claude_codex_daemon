#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 规范化源目录，避免符号链接导致的自我删除
SOURCE_ROOT="$(cd "$REPO_ROOT" && pwd -P)"

if [[ $EUID -ne 0 ]]; then
  echo "❌ 本安装脚本需要管理员权限，请使用 sudo ./install.sh install" >&2
  exit 1
fi

TARGET_USER="${SUDO_USER:-$(id -un)}"
TARGET_HOME="$(eval echo "~${TARGET_USER}")"
if [[ -z "$TARGET_HOME" || ! -d "$TARGET_HOME" ]]; then
  echo "❌ 无法解析目标用户 $TARGET_USER 的家目录" >&2
  exit 1
fi
TARGET_HOME="${TARGET_HOME%/}"
TARGET_CHOWN="${TARGET_USER}:${TARGET_USER}"
DEFAULT_PREFIX="${CODEX_INSTALL_PREFIX:-$TARGET_HOME/.local/share/claude-codex-lock}"
DEFAULT_BIN_DIR="${CODEX_BIN_DIR:-$TARGET_HOME/.local/bin}"

usage() {
  cat <<'USAGE'
用法:
  ./install.sh install   # 安装或更新 claude-codex
  ./install.sh uninstall # 卸载 claude-codex

可选环境变量:
  CODEX_INSTALL_PREFIX     安装目录 (默认: ~/.local/share/claude-codex-lock)
  CODEX_BIN_DIR            可执行文件目录 (默认: ~/.local/bin)
  CODEX_CLAUDE_COMMAND_DIR Claude 命令目录 (默认自动检测)
USAGE
}

detect_claude_command_dir() {
  if [[ -n "${CODEX_CLAUDE_COMMAND_DIR:-}" ]]; then
    echo "$CODEX_CLAUDE_COMMAND_DIR"
    return
  fi

  local candidates=(
    "$TARGET_HOME/.config/claude/commands"
    "$TARGET_HOME/.claude/commands"
    "$TARGET_HOME/.local/share/claude/commands"
  )

  for dir in "${candidates[@]}"; do
    if [[ -d "$dir" ]]; then
      echo "$dir"
      return
    fi
  done

  local fallback="$TARGET_HOME/.claude/commands"
  mkdir -p "$fallback"
  echo "$fallback"
}

fix_tmp_permissions() {
  local current_mode
  current_mode="$(stat -c '%a' /tmp 2>/dev/null || echo '')"

  if [[ "$current_mode" != "1777" ]]; then
    echo "🔧 调整 /tmp 权限为 1777"
    chmod 1777 /tmp
  fi

  local current_owner
  current_owner="$(stat -c '%u:%g' /tmp 2>/dev/null || echo '')"
  if [[ "$current_owner" != "0:0" ]]; then
    echo "🔧 调整 /tmp 所有者为 root:root"
    chown root:root /tmp
  fi
}

prepare_runtime_dirs() {
  local runtime_tmp="/tmp/codex-$TARGET_USER"
  local runtime_home="$TARGET_HOME/.codex_runtime"

  mkdir -p "$runtime_tmp"
  chown "$TARGET_CHOWN" "$runtime_tmp"
  chmod 700 "$runtime_tmp"

  mkdir -p "$runtime_home"
  chown "$TARGET_CHOWN" "$runtime_home"
  chmod 700 "$runtime_home"
}

install_python_bootstrap() {
  local prefix="$1"
  local user_site

  user_site=$(runuser -u "$TARGET_USER" -- python3 - <<'PY' 2>/dev/null || true
import site
print(site.getusersitepackages())
PY
)

  if [[ -z "$user_site" ]]; then
    echo "⚠️ 无法获取 Python 用户 site-packages 路径，跳过自动注入"
    return
  fi

  mkdir -p "$user_site"
  chown "$TARGET_CHOWN" "$user_site"

  local pth_file="$user_site/claude_codex.pth"
  cat >"$pth_file" <<EOF
$prefix
import codex_bootstrap
EOF
  chmod 644 "$pth_file"
  chown "$TARGET_CHOWN" "$pth_file"
}

copy_project_files() {
  local prefix="$1"
  local target_root=""
  if [[ -d "$prefix" ]]; then
    target_root="$(cd "$prefix" && pwd -P)"
  fi

  if [[ -n "$target_root" && "$SOURCE_ROOT" == "$target_root" ]]; then
    echo "❌ 安装源与目标目录相同: $SOURCE_ROOT" >&2
    echo "   请在源码仓库目录中执行 ./install.sh install，再次安装。" >&2
    exit 1
  fi

  if ! rm -rf "$prefix"; then
    echo "❌ 无法清理旧的安装目录: $prefix" >&2
    echo "   请确认具备写权限，或手动删除该目录后重试。" >&2
    exit 1
  fi
  mkdir -p "$prefix"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git/' \
      --exclude '.mypy_cache/' \
      --exclude '__pycache__/' \
      --exclude '.pytest_cache/' \
      "$REPO_ROOT"/ "$prefix"/
  else
    tar -C "$REPO_ROOT" \
      --exclude '.git' \
      --exclude '.mypy_cache' \
      --exclude '__pycache__' \
      --exclude '.pytest_cache' \
      -cf - . | tar -C "$prefix" -xf -
  fi

  chown -R "$TARGET_CHOWN" "$prefix"
}

create_bin_links() {
  local prefix="$1"
  local bin_dir="$2"

  mkdir -p "$bin_dir"
  chown "$TARGET_CHOWN" "$bin_dir"
  ln -sf "$prefix/claude-codex" "$bin_dir/claude-codex"
  ln -sf "$prefix/install.sh" "$bin_dir/claude-codex-install"
  chown -h "$TARGET_CHOWN" "$bin_dir/claude-codex" "$bin_dir/claude-codex-install"

  chmod +x "$prefix/codex_cli.py"
  chown "$TARGET_CHOWN" "$prefix/codex_cli.py"

  ln -sf "$prefix/codex_cli.py" "$bin_dir/codex-cli"
  chown -h "$TARGET_CHOWN" "$bin_dir/codex-cli"

  local cli_aliases=(
    codex-ask
    codex-status
    codex-stop
    codex-config
    codex-reasoning
    codex-final_only
  )
  for alias in "${cli_aliases[@]}"; do
    ln -sf "$prefix/codex_cli.py" "$bin_dir/$alias"
    chown -h "$TARGET_CHOWN" "$bin_dir/$alias"
  done
}

create_claude_command() {
  local prefix="$1"
  local claude_dir="$2"
  local command_path="$claude_dir/codex"

  mkdir -p "$claude_dir"
  chown "$TARGET_CHOWN" "$claude_dir"
  cat >"$command_path" <<'CMD'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${CODEX_HOME:-PREFIX_PLACEHOLDER}"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "❌ Codex安装目录不存在: $PROJECT_DIR" >&2
  exit 1
fi

export CODEX_HOME="$PROJECT_DIR"
python3 - "$@" <<'PY'
import sys
import os

project_dir = os.environ.get("CODEX_HOME")
if not project_dir:
    print("❌ 未设置 CODEX_HOME 环境变量")
    sys.exit(1)

sys.path.insert(0, project_dir)
try:
    from codex_commands import handle_codex_command
except ImportError as exc:
    print(f"❌ 无法导入 codex_commands: {exc}")
    sys.exit(1)

if len(sys.argv) <= 1:
    print("❌ 请提供要执行的 codex 命令，例如 /codex-help")
    sys.exit(1)

command = " ".join(sys.argv[1:])
print(handle_codex_command(command))
PY
CMD
  sed -i "s|PREFIX_PLACEHOLDER|$prefix|" "$command_path"
  chmod +x "$command_path"
  chown "$TARGET_CHOWN" "$command_path"

  for doc in "$prefix"/commands/codex-*.md; do
    if [[ -f "$doc" ]]; then
      cp "$doc" "$claude_dir/$(basename "$doc")"
      chmod 644 "$claude_dir/$(basename "$doc")"
      chown "$TARGET_CHOWN" "$claude_dir/$(basename "$doc")"
    fi
  done
}

install_codex() {
  local prefix="$DEFAULT_PREFIX"
  local bin_dir="$DEFAULT_BIN_DIR"
  local claude_dir
  claude_dir="$(detect_claude_command_dir)"

  echo "👤 目标用户: $TARGET_USER ($TARGET_HOME)"
  echo "📦 安装目录: $prefix"
  echo "🛠️  可执行目录: $bin_dir"
  echo "🔗 Claude 命令目录: $claude_dir"

  fix_tmp_permissions
  prepare_runtime_dirs

  copy_project_files "$prefix"
  create_bin_links "$prefix" "$bin_dir"
  create_claude_command "$prefix" "$claude_dir"
  install_python_bootstrap "$prefix"

  chmod +x "$prefix/claude-codex"
  chmod +x "$prefix/install.sh"

  echo "✅ 安装完成。"
  echo "• 使用 claude-codex 启动后台服务"
  echo "• claude-codex-install uninstall 可随时卸载"
}

uninstall_codex() {
  local prefix="$DEFAULT_PREFIX"
  local bin_dir="$DEFAULT_BIN_DIR"
  local claude_dir
  claude_dir="$(detect_claude_command_dir)"
  local user_site
  user_site=$(runuser -u "$TARGET_USER" -- python3 - <<'PY' 2>/dev/null || true
import site
print(site.getusersitepackages())
PY
)

  echo "🧹 开始卸载 claude-codex..."
  rm -f "$bin_dir/claude-codex" "$bin_dir/claude-codex-install" \
        "$bin_dir/codex-cli" "$bin_dir/codex-ask" "$bin_dir/codex-status" \
        "$bin_dir/codex-stop" "$bin_dir/codex-config" "$bin_dir/codex-reasoning" \
        "$bin_dir/codex-final_only"
  rm -f "$claude_dir/codex"
  rm -rf "$prefix"
  if [[ -n "$user_site" ]]; then
    rm -f "$user_site/claude_codex.pth"
  fi
  echo "✅ 卸载完成。"
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

case "$1" in
  install)
    install_codex
    ;;
  uninstall)
    uninstall_codex
    ;;
  *)
    usage
    exit 1
    ;;
esac
