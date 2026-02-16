package display

import (
	"fmt"
	"os"
	"runtime"
	"strings"

	"github.com/matthiaspetry/DeepLoop/cli/pkg/paths"
	"github.com/matthiaspetry/DeepLoop/cli/pkg/state"
)

// Success prints a success message with a checkmark.
func Success(message string) {
	fmt.Printf("✅ %s\n", message)
}

// Warning prints a warning message.
func Warning(message string) {
	fmt.Printf("⚠️  %s\n", message)
}

// Error prints an error message to stderr.
func Error(message string) {
	fmt.Fprintf(os.Stderr, "❌ %s\n", message)
}

// Info prints an informational message.
func Info(message string) {
	fmt.Printf("ℹ️  %s\n", message)
}

// Progress prints a progress indicator.
func Progress(message string) {
	fmt.Printf("🔄 %s\n", message)
}

// PrintRunsTable prints a table of runs.
func PrintRunsTable(runs []state.RunInfo) {
	if len(runs) == 0 {
		return
	}

	// Print header
	fmt.Printf("%-30s %-25s %s\n", "Cycle", "Status", "Path")
	fmt.Println(strings.Repeat("-", 100))

	// Print rows
	for _, run := range runs {
		path := run.Path
		if len(path) > 45 {
			path = "..." + path[len(path)-42:]
		}
		fmt.Printf("%-30s %-25s %s\n", run.Name, run.Status, path)
	}
}

// PrintState prints state information.
func PrintState(st *state.State, statePath string) {
	if st == nil {
		fmt.Println("\nNo state file found.")
		return
	}

	fmt.Printf("\n📁 State: %s\n", statePath)
	fmt.Printf("   Status: %s\n", st.Status)
	fmt.Printf("   Current cycle: %d\n", st.CurrentCycle)

	if st.BestMetric != nil {
		fmt.Printf("   Best metric: %.4f\n", *st.BestMetric)
	} else {
		fmt.Print("   Best metric: N/A\n")
	}
	fmt.Printf("   Best cycle: %d\n", st.BestCycle)

	if st.StartTime != nil {
		fmt.Printf("   Started: %s\n", state.FormatTime(*st.StartTime))
	}
	if st.LastUpdate != nil {
		fmt.Printf("   Last update: %s\n", state.FormatTime(*st.LastUpdate))
	}
}

// PrintSection prints a section header.
func PrintSection(title string) {
	fmt.Printf("\n%s\n", title)
	fmt.Println(strings.Repeat("=", len(title)))
}

// PrintSubSection prints a subsection header.
func PrintSubSection(title string) {
	fmt.Printf("\n## %s\n", title)
}

// PrintPlatformInfo prints platform-specific information.
func PrintPlatformInfo() {
	fmt.Printf("\n🖥️  Platform: %s\n", runtime.GOOS)
	fmt.Printf("   Architecture: %s\n", runtime.GOARCH)
}

// PrintWindowsNote prints a Windows-specific note.
func PrintWindowsNote() {
	if paths.IsWindows() {
		fmt.Println("\n💡 Windows Tip: Use PowerShell or Command Prompt for best experience.")
		fmt.Println("   For virtual environments: venv\\Scripts\\python.exe")
		fmt.Println("   For Python launcher: py -3 (recommended)")
	}
}

// PrintPythonNotFound prints helpful message when Python is not found.
func PrintPythonNotFound() {
	Error("Python not found or not accessible")
	fmt.Println("\nTo fix this issue:")
	if paths.IsWindows() {
		fmt.Println("1. Install Python from https://python.org")
		fmt.Println("2. During installation, check 'Add Python to PATH'")
		fmt.Println("3. Verify with: python --version or py --version")
		fmt.Println("4. For virtual environments: venv\\Scripts\\python.exe")
	} else {
		fmt.Println("1. Install Python 3.9+: sudo apt install python3 (Ubuntu/Debian)")
		fmt.Println("2. Or use your package manager: brew install python (macOS)")
		fmt.Println("3. Verify with: python3 --version")
		fmt.Println("4. For virtual environments: venv/bin/python")
	}
}
