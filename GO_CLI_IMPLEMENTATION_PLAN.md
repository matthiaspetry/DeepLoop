# Go CLI Rewrite Implementation Plan

## Overview
Rewrite the Python CLI (`ralph_ml/cli.py`) in Go while keeping the Python training/orchestration logic intact. The Go CLI will be a thin wrapper that:
- Parses commands and arguments
- Manages configuration
- Invokes Python scripts as subprocesses
- Displays progress and results
- Provides cross-platform binaries (especially Windows)

## Architecture

```
ralph-ml (Go binary)
    ├── cmd/               # Command implementations
    │   ├── init.go        # init command
    │   ├── start.go       # start command
    │   ├── resume.go      # resume command
    │   ├── status.go      # status command
    │   └── report.go      # report command
    ├── pkg/               # Shared packages
    │   ├── config/        # Config loading/validation
    │   ├── orchestrator/  # Python orchestrator invocation
    │   ├── state/         # State file management
    │   ├── display/       # Terminal output/formatting
    │   └── paths/         # Path resolution
    └── main.go            # Entry point
```

## Phases

### Phase 1: Project Setup & Basic Commands
**Goal**: Get a working Go CLI skeleton with init and status commands

1. **Initialize Go module**
   - Create `go.mod`
   - Set up project structure
   - Add CLI framework (choose: `cobra` or `urfave/cli`)

2. **Implement `init` command**
   - Create default config file
   - Validate config JSON schema
   - Mirror Python behavior exactly

3. **Implement `status` command**
   - List runs directories
   - Parse state files
   - Display formatted tables

**Deliverable**: Working binary with `init` and `status` commands

---

### Phase 2: Config & State Management
**Goal**: Shared packages for config and state handling

1. **Config package (`pkg/config/`)**
   - Load JSON config files
   - Merge CLI overrides with config
   - Path resolution (absolute paths, home dir expansion)
   - Default values matching Python

2. **State package (`pkg/state/`)**
   - Load/save JSON state files
   - Parse cycle history
   - Extract metrics and status
   - Validate JSON schema

3. **Paths package (`pkg/paths/`)**
   - Resolve run directories
   - Create directories as needed
   - Handle session vs legacy layouts

**Deliverable**: Robust config/state handling with tests

---

### Phase 3: Python Orchestrator Integration
**Goal**: Call Python orchestrator from Go

1. **Orchestrator package (`pkg/orchestrator/`)**
   - Locate Python interpreter
   - Execute `orchestrator.py` as subprocess
   - Stream stdout/stderr in real-time
   - Handle timeouts and interrupts
   - Capture exit codes

2. **Display package (`pkg/display/`)**
   - Colorized output (Windows + Unix)
   - Progress indicators
   - Table formatting for runs/status
   - Error messages

3. **Implement `start` command**
   - Parse prompt and arguments
   - Load/merge config
   - Create run directory
   - Invoke Python orchestrator
   - Stream output

**Deliverable**: Full `start` command that runs Python training

---

### Phase 4: Resume & Report Commands
**Goal**: Complete the remaining CLI commands

1. **Implement `resume` command**
   - Load state file
   - Reconstruct config
   - Invoke orchestrator with resume flag
   - Display current cycle/best metric

2. **Implement `report` command**
   - Scan cycles directory
   - Parse metrics and analysis files
   - Generate markdown report
   - Handle multiple run layouts

**Deliverable**: Complete feature parity with Python CLI

---

### Phase 5: Cross-Platform Polish
**Goal**: Windows support and UX improvements

1. **Windows compatibility**
   - Path handling (backslashes)
   - Python detection on Windows
   - Virtual environment support
   - Color codes for CMD/PowerShell

2. **User experience**
   - Better error messages
   - Progress bars for long operations
   - Helpful hints for common issues
   -- Auto-detect and suggest Python install

3. **Build & distribution**
   - Cross-compilation scripts
   - Build for Windows, macOS, Linux
   - Package as single binary
   - Optional installer generation

**Deliverable**: Production-ready cross-platform binaries

