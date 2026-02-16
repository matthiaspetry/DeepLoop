package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestNewDefaultConfig(t *testing.T) {
	cfg := NewDefaultConfig()

	if cfg.Project.Name != "my-ml-project" {
		t.Errorf("Expected project name 'my-ml-project', got '%s'", cfg.Project.Name)
	}

	if cfg.Project.Framework != "pytorch" {
		t.Errorf("Expected framework 'pytorch', got '%s'", cfg.Project.Framework)
	}

	if cfg.Project.TargetMetric.Name != "test_accuracy" {
		t.Errorf("Expected metric name 'test_accuracy', got '%s'", cfg.Project.TargetMetric.Name)
	}

	if cfg.Project.TargetMetric.Value != 0.85 {
		t.Errorf("Expected metric value 0.85, got '%v'", cfg.Project.TargetMetric.Value)
	}

	if cfg.Data.Root != "./data" {
		t.Errorf("Expected data root './data', got '%s'", cfg.Data.Root)
	}

	if cfg.Safeguards.MaxCycles != 10 {
		t.Errorf("Expected max cycles 10, got '%d'", cfg.Safeguards.MaxCycles)
	}
}

func TestSaveAndLoadConfig(t *testing.T) {
	// Create temporary directory
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "test_config.json")

	// Create config
	cfg := NewDefaultConfig()
	cfg.Project.Name = "test-project"
	cfg.Project.Framework = "tensorflow"

	// Save config
	err := SaveConfig(configPath, cfg)
	if err != nil {
		t.Fatalf("Failed to save config: %v", err)
	}

	// Verify file exists
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		t.Error("Config file was not created")
	}

	// Load config
	loadedCfg, err := LoadConfig(configPath)
	if err != nil {
		t.Fatalf("Failed to load config: %v", err)
	}

	// Verify values
	if loadedCfg.Project.Name != "test-project" {
		t.Errorf("Expected project name 'test-project', got '%s'", loadedCfg.Project.Name)
	}

	if loadedCfg.Project.Framework != "tensorflow" {
		t.Errorf("Expected framework 'tensorflow', got '%s'", loadedCfg.Project.Framework)
	}
}

func TestLoadConfigFromJSON(t *testing.T) {
	cfg := NewDefaultConfig()
	cfg.Project.Name = "json-test"
	cfg.Data.Root = "/tmp/data"

	// Convert to JSON
	jsonData, err := os.ReadFile("testdata/config.json")
	if err == nil {
		// Test with test data if available
		loadedCfg, err := LoadConfigFromJSON(jsonData)
		if err != nil {
			t.Fatalf("Failed to load config from JSON: %v", err)
		}

		if loadedCfg.Project.Name != "json-test" {
			t.Errorf("Expected project name 'json-test', got '%s'", loadedCfg.Project.Name)
		}
	}
}

func TestCreateDirectories(t *testing.T) {
	tmpDir := t.TempDir()

	cfg := NewDefaultConfig()
	cfg.Paths.Workspace = filepath.Join(tmpDir, "workspace")
	cfg.Paths.Runs = filepath.Join(tmpDir, "runs")
	cfg.Paths.Reports = filepath.Join(tmpDir, "reports")
	cfg.Paths.State = filepath.Join(tmpDir, "state")
	cfg.Data.Root = filepath.Join(tmpDir, "data")

	// Create directories
	err := cfg.CreateDirectories()
	if err != nil {
		t.Fatalf("Failed to create directories: %v", err)
	}

	// Verify directories exist
	expectedDirs := []string{
		cfg.Paths.Workspace,
		cfg.Paths.Runs,
		cfg.Paths.Reports,
		cfg.Paths.State,
		cfg.Data.Root,
	}

	for _, dir := range expectedDirs {
		if _, err := os.Stat(dir); os.IsNotExist(err) {
			t.Errorf("Directory was not created: %s", dir)
		}
	}
}
