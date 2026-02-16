package paths

import (
	"fmt"
	"os"
	"path/filepath"
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
	p.Workspace = workspace

	// Resolve runs directory
	runs, err := filepath.Abs(cfg.Paths.Runs)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve runs path: %w", err)
	}
	p.Runs = runs

	// Resolve reports directory
	reports, err := filepath.Abs(cfg.Paths.Reports)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve reports path: %w", err)
	}
	p.Reports = reports

	// Resolve state directory
	state, err := filepath.Abs(cfg.Paths.State)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve state path: %w", err)
	}
	p.State = state

	// Resolve data root
	data, err := filepath.Abs(cfg.Data.Root)
	if err != nil {
		return nil, fmt.Errorf("failed to resolve data path: %w", err)
	}
	p.Data = data

	return p, nil
}

// CreateRunDirectory creates a new session-specific run directory.
func (p *Paths) CreateRunDirectory() (string, error) {
	// Generate run ID based on timestamp
	runID := time.Now().Format("run_20060102_150405") + "_000"
	
	runRoot := filepath.Join(p.Runs, runID)
	p.RunRoot = runRoot

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

	return runRoot, nil
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

// GetCycleDir returns the directory for a specific cycle.
func GetCycleDir(runsDir string, cycleNum int) string {
	return filepath.Join(runsDir, fmt.Sprintf("cycle_%04d", cycleNum))
}

// GetSessionCycleDir returns the directory for a specific cycle within a session.
func GetSessionCycleDir(runRoot string, cycleNum int) string {
	return filepath.Join(runRoot, "cycles", fmt.Sprintf("cycle_%04d", cycleNum))
}

// GetStatePath returns the path to the state file within a run directory.
func (p *Paths) GetStatePath() string {
	if p.RunRoot != "" {
		return filepath.Join(p.RunRoot, "state", "ralph_state.json")
	}
	return filepath.Join(p.State, "ralph_state.json")
}

// UpdateFromConfig updates paths from a config object.
func (p *Paths) UpdateFromConfig(cfg *config.Config) error {
	// Update paths from config
	p.Workspace = cfg.Paths.Workspace
	p.Runs = cfg.Paths.Runs
	p.Reports = cfg.Paths.Reports
	p.State = cfg.Paths.State
	p.Data = cfg.Data.Root

	return nil
}
