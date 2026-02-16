package main

import (
	"fmt"

	"github.com/spf13/cobra"
)

var (
	reportRun   string
	reportOut   string
)

var reportCmd = &cobra.Command{
	Use:   "report",
	Short: "Generate a final report from runs",
	Long:  `Generate a markdown summary report of all cycles and results.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		// TODO: Implement report command
		fmt.Println("✓ report command - to be implemented")
		return nil
	},
}

func init() {
	reportCmd.Flags().StringVarP(&reportRun, "run", "r", "./runs", "Path to runs directory")
	reportCmd.Flags().StringVarP(&reportOut, "out", "o", "./reports/final_report.md", "Output report file")
}
