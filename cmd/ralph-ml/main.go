package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "ralph-ml",
	Short: "Ralph ML Loop - Autonomous Deep Learning Improvement Cycle",
	Long: `Ralph ML Loop CLI

A cross-platform command-line tool for autonomous deep learning improvement.
Rewrite of the Python CLI for better Windows support and distribution.`,
}

func init() {
	// Add subcommands
	rootCmd.AddCommand(initCmd)
	rootCmd.AddCommand(startCmd)
	rootCmd.AddCommand(resumeCmd)
	rootCmd.AddCommand(statusCmd)
	rootCmd.AddCommand(reportCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
