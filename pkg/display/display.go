// Package display handles terminal output formatting and user feedback.
package display

import (
	"fmt"
	"os"
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
