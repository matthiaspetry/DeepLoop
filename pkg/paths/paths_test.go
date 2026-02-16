package paths

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/config"
)

func TestResolvePaths(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := config.NewDefaultConfig()
	cfg.Paths.Workspace = filepath.Join(tmpDir, "workspace")
	cfg.Paths.Runs = filepath.Join(tmpDir, "runs")
	cfg.Paths.Reports = filepath.Join(tmpDir, "reports")
	cfg.Paths.State = filepath.Join(tmpDir, "state")
	cfg.Data.Root = filepath.Join(tmpDir, "data")

	// Resolve paths
	resolved, err := ResolvePaths(cfg)
	if err != nil {
		t.Fatalf("Failed to resolve paths: %v", err)
	}

	// Verify paths are absolute
	if !filepath.IsAbs(resolved.Workspace) {
		t.Error("Workspace path should be absolute")
	}

	if !filepath.IsAbs(resolved.Runs) {
		t.Error("Runs path should be absolute")
	}

	if !filepath.IsAbs(resolved.Reports) {
		t.Error("Reports path should be absolute")
	}

	if !filepath.IsAbs(resolved.State) {
		t.Error("State path should be absolute")
	}

	if !filepath.IsAbs(resolved.Data) {
		t.Error("Data path should be absolute")
	}
}

func TestCreateRunDirectory(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := config.NewDefaultConfig()
	cfg.Paths.Runs = tmpDir

	p, err := ResolvePaths(cfg)
	if err != nil {
		t.Fatalf("Failed to resolve paths: %v", err)
	}

	// Create run directory
	runRoot, err := p.CreateRunDirectory()
	if err != nil {
		t.Fatalf("Failed to create run directory: %v", err)
	}

	// Verify run root exists
	if _, err := os.Stat(runRoot); os.IsNotExist(err) {
		t.Errorf("Run root directory was not created: %s", runRoot)
	}

	// Verify subdirectories exist
	expectedSubdirs := []string{
		filepath.Join(runRoot, "workspace"),
		filepath.Join(runRoot, "cycles"),
		filepath.Join(runRoot, "reports"),
		filepath.Join(runRoot, "state"),
	}

	for _, subdir := range expectedSubdirs {
		if _, err := os.Stat(subdir); os.IsNotExist(err) {
			t.Errorf("Subdirectory was not created: %s", subdir)
		}
	}

	// Verify run root is in runs dir
	if filepath.Dir(runRoot) != tmpDir {
		t.Errorf("Run root should be in runs directory")
	}
}

func TestGetCycleDir(t *testing.T) {
	runsDir := "/tmp/runs"
	cycleNum := 5

	cycleDir := GetCycleDir(runsDir, cycleNum)
	expected := "/tmp/runs/cycle_0005"

	if cycleDir != expected {
		t.Errorf("Expected '%s', got '%s'", expected, cycleDir)
	}
}

func TestGetSessionCycleDir(t *testing.T) {
	runRoot := "/tmp/runs/run_20260101_120000"
	cycleNum := 3

	cycleDir := GetSessionCycleDir(runRoot, cycleNum)
	expected := "/tmp/runs/run_20260101_120000/cycles/cycle_0003"

	if cycleDir != expected {
		t.Errorf("Expected '%s', got '%s'", expected, cycleDir)
	}
}

func TestGetStatePath(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := config.NewDefaultConfig()
	cfg.Paths.State = tmpDir

	p, err := ResolvePaths(cfg)
	if err != nil {
		t.Fatalf("Failed to resolve paths: %v", err)
	}

	// Test with no run root
	statePath := p.GetStatePath()
	if statePath != filepath.Join(tmpDir, "ralph_state.json") {
		t.Errorf("Expected '%s', got '%s'", filepath.Join(tmpDir, "ralph_state.json"), statePath)
	}

	// Test with run root
	p.RunRoot = filepath.Join(tmpDir, "run_test")
	statePathWithRoot := p.GetStatePath()
	expected := filepath.Join(tmpDir, "run_test", "state", "ralph_state.json")

	if statePathWithRoot != expected {
		t.Errorf("Expected '%s', got '%s'", expected, statePathWithRoot)
	}
}

func TestIsWindows(t *testing.T) {
	// We can't easily test platform detection without mocking
	// Just verify the function exists and returns a bool
	result := IsWindows()
	if result != (false) && result != (true) {
		t.Error("IsWindows should return a bool")
	}
}

func TestIsLinux(t *testing.T) {
	result := IsLinux()
	if result != (false) && result != (true) {
		t.Error("IsLinux should return a bool")
	}
}

func TestIsMac(t *testing.T) {
	result := IsMac()
	if result != (false) && result != (true) {
		t.Error("IsMac should return a bool")
	}
}

func TestNormalizePath(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"./test", "test"},
		{"../test", "../test"},
		{"/tmp/test", "/tmp/test"},
		{"test/.", "test"},
	}

	for _, test := range tests {
		result := normalizePath(test.input)
		if result != test.expected {
			t.Errorf("normalizePath(%q) = %q, want %q", test.input, result, test.expected)
		}
	}
}
