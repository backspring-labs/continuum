#!/bin/bash
# Check for compile-time coupling between shell and plugins.
#
# This script verifies that the shell does not import any code from
# plugin UI directories, which would create compile-time coupling and
# defeat the purpose of dynamic plugin loading.
#
# Usage: ./scripts/check-plugin-coupling.sh
# Exit code 0: No coupling detected
# Exit code 1: Coupling detected (CI should fail)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
WEB_SRC="$PROJECT_ROOT/web/src"

echo "Checking for compile-time plugin coupling..."
echo ""

# Check for imports from plugins/ directory in shell source
# Patterns to detect:
# - from 'plugins/...'
# - from "plugins/..."
# - from '../plugins/...'
# - import 'plugins/...'

COUPLING_FOUND=0

# Check TypeScript and Svelte files
while IFS= read -r file; do
    # Skip node_modules
    if [[ "$file" == *"node_modules"* ]]; then
        continue
    fi

    # Look for plugin imports
    if grep -E "(from|import)\s+['\"].*plugins/" "$file" 2>/dev/null; then
        echo "ERROR: Shell has import from plugins/ in:"
        echo "  $file"
        COUPLING_FOUND=1
    fi

    # Look for direct component imports from old location
    if grep -E "from\s+['\"].*components/plugins" "$file" 2>/dev/null; then
        echo "ERROR: Shell has import from components/plugins/ in:"
        echo "  $file"
        COUPLING_FOUND=1
    fi
done < <(find "$WEB_SRC" -type f \( -name "*.ts" -o -name "*.svelte" -o -name "*.js" \) 2>/dev/null)

# Check if the old plugins component directory still exists
OLD_PLUGINS_DIR="$WEB_SRC/lib/components/plugins"
if [ -d "$OLD_PLUGINS_DIR" ]; then
    if [ -n "$(ls -A "$OLD_PLUGINS_DIR" 2>/dev/null)" ]; then
        echo "ERROR: Old plugins component directory still exists and is not empty:"
        echo "  $OLD_PLUGINS_DIR"
        ls -la "$OLD_PLUGINS_DIR"
        COUPLING_FOUND=1
    fi
fi

echo ""
if [ $COUPLING_FOUND -eq 1 ]; then
    echo "FAIL: Compile-time plugin coupling detected"
    echo ""
    echo "The shell must not have any compile-time imports from plugin code."
    echo "Plugin UI components should be loaded dynamically at runtime via"
    echo "Web Components and the plugin bundle loader."
    exit 1
else
    echo "OK: No compile-time plugin coupling detected"
    exit 0
fi
