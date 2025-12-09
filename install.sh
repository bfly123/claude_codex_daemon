#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${CODEX_INSTALL_PREFIX:-$HOME/.local/share/codex-dual}"
BIN_DIR="${CODEX_BIN_DIR:-$HOME/.local/bin}"
readonly REPO_ROOT INSTALL_PREFIX BIN_DIR

SCRIPTS_TO_LINK=(
  cask
  cask-w
  claude_codex
  cpend
  cping
)

CLAUDE_MARKDOWN=(
  cask.md
  cask-w.md
  cpend.md
  cping.md
)

LEGACY_SCRIPTS=(
  cast
  cast-w
  codex-ask
  codex-pending
  codex-ping
  claude-codex-dual
)

usage() {
  cat <<'USAGE'
用法:
  ./install.sh install    # 安装或更新 Codex 双窗口工具
  ./install.sh uninstall  # 卸载已安装内容

可选环境变量:
  CODEX_INSTALL_PREFIX     安装目录 (默认: ~/.local/share/codex-dual)
  CODEX_BIN_DIR            可执行文件目录 (默认: ~/.local/bin)
  CODEX_CLAUDE_COMMAND_DIR 自定义 Claude 命令目录 (默认自动检测)
USAGE
}

detect_claude_dir() {
  if [[ -n "${CODEX_CLAUDE_COMMAND_DIR:-}" ]]; then
    echo "$CODEX_CLAUDE_COMMAND_DIR"
    return
  fi

  local candidates=(
    "$HOME/.claude/commands"
    "$HOME/.config/claude/commands"
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

require_command() {
  local cmd="$1"
  local pkg="${2:-$1}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ 缺少依赖: $cmd"
    echo "   请先安装 $pkg，再重新运行 install.sh"
    exit 1
  fi
}

# 根据 uname 返回 linux / macos / unknown
detect_platform() {
  local name
  name="$(uname -s 2>/dev/null || echo unknown)"
  case "$name" in
    Linux) echo "linux" ;;
    Darwin) echo "macos" ;;
    *) echo "unknown" ;;
  esac
}

print_tmux_install_hint() {
  local platform
  platform="$(detect_platform)"
  case "$platform" in
    macos)
      if command -v brew >/dev/null 2>&1; then
        echo "   macOS: 运行 'brew install tmux'"
      else
        echo "   macOS: 未检测到 Homebrew，可先安装 https://brew.sh 然后执行 'brew install tmux'"
      fi
      ;;
    linux)
      if command -v apt-get >/dev/null 2>&1; then
        echo "   Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y tmux"
      elif command -v dnf >/dev/null 2>&1; then
        echo "   Fedora/CentOS/RHEL: sudo dnf install -y tmux"
      elif command -v yum >/dev/null 2>&1; then
        echo "   CentOS/RHEL: sudo yum install -y tmux"
      elif command -v pacman >/dev/null 2>&1; then
        echo "   Arch/Manjaro: sudo pacman -S tmux"
      elif command -v apk >/dev/null 2>&1; then
        echo "   Alpine: sudo apk add tmux"
      elif command -v zypper >/dev/null 2>&1; then
        echo "   openSUSE: sudo zypper install -y tmux"
      else
        echo "   Linux: 请使用发行版自带的包管理器安装 tmux"
      fi
      ;;
    *)
      echo "   请参考 https://github.com/tmux/tmux/wiki/Installing 获取 tmux 安装方法"
      ;;
  esac
}

require_tmux() {
  if command -v tmux >/dev/null 2>&1; then
    return
  fi
  echo "❌ 缺少依赖: tmux"
  print_tmux_install_hint
  exit 1
}

copy_project() {
  local staging
  staging="$(mktemp -d)"
  trap 'rm -rf "$staging"' EXIT

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git/' \
      --exclude '__pycache__/' \
      --exclude '.pytest_cache/' \
      --exclude '.mypy_cache/' \
      --exclude '.venv/' \
      "$REPO_ROOT"/ "$staging"/
  else
    tar -C "$REPO_ROOT" \
      --exclude '.git' \
      --exclude '__pycache__' \
      --exclude '.pytest_cache' \
      --exclude '.mypy_cache' \
      --exclude '.venv' \
      -cf - . | tar -C "$staging" -xf -
  fi

  rm -rf "$INSTALL_PREFIX"
  mkdir -p "$(dirname "$INSTALL_PREFIX")"
  mv "$staging" "$INSTALL_PREFIX"
  trap - EXIT
}

install_bin_links() {
  mkdir -p "$BIN_DIR"

  for name in "${SCRIPTS_TO_LINK[@]}"; do
    if [[ ! -f "$INSTALL_PREFIX/$name" ]]; then
      echo "⚠️ 未找到脚本 $INSTALL_PREFIX/$name，跳过创建链接"
      continue
    fi
    chmod +x "$INSTALL_PREFIX/$name"
    ln -sf "$INSTALL_PREFIX/$name" "$BIN_DIR/$name"
  done

  for legacy in "${LEGACY_SCRIPTS[@]}"; do
    rm -f "$BIN_DIR/$legacy"
  done

  echo "已在 $BIN_DIR 创建可执行入口: ${SCRIPTS_TO_LINK[*]}"
}

install_claude_commands() {
  local claude_dir
  claude_dir="$(detect_claude_dir)"
  mkdir -p "$claude_dir"

  for doc in "${CLAUDE_MARKDOWN[@]}"; do
    install -m 0644 "$REPO_ROOT/commands/$doc" "$claude_dir/$doc"
  done

  echo "已更新 Claude 命令目录: $claude_dir"
}

install_requirements() {
  require_command python3 python3
  require_tmux
}

install_all() {
  install_requirements
  copy_project
  install_bin_links
  install_claude_commands
  echo "✅ 安装完成"
  echo "   项目目录 : $INSTALL_PREFIX"
  echo "   可执行目录: $BIN_DIR"
  echo "   Claude 命令已更新"
}

uninstall_all() {
  rm -rf "$INSTALL_PREFIX"
  for name in "${SCRIPTS_TO_LINK[@]}"; do
    rm -f "$BIN_DIR/$name"
  done
  for legacy in "${LEGACY_SCRIPTS[@]}"; do
    rm -f "$BIN_DIR/$legacy"
  done
  local claude_dir
  claude_dir="$(detect_claude_dir)"
  for doc in "${CLAUDE_MARKDOWN[@]}"; do
    rm -f "$claude_dir/$doc"
  done
  echo "✅ 卸载完成"
}

main() {
  if [[ $# -ne 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    install)
      install_all
      ;;
    uninstall)
      uninstall_all
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
