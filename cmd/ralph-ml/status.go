package main

import (
	"fmt"
	"os"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/display"
	"github.com/matthiaspetry/DeepLoop/cli/pkg/state"
	"github.com/spf13/cobra"
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show status of recent runs",
	Long:  `Show status of recent Ralph ML Loop runs, including cycle history and best metrics.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		display.PrintSection("📊 Ralph ML Loop Status")

		// Scan runs directory
		runsDir := "./runs"
		runs, stateFile, err := state.ScanRuns(runsDir)
		if err != nil {
			return fmt.Errorf("failed to scan runs: %w", err)
		}

		// Show runs
		if _, err := os.Stat(runsDir); err == nil {
			if len(runs) > 0 {
				display.PrintRunsTable(runs)
			} else {
				cmd.Println("No runs found.")
			}
		} else {
			cmd.Println("No runs directory found.")
		}

		// Show state
		var statePath string
		if stateFile != nil {
			// Find the state file path
			if len(runs) > 0 {
				// Check for session layout
				for _, run := range runs {
					if len(run.Name) >= 4 && run.Name[:4] == "run_" {
						statePath = run.Path + "/state/ralph_state.json"
						break
					}
				}
			}
			if statePath == "" {
				// Legacy state file
				statePath = "./state/ralph_state.json"
			}
			display.PrintState(stateFile, statePath)
		} else {
			// Try legacy state file
			legacyStatePath := "./state/ralph_state.json"
			if legacyState, err := state.LoadState(legacyStatePath); err == nil {
				display.PrintState(legacyState, legacyStatePath)
			}
		}

		return nil
	},
}
