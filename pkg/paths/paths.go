// Package paths handles path resolution for Ralph ML Loop.
package paths

import (
	"path/filepath"
)

// Paths holds all resolved paths for a Ralph ML Loop run.
type Paths struct {
	Workspace string
	Runs      string
	Reports   string
	State     string
	Data      string
}

// ResolvePaths resolves all configuration paths to absolute paths.
func ResolvePaths(configPaths map[string]string) (*Paths, error) {
	// TODO: Implement path resolution with home dir expansion
	return &Paths{}, nil
}

// CreateDirectories creates all directories in the Paths struct.
func (p *Paths) CreateDirectories() error {
	// TODO: Implement directory creation
	return nil
}

// GetRunDir returns the directory for a specific cycle.
func GetRunDir(runsDir string, cycleNum int) string {
	return filepath.Join(runsDir, filepath.Sprintf("cycle_%04d", cycleNum))
}
