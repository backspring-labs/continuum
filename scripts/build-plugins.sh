#!/bin/bash
# Build all plugin UI bundles
#
# This script iterates over plugins with ui/ directories and builds
# their Web Component bundles using Vite.
#
# Usage: ./scripts/build-plugins.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PLUGINS_DIR="$PROJECT_ROOT/plugins"

echo "Building plugin UI bundles..."
echo "Plugins directory: $PLUGINS_DIR"
echo ""

# Track build results
built=0
failed=0
skipped=0

# Find all plugins with ui/ directories
for plugin_dir in "$PLUGINS_DIR"/*/; do
    plugin_name=$(basename "$plugin_dir")
    ui_dir="$plugin_dir/ui"

    # Skip if no ui/ directory
    if [ ! -d "$ui_dir" ]; then
        echo "[$plugin_name] No ui/ directory, skipping"
        ((skipped++))
        continue
    fi

    # Skip if no package.json (not a buildable UI)
    if [ ! -f "$ui_dir/package.json" ]; then
        echo "[$plugin_name] No package.json in ui/, skipping"
        ((skipped++))
        continue
    fi

    echo "[$plugin_name] Building..."

    # Install dependencies if node_modules doesn't exist
    if [ ! -d "$ui_dir/node_modules" ]; then
        echo "[$plugin_name] Installing dependencies..."
        (cd "$ui_dir" && npm install --silent)
    fi

    # Build the plugin
    if (cd "$ui_dir" && npm run build --silent); then
        # Verify output exists
        if [ -f "$plugin_dir/dist/plugin.js" ]; then
            size=$(wc -c < "$plugin_dir/dist/plugin.js")
            echo "[$plugin_name] Built successfully (${size} bytes)"
            ((built++))
        else
            echo "[$plugin_name] ERROR: Build completed but plugin.js not found"
            ((failed++))
        fi
    else
        echo "[$plugin_name] ERROR: Build failed"
        ((failed++))
    fi

    echo ""
done

echo "========================================="
echo "Build complete!"
echo "  Built:   $built"
echo "  Skipped: $skipped"
echo "  Failed:  $failed"
echo ""

if [ $failed -gt 0 ]; then
    exit 1
fi
