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

	"github.com/matthiaspetry/DeepLoop/cli/pkg/paths"
)

// Orchestrator manages execution of the Python training/orchestration code.
type Orchestrator struct {
	pythonPath string
	timeout    time.Duration
}

// NewOrchestrator creates a new orchestrator instance.
func NewOrchestrator() *Orchestrator {
	return &Orchestrator{
		pythonPath: "python", // Default to python, will be detected
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

// Run starts the Python orchestrator with given prompt and config.
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
			return normalizePath(cliPath)
		}
	}

	return ""
}

// detectPythonPath detects the Python interpreter to use.
// This is called from the start command.
func DetectPythonPath(configPython string) (string, error) {
	// If explicitly specified and exists, use it
	if configPython != "" && configPython != "python" {
		if _, err := os.Stat(configPython); err == nil {
			return normalizePath(configPython), nil
		}
	}

	// Detect based on OS
	if paths.IsWindows() {
		return detectPythonWindows()
	}

	// Unix-like systems
	return detectPythonUnix()
}

// detectPythonWindows detects Python on Windows.
func detectPythonWindows() (string, error) {
	// Check for virtual environment (Windows uses Scripts/ instead of bin/)
	if _, err := os.Stat("venv/Scripts/python.exe"); err == nil {
		absPath, err := filepath.Abs("venv/Scripts/python.exe")
		if err == nil {
			return normalizePath(absPath), nil
		}
	}

	if _, err := os.Stat("venv/Scripts/python3.exe"); err == nil {
		absPath, err := filepath.Abs("venv/Scripts/python3.exe")
		if err == nil {
			return normalizePath(absPath), nil
		}
	}

	if _, err := os.Stat(".venv/Scripts/python.exe"); err == nil {
		absPath, err := filepath.Abs(".venv/Scripts/python.exe")
		if err == nil {
			return normalizePath(absPath), nil
		}
	}

	// Check for py launcher (Python launcher)
	if _, err := exec.LookPath("py"); err == nil {
		// Try py -3 to get Python 3 specifically
		if _, err := exec.Command("py", "-3", "--version").CombinedOutput(); err == nil {
			return "py", nil
		}
		// Fall back to py
		return "py", nil
	}

	// Check for python.exe
	if _, err := exec.LookPath("python.exe"); err == nil {
		return "python.exe", nil
	}

	// Check for python3.exe
	if _, err := exec.LookPath("python3.exe"); err == nil {
		return "python3.exe", nil
	}

	return "", fmt.Errorf("could not find python interpreter (tried venv/Scripts/python.exe, py, python.exe, python3.exe)")
}

// detectPythonUnix detects Python on Unix-like systems.
func detectPythonUnix() (string, error) {
	// Check for virtual environment
	if _, err := os.Stat("venv/bin/python"); err == nil {
		absPath, err := filepath.Abs("venv/bin/python")
		if err == nil {
			return normalizePath(absPath), nil
		}
	}

	if _, err := os.Stat("venv/bin/python3"); err == nil {
		absPath, err := filepath.Abs("venv/bin/python3")
		if err == nil {
			return normalizePath(absPath), nil
		}
	}

	if _, err := os.Stat(".venv/bin/python"); err == nil {
		absPath, err := filepath.Abs(".venv/bin/python")
		if err == nil {
			return normalizePath(absPath), nil
		}
	}

	// Check for python3
	if _, err := exec.LookPath("python3"); err == nil {
		return "python3", nil
	}

	// Check for python
	if _, err := exec.LookPath("python"); err == nil {
		return "python", nil
	}

	return "", fmt.Errorf("could not find python interpreter (tried venv/bin/python, python3, python)")
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

// normalizePath normalizes a path for the current OS.
func normalizePath(path string) string {
	return filepath.Clean(path)
}

// AddExtension adds the appropriate executable extension for the OS.
func AddExtension(executable string) string {
	if paths.IsWindows() && !strings.HasSuffix(strings.ToLower(executable), ".exe") {
		return executable + ".exe"
	}
	return executable
}
