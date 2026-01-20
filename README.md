# Chapgent

AI-powered coding agent for the terminal. A TUI-based assistant that can read, write, and execute code in your projects.

## Features

- **Interactive TUI** - Full terminal interface with conversation panel, tool output, and session sidebar
- **26 Built-in Tools** - File operations, git, search, shell, testing, web fetch, and project scaffolding
- **Multi-Provider LLM Support** - Anthropic, OpenAI, Ollama, Groq, and 12 more providers via LiteLLM
- **Syntax Highlighting** - Code blocks rendered with Pygments, theme-aware colors
- **Session Management** - Save, resume, and switch between conversations
- **Project Context Awareness** - Auto-detects project type and adapts behavior
- **Parallel Tool Execution** - Read operations run concurrently for speed
- **Result Caching** - Configurable LRU cache with TTL for tool results

## Requirements

- Python 3.10+
- Linux or macOS (Windows requires WSL for shell commands)
- An API key for your chosen LLM provider

## Installation

```bash
pip install chapgent
```

Or install from source:

```bash
git clone https://github.com/davewil/chapgent.git
cd chapgent
pip install -e .
```

## Quick Start

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-key"

# Start a chat session
chapgent chat

# Or use mock mode (no API key needed, for testing)
chapgent chat --mock
```

## TUI Interface

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Quit |
| `Ctrl+N` | New session |
| `Ctrl+S` | Save session |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+T` | Toggle tool panel |
| `Ctrl+P` | Command palette |
| `Ctrl+L` | Clear conversation |

### Slash Commands

Type these in the message input:

| Command | Aliases | Description |
|---------|---------|-------------|
| `/help [topic]` | `/h`, `/?` | Show help topics |
| `/tools [category]` | | View available tools |
| `/theme` | | Change TUI theme |
| `/model` | `/llm` | Configure LLM settings |
| `/config [show\|set]` | `/cfg` | Show or set configuration |
| `/new` | `/n` | Start new session |
| `/save` | `/s` | Save current session |
| `/sidebar` | `/sb` | Toggle sessions sidebar |
| `/toolpanel` | `/tp` | Toggle tool panel |
| `/clear` | `/cls` | Clear conversation |
| `/quit` | `/exit`, `/q` | Exit application |

### Themes

11 built-in themes: `textual-dark` (default), `textual-light`, `dracula`, `nord`, `gruvbox`, `monokai`, `tokyo-night`, `rose-pine`, `solarized-dark`, `solarized-light`, `textual-ansi`

Change via `/theme` or:
```bash
chapgent config set tui.theme dracula
```

## Tools

### Filesystem
| Tool | Description | Risk |
|------|-------------|------|
| `read_file` | Read file contents | Low |
| `list_files` | List directory contents | Low |
| `create_file` | Create new file | Medium |
| `edit_file` | Edit file (string replacement) | Medium |
| `delete_file` | Delete a file | High |
| `move_file` | Move or rename file | Medium |
| `copy_file` | Copy file | Medium |

### Git
| Tool | Description | Risk |
|------|-------------|------|
| `git_status` | Show working tree status | Low |
| `git_diff` | Show changes | Low |
| `git_log` | Show commit history | Low |
| `git_branch` | List/create/delete branches | Low |
| `git_add` | Stage files | Medium |
| `git_commit` | Create commit | Medium |
| `git_checkout` | Switch branches | Medium |
| `git_pull` | Fetch and merge | Medium |
| `git_push` | Push to remote | High |

### Search
| Tool | Description | Risk |
|------|-------------|------|
| `grep_search` | Search file contents (regex) | Low |
| `find_files` | Find files by glob pattern | Low |
| `find_definition` | Find symbol definitions | Low |

### Other
| Tool | Description | Risk |
|------|-------------|------|
| `shell` | Execute shell commands | High |
| `run_tests` | Run project tests | Medium |
| `web_fetch` | Fetch URL content | High |
| `list_templates` | List project templates | Low |
| `create_project` | Create from template | Medium |
| `list_components` | List available components | Low |
| `add_component` | Add component to project | Medium |

## Configuration

### Config Files

Priority (highest to lowest):
1. Environment variables
2. Project config (`.chapgent.toml`)
3. User config (`~/.config/chapgent/config.toml`)
4. Defaults

### Environment Variables

```bash
# LLM settings
export CHAPGENT_PROVIDER="anthropic"
export CHAPGENT_MODEL="claude-sonnet-4-20250514"
export CHAPGENT_MAX_TOKENS=4096
export CHAPGENT_API_KEY="your-key"

# Provider-specific API keys (fallbacks)
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

### Config Commands

```bash
chapgent config show          # Display current config
chapgent config path          # Show config file locations
chapgent config init          # Create default config
chapgent config edit          # Open in $EDITOR
chapgent config set KEY VALUE # Set a config value

