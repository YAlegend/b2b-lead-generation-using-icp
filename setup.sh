#!/bin/bash
# One-command setup — installs everything then runs the pipeline
set -e

echo ""
echo "================================================"
echo "  B2B Outreach Framework — Setup"
echo "================================================"
echo ""

# Python check
if ! command -v python3 &>/dev/null; then
  echo "❌  Python 3 not found. Install from python.org and re-run."
  exit 1
fi
echo "✅  Python $(python3 --version | cut -d' ' -f2)"

# Install pip deps
echo "📦  Installing Python dependencies..."
pip install -r requirements.txt -q
echo "✅  Dependencies installed"

# Install uv + OpenOutreach
if ! command -v uv &>/dev/null; then
  echo "📦  Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v openoutreach &>/dev/null; then
  echo "📦  Installing OpenOutreach..."
  uv tool install openoutreach
fi
echo "✅  OpenOutreach ready"

echo ""
echo "================================================"
echo "  Ready! Running the framework..."
echo "================================================"
echo ""

python3 run.py "$@"
