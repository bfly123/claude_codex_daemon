#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PREFIX="${CODEX_INSTALL_PREFIX:-$HOME/.local/share/claude-codex-lock}"
DEFAULT_BIN_DIR="${CODEX_BIN_DIR:-$HOME/.local/bin}"

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
    "$HOME/.config/claude/commands"
    "$HOME/.claude/commands"
    "$HOME/.local/share/claude/commands"
  )

  for dir in "${candidates[@]}"; do
    if [[ -d "$dir" ]]; then
      echo "$dir"
      return
    fi
  done

  local fallback="$HOME/.claude/commands"
  mkdir -p "$fallback"
  echo "$fallback"
}

copy_project_files() {
  local prefix="$1"
  rm -rf "$prefix"
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
}

create_bin_links() {
  local prefix="$1"
  local bin_dir="$2"

  mkdir -p "$bin_dir"
  ln -sf "$prefix/claude-codex" "$bin_dir/claude-codex"
  ln -sf "$prefix/install.sh" "$bin_dir/claude-codex-install"
}

create_claude_command() {
  local prefix="$1"
  local claude_dir="$2"
  local command_path="$claude_dir/codex"

  mkdir -p "$claude_dir"
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

  for doc in "$prefix"/commands/codex-*.md; do
    if [[ -f "$doc" ]]; then
      cp "$doc" "$claude_dir/$(basename "$doc")"
      chmod 644 "$claude_dir/$(basename "$doc")"
    fi
  done
}

install_codex() {
  local prefix="$DEFAULT_PREFIX"
  local bin_dir="$DEFAULT_BIN_DIR"
  local claude_dir
  claude_dir="$(detect_claude_command_dir)"

  echo "📦 安装目录: $prefix"
  echo "🛠️  可执行目录: $bin_dir"
  echo "🔗 Claude 命令目录: $claude_dir"

  copy_project_files "$prefix"
  create_bin_links "$prefix" "$bin_dir"
  create_claude_command "$prefix" "$claude_dir"

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

  echo "🧹 开始卸载 claude-codex..."
  rm -f "$bin_dir/claude-codex" "$bin_dir/claude-codex-install"
  rm -f "$claude_dir/codex"
  rm -rf "$prefix"
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