---

### Phase 6: Testing & Documentation
**Goal**: Ensure reliability and easy adoption

1. **Testing**
   - Unit tests for config/state parsing
   - Integration tests for Python invocation
   - End-to-end tests on sample projects
   - Windows-specific testing

2. **Documentation**
   - Go doc comments
   - Installation guide
   - Windows setup guide
   - Migration guide from Python CLI
   - Contribution guidelines

3. **CI/CD**
   - GitHub Actions for building
   - Multi-platform testing matrix
   - Automated releases with binaries

**Deliverable**: Well-tested, documented, release-ready CLI

---

## Key Decisions

### CLI Framework
**Choice**: `cobra` (used by kubectl, docker, hugo)
- **Pros**: Mature ecosystem, subcommands, flag handling, shell completion
- **Cons**: Slightly more verbose
- **Alternative**: `urfave/cli` (simpler, used by Heroku CLI)

**Recommendation**: `cobra` for its extensibility and community support

### Config Handling
**Choice**: Load JSON in Go, mirror Python data structures
- **Pros**: No Python dependency for basic commands (init/status)
- **Cons**: Must keep in sync with Python config
- **Mitigation**: Generate Go structs from Pydantic models, add validation tests

### Python Integration
**Choice**: Subprocess execution (not ctypes/cgo)
- **Pros**: Clean separation, easier debugging, no build dependencies
- **Cons**: Slightly slower startup
- **Tradeoff**: Acceptable for long-running training jobs

### Output Formatting
**Choice**: Use Go libs (tablewriter, color, bubbletea)
- **Pros**: Native Windows support, consistent UX
- **Cons**: More Go code
- **Alternative**: Delegate to Python rich library (loses Windows control)

---

## File Structure

```
ralph-ml-loop/
├── go.mod                          # Go module definition
├── go.sum                          # Dependencies lock
├── cmd/
│   └── ralph-ml/
│       └── main.go                 # Entry point
├── pkg/
│   ├── config/
│   │   ├── config.go               # Config structs & loading
│   │   └── config_test.go
│   ├── orchestrator/
│   │   ├── orchestrator.go         # Python execution
│   │   └── orchestrator_test.go
│   ├── state/
│   │   ├── state.go                # State file handling
│   │   └── state_test.go
│   ├── paths/
│   │   ├── paths.go                # Path resolution
│   │   └── paths_test.go
│   └── display/
│       ├── display.go              # Terminal output
│       └── tables.go               # Table formatting
└── scripts/
    ├── build.sh                    # Cross-compilation script
    └── release.sh                  # Release automation
```

---

## Commands Mapping

| Python Command | Go Command | Phase |
|---------------|------------|-------|
| `init` | `init` | 1 |
| `status` | `status` | 1 |
| `start` | `start` | 3 |
| `resume` | `resume` | 4 |
| `report` | `report` | 4 |

---

## Success Criteria

- [ ] All Python CLI commands work identically in Go
- [ ] Windows users can run without Python installation issues
- [ ] Binary distribution for Windows, macOS, Linux (amd64/arm64)
- [ ] Documentation for Windows setup
- [ ] Test coverage >80% for core packages
- [ ] Zero breaking changes to Python training/orchestrator
- [ ] Performance: CLI startup <100ms on modern hardware

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Config drift (Go vs Python) | High | Shared JSON schema, integration tests |
| Python path issues on Windows | High | Auto-detect, virtual env support, clear docs |
| Terminal output differs | Medium | Extensive output comparison testing |
| Dependency bloat | Low | Minimal external deps (cobra, tablewriter) |
| Windows color codes | Low | Use cross-platform color libraries |

---

## Next Steps

1. ✅ Create branch `feature/go-cli-rewrite`
2. 🔄 **Initialize Go project** (`go mod init github.com/matthiaspetry/DeepLoop/cli`)
3. ⏳ Set up basic cobra structure
4. ⏳ Implement `init` and `status` (Phase 1)
5. ⏳ Continue with remaining phases

Ready to start Phase 1?
