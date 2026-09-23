#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "  Starting B2B Outreach Framework..."
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "  Python not found. Opening download page..."
    open "https://www.python.org/downloads/"
    echo ""
    echo "  Install Python, then double-click START_MAC.command again."
    read -p "  Press Enter to close..."
    exit 1
fi

python3 wizard.py
read -p "  Press Enter to close..."
