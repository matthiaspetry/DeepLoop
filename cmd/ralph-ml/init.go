package main

import (
	"fmt"

	"github.com/spf13/cobra"
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize a new Ralph ML Loop project",
	Long:  `Initialize a new Ralph ML Loop project by creating a default config file.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO: Implement init command
		fmt.Println("✓ init command - to be implemented")
		return nil
	},
}
