package state

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadState(t *testing.T) {
	tmpDir := t.TempDir()
	statePath := filepath.Join(tmpDir, "test_state.json")

	// Create test state
	testState := &State{
		Config: map[string]interface{}{
			"project": map[string]interface{}{
				"name": "test-project",
			},
		},
		CurrentCycle: 5,
		BestMetric:  float64Ptr(0.95),
		BestCycle:    3,
		Status:       "running",
	}

	// Save state
	err := SaveState(statePath, testState)
	if err != nil {
		t.Fatalf("Failed to save state: %v", err)
	}

	// Load state
	loadedState, err := LoadState(statePath)
	if err != nil {
		t.Fatalf("Failed to load state: %v", err)
	}

	// Verify values
	if loadedState.CurrentCycle != 5 {
		t.Errorf("Expected current cycle 5, got %d", loadedState.CurrentCycle)
	}

	if loadedState.Status != "running" {
		t.Errorf("Expected status 'running', got '%s'", loadedState.Status)
	}

	if loadedState.BestMetric == nil || *loadedState.BestMetric != 0.95 {
		t.Errorf("Expected best metric 0.95, got %v", loadedState.BestMetric)
	}
}

func TestSaveState(t *testing.T) {
	tmpDir := t.TempDir()
	statePath := filepath.Join(tmpDir, "test_save.json")

	testState := &State{
		Config:       map[string]interface{}{},
		CurrentCycle: 1,
		Status:       "completed",
	}

	err := SaveState(statePath, testState)
	if err != nil {
		t.Fatalf("Failed to save state: %v", err)
	}

	// Verify file exists
	if _, err := os.Stat(statePath); os.IsNotExist(err) {
		t.Error("State file was not created")
	}

	// Verify directory was created
	stateDir := filepath.Dir(statePath)
	if _, err := os.Stat(stateDir); os.IsNotExist(err) {
		t.Error("State directory was not created")
	}
}

func TestScanRuns(t *testing.T) {
	tmpDir := t.TempDir()
	runsDir := filepath.Join(tmpDir, "runs")

	// Create test run directories
	os.MkdirAll(filepath.Join(runsDir, "cycle_0001"), 0755)
	os.MkdirAll(filepath.Join(runsDir, "cycle_0002"), 0755)
	os.MkdirAll(filepath.Join(runsDir, "cycle_0003"), 0755)

	// Add metrics to one cycle
	metricsPath := filepath.Join(runsDir, "cycle_0001", "metrics.json")
	os.WriteFile(metricsPath, []byte(`{"cycle": 1, "result": {"test_accuracy": 0.9}}`), 0644)

	// Scan runs
	runs, _, err := ScanRuns(runsDir)
	if err != nil {
		t.Fatalf("Failed to scan runs: %v", err)
	}

	// Verify we found 3 runs
	if len(runs) != 3 {
		t.Errorf("Expected 3 runs, got %d", len(runs))
	}

	// Verify first run is complete
	if runs[0].Status != "✅ Complete" {
		t.Errorf("Expected first run to be complete, got '%s'", runs[0].Status)
	}

	// Verify second run is incomplete
	if runs[1].Status != "⏳ Incomplete" {
		t.Errorf("Expected second run to be incomplete, got '%s'", runs[1].Status)
	}
}

func TestScanRunsWithSession(t *testing.T) {
	tmpDir := t.TempDir()
	runsDir := filepath.Join(tmpDir, "runs")

	// Create session directory
	sessionID := "run_20260101_120000_000"
	sessionDir := filepath.Join(runsDir, sessionID)
	cyclesDir := filepath.Join(sessionDir, "cycles")
	stateDir := filepath.Join(sessionDir, "state")

	// Create structure
	os.MkdirAll(cyclesDir, 0755)
	os.MkdirAll(stateDir, 0755)

	// Add a cycle
	cycleDir := filepath.Join(cyclesDir, "cycle_0001")
	os.MkdirAll(cycleDir, 0755)

	// Scan runs
	runs, stateFile, err := ScanRuns(runsDir)
	if err != nil {
		t.Fatalf("Failed to scan runs: %v", err)
	}

	// Verify we found the session
	if len(runs) != 1 {
		t.Errorf("Expected 1 run, got %d", len(runs))
	}

	if runs[0].Name != sessionID {
		t.Errorf("Expected run name '%s', got '%s'", sessionID, runs[0].Name)
	}

	// Verify state file was loaded
	if stateFile != nil {
		t.Error("Expected state file to not be loaded (no state.json exists)")
	}
}

func TestFormatTime(t *testing.T) {
	// Test valid timestamp
	timestamp := "2026-02-16T17:50:00Z"
	formatted := FormatTime(timestamp)
	
	// Should not be N/A
	if formatted == "N/A" {
		t.Error("Expected formatted time, got N/A")
	}

	// Test empty timestamp
	emptyFormatted := FormatTime("")
	if emptyFormatted != "N/A" {
		t.Errorf("Expected N/A for empty timestamp, got '%s'", emptyFormatted)
	}
}

// Helper function to create a float64 pointer
func float64Ptr(f float64) *float64 {
	return &f
}
