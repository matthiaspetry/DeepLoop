# Go CLI for Ralph ML Loop

This directory contains the Go rewrite of the Python CLI for Ralph ML Loop. The Python training and orchestration logic remains in `ralph_ml/`, while the Go CLI provides a cross-platform, Windows-friendly interface.

## Project Structure

```
cli/
├── cmd/ralph-ml/          # Command-line interface
│   ├── main.go            # Entry point
│   ├── init.go            # init command
│   ├── start.go           # start command
│   ├── resume.go          # resume command
│   ├── status.go          # status command
│   └── report.go          # report command
├── pkg/                   # Shared packages
│   ├── config/            # Config loading/validation
│   ├── orchestrator/      # Python subprocess execution
│   ├── state/             # State file management
│   ├── paths/             # Path resolution
│   └── display/           # Terminal output formatting
└── scripts/               # Build and release scripts
```

## Commands

| Command | Description | Status |
|---------|-------------|--------|
| `init` | Initialize a new Ralph ML Loop project | ⏳ Not implemented |
| `start` | Start the ML loop with a prompt | ⏳ Not implemented |
| `resume` | Resume from a saved state | ⏳ Not implemented |
| `status` | Show status of recent runs | ⏳ Not implemented |
| `report` | Generate a final report | ⏳ Not implemented |

## Development Setup

### Prerequisites

- Go 1.21 or later
- Python 3.9+ (for training/orchestration)
- Dependencies from Python CLI (see `requirements.txt`)

### Installing Go

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install golang-go
```

**macOS:**
```bash
brew install go
```

**Windows:**
Download from https://go.dev/dl/

### Building

```bash
# From ralph-ml-loop directory
go build -o ralph-ml ./cmd/ralph-ml

# Run the CLI
./ralph-ml --help
```

### Cross-Compilation

```bash
# Windows (amd64)
GOOS=windows GOARCH=amd64 go build -o ralph-ml.exe ./cmd/ralph-ml

# macOS (arm64 - Apple Silicon)
GOOS=darwin GOARCH=arm64 go build -o ralph-ml-mac-arm64 ./cmd/ralph-ml

# macOS (amd64 - Intel)
GOOS=darwin GOARCH=amd64 go build -o ralph-ml-mac-amd64 ./cmd/ralph-ml

# Linux (arm64)
GOOS=linux GOARCH=arm64 go build -o ralph-ml-linux-arm64 ./cmd/ralph-ml
```

## Implementation Status

See [GO_CLI_IMPLEMENTATION_PLAN.md](../GO_CLI_IMPLEMENTATION_PLAN.md) for the full implementation plan.

### Completed
- ✅ Project structure created
- ✅ Command scaffolding (all 5 commands defined)
- ✅ Package structure created
- ✅ Implementation plan written

### In Progress
- ⏳ Phase 1: Basic commands (init, status)
- ⏳ Phase 2: Config & state management
- ⏳ Phase 3: Python orchestrator integration
- ⏳ Phase 4: Resume & report commands
- ⏳ Phase 5: Windows support & polish
- ⏳ Phase 6: Testing & documentation

## Dependencies

The Go CLI uses the following main dependencies:

- `github.com/spf13/cobra` - CLI framework
- (Additional dependencies to be added as needed)

## Notes

- The Go CLI is a thin wrapper around the Python training code
- All ML training and orchestration still happens in Python (`ralph_ml/`)
- The Go CLI provides:
  - Cross-platform binary distribution
  - Better Windows support
  - Faster startup
  - Consistent user experience across platforms
