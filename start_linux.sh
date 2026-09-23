#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "  Starting B2B Outreach Framework..."
echo ""

if ! command -v python3 &>/dev/null; then
    echo "  Installing Python..."
    sudo apt-get install -y python3 python3-pip 2>/dev/null || \
    sudo yum install -y python3 2>/dev/null || \
    echo "  Please install Python 3: https://www.python.org/downloads/"
fi

python3 wizard.py
