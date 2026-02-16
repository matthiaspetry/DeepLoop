package main

import (
	"fmt"

	"github.com/spf13/cobra"
)

var (
	resumeState string
)

var resumeCmd = &cobra.Command{
	Use:   "resume",
	Short: "Resume a previous Ralph ML Loop run",
	Long:  `Resume a previous Ralph ML Loop run from a saved state file.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO: Implement resume command
		fmt.Println("✓ resume command - to be implemented")
		return nil
	},
}

func init() {
	resumeCmd.Flags().StringVarP(&resumeState, "state", "s", "./state/ralph_state.json", "Path to state file")
}
