package state

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// CycleMetrics represents metrics from a cycle.
type CycleMetrics struct {
	Cycle int                    `json:"cycle"`
	Result map[string]interface{} `json:"result"`
	Runtime map[string]interface{} `json:"runtime"`
}

// CycleSnapshot represents a snapshot of a cycle.
type CycleSnapshot struct {
	CycleNumber    int                    `json:"cycle_number"`
	Metrics        CycleMetrics           `json:"metrics"`
	Timestamp      string                 `json:"timestamp"`
	BestMetric     *float64               `json:"best_metric,omitempty"`
	Analysis       map[string]interface{} `json:"analysis,omitempty"`
}

// State represents the Ralph ML Loop state.
type State struct {
	Config       map[string]interface{} `json:"config"`
	CurrentCycle int                    `json:"current_cycle"`
	BestMetric   *float64               `json:"best_metric"`
	BestCycle    int                    `json:"best_cycle"`
	History      []CycleSnapshot        `json:"history"`
	Status       string                 `json:"status"`
	StartTime    *string                `json:"start_time,omitempty"`
	LastUpdate   *string                `json:"last_update,omitempty"`
}

// LoadState loads a state from a JSON file.
func LoadState(path string) (*State, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read state file: %w", err)
	}

	var state State
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, fmt.Errorf("failed to parse state file: %w", err)
	}

	return &state, nil
}

// SaveState saves a state to a JSON file.
func SaveState(path string, state *State) error {
	// Create directory if it doesn't exist
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create state directory: %w", err)
	}

	// Marshal with indentation
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal state: %w", err)
	}

	// Write file
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write state file: %w", err)
	}

	return nil
}

// RunInfo represents information about a run.
type RunInfo struct {
	Name     string
	Path     string
	Status   string
	Cycles   int
	CycleDir string
}

// ScanRuns scans the runs directory and returns information about all runs.
func ScanRuns(runsDir string) ([]RunInfo, *State, error) {
	var runs []RunInfo
	var stateFile *State

	// Check if runs directory exists
	if _, err := os.Stat(runsDir); os.IsNotExist(err) {
		return runs, stateFile, nil
	}

	// Read all subdirectories
	entries, err := os.ReadDir(runsDir)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read runs directory: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		name := entry.Name()
		runPath := filepath.Join(runsDir, name)

		// Check for session layout (runs/run_YYYY.../)
		if len(name) >= 4 && name[:4] == "run_" {
			sessionPath := runPath
			cyclesPath := filepath.Join(sessionPath, "cycles")
			statePath := filepath.Join(sessionPath, "state", "ralph_state.json")

			// Check for state file
			if stat, err := os.Stat(statePath); err == nil && !stat.IsDir() {
				state, err := LoadState(statePath)
				if err == nil {
					stateFile = state
				}
			}

			// Count cycles
			var cycleCount int
			if cyclesEntries, err := os.ReadDir(cyclesPath); err == nil {
				for _, ce := range cyclesEntries {
					if ce.IsDir() && len(ce.Name()) >= 6 && ce.Name()[:6] == "cycle_" {
						cycleCount++
					}
				}
			}

			runs = append(runs, RunInfo{
				Name:     name,
				Path:     runPath,
				Status:   fmt.Sprintf("🧪 Session (%d cycles)", cycleCount),
				Cycles:   cycleCount,
				CycleDir: cyclesPath,
			})
			continue
		}

		// Check for legacy layout (runs/cycle_XXXX/)
		if len(name) >= 6 && name[:6] == "cycle_" {
			metricsPath := filepath.Join(runPath, "metrics.json")
			hasMetrics := false
			if stat, err := os.Stat(metricsPath); err == nil && !stat.IsDir() {
				hasMetrics = true
			}

			status := "⏳ Incomplete"
			if hasMetrics {
				status = "✅ Complete"
			}

			runs = append(runs, RunInfo{
				Name:     name,
				Path:     runPath,
				Status:   status,
				Cycles:   1,
				CycleDir: runsDir,
			})
			continue
		}

		// Unknown directory
		runs = append(runs, RunInfo{
			Name:     name,
			Path:     runPath,
			Status:   "❓ Unknown",
			Cycles:   0,
		})
	}

	// If no session layout found, check for legacy state file
	if stateFile == nil {
		legacyStatePath := filepath.Join(filepath.Dir(runsDir), "state", "ralph_state.json")
		if stat, err := os.Stat(legacyStatePath); err == nil && !stat.IsDir() {
			state, err := LoadState(legacyStatePath)
			if err == nil {
				stateFile = state
			}
		}
	}

	return runs, stateFile, nil
}

// FormatTime formats a timestamp string nicely.
func FormatTime(timestamp string) string {
	if timestamp == "" {
		return "N/A"
	}

	t, err := time.Parse(time.RFC3339Nano, timestamp)
	if err != nil {
		return timestamp
	}

	return t.Format("2006-01-02 15:04:05")
}
