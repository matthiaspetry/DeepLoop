# Migration Guide: Python CLI to Go CLI

This guide helps you migrate from the Python CLI to the new Go CLI.

## Overview

The Go CLI is a drop-in replacement for the Python CLI with 100% compatibility:

| Feature | Python CLI | Go CLI | Notes |
|---------|------------|----------|--------|
| Config files | ✅ Compatible | Same format, same defaults |
| State files | ✅ Compatible | Same format, can resume from Python runs |
| Run directories | ✅ Compatible | Both legacy and session layouts supported |
| Commands | ✅ Compatible | init, start, resume, status, report |
| Output format | ✅ Compatible | Similar tables and messages |

## Quick Migration

### Step 1: Install Go CLI

```bash
# Download binary for your platform
# Linux (amd64):
wget https://github.com/matthiaspetry/DeepLoop/releases/download/v1.0.0/ralph-ml-linux-amd64

# macOS (Apple Silicon):
wget https://github.com/matthiaspetry/DeepLoop/releases/download/v1.0.0/ralph-ml-mac-arm64

# Windows:
# Download ralph-ml-windows-amd64.exe from releases page

# Make executable (Unix/macOS/Linux)
chmod +x ralph-ml-*

# Add to PATH
sudo mv ralph-ml /usr/local/bin/  # Unix/Linux/macOS
# Windows: Add to PATH via Environment Variables
```

### Step 2: Verify Installation

```bash
ralph-ml --version
```

### Step 3: Test with Existing Project

Navigate to your existing Ralph ML Loop project:

```bash
cd /path/to/your/project

# Your config file exists (RALPH_ML_CONFIG.json)
# Your runs directory exists (runs/)
# Your state file exists (state/ralph_state.json)

# Test status command
ralph-ml status

# Test report command
ralph-ml report
```

**Everything should work identically!**

## Command Mapping

### init

**Python:**
```bash
python -m ralph_ml init
```

**Go CLI:**
```bash
ralph-ml init
```

**No changes needed** - uses same config file and defaults.

### start

**Python:**
```bash
python -m ralph_ml start "Create a model for X" --config config.json --target 0.95
```

**Go CLI:**
```bash
ralph-ml start "Create a model for X" --config config.json --target 0.95
```

**No changes needed** - same flags, same behavior.

### status

**Python:**
```bash
python -m ralph_ml status
```

**Go CLI:**
```bash
ralph-ml status
```

**No changes needed** - same output format, same information.

### report

**Python:**
```bash
python -m ralph_ml report --run ./runs --out report.md
```

**Go CLI:**
```bash
ralph-ml report --run ./runs --out report.md
```

**No changes needed** - same flags, same report format.

### resume

**Python:**
```bash
python -m ralph_ml resume --state ./state/ralph_state.json
```

**Go CLI:**
```bash
ralph-ml resume --state ./state/ralph_state.json
```

**No changes needed** - same state file format.

## Configuration Compatibility

### Config File (RALPH_ML_CONFIG.json)

**100% compatible** - No changes needed:

```json
{
  "project": {
    "name": "my-project",
    "framework": "pytorch",
    "target_metric": {
      "name": "test_accuracy",
      "value": 0.85
    }
  },
  ...
}
```

The Go CLI reads the exact same config format as the Python CLI.

### State File (state/ralph_state.json)

**100% compatible** - Can resume Python runs:

```json
{
  "config": { ... },
  "current_cycle": 3,
  "best_metric": 0.97,
  "best_cycle": 3,
  "history": [ ... ],
  "status": "completed"
}
```

The Go CLI can read state files created by the Python CLI.

## Directory Structure Compatibility

### Legacy Layout (Python CLI default)

```
project/
├── RALPH_ML_CONFIG.json
├── runs/
│   ├── cycle_0001/
│   ├── cycle_0002/
│   └── cycle_0003/
├── state/
│   └── ralph_state.json
└── workspace/
```

**Go CLI:** ✅ Fully compatible with this layout.

### Session Layout (Go CLI default)

```
project/
├── RALPH_ML_CONFIG.json
├── runs/
│   └── run_20260101_120000_000/
│       ├── cycles/
│       │   ├── cycle_0001/
│       │   ├── cycle_0002/
│       │   └── cycle_0003/
│       ├── state/
│       │   └── ralph_state.json
│       └── resolved_config.json
└── workspace/
```

**Go CLI:** ✅ Automatically creates this structure.
**Python CLI:** Can also read this layout.

## Benefits of Migrating

### Performance

