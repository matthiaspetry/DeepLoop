package orchestrator

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// Orchestrator manages execution of the Python training/orchestration code.
type Orchestrator struct {
	pythonPath string
	timeout    time.Duration
}

// NewOrchestrator creates a new orchestrator instance.
func NewOrchestrator() *Orchestrator {
	return &Orchestrator{
		pythonPath: "python", // Default to python, can be configured
		timeout:    30 * time.Minute,
	}
}

// SetPythonPath sets the Python interpreter path.
func (o *Orchestrator) SetPythonPath(path string) {
	o.pythonPath = path
}

// SetTimeout sets the timeout for training runs.
func (o *Orchestrator) SetTimeout(timeout time.Duration) {
	o.timeout = timeout
}

// Run starts the Python orchestrator with the given prompt and config.
func (o *Orchestrator) Run(ctx context.Context, prompt string, configPath string) error {
	// Find orchestrator CLI
	cliPath := o.findOrchestratorCLI()
	if cliPath == "" {
		return fmt.Errorf("could not find orchestrator_cli.py. Is ralph_ml installed?")
	}

	// Build Python command
	args := []string{cliPath, prompt}
	if configPath != "" {
		args = append(args, "--config", configPath)
	}

	// Create command
	cmd := exec.CommandContext(ctx, o.pythonPath, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	// Start the command
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start orchestrator: %w", err)
	}

	// Wait for completion
	done := make(chan error, 1)
	go func() {
		done <- cmd.Wait()
	}()

	// Wait for command or timeout
	select {
	case <-ctx.Done():
		// Context cancelled
		cmd.Process.Kill()
		return fmt.Errorf("operation cancelled")
	case err := <-done:
		if err != nil {
			return fmt.Errorf("orchestrator failed: %w", err)
		}
		return nil
	}
}

// RunWithStreaming runs the Python orchestrator with streaming output.
func (o *Orchestrator) RunWithStreaming(ctx context.Context, prompt string, configPath string, outputWriter io.Writer) error {
	// Find orchestrator CLI
	cliPath := o.findOrchestratorCLI()
	if cliPath == "" {
		return fmt.Errorf("could not find orchestrator_cli.py. Is ralph_ml installed?")
	}

	// Build Python command
	args := []string{cliPath, prompt}
	if configPath != "" {
		args = append(args, "--config", configPath)
	}

	// Create command
	cmd := exec.CommandContext(ctx, o.pythonPath, args...)

	// Create pipes for stdout and stderr
	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to create stdout pipe: %w", err)
	}

	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("failed to create stderr pipe: %w", err)
	}

	// Start the command
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start orchestrator: %w", err)
	}

	// Stream output
	done := make(chan error, 2)

	// Stream stdout
	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		for scanner.Scan() {
			fmt.Fprintln(outputWriter, scanner.Text())
		}
		done <- scanner.Err()
	}()

	// Stream stderr
	go func() {
		scanner := bufio.NewScanner(stderrPipe)
		for scanner.Scan() {
			fmt.Fprintln(outputWriter, "[STDERR] "+scanner.Text())
		}
		done <- scanner.Err()
	}()

	// Wait for completion
	cmdDone := make(chan error, 1)
	go func() {
		cmdDone <- cmd.Wait()
	}()

	// Wait for all streams and command
	var waitErr error
	for i := 0; i < 3; i++ {
		select {
		case err := <-done:
			if err != nil {
				waitErr = err
			}
		case err := <-cmdDone:
			if err != nil {
				waitErr = err
			}
		case <-ctx.Done():
			// Context cancelled
			cmd.Process.Kill()
			return fmt.Errorf("operation cancelled")
		}
	}

	if waitErr != nil {
		return fmt.Errorf("orchestrator failed: %w", waitErr)
	}

	return nil
}

// findOrchestratorCLI finds the orchestrator_cli.py file.
func (o *Orchestrator) findOrchestratorCLI() string {
	// Try current directory first
	if _, err := os.Stat("ralph_ml/orchestrator_cli.py"); err == nil {
		return "ralph_ml/orchestrator_cli.py"
	}

	// Try absolute path
	if cwd, err := os.Getwd(); err == nil {
		cliPath := filepath.Join(cwd, "ralph_ml", "orchestrator_cli.py")
		if _, err := os.Stat(cliPath); err == nil {
			return cliPath
		}
	}

	return ""
}

// CheckPython checks if Python is available and returns version info.
func (o *Orchestrator) CheckPython() (string, error) {
	cmd := exec.Command(o.pythonPath, "--version")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("python not found: %w", err)
	}
	return strings.TrimSpace(string(output)), nil
}
