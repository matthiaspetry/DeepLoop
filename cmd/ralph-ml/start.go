package main

import (
	"fmt"

	"github.com/spf13/cobra"
)

var (
	startConfig      string
	startNoConfig    bool
	startTarget      float64
	startMaxCycles   int
	startDataRoot    string
	startFramework   string
)

var startCmd = &cobra.Command{
	Use:   "start [prompt]",
	Short: "Start the Ralph ML Loop",
	Long:  `Start the Ralph ML Loop with a prompt describing the model to build.`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		prompt := args[0]
		// TODO: Implement start command
		fmt.Printf("✓ start command - prompt: %s\n", prompt)
		fmt.Println("  to be implemented")
		return nil
	},
}

func init() {
	startCmd.Flags().StringVarP(&startConfig, "config", "c", "", "Path to config file")
	startCmd.Flags().BoolVar(&startNoConfig, "no-config", false, "Ignore RALPH_ML_CONFIG.json")
	startCmd.Flags().Float64Var(&startTarget, "target", 0, "Override target metric value")
	startCmd.Flags().IntVar(&startMaxCycles, "max-cycles", 0, "Override max optimization cycles")
	startCmd.Flags().StringVar(&startDataRoot, "data-root", "", "Override dataset root path")
	startCmd.Flags().StringVar(&startFramework, "framework", "", "Override framework (pytorch/tensorflow/jax)")
}