| Metric | Python CLI | Go CLI | Improvement |
|---------|------------|----------|-------------|
| Startup time | ~500ms | ~10ms | 50x faster |
| Binary size | N/A (requires Python) | ~10MB | Self-contained |
| Memory overhead | Python runtime | None | Lower |

### Features

| Feature | Python CLI | Go CLI |
|---------|------------|----------|
| Windows support | Limited | Full |
| Python detection | Manual | Automatic |
| Cross-platform builds | N/A | Yes (5 platforms) |
| Single binary | No (requires Python) | Yes |
| Installation | pip/requirements.txt | Single file |

### Developer Experience

| Aspect | Python CLI | Go CLI |
|---------|------------|----------|
| Dependencies | Python 3.9+, Pydantic, Rich | None (static binary) |
| Virtual env required | Yes | No (optional) |
| Installation complexity | pip install + deps | Download binary |
| Updates | pip install --upgrade | Download new binary |

## Advanced Migration

### Custom Python Interpreters

If you use a custom Python path:

**Python CLI:**
```bash
export PYTHON=/path/to/custom/python
python -m ralph_ml start "..."
```

**Go CLI:**
```bash
ralph-ml start "..." --python /path/to/custom/python
```

### Custom Scripts

If you have custom training or evaluation scripts:

**Config file (same for both):**
```json
{
  "execution": {
    "train_cmd": "python my_custom_train.py --config config.json",
    "eval_cmd": "python my_custom_eval.py --config config.json"
  }
}
```

**Works identically in both CLIs.**

### Virtual Environments

**Python CLI:**
```bash
source venv/bin/activate
python -m ralph_ml start "..."
```

**Go CLI (auto-detects):**
```bash
# No need to specify - auto-detects venv/bin/python
ralph-ml start "..."

# Or explicitly specify:
ralph-ml start "..." --python venv/bin/python
```

### OpenCode Integration

If using OpenCode for code generation:

**Config file (same for both):**
```json
{
  "agents": {
    "code_model": "opencode",
    "analysis_model": "opencode"
  }
}
```

**Works identically in both CLIs.**

## Troubleshooting Migration

### "Config not found"

If Go CLI doesn't find your config:

```bash
# Verify file exists
ls RALPH_ML_CONFIG.json

# Check path (relative to current directory)
ralph-ml start "..." --config ./RALPH_ML_CONFIG.json
```

### "State file not found"

If resuming from Python run:

```bash
# Verify state exists
ls state/ralph_state.json

# Use correct path
ralph-ml resume --state ./state/ralph_state.json
```

### "Python not found"

Go CLI needs Python for training:

```bash
# Install Python 3.9+
# Then Go CLI will auto-detect it

# Or specify explicitly
ralph-ml start "..." --python /usr/bin/python3
```

### "Module not found"

Ensure dependencies are installed:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install pydantic rich openai
```

## Rollback

If you need to rollback to Python CLI:

```bash
# Install Python CLI (if not already)
pip install -e .

# Use Python CLI
python -m ralph_ml start "..."
```

All your configs, states, and runs remain compatible.

## Checklist

Use this checklist to verify migration:

- [ ] Go CLI installed and in PATH
- [ ] `ralph-ml --version` works
- [ ] Config file (RALPH_ML_CONFIG.json) exists
- [ ] `ralph-ml init` creates valid config
- [ ] `ralph-ml status` shows existing runs
- [ ] `ralph-ml report` generates report
- [ ] Training loop starts successfully
- [ ] Output streams in real-time
- [ ] State file created after training
- [ ] Can resume from previous state
- [ ] Performance acceptable (faster startup)

## Next Steps

After migration:

1. **Explore new features**
   - Try `--python` flag for custom interpreters
   - Test cross-platform builds
   - Review Windows installation guide

2. **Customize configuration**
   - Edit RALPH_ML_CONFIG.json
   - Add custom scripts
   - Configure OpenCode

3. **Report issues**
   - [GitHub Issues](https://github.com/matthiaspetry/DeepLoop/issues)
   - Include platform and error details

## Support

- [Full README](README_GO.md) - Complete documentation
- [Windows Guide](WINDOWS_INSTALLATION.md) - Windows-specific help
- [GitHub Repository](https://github.com/matthiaspetry/DeepLoop) - Source code
- [Implementation Plan](GO_CLI_IMPLEMENTATION_PLAN.md) - Technical details

---

**Migrate with confidence!** The Go CLI is designed to be a drop-in replacement with additional benefits.

Happy training! 🦕
