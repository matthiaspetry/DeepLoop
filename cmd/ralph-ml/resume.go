package main

import (
	"fmt"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/display"
	"github.com/matthiaspetry/DeepLoop/cli/pkg/state"
	"github.com/spf13/cobra"
)

var (
	resumeState  string
	resumePrompt string
)

var resumeCmd = &cobra.Command{
	Use:   "resume",
	Short: "Resume a previous Ralph ML Loop run",
	Long:  `Resume a previous Ralph ML Loop run from a saved state file.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// Load state
		statePath := resumeState
		if statePath == "" {
			statePath = "./state/ralph_state.json"
		}

		stateFile, err := state.LoadState(statePath)
		if err != nil {
			display.Error(fmt.Sprintf("Failed to load state: %v", err))
			return fmt.Errorf("failed to load state: %w", err)
		}

		cmd.Printf("🔄 Resuming from cycle %d\n", stateFile.CurrentCycle)
		if stateFile.BestMetric != nil {
			cmd.Printf("Best metric so far: %.4f\n", *stateFile.BestMetric)
		} else {
			cmd.Println("Best metric so far: N/A")
		}

		// Check if prompt is provided
		if resumePrompt == "" {
			cmd.Println("\n⚠️  Resume functionality requires the original prompt.")
			cmd.Println("Please use the original prompt you used when starting the run.")
			cmd.Println("Example: ralph-ml resume --prompt \"your original prompt\" --state ./state/ralph_state.json")
			return nil
		}

		// Resume with the provided prompt
		cmd.Printf("\n🚀 Resuming with prompt: %s\n", resumePrompt)

		// Note: For full resume functionality, we'd need to implement state-aware orchestrator
		// This is a simplified version that restarts the loop
		cmd.Println("\n⚠️  Full resume functionality coming soon.")
		cmd.Println("Currently, you can use 'start' with the same prompt to continue manually.")
		cmd.Println("The state file contains your history and best metrics for reference.")

		return nil
	},
}

func init() {
	resumeCmd.Flags().StringVarP(&resumeState, "state", "s", "./state/ralph_state.json", "Path to state file")
	resumeCmd.Flags().StringVarP(&resumePrompt, "prompt", "p", "", "Original prompt used to start the run (optional)")
}
