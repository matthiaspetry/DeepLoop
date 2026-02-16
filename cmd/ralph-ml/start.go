package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/config"
	"github.com/matthiaspetry/DeepLoop/cli/pkg/display"
	"github.com/matthiaspetry/DeepLoop/cli/pkg/orchestrator"
	"github.com/matthiaspetry/DeepLoop/cli/pkg/paths"
	"github.com/spf13/cobra"
)

var (
	startConfig    string
	startNoConfig  bool
	startTarget    float64
	startMaxCycles int
	startDataRoot  string
	startFramework string
	startPython   string
)

var startCmd = &cobra.Command{
	Use:   "start [prompt]",
	Short: "Start the Ralph ML Loop",
	Long:  `Start the Ralph ML Loop with a prompt describing the model to build.`,
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		prompt := args[0]

		// Load config
		cfg, configPath, err := loadConfigForStart()
		if err != nil {
			return err
		}

		cmd.Printf("📄 Using config: %s\n", configPath)

		// Apply CLI overrides
		applyConfigOverrides(cfg)

		// Resolve data root to absolute path
		absDataRoot, err := filepath.Abs(cfg.Data.Root)
		if err != nil {
			return fmt.Errorf("failed to resolve data root: %w", err)
		}
		cfg.Data.Root = absDataRoot

		// Detect Python path
		pythonPath, err := orchestrator.DetectPythonPath(cfg.Execution.Python)
		if err != nil {
			display.PrintPythonNotFound()
			return fmt.Errorf("python detection failed: %w", err)
		}
		cfg.Execution.Python = pythonPath

		// Create run directory
		p, err := paths.ResolvePaths(cfg)
		if err != nil {
			return fmt.Errorf("failed to resolve paths: %w", err)
		}

		runRoot, err := p.CreateRunDirectory()
		if err != nil {
			return fmt.Errorf("failed to create run directory: %w", err)
		}

		cmd.Printf("📁 Run directory: %s\n", runRoot)

		// Show platform info (helpful for debugging)
		if paths.IsWindows() {
			display.Info(fmt.Sprintf("Using Python: %s", pythonPath))
			display.PrintWindowsNote()
		}

		// Save resolved config
		resolvedConfigPath := filepath.Join(runRoot, "resolved_config.json")
		if err := config.SaveConfig(resolvedConfigPath, cfg); err != nil {
			return fmt.Errorf("failed to save resolved config: %w", err)
		}

		// Set up orchestrator
		orch := orchestrator.NewOrchestrator()
		orch.SetPythonPath(cfg.Execution.Python)

		// Check Python availability
		pythonVer, err := orch.CheckPython()
		if err != nil {
			display.Error(fmt.Sprintf("Python check failed: %v", err))
			display.PrintPythonNotFound()
			return fmt.Errorf("python check failed: %w", err)
		}
		cmd.Printf("🐍 Python: %s\n", pythonVer)

		// Run orchestrator with timeout
		timeoutMinutes := cfg.Safeguards.TimeLimitPerCycleMinutes
		if timeoutMinutes <= 0 {
			timeoutMinutes = 30
		}

		ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutMinutes)*time.Minute)
		defer cancel()

		display.Progress("Starting Ralph ML Loop...")
		fmt.Println()

		// Run orchestrator with streaming
		if err := orch.RunWithStreaming(ctx, prompt, configPath, os.Stdout); err != nil {
			display.Error(fmt.Sprintf("Orchestrator failed: %v", err))
			return err
		}

		display.Success("Ralph ML Loop completed!")
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
	startCmd.Flags().StringVarP(&startPython, "python", "p", "", "Python interpreter path (auto-detected if not specified)")
}

// loadConfigForStart loads configuration for the start command.
func loadConfigForStart() (*config.Config, string, error) {
	defaultConfigPath := "RALPH_ML_CONFIG.json"
	configPath := ""
	var cfg *config.Config

	// Determine which config to use
	if startNoConfig && startConfig != "" {
		return nil, "", fmt.Errorf("use either --config or --no-config, not both")
	}

	if startNoConfig {
		// Use built-in defaults
		cfg = config.NewDefaultConfig()
		cfg.Project.Name = "quickstart-ml-project"
		cfg.Project.TargetMetric.Value = 0.90
		configPath = "<built-in>"
	} else if startConfig != "" {
		// Use specified config
		if _, err := os.Stat(startConfig); os.IsNotExist(err) {
			return nil, "", fmt.Errorf("config file not found: %s", startConfig)
		}
		var err error
		cfg, err = config.LoadConfig(startConfig)
		if err != nil {
			return nil, "", fmt.Errorf("failed to load config: %w", err)
		}
		configPath = startConfig
	} else {
		// Try default config
		if _, err := os.Stat(defaultConfigPath); err == nil {
			var loadErr error
			cfg, loadErr = config.LoadConfig(defaultConfigPath)
			if loadErr != nil {
				return nil, "", fmt.Errorf("failed to load default config: %w", loadErr)
			}
			configPath = defaultConfigPath
		} else {
			// No config found, use defaults
			cfg = config.NewDefaultConfig()
			cfg.Project.Name = "quickstart-ml-project"
			cfg.Project.TargetMetric.Value = 0.90
			configPath = "<built-in>"
		}
	}

	return cfg, configPath, nil
}

// applyConfigOverrides applies CLI overrides to the config.
func applyConfigOverrides(cfg *config.Config) {
	if startTarget != 0 {
		cfg.Project.TargetMetric.Value = startTarget
	}
	if startMaxCycles != 0 {
		cfg.Safeguards.MaxCycles = startMaxCycles
	}
	if startDataRoot != "" {
		cfg.Data.Root = startDataRoot
	}
	if startFramework != "" {
		cfg.Project.Framework = startFramework
	}
	if startPython != "" {
		cfg.Execution.Python = startPython
	}
}
