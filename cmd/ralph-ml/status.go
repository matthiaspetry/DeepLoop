package main

import (
	"fmt"

	"github.com/spf13/cobra"
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show status of recent runs",
	Long:  `Show status of recent Ralph ML Loop runs, including cycle history and best metrics.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO: Implement status command
		fmt.Println("✓ status command - to be implemented")
		return nil
	},
}
