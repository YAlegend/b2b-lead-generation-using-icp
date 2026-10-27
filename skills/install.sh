#!/usr/bin/env bash
# Install the b2b-outreach skill into one or more agents, or build a zip
# for uploading to Claude.ai / ChatGPT.
#
#   bash skills/install.sh claude      # Claude Code   -> ~/.claude/skills/
#   bash skills/install.sh codex       # OpenAI Codex  -> ~/.codex/skills/
#   bash skills/install.sh hermes      # Hermes Agent  -> ~/.hermes/skills/sales/
#   bash skills/install.sh all         # every agent found on this machine
#   bash skills/install.sh zip         # b2b-outreach.zip for web upload
#
# Re-running replaces the installed copy with the current one.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/b2b-outreach"
NAME="b2b-outreach"

copy_to() {
  local dest="$1/$NAME"
  mkdir -p "$1"
  rm -rf "$dest"
  cp -R "$SRC" "$dest"
  rm -rf "$dest/scripts/__pycache__"
  echo "Installed -> $dest"
}

install_claude() { copy_to "$HOME/.claude/skills"; }
install_codex()  { copy_to "${CODEX_HOME:-$HOME/.codex}/skills"; }
install_hermes() {
  local cat_dir="${HERMES_HOME:-$HOME/.hermes}/skills/sales"
  mkdir -p "$cat_dir"
  [ -f "$cat_dir/DESCRIPTION.md" ] || printf -- '---\ndescription: Skills for B2B sales, lead generation and outreach.\n---\n' > "$cat_dir/DESCRIPTION.md"
  copy_to "$cat_dir"
}

build_zip() {
  local out="$HERE/$NAME.zip"
  rm -f "$out"
  (cd "$HERE" && zip -qr "$out" "$NAME" -x '*.DS_Store' '*__pycache__*')
  echo "Built -> $out"
}

case "${1:-}" in
  claude) install_claude ;;
  codex)  install_codex ;;
  hermes) install_hermes ;;
  zip)    build_zip ;;
  all)
    found=0
    [ -d "$HOME/.claude" ] && { install_claude; found=1; }
    [ -d "${CODEX_HOME:-$HOME/.codex}" ] && { install_codex; found=1; }
    [ -d "${HERMES_HOME:-$HOME/.hermes}" ] && { install_hermes; found=1; }
    [ "$found" = 1 ] || echo "No Claude Code, Codex or Hermes folder found. Use 'zip' for web upload."
    ;;
  *) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
