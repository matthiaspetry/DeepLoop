package paths

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/config"
)

// Paths holds all resolved paths for a Ralph ML Loop run.
type Paths struct {
	Workspace string
	Runs      string
	Reports   string
	State     string
	Data      string
	RunRoot   string // The session-specific run directory
}

// ResolvePaths resolves all configuration paths to absolute paths.
func ResolvePaths(cfg *config.Config) (*Paths, error) {
	p := &Paths{}

	// Resolve workspace to absolute path
	workspace, err := filepath.Abs(cfg.Paths.Workspace)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve workspace path: %w", err)
	}
	p.Workspace = normalizePath(workspace)

	// Resolve runs directory
	runs, err := filepath.Abs(cfg.Paths.Runs)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve runs path: %w", err)
	}
	p.Runs = normalizePath(runs)

	// Resolve reports directory
	reports, err := filepath.Abs(cfg.Paths.Reports)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve reports path: %w", err)
	}
	p.Reports = normalizePath(reports)

	// Resolve state directory
	state, err := filepath.Abs(cfg.Paths.State)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve state path: %w", err)
	}
	p.State = normalizePath(state)

	// Resolve data root
	data, err := filepath.Abs(cfg.Data.Root)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve data path: %w", err)
	}
	p.Data = normalizePath(data)

	return p, nil
}

// CreateRunDirectory creates a new session-specific run directory.
func (p *Paths) CreateRunDirectory() (string, error) {
	// Generate run ID based on timestamp
	runID := time.Now().Format("run_20060102_150405") + "_000"
	
	runRoot := filepath.Join(p.Runs, runID)
	p.RunRoot = normalizePath(runRoot)

	// Create run directory structure
	subdirs := []string{
		runRoot,
		filepath.Join(runRoot, "workspace"),
		filepath.Join(runRoot, "cycles"),
		filepath.Join(runRoot, "reports"),
		filepath.Join(runRoot, "state"),
	}

	for _, dir := range subdirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return "", fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	return normalizePath(runRoot), nil
}

// CreateDirectories creates all directories in the Paths struct.
func (p *Paths) CreateDirectories() error {
	dirs := []string{
		p.Workspace,
		p.Runs,
		p.Reports,
		p.State,
		p.Data,
	}

	for _, dir := range dirs {
		if dir == "" {
			continue
		}
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	return nil
}

// GetCycleDir returns directory for a specific cycle.
func GetCycleDir(runsDir string, cycleNum int) string {
	return normalizePath(filepath.Join(runsDir, fmt.Sprintf("cycle_%04d", cycleNum)))
}

// GetSessionCycleDir returns directory for a specific cycle within a session.
func GetSessionCycleDir(runRoot string, cycleNum int) string {
	return normalizePath(filepath.Join(runRoot, "cycles", fmt.Sprintf("cycle_%04d", cycleNum)))
}

// GetStatePath returns path to state file within a run directory.
func (p *Paths) GetStatePath() string {
	if p.RunRoot != "" {
		return normalizePath(filepath.Join(p.RunRoot, "state", "ralph_state.json"))
	}
	return normalizePath(filepath.Join(p.State, "ralph_state.json"))
}

// UpdateFromConfig updates paths from a config object.
func (p *Paths) UpdateFromConfig(cfg *config.Config) error {
	// Update paths from config
	p.Workspace = normalizePath(cfg.Paths.Workspace)
	p.Runs = normalizePath(cfg.Paths.Runs)
	p.Reports = normalizePath(cfg.Paths.Reports)
	p.State = normalizePath(cfg.Paths.State)
	p.Data = normalizePath(cfg.Data.Root)

	return nil
}

// normalizePath normalizes a path for the current OS.
func normalizePath(path string) string {
	// Clean the path to remove any . or .. elements
	path = filepath.Clean(path)
	
	// On Windows, paths are already normalized by filepath.Clean
	// On Unix, ensure we're using forward slashes (Go's default)
	return path
}

// IsWindows returns true if running on Windows.
func IsWindows() bool {
	return runtime.GOOS == "windows"
}

// IsLinux returns true if running on Linux.
func IsLinux() bool {
	return runtime.GOOS == "linux"
}

// IsMac returns true if running on macOS.
func IsMac() bool {
	return runtime.GOOS == "darwin"
}
