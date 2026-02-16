package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/display"
	"github.com/spf13/cobra"
)

var (
	reportRun string
	reportOut string
)

var reportCmd = &cobra.Command{
	Use:   "report",
	Short: "Generate a final report from runs",
	Long:  `Generate a markdown summary report of all cycles and results.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		runsPath := reportRun
		if runsPath == "" {
			runsPath = "./runs"
		}
		outputPath := reportOut
		if outputPath == "" {
			outputPath = "./reports/final_report.md"
		}

		// Check if runs directory exists
		if _, err := os.Stat(runsPath); os.IsNotExist(err) {
			display.Error(fmt.Sprintf("Runs directory not found: %s", runsPath))
			return fmt.Errorf("runs directory not found: %s", runsPath)
		}

		// Resolve cycles path
		cyclesPath, useSession, err := resolveCyclesPath(runsPath, cmd)
		if err != nil {
			return err
		}

		if useSession {
			display.Info(fmt.Sprintf("Using latest session: %s", filepath.Base(filepath.Dir(cyclesPath))))
		}

		// Find all cycle directories
		cycleDirs, err := findCycleDirs(cyclesPath)
		if err != nil {
			display.Error(fmt.Sprintf("No cycles found in: %s", cyclesPath))
			return err
		}

		if len(cycleDirs) == 0 {
			display.Error(fmt.Sprintf("No cycles found in: %s", cyclesPath))
			return fmt.Errorf("no cycles found")
		}

		// Generate report
		report, err := generateReport(cycleDirs)
		if err != nil {
			return fmt.Errorf("failed to generate report: %w", err)
		}

		// Create output directory
		if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
			return fmt.Errorf("failed to create reports directory: %w", err)
		}

		// Write report
		if err := os.WriteFile(outputPath, []byte(report), 0644); err != nil {
			return fmt.Errorf("failed to write report: %w", err)
		}

		display.Success(fmt.Sprintf("Report generated: %s", outputPath))
		cmd.Printf("Total cycles: %d\n", len(cycleDirs))

		return nil
	},
}

func init() {
	reportCmd.Flags().StringVarP(&reportRun, "run", "r", "./runs", "Path to runs directory")
	reportCmd.Flags().StringVarP(&reportOut, "out", "o", "./reports/final_report.md", "Output report file")
}

// resolveCyclesPath resolves the cycles directory path.
func resolveCyclesPath(runsPath string, cmd *cobra.Command) (string, bool, error) {
	// First, check if the specified path has cycle directories directly
	entries, err := os.ReadDir(runsPath)
	if err == nil {
		hasCycles := false
		hasSessions := false

		for _, entry := range entries {
			if entry.IsDir() {
				if len(entry.Name()) >= 6 && entry.Name()[:6] == "cycle_" {
					hasCycles = true
					break
				}
				if len(entry.Name()) >= 4 && entry.Name()[:4] == "run_" {
					hasSessions = true
				}
			}
		}

		// If cycles are directly in the specified path, use it
		if hasCycles {
			return runsPath, false, nil
		}

		// If there are sessions, use the latest one
		if hasSessions {
			var sessions []string
			for _, entry := range entries {
				if entry.IsDir() && len(entry.Name()) >= 4 && entry.Name()[:4] == "run_" {
					sessions = append(sessions, entry.Name())
				}
			}
			if len(sessions) > 0 {
				// Sort by name (which includes timestamp)
				sort.Strings(sessions)
				latestSession := sessions[len(sessions)-1]
				sessionPath := filepath.Join(runsPath, latestSession)
				latestCycles := filepath.Join(sessionPath, "cycles")
				return latestCycles, true, nil
			}
		}
	}

	return runsPath, false, nil
}

// findCycleDirs finds all cycle directories.
func findCycleDirs(cyclesPath string) ([]string, error) {
	var cycleDirs []string

	entries, err := os.ReadDir(cyclesPath)
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		if entry.IsDir() && len(entry.Name()) >= 6 && entry.Name()[:6] == "cycle_" {
			cycleDirs = append(cycleDirs, filepath.Join(cyclesPath, entry.Name()))
		}
	}

	// Sort by cycle number
	sort.Slice(cycleDirs, func(i, j int) bool {
		nameI := filepath.Base(cycleDirs[i])
		nameJ := filepath.Base(cycleDirs[j])
		return nameI < nameJ
	})

	return cycleDirs, nil
}

// generateReport generates a markdown report from cycle directories.
func generateReport(cycleDirs []string) (string, error) {
	lines := []string{
		"# Ralph ML Loop - Final Report",
		"",
		fmt.Sprintf("**Generated:** %s", time.Now().Format("2006-01-02 15:04:05")),
		fmt.Sprintf("**Total cycles:** %d", len(cycleDirs)),
		"",
		"## Cycle Results",
		"",
	}

	for _, cycleDir := range cycleDirs {
		cycleName := filepath.Base(cycleDir)
		lines = append(lines, fmt.Sprintf("### %s", cycleName), "")

		// Read metrics
		metricsPath := filepath.Join(cycleDir, "metrics.json")
		if _, err := os.Stat(metricsPath); err == nil {
			data, err := os.ReadFile(metricsPath)
			if err == nil {
				var metrics map[string]interface{}
				if json.Unmarshal(data, &metrics) == nil {
					lines = append(lines, "**Metrics:**")
					if cycleNum, ok := metrics["cycle"].(float64); ok {
						lines = append(lines, fmt.Sprintf("- Cycle: %.0f", cycleNum))
					}
					if result, ok := metrics["result"].(map[string]interface{}); ok {
						lines = append(lines, "- Results:")
						for key, value := range result {
							lines = append(lines, fmt.Sprintf("  - %s: %v", key, value))
						}
					}
				}
			}
		}

		// Read analysis
		analysisPath := filepath.Join(cycleDir, "analysis.json")
		if _, err := os.Stat(analysisPath); err == nil {
			data, err := os.ReadFile(analysisPath)
			if err == nil {
				var analysis map[string]interface{}
				if json.Unmarshal(data, &analysis) == nil {
					if summary, ok := analysis["summary"].(string); ok {
						lines = append(lines, "")
						lines = append(lines, "**Summary:**")
						lines = append(lines, summary)
					}
					if decision, ok := analysis["decision"].(map[string]interface{}); ok {
						lines = append(lines, "")
						if action, ok := decision["action"].(string); ok {
							lines = append(lines, fmt.Sprintf("**Decision:** %s", action))
						}
						if rationale, ok := decision["rationale"].(string); ok {
							lines = append(lines, fmt.Sprintf("_%s_", rationale))
						}
					}
				}
			}
		}

		lines = append(lines, "")
	}

	return strings.Join(lines, "\n"), nil
}
