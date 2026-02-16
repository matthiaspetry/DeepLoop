# Ralph ML Loop CLI - Go Version

Cross-platform command-line interface for Ralph ML Loop - autonomous deep learning improvement cycles.

## Features

- ✅ **Cross-platform binaries** - Windows, macOS, Linux
- ✅ **Fast startup** - Compiled Go binary, no Python overhead
- ✅ **Python integration** - Seamlessly calls Python training code
- ✅ **Auto-detection** - Finds Python interpreter and virtual environments
- ✅ **Real-time output** - Streams training progress live
- ✅ **Session management** - Organized run directories with state tracking
- ✅ **Report generation** - Markdown reports of all cycles

## Installation

### Quick Start (Pre-built Binary)

1. Download the latest binary for your platform:
   - [Linux (amd64)](https://github.com/matthiaspetry/DeepLoop/releases)
   - [Linux (arm64)](https://github.com/matthiaspetry/DeepLoop/releases)
   - [macOS (Intel)](https://github.com/matthiaspetry/DeepLoop/releases)
   - [macOS (Apple Silicon)](https://github.com/matthiaspetry/DeepLoop/releases)
   - [Windows](https://github.com/matthiaspetry/DeepLoop/releases)

2. Make it executable (Unix/Linux/macOS):
   ```bash
   chmod +x ralph-ml
   ```

3. Add to PATH:
   - **Unix/Linux/macOS**: `mv ralph-ml /usr/local/bin/` or `~/bin/`
   - **Windows**: Add to PATH via Environment Variables

4. Verify installation:
   ```bash
   ralph-ml --version
   ```

### Build from Source

1. Install Go 1.21 or later: https://go.dev/dl/

2. Clone repository:
   ```bash
   git clone https://github.com/matthiaspetry/DeepLoop.git
   cd DeepLoop
   ```

3. Build:
   ```bash
   go build -o ralph-ml ./cmd/ralph-ml
   ```

4. Add to PATH (see Quick Start step 3)

### Prerequisites

The Go CLI wraps Python ML code, so you need:

- Python 3.9+
- Virtual environment with dependencies (see [Python CLI README](../ralph_ml/cli.py))
- Optional: OpenCode for code generation

## Quick Start

### Initialize a Project

```bash
ralph-ml init
```

This creates `RALPH_ML_CONFIG.json` with default settings.

### Start Training Loop

```bash
ralph-ml start "Create a classifier for MNIST with 98% accuracy"
```

The CLI will:
1. Detect your Python environment
2. Create a session directory (`runs/run_YYYYMMDD_HHMMSS_000`)
3. Start the Python orchestrator
4. Stream real-time training output

### Check Status

```bash
ralph-ml status
```

Shows all runs and current state.

### Generate Report

```bash
ralph-ml report
```

Generates a markdown report of all cycles.

### Resume from State

```bash
ralph-ml resume --state ./state/ralph_state.json --prompt "your original prompt"
```

## Configuration

Configuration is done via `RALPH_ML_CONFIG.json`:

```json
{
  "project": {
    "name": "my-ml-project",
    "framework": "pytorch",
    "target_metric": {
      "name": "test_accuracy",
      "value": 0.85
    }
  },
  "data": {
    "root": "./data",
    "train_split": "train",
    "val_split": "val",
    "test_split": "test"
  },
  "safeguards": {
    "max_cycles": 10,
    "no_improvement_stop_cycles": 3,
    "min_improvement_delta": 0.002,
    "time_limit_per_cycle_minutes": 30,
    "token_budget_per_cycle": 100000
  },
  "execution": {
    "mode": "local",
    "python": "python",
    "train_cmd": "python train.py --config config.json",
    "eval_cmd": "python eval.py --config config.json"
  },
  "agents": {
    "code_model": "opencode",
    "analysis_model": "opencode",
    "thinking": "medium"
  },
  "paths": {
    "workspace": "./workspace",
    "runs": "./runs",
    "reports": "./reports",
    "state": "./state"
  },
  "observability": {
    "logger": "tensorboard",
    "save_stdout": true,
    "emit_events_jsonl": true
  }
}
```

## Commands Reference

### init

Initialize a new Ralph ML Loop project.

```bash
ralph-ml init [flags]

Flags:
  -c, --config string   Path to config file (default: RALPH_ML_CONFIG.json)
```

### start

Start the ML training loop with a prompt.

```bash
ralph-ml start [prompt] [flags]

Flags:
  -c, --config string        Path to config file
  --no-config               Ignore RALPH_ML_CONFIG.json
  --data-root string         Override dataset root path
  --framework string          Override framework (pytorch/tensorflow/jax)
  --max-cycles int          Override max optimization cycles
  -p, --python string        Python interpreter path (auto-detected)
  --target float             Override target metric value
```

### status

Show status of recent runs.

```bash
ralph-ml status
```

### report

Generate a markdown report from runs.

```bash
ralph-ml report [flags]

Flags:
  -r, --run string   Path to runs directory (default: ./runs)
  -o, --out string   Output report file (default: ./reports/final_report.md)
```

### resume

Resume a previous run from state.

```bash
ralph-ml resume [flags]

Flags:
  -s, --state string   Path to state file (default: ./state/ralph_state.json)
  -p, --prompt string  Original prompt used to start the run
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Go CLI (ralph-ml)              │
│              Cross-platform interface               │
└───────────────────────┬─────────────────────────┘
                        │
                        │ Start command
                        ▼
            ┌───────────────────────┐
            │  Python Orchestrator  │
            │   (subprocess)      │
            └───────────┬───────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   ML Training Loop   │
            │  (ralph_ml package) │
            └───────────┬───────────┘
                        │
            ┌───────────┴───────────┐
            │  Output Files        │
            │  - metrics.json     │
            │  - analysis.json    │
            │  - state.json      │
            └───────────────────────┘
```

## Project Structure

```
ralph-ml-loop/
├── cmd/ralph-ml/          # Go CLI commands
│   ├── main.go
│   ├── init.go
│   ├── start.go
│   ├── resume.go
│   ├── status.go
│   └── report.go
├── pkg/                    # Go packages
│   ├── config/           # Configuration handling
│   ├── orchestrator/     # Python execution
│   ├── state/            # State management
│   ├── paths/            # Path resolution
│   └── display/          # Terminal output
├── ralph_ml/              # Python ML code (unchanged)
│   ├── orchestrator.py
│   ├── orchestrator_cli.py
│   └── ...
├── scripts/
│   └── build.sh          # Cross-platform build
└── README_GO.md           # This file
```

## Development

### Building

```bash
# Single platform
go build -o ralph-ml ./cmd/ralph-ml

# All platforms
./scripts/build.sh
```

### Running Tests

```bash
# Run all tests
go test ./...

# Run specific package tests
go test ./pkg/config
go test ./pkg/state
go test ./pkg/paths
```

### Adding a New Command

1. Create `cmd/ralph-ml/<command>.go`
2. Import packages as needed
3. Create a cobra.Command struct
4. Add to `rootCmd` in `main.go`
5. Rebuild and test

## Migration from Python CLI

See [MIGRATION.md](MIGRATION.md) for detailed migration guide.

**Quick comparison:**

| Feature | Python CLI | Go CLI |
|---------|------------|----------|
| Startup speed | ~500ms | ~10ms |
| Binary size | N/A (requires Python) | ~10MB |
| Windows support | Limited | Full |
| Dependencies | Python + libs | Go binary only |
| Config | RALPH_ML_CONFIG.json | Same (compatible) |
| State | Same | Same (compatible) |

## Platform-Specific Guides

- [Windows Installation Guide](WINDOWS_INSTALLATION.md) - Detailed Windows setup
- [macOS](#installation) - See Quick Start
- [Linux](#installation) - See Quick Start

## Troubleshooting

### Python Not Found

**Error:** `python not found or not accessible`

**Solution:**
1. Install Python 3.9+
2. Add to PATH (Windows: check "Add to PATH" during install)
3. Verify: `python --version`

### Virtual Environment Issues

**Error:** `ModuleNotFoundError`

**Solution:**
```bash
# Activate venv
source venv/bin/activate  # Unix/Linux/macOS
venv\Scripts\activate     # Windows
```

### Path Issues

**Error:** Long path names (Windows 260 char limit)

**Solution:** Use shorter directory names or enable long paths.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `go test ./...`
5. Submit a pull request

## License

[Insert your license here]

## Links

- [Full Implementation Plan](GO_CLI_IMPLEMENTATION_PLAN.md)
- [Python CLI Documentation](../ralph_ml/cli.py)
- [Progress Tracker](PROGRESS.md)
- [GitHub Repository](https://github.com/matthiaspetry/DeepLoop)

---

Made with 🦕 by the Ralph ML Loop team
