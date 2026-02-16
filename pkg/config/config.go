package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// TargetMetric represents a target metric definition.
type TargetMetric struct {
	Name     string  `json:"name"`
	Value    float64 `json:"value"`
	Direction string `json:"direction,omitempty"` // maximize, minimize
}

// ProjectConfig represents project configuration.
type ProjectConfig struct {
	Name        string       `json:"name"`
	Framework   string       `json:"framework,omitempty"`
	Task        string       `json:"task,omitempty"`
	TargetMetric TargetMetric `json:"target_metric"`
}

// DataConfig represents data configuration.
type DataConfig struct {
	Root      string `json:"root,omitempty"`
	TrainSplit string `json:"train_split,omitempty"`
	ValSplit   string `json:"val_split,omitempty"`
	TestSplit  string `json:"test_split,omitempty"`
}

// SafeguardsConfig represents safeguards configuration.
type SafeguardsConfig struct {
	MaxCycles              int     `json:"max_cycles,omitempty"`
	NoImprovementStopCycles int     `json:"no_improvement_stop_cycles,omitempty"`
	MinImprovementDelta    float64 `json:"min_improvement_delta,omitempty"`
	TimeLimitPerCycleMinutes int    `json:"time_limit_per_cycle_minutes,omitempty"`
	TokenBudgetPerCycle    int     `json:"token_budget_per_cycle,omitempty"`
}

// ExecutionConfig represents execution configuration.
type ExecutionConfig struct {
	Mode        string `json:"mode,omitempty"`
	Python      string `json:"python,omitempty"`
	TrainCmd    string `json:"train_cmd,omitempty"`
	EvalCmd     string `json:"eval_cmd,omitempty"`
	EnvCapture  bool   `json:"env_capture,omitempty"`
}

// AgentsConfig represents agent configuration.
type AgentsConfig struct {
	CodeModel     string `json:"code_model,omitempty"`
	AnalysisModel string `json:"analysis_model,omitempty"`
	Thinking      string `json:"thinking,omitempty"`
}

// PathsConfig represents path configuration.
type PathsConfig struct {
	Workspace string `json:"workspace,omitempty"`
	Runs      string `json:"runs,omitempty"`
	Reports   string `json:"reports,omitempty"`
	State     string `json:"state,omitempty"`
}

// ObservabilityConfig represents observability configuration.
type ObservabilityConfig struct {
	Logger          string `json:"logger,omitempty"`
	SaveStdout      bool   `json:"save_stdout,omitempty"`
	EmitEventsJsonl bool   `json:"emit_events_jsonl,omitempty"`
}

// Config represents the full Ralph ML Loop configuration.
type Config struct {
	Project        ProjectConfig        `json:"project"`
	Data           DataConfig           `json:"data,omitempty"`
	Safeguards     SafeguardsConfig     `json:"safeguards,omitempty"`
	Execution      ExecutionConfig      `json:"execution,omitempty"`
	Agents         AgentsConfig         `json:"agents,omitempty"`
	Paths          PathsConfig          `json:"paths,omitempty"`
	Observability  ObservabilityConfig  `json:"observability,omitempty"`
}

// NewDefaultConfig creates a default configuration.
func NewDefaultConfig() *Config {
	return &Config{
		Project: ProjectConfig{
			Name:      "my-ml-project",
			Framework: "pytorch",
			TargetMetric: TargetMetric{
				Name:  "test_accuracy",
				Value: 0.85,
			},
		},
		Data: DataConfig{
			Root:      "./data",
			TrainSplit: "train",
			ValSplit:   "val",
			TestSplit:  "test",
		},
		Safeguards: SafeguardsConfig{
			MaxCycles:              10,
			NoImprovementStopCycles: 3,
			MinImprovementDelta:    0.002,
			TimeLimitPerCycleMinutes: 30,
			TokenBudgetPerCycle:    100000,
		},
		Execution: ExecutionConfig{
			Mode:       "local",
			Python:     "python",
			TrainCmd:   "python train.py --config config.json",
			EvalCmd:    "python eval.py --config config.json",
			EnvCapture: true,
		},
		Agents: AgentsConfig{
			CodeModel:     "opencode",
			AnalysisModel: "opencode",
			Thinking:      "medium",
		},
		Paths: PathsConfig{
			Workspace: "./workspace",
			Runs:      "./runs",
			Reports:   "./reports",
			State:     "./state",
		},
		Observability: ObservabilityConfig{
			Logger:          "tensorboard",
			SaveStdout:      true,
			EmitEventsJsonl: true,
		},
	}
}

// LoadConfig loads a configuration from a JSON file.
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config file: %w", err)
	}

	return &config, nil
}

// SaveConfig saves a configuration to a JSON file.
func SaveConfig(path string, config *Config) error {
	// Create directory if it doesn't exist
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	// Marshal with indentation
	data, err := json.MarshalIndent(config, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	// Write file
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}

// LoadConfigFromJSON loads a configuration from JSON bytes.
func LoadConfigFromJSON(data []byte) (*Config, error) {
	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("failed to parse config JSON: %w", err)
	}
	return &config, nil
}

// CreateDirectories creates all directories specified in the config.
func (c *Config) CreateDirectories() error {
	dirs := []string{
		c.Paths.Workspace,
		c.Paths.Runs,
		c.Paths.Reports,
		c.Paths.State,
		c.Data.Root,
	}

	for _, dir := range dirs {
		if dir == "" {
			continue
		}
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	return nil
}
