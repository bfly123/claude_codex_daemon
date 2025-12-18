#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${CODEX_INSTALL_PREFIX:-$HOME/.local/share/codex-dual}"
BIN_DIR="${CODEX_BIN_DIR:-$HOME/.local/bin}"
readonly REPO_ROOT INSTALL_PREFIX BIN_DIR

SCRIPTS_TO_LINK=(
  bin/cask
  bin/cask-w
  bin/cpend
  bin/cping
  bin/gask
  bin/gask-w
  bin/gpend
  bin/gping
  ccb
)

CLAUDE_MARKDOWN=(
  cask.md
  cask-w.md
  cpend.md
  cping.md
  gask.md
  gask-w.md
  gpend.md
  gping.md
)

LEGACY_SCRIPTS=(
  cast
  cast-w
  codex-ask
  codex-pending
  codex-ping
  claude-codex-dual
  claude_codex
  claude_ai
  claude_bridge
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

require_python_version() {
  # ccb requires Python 3.10+ (PEP 604 type unions: `str | None`, etc.)
  local version
  version="$(python3 -c 'import sys; print("{}.{}.{}".format(sys.version_info[0], sys.version_info[1], sys.version_info[2]))' 2>/dev/null || echo unknown)"
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "❌ Python 版本过低: $version"
    echo "   需要 Python 3.10+，请升级后重试"
    exit 1
  fi
  echo "✓ Python $version"
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

require_terminal_backend() {
  # 检测 WezTerm（优先）
  local wezterm_override="${CODEX_WEZTERM_BIN:-${WEZTERM_BIN:-}}"
  if [[ -n "${wezterm_override}" ]]; then
    if command -v "${wezterm_override}" >/dev/null 2>&1 || [[ -f "${wezterm_override}" ]]; then
      echo "✓ 检测到 WezTerm (${wezterm_override})"
      return
    fi
  fi
  if command -v wezterm >/dev/null 2>&1 || command -v wezterm.exe >/dev/null 2>&1; then
    echo "✓ 检测到 WezTerm"
    return
  fi
  # WSL 场景：Windows PATH 可能未注入 WSL，尝试常见安装路径
  if [[ -f "/proc/version" ]] && grep -qi microsoft /proc/version 2>/dev/null; then
    if [[ -x "/mnt/c/Program Files/WezTerm/wezterm.exe" ]] || [[ -f "/mnt/c/Program Files/WezTerm/wezterm.exe" ]]; then
      echo "✓ 检测到 WezTerm (/mnt/c/Program Files/WezTerm/wezterm.exe)"
      return
    fi
    if [[ -x "/mnt/c/Program Files (x86)/WezTerm/wezterm.exe" ]] || [[ -f "/mnt/c/Program Files (x86)/WezTerm/wezterm.exe" ]]; then
      echo "✓ 检测到 WezTerm (/mnt/c/Program Files (x86)/WezTerm/wezterm.exe)"
      return
    fi
  fi
  # 检测 tmux（备选）
  if command -v tmux >/dev/null 2>&1; then
    echo "✓ 检测到 tmux（建议同时安装 WezTerm 以获得更好体验）"
    return
  fi
  echo "❌ 缺少依赖: WezTerm 或 tmux（推荐 WezTerm）"
  echo "   WezTerm 官网: https://wezfurlong.org/wezterm/"
  print_tmux_install_hint
  exit 1
}

has_wezterm() {
  local wezterm_override="${CODEX_WEZTERM_BIN:-${WEZTERM_BIN:-}}"
  if [[ -n "${wezterm_override}" ]]; then
    command -v "${wezterm_override}" >/dev/null 2>&1 || [[ -f "${wezterm_override}" ]] && return 0
  fi
  command -v wezterm >/dev/null 2>&1 && return 0
  command -v wezterm.exe >/dev/null 2>&1 && return 0
  if [[ -f "/proc/version" ]] && grep -qi microsoft /proc/version 2>/dev/null; then
    [[ -f "/mnt/c/Program Files/WezTerm/wezterm.exe" ]] && return 0
    [[ -f "/mnt/c/Program Files (x86)/WezTerm/wezterm.exe" ]] && return 0
  fi
  return 1
}

detect_wezterm_path() {
  local wezterm_override="${CODEX_WEZTERM_BIN:-${WEZTERM_BIN:-}}"
  if [[ -n "${wezterm_override}" ]] && [[ -f "${wezterm_override}" ]]; then
    echo "${wezterm_override}"
    return
  fi
  local found
  found="$(command -v wezterm 2>/dev/null)" && [[ -n "$found" ]] && echo "$found" && return
  found="$(command -v wezterm.exe 2>/dev/null)" && [[ -n "$found" ]] && echo "$found" && return
  if is_wsl; then
    for drive in c d e f; do
      for path in "/mnt/${drive}/Program Files/WezTerm/wezterm.exe" \
                  "/mnt/${drive}/Program Files (x86)/WezTerm/wezterm.exe"; do
        if [[ -f "$path" ]]; then
          echo "$path"
          return
        fi
      done
    done
  fi
}

save_wezterm_config() {
  local wezterm_path
  wezterm_path="$(detect_wezterm_path)"
  if [[ -n "$wezterm_path" ]]; then
    mkdir -p "$HOME/.config/ccb"
    echo "CODEX_WEZTERM_BIN=${wezterm_path}" > "$HOME/.config/ccb/env"
    echo "✓ WezTerm 路径已缓存: $wezterm_path"
  fi
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

  for path in "${SCRIPTS_TO_LINK[@]}"; do
    local name
    name="$(basename "$path")"
    if [[ ! -f "$INSTALL_PREFIX/$path" ]]; then
      echo "⚠️ 未找到脚本 $INSTALL_PREFIX/$path，跳过创建链接"
      continue
    fi
    chmod +x "$INSTALL_PREFIX/$path"
    if ln -sf "$INSTALL_PREFIX/$path" "$BIN_DIR/$name" 2>/dev/null; then
      :
    else
      # Windows (Git Bash) / restricted environments may not allow symlinks. Fall back to copying.
      cp -f "$INSTALL_PREFIX/$path" "$BIN_DIR/$name"
      chmod +x "$BIN_DIR/$name" 2>/dev/null || true
    fi
  done

  for legacy in "${LEGACY_SCRIPTS[@]}"; do
    rm -f "$BIN_DIR/$legacy"
  done

  echo "已在 $BIN_DIR 创建可执行入口"
}

install_claude_commands() {
  local claude_dir
  claude_dir="$(detect_claude_dir)"
  mkdir -p "$claude_dir"

  for doc in "${CLAUDE_MARKDOWN[@]}"; do
    cp -f "$REPO_ROOT/commands/$doc" "$claude_dir/$doc"
    chmod 0644 "$claude_dir/$doc" 2>/dev/null || true
  done

  echo "已更新 Claude 命令目录: $claude_dir"
}

RULE_MARKER="## Codex Collaboration Rules"
LEGACY_RULE_MARKER="## Codex 协作规则"

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

  # Remove old rules (both legacy Chinese and new English versions)
  if [[ -f "$claude_md" ]]; then
    if grep -qE "$RULE_MARKER|$LEGACY_RULE_MARKER|## Gemini" "$claude_md" 2>/dev/null; then
      echo "Removing old collaboration rules..."
      python3 -c "
import re
with open('$claude_md', 'r', encoding='utf-8') as f:
    content = f.read()
# Remove all collaboration rule sections
patterns = [
    r'## Codex Collaboration Rules.*?(?=\n## |\Z)',
    r'## Codex 协作规则.*?(?=\n## |\Z)',
    r'## Gemini Collaboration Rules.*?(?=\n## |\Z)',
    r'## Gemini 协作规则.*?(?=\n## |\Z)',
]
for p in patterns:
    content = re.sub(p, '', content, flags=re.DOTALL)
content = content.rstrip() + '\n'
with open('$claude_md', 'w', encoding='utf-8') as f:
    f.write(content)
"
    fi
  fi

  cat >> "$claude_md" << 'AI_RULES'

## Codex Collaboration Rules
Codex is another AI assistant running in a separate terminal session (WezTerm or tmux). When user intent involves asking/consulting/collaborating with Codex:

Fast path (minimize latency):
- If the user message starts with any of: `调取codex`, `@codex`, `codex:`, `codex：`, `问codex`, `让codex` then immediately run:
  - `cask-w "<rest of the message after the prefix>"` (no extra analysis, no pre-checks like cping)
- If user message is only the prefix (no content), ask a 1-line clarification for what to send.

Trigger conditions (any match):
- User mentions codex/Codex with questioning/requesting tone
- User wants codex to do something, give advice, or help review
- User asks about codex's status or previous reply

Command selection:
- Default ask/collaborate → `cask-w "<question>"` (sync, waits for reply)
- Send without waiting → `cask "<question>"` (async, returns immediately)
- Check connectivity → `cping`
- View previous reply → `cpend`

Examples:
- "what does codex think" → cask-w
- "ask codex to review this" → cask-w
- "is codex alive" → cping
- "don't wait for reply" → cask

## Gemini Collaboration Rules
Gemini is another AI assistant running in a separate terminal session (WezTerm or tmux). When user intent involves asking/consulting/collaborating with Gemini:

Fast path (minimize latency):
- If the user message starts with any of: `调取gemini`, `@gemini`, `gemini:`, `gemini：`, `问gemini`, `让gemini` then immediately run:
  - `gask-w "<rest of the message after the prefix>"` (no extra analysis, no pre-checks like gping)
- If user message is only the prefix (no content), ask a 1-line clarification for what to send.

Trigger conditions (any match):
- User mentions gemini/Gemini with questioning/requesting tone
- User wants gemini to do something, give advice, or help review
- User asks about gemini's status or previous reply

Command selection:
- Default ask/collaborate → `gask-w "<question>"` (sync, waits for reply)
- Send without waiting → `gask "<question>"` (async, returns immediately)
- Check connectivity → `gping`
- View previous reply → `gpend`

Examples:
- "what does gemini think" → gask-w
- "ask gemini to review this" → gask-w
- "is gemini alive" → gping
- "don't wait for reply" → gask
AI_RULES

  echo "Updated AI collaboration rules in $claude_md"
}

install_settings_permissions() {
  local settings_file="$HOME/.claude/settings.json"
  mkdir -p "$HOME/.claude"

  local perms_to_add=(
    'Bash(cask:*)'
    'Bash(cask-w:*)'
    'Bash(cpend)'
    'Bash(cping)'
    'Bash(gask:*)'
    'Bash(gask-w:*)'
    'Bash(gpend)'
    'Bash(gping)'
  )

  if [[ ! -f "$settings_file" ]]; then
    cat > "$settings_file" << 'SETTINGS'
{
  "permissions": {
    "allow": [
      "Bash(cask:*)",
      "Bash(cask-w:*)",
      "Bash(cpend)",
      "Bash(cping)",
      "Bash(gask:*)",
      "Bash(gask-w:*)",
      "Bash(gpend)",
      "Bash(gping)"
    ],
    "deny": []
  }
}
SETTINGS
    echo "Created $settings_file with permissions"
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
  require_python_version
  require_terminal_backend
  if ! has_wezterm; then
    echo
    echo "================================================================"
    echo "⚠️ 建议安装 WezTerm 作为终端前端（体验更好，推荐 WSL2/Windows 用户）"
    echo "   - 官网: https://wezfurlong.org/wezterm/"
    echo "   - 优势: 更顺滑的分屏/滚动/字体渲染，WezTerm 模式下桥接更稳定"
    echo "================================================================"
    echo
  fi
}

install_all() {
  install_requirements
  remove_codex_mcp
  save_wezterm_config
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