# Examples
chapgent config set llm.provider openai
chapgent config set llm.model gpt-4o
chapgent config set tui.theme dracula
```

### Example Config File

```toml
# ~/.config/chapgent/config.toml

[llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
max_tokens = 4096
# api_key = "..."  # Better to use env var

[tui]
theme = "dracula"

[permissions]
auto_approve_low_risk = true
session_override_allowed = true
```

## LLM Providers

Chapgent supports 16 providers via LiteLLM:

| Provider | Models | Notes |
|----------|--------|-------|
| `anthropic` | claude-sonnet-4, claude-opus-4, etc. | Default provider |
| `openai` | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | |
| `ollama` | llama3.1, codestral, deepseek-coder | Local, no API key |
| `groq` | llama-3.1-70b, mixtral-8x7b | Fast inference |
| `together_ai` | Various open models | |
| `fireworks_ai` | Fast Llama/Mixtral | |
| `mistral` | mistral-large, codestral | |
| `azure` | Azure OpenAI deployments | |
| `bedrock` | AWS Bedrock models | |
| `vertex_ai` | Google Vertex AI | |
| `cohere` | command-r, command-r-plus | |
| `replicate` | Various hosted models | |
| `huggingface` | HuggingFace Inference API | |
| `deepinfra` | Various open models | |
| `perplexity` | pplx-* models | |
| `anyscale` | Various open models | |

### Using Ollama (Local)

```bash
# Install and run Ollama
ollama pull llama3.1:70b

# Configure chapgent
chapgent config set llm.provider ollama
chapgent config set llm.model llama3.1:70b

# Start chatting (no API key needed)
chapgent chat
```

## CLI Reference

```bash
chapgent chat [--mock] [--session ID]  # Start TUI chat
chapgent tools [--category CAT]        # List available tools
chapgent sessions                       # List saved sessions
chapgent resume [SESSION_ID]           # Resume a session
chapgent config show|path|init|edit|set # Config management
chapgent setup                          # First-run setup wizard
chapgent help [TOPIC]                   # Show help
chapgent logs                           # Show log file location
chapgent report                         # Generate debug report
```

## Development

### Setup

```bash
git clone https://github.com/davewil/chapgent.git
cd chapgent
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest                              # Run all tests
pytest --cov=chapgent               # With coverage
pytest tests/test_tools/ -v         # Specific directory
pytest -k "test_read_file" -v       # Specific test pattern
```

### Code Quality

```bash
ruff check .           # Lint
ruff format .          # Format
mypy                   # Type check
```

## Architecture

```
src/chapgent/
├── cli.py              # CLI entry point (Click)
├── config/             # Configuration system
│   ├── loader.py       # Config file loading
│   ├── settings.py     # Pydantic models
│   ├── writer.py       # Config persistence
│   └── prompt.py       # System prompt handling
├── context/            # Project context detection
│   ├── detection.py    # Auto-detect project type
│   └── prompt.py       # Context-aware prompts
├── core/               # Core agent infrastructure
│   ├── agent.py        # Agent class
│   ├── loop.py         # Conversation loop
│   ├── provider.py     # LLM provider (LiteLLM)
│   ├── cache.py        # Tool result caching
│   ├── parallel.py     # Parallel tool execution
│   ├── recovery.py     # Error recovery
│   └── logging.py      # Loguru logging setup
├── session/            # Session management
│   ├── models.py       # Session/Message models
│   └── storage.py      # Session persistence
├── tools/              # Tool implementations
│   ├── base.py         # Tool decorator & registry
│   ├── registry.py     # Tool registration
│   ├── filesystem.py   # File operations
│   ├── git.py          # Git operations
│   ├── search.py       # grep, find, definitions
│   ├── shell.py        # Shell command execution
│   ├── testing.py      # Test runner
│   ├── scaffold.py     # Project scaffolding
│   └── web.py          # Web fetching
├── tui/                # Terminal UI (Textual)
│   ├── app.py          # Main application
│   ├── widgets.py      # Custom widgets
│   ├── screens.py      # Modal screens
│   ├── commands.py     # Slash command registry
│   ├── highlighter.py  # Syntax highlighting
│   ├── markdown.py     # Markdown rendering
│   ├── themes/         # Theme integration
│   └── styles.tcss     # TCSS styling
└── ux/                 # User experience
    ├── errors.py       # Friendly error messages
    ├── help.py         # Help system
    └── first_run.py    # Setup wizard
```

## License

MIT
