#!/bin/bash
# Cross-platform build script for Ralph ML Loop CLI

set -e

VERSION="1.0.0"
BINARY_NAME="ralph-ml"

echo "🔨 Building Ralph ML Loop CLI v${VERSION}"
echo "================================="

# Clean old builds
echo "🧹 Cleaning old builds..."
rm -rf dist
mkdir -p dist

# Build for Linux (amd64)
echo "📦 Building for Linux (amd64)..."
GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o dist/${BINARY_NAME}-linux-amd64 ./cmd/ralph-ml
chmod +x dist/${BINARY_NAME}-linux-amd64
echo "✅ dist/${BINARY_NAME}-linux-amd64"

# Build for Linux (arm64)
echo "📦 Building for Linux (arm64)..."
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o dist/${BINARY_NAME}-linux-arm64 ./cmd/ralph-ml
chmod +x dist/${BINARY_NAME}-linux-arm64
echo "✅ dist/${BINARY_NAME}-linux-arm64"

# Build for macOS (amd64 - Intel)
echo "📦 Building for macOS (amd64 - Intel)..."
GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o dist/${BINARY_NAME}-mac-amd64 ./cmd/ralph-ml
chmod +x dist/${BINARY_NAME}-mac-amd64
echo "✅ dist/${BINARY_NAME}-mac-amd64"

# Build for macOS (arm64 - Apple Silicon)
echo "📦 Building for macOS (arm64 - Apple Silicon)..."
GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o dist/${BINARY_NAME}-mac-arm64 ./cmd/ralph-ml
chmod +x dist/${BINARY_NAME}-mac-arm64
echo "✅ dist/${BINARY_NAME}-mac-arm64"

# Build for Windows (amd64)
echo "📦 Building for Windows (amd64)..."
GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o dist/${BINARY_NAME}-windows-amd64.exe ./cmd/ralph-ml
echo "✅ dist/${BINARY_NAME}-windows-amd64.exe"

# Generate checksums
echo "🔐 Generating checksums..."
cd dist
for file in ${BINARY_NAME}-*; do
    if [[ "$OSTYPE" == "darwin"* ]]; then
        shasum -a 256 $file > ${file}.sha256
    else
        sha256sum $file > ${file}.sha256
    fi
done
cd ..

# List builds
echo ""
echo "✨ Build complete!"
echo "================================"
ls -lh dist/

# Create symlinks for convenience (Unix only)
if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ln -sf ${BINARY_NAME}-mac-arm64 dist/${BINARY_NAME}
    else
        # Linux
        ln -sf ${BINARY_NAME}-linux-amd64 dist/${BINARY_NAME}
    fi
fi

echo ""
echo "💡 Usage:"
echo "  Linux:    ./dist/${BINARY_NAME}-linux-amd64"
echo "  macOS:     ./dist/${BINARY_NAME}-mac-arm64"
echo "  Windows:   .\\dist\\${BINARY_NAME}-windows-amd64.exe"
