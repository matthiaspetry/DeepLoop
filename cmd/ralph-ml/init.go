package main

import (
	"os"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/config"
	"github.com/spf13/cobra"
)

var (
	initConfig string
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize a new Ralph ML Loop project",
	Long:  `Initialize a new Ralph ML Loop project by creating a default config file.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		configPath := initConfig
		if configPath == "" {
			configPath = "RALPH_ML_CONFIG.json"
		}

		// Check if config already exists
		if _, err := os.Stat(configPath); err == nil {
			cmd.Printf("⚠️  Config file already exists: %s\n", configPath)
			return nil
		}

		// Create default config
		defaultConfig := config.NewDefaultConfig()

		// Save config
		if err := config.SaveConfig(configPath, defaultConfig); err != nil {
			return err
		}

		cmd.Printf("✅ Created config file: %s\n", configPath)
		cmd.Println("\nEdit the config file, then run:")
		cmd.Printf("  ralph-ml start --config %s \"your prompt here\"\n", configPath)

		return nil
	},
}

func init() {
	initCmd.Flags().StringVarP(&initConfig, "config", "c", "", "Path to config file (default: RALPH_ML_CONFIG.json)")
}
