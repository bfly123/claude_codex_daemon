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

is_wsl() {
  [[ -f /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null
}

get_wsl_version() {
  if [[ -n "${WSL_INTEROP:-}" ]]; then
    echo 2
  else
    echo 1
  fi
}

check_wsl_compatibility() {
  if is_wsl; then
    local ver
    ver="$(get_wsl_version)"
    if [[ "$ver" == "1" ]]; then
      echo "❌ WSL 1 不支持 FIFO 管道，请升级到 WSL 2"
      echo "   运行: wsl --set-version <distro> 2"
      exit 1
    fi
    echo "✅ 检测到 WSL 2 环境"
  fi
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

CODEX_RULE_MARKER="## Codex 协作规则"

remove_codex_mcp() {
  local claude_config="$HOME/.claude.json"

  if [[ ! -f "$claude_config" ]]; then
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "⚠️ 需要 python3 来检测 MCP 配置"
    return
  fi

  local has_codex_mcp
  has_codex_mcp=$(python3 -c "
import json
try:
    with open('$claude_config', 'r') as f:
        data = json.load(f)
    found = False
    for proj, cfg in data.get('projects', {}).items():
        servers = cfg.get('mcpServers', {})
        for name in list(servers.keys()):
            if 'codex' in name.lower():
                found = True
                break
        if found:
            break
    print('yes' if found else 'no')
except:
    print('no')
" 2>/dev/null)

  if [[ "$has_codex_mcp" == "yes" ]]; then
    echo "⚠️ 检测到 codex 相关的 MCP 配置，正在移除以避免冲突..."
    python3 -c "
import json
with open('$claude_config', 'r') as f:
    data = json.load(f)
removed = []
for proj, cfg in data.get('projects', {}).items():
    servers = cfg.get('mcpServers', {})
    for name in list(servers.keys()):
        if 'codex' in name.lower():
            del servers[name]
            removed.append(f'{proj}: {name}')
with open('$claude_config', 'w') as f:
    json.dump(data, f, indent=2)
if removed:
    print('已移除以下 MCP 配置:')
    for r in removed:
        print(f'  - {r}')
"
    echo "✅ Codex MCP 配置已清理"
  fi
}

install_claude_md_config() {
  local claude_md="$HOME/.claude/CLAUDE.md"
  mkdir -p "$HOME/.claude"

  if [[ -f "$claude_md" ]] && grep -q "$CODEX_RULE_MARKER" "$claude_md" 2>/dev/null; then
    echo "检测到旧的 Codex 协作规则，正在更新..."
    python3 -c "
import re
with open('$claude_md', 'r', encoding='utf-8') as f:
    content = f.read()
pattern = r'## Codex 协作规则.*?(?=\n## |\Z)'
content = re.sub(pattern, '', content, flags=re.DOTALL)
content = content.rstrip() + '\n'
with open('$claude_md', 'w', encoding='utf-8') as f:
    f.write(content)
"
  fi

  cat >> "$claude_md" << 'CODEX_RULES'

## Codex 协作规则
Codex 是通过 tmux 运行的另一个 AI 助手。当用户的意图涉及「询问/请教/协作 Codex」时，根据语义判断调用：

判断标准（任一满足即调用）：
- 用户提到 codex/Codex 且带有疑问/请求/协作语气
- 用户想让 codex 做某事、给建议、帮忙看
- 用户询问 codex 的状态或之前的回复

命令选择：
- 默认询问/协作 → `cask-w "<问题或指令>"`（同步等待回复，无限等待）
- 仅发送不等待 → `cask "<问题或指令>"`（异步，立即返回）
- 只想查状态/连通性 → `cping`
- 只想看之前的回复 → `cpend`

示例：
- "codex 对此有什么建议" → cask-w（默认同步）
- "让 codex 帮忙看看" → cask-w
- "问一下 codex 这个问题" → cask-w
- "codex 那边怎么说" → cpend
- "codex 还活着吗" → cping
- "不用等回复" / "异步发送" → cask
CODEX_RULES

  echo "已更新 Codex 协作规则到 $claude_md"
}

install_settings_permissions() {
  local settings_file="$HOME/.claude/settings.json"
  mkdir -p "$HOME/.claude"

  local perms_to_add=(
    'Bash(cask:*)'
    'Bash(cask-w:*)'
    'Bash(cpend)'
    'Bash(cping)'
  )

  if [[ ! -f "$settings_file" ]]; then
    cat > "$settings_file" << 'SETTINGS'
{
  "permissions": {
    "allow": [
      "Bash(cask:*)",
      "Bash(cask-w:*)",
      "Bash(cpend)",
      "Bash(cping)"
    ],
    "deny": []
  }
}
SETTINGS
    echo "已创建 $settings_file 并添加权限"
    return
  fi

  local added=0
  for perm in "${perms_to_add[@]}"; do
    if ! grep -q "$perm" "$settings_file" 2>/dev/null; then
      if command -v python3 >/dev/null 2>&1; then
        python3 -c "
import json, sys
with open('$settings_file', 'r') as f:
    data = json.load(f)
if 'permissions' not in data:
    data['permissions'] = {'allow': [], 'deny': []}
if 'allow' not in data['permissions']:
    data['permissions']['allow'] = []
if '$perm' not in data['permissions']['allow']:
    data['permissions']['allow'].append('$perm')
with open('$settings_file', 'w') as f:
    json.dump(data, f, indent=2)
"
        added=1
      fi
    fi
  done

  if [[ $added -eq 1 ]]; then
    echo "已更新 $settings_file 权限配置"
  else
    echo "权限配置已存在于 $settings_file"
  fi
}

install_requirements() {
  check_wsl_compatibility
  require_command python3 python3
  require_tmux
}

install_all() {
  install_requirements
  remove_codex_mcp
  copy_project
  install_bin_links
  install_claude_commands
  install_claude_md_config
  install_settings_permissions
  echo "✅ 安装完成"
  echo "   项目目录 : $INSTALL_PREFIX"
  echo "   可执行目录: $BIN_DIR"
  echo "   Claude 命令已更新"
  echo "   全局 CLAUDE.md 已配置 Codex 协作规则"
  echo "   全局 settings.json 已添加权限"
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
