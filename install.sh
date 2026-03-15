#!/bin/bash
set -e
# Check/install uv
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
# Install fin-toolkit
uv tool install fin-toolkit
# Run setup
fin-toolkit setup
echo "✓ fin-toolkit installed and configured"
