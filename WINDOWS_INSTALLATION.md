# Windows Installation Guide

Welcome to Ralph ML Loop CLI for Windows! This guide will help you get up and running.

## Prerequisites

### 1. Install Python

1. Download Python from https://python.org/downloads/
2. Run the installer
3. **Important:** Check the box **"Add Python to PATH"** during installation
4. Verify installation:
   ```cmd
   python --version
   # or
   py --version
   ```

### 2. Install Python Dependencies

Ralph ML Loop requires Python packages. Open Command Prompt or PowerShell and run:

```cmd
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Command Prompt:
venv\Scripts\activate

# PowerShell:
venv\Scripts\Activate.ps1

# Install dependencies
pip install pydantic rich openai
```

### 3. Get the Ralph ML Loop CLI

#### Option A: Download Pre-built Binary (Recommended)

1. Download the Windows binary from the [latest release](https://github.com/matthiaspetry/DeepLoop/releases)
2. Extract the ZIP file
3. Move `ralph-ml.exe` to a directory in your PATH (e.g., `C:\Users\YourName\bin`)
4. Open a new terminal and verify:
   ```cmd
   ralph-ml --version
   ```

#### Option B: Build from Source

1. Install Go from https://go.dev/dl/
2. During installation, add Go to your PATH
3. Clone the repository:
   ```cmd
   git clone https://github.com/matthiaspetry/DeepLoop.git
   cd DeepLoop
   ```
4. Build the CLI:
   ```cmd
   go build -o ralph-ml.exe ./cmd/ralph-ml
   ```
5. Move `ralph-ml.exe` to a directory in your PATH

## Usage

### Initialize a Project

```cmd
ralph-ml init
```

This creates `RALPH_ML_CONFIG.json` in the current directory.

### Start the ML Loop

```cmd
ralph-ml start "Create a model for MNIST classification with 98% accuracy"
```

### Check Status

```cmd
ralph-ml status
```

### Generate Report

```cmd
ralph-ml report
```

### Resume from State

```cmd
ralph-ml resume --state .\state\ralph_state.json --prompt "your original prompt"
```

## Windows-Specific Tips

### Virtual Environments

On Windows, Python virtual environments use `Scripts\` instead of `bin/`:

```
venv\
├── Scripts\
│   ├── python.exe
│   ├── python3.exe
│   └── Activate.ps1  (PowerShell)
│   └── activate.bat   (Command Prompt)
└── ...
```

The CLI automatically detects and uses `venv\Scripts\python.exe` when available.

### Python Launcher

Windows has a Python launcher (`py`) that helps manage multiple Python versions:

```cmd
# Use Python 3 (recommended)
py -3

# Check installed versions
py --list
```

The CLI prefers `py` on Windows if available.

### Path Separators

Windows uses backslashes (`\`) for paths, but the CLI handles this automatically:

```cmd
# Both work
ralph-ml start "test" --config C:\Users\Me\config.json
ralph-ml start "test" --config C:/Users/Me/config.json
```

### PowerShell vs Command Prompt

Both work, but there are some differences:

**Command Prompt:**
- Faster startup
- No profile loading
- Recommended for automation

**PowerShell:**
- Tab completion
- Better error messages
- Activation: `.\venv\Scripts\Activate.ps1`

The CLI works identically in both.

## Troubleshooting

### "python: command not found"

**Cause:** Python not in PATH

**Solution:**
1. Reinstall Python and check "Add Python to PATH"
2. Or manually add to PATH:
   - Search for "Environment Variables" in Windows
   - Edit "Path" under System or User variables
   - Add `C:\Python312` and `C:\Python312\Scripts`
3. Restart terminal

### "ModuleNotFoundError: No module named 'pydantic'"

**Cause:** Python dependencies not installed

**Solution:**
```cmd
# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install pydantic rich openai
```

### Long Path Names

Windows has a 260 character path limit. If you encounter this:

**Solution:** Enable long paths or use shorter directory names:
```cmd
# Use short project directory
mkdir ml
cd ml
ralph-ml init
```

### Execution Policy Error (PowerShell)

If you see "running scripts is disabled on this system":

**Solution:**
```powershell
# For current session
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# Or permanently (not recommended)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Performance Tips

### SSD vs HDD

ML training benefits greatly from SSDs. If possible:
- Place your data directory on SSD
- Place runs directory on SSD
- Keep temporary files on SSD

### Antivirus Exclusions

Some antivirus software slows down Python execution. Consider adding exclusions for:
- Your project directory
- Virtual environment (`venv\`)
- Python interpreter

## Getting Help

If you encounter issues:

1. Check the logs in `runs/` directories
2. Use `--help` flag for any command
3. Check the [GitHub Issues](https://github.com/matthiaspetry/DeepLoop/issues)
4. Verify Python and Go are in your PATH

## Next Steps

- Read the [README](../README.md) for full documentation
- Check [Example Configs](../RALPH_ML_CONFIG.json) for configuration options
- Explore the [Python CLI docs](../../ralph_ml/cli.py) for advanced usage

Happy training! 🦕
