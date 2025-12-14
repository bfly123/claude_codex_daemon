# Claude-Codex

Dual-pane collaboration tool that bridges Claude and Codex (or other AI IDEs) over tmux with persistent session isolation. Works on Linux/macOS; Windows supported via WSL2.

![Dual-pane diagram](figure.png)

## Why This Project?

With traditional MCP calls, Claude must feed large chunks of context to Codex on every request. Codex acts as a stateless executor with no memory.

**claude_codex is different**: It establishes a persistent communication channel between Claude and a full Codex instance. Each maintains its own context independently—only brief instructions need to be exchanged.

| Aspect | MCP Ephemeral Calls | Persistent Dual-Pane |
|--------|---------------------|----------------------|
| Codex State | Stateless, no memory | Persistent session |
| Context Source | Passed from Claude | Self-maintained |
| Token Cost | High (5k-20k/call) | Low (50-200/call) |
| Work Mode | Master-slave | Parallel collaboration |
| Capabilities | Limited by MCP API | Full CLI access |
| Session Recovery | Not possible | Supported (`-C` flag) |

### Key Benefits

**1. Context Independence**
- MCP: Codex only sees what Claude feeds it
- Dual-pane: Codex has its own eyes—reads project files, remembers conversation history

**2. Token Savings (70-90% reduction)**
```
MCP approach:
  Claude → [full code + history + instructions] → Codex
  Cost: 5,000-20,000 tokens/call

Dual-pane approach:
  Claude → "optimize the performance of utils.py" → Codex
  Cost: 50-200 tokens/call
  Codex reads utils.py on its own
```

**3. True Parallel Collaboration**
- Claude and Codex work independently
- Async mode allows Claude to continue without blocking
- Ideal for complex task distribution

**4. Full Codex Capabilities**
- File read/write, command execution, git operations
- Not limited by MCP interface constraints
- `--full-auto` mode for complete autonomy

## Install

```bash
./install.sh install
```

## Start

```bash
claude_codex              # default start
claude_codex -c           # resume Claude context
claude_codex -C           # resume Codex context
claude_codex -C -c        # resume both
claude_codex -a           # full permissions mode
```

`-a` / `--all-permissions` enables maximum permissions: Claude uses `--dangerously-skip-permissions`, Codex uses `--full-auto`.

## Usage

After install, just use natural language to trigger Codex collaboration.

### Practical Examples
- "Have Codex review my code changes and suggest improvements"
- "Ask Codex to plan the refactoring, then supervise while I implement"
- "Let Codex write the backend API while I work on the frontend"

### Fun & Creative
- "Play Gomoku (five-in-a-row) with Codex"
- "Have Claude and Codex debate: tabs vs spaces"
- "Let Codex quiz me on algorithms, Claude checks my answers"
- "Codex writes a function, Claude tries to find bugs"
- "Role-play: Codex is the senior dev, I'm the intern asking questions"

### Advanced Workflows
- "Codex designs the architecture, Claude implements each module"
- "Parallel code review: both analyze the PR from different angles"
- "Codex monitors test results while Claude fixes failing tests"

For explicit control, use the commands below.

## Commands

| Command | Description |
|---------|-------------|
| `cask-w <question>` | Synchronous; waits for Codex reply (recommended) |
| `cask <question>` | Async fire-and-forget |
| `cpend` | Show latest reply |
| `cping` | Connectivity check |

## Automation

After installing, Claude automatically detects collaboration intent and calls the appropriate command. Default is synchronous `cask-w`; use `cask` for async, `cping` for health checks, `cpend` to read replies.

## Project Structure

```
claude_codex/
├── cask                  # async forwarder
├── cask-w                # sync forwarder
├── cpend                 # show reply
├── cping                 # connectivity check
├── claude_codex          # main launcher
├── codex_comm.py         # communication layer
├── codex_dual_bridge.py  # tmux bridge
├── commands/             # command docs
└── install.sh            # installer
```

## Highlights

- Dual-pane Claude-Codex collaboration
- Session isolation via session_id filtering
- tmux-based command forwarding
- Async and sync communication modes
- Automatic temp file cleanup

## Uninstall

```bash
./install.sh uninstall
```

## Requirements

- Python 3.8+
- tmux

macOS: `brew install tmux`
Linux: `sudo apt-get install tmux` / `sudo dnf install tmux` / `sudo pacman -S tmux`

## WSL Support

- WSL2: fully supported
- WSL1: not supported (FIFO limitation)

Upgrade to WSL2:
```powershell
wsl --set-version <distro> 2
```

For best performance, work inside the WSL filesystem (e.g., `~/projects`) instead of `/mnt/c`.
