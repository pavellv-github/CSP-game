#!/usr/bin/env bash
# Sets up the local Claude Code environment for this project (the single entry point).
#
#   tools/claude/setup.sh                 # agents only: tools/claude/agents/*.md -> .claude/agents/
#   tools/claude/setup.sh --recommended   # + Godot skills, review/commit plugins, Godot MCP server
#   tools/claude/setup.sh --all           # + Supabase, Firebase, Aseprite pixel-art plugin
#   tools/claude/setup.sh --force         # overwrite agents that were edited locally
#
# Everything is installed with the "local" scope: it applies to this checkout only and
# is not committed (.claude/ is in .gitignore). Re-running is safe.
#
# Requirements: Claude Code CLI (`claude`); for --recommended also Node.js (npx) and
# Godot 4.5.2 (path in $GODOT, used by the Godot MCP server); for --all also Aseprite >= 1.3.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_AGENTS="$ROOT/tools/claude/agents"
TARGET_AGENTS="$ROOT/.claude/agents"

# --- Plugins and MCP servers -------------------------------------------------
# Format: "marketplace-source|plugin@marketplace|why"
# An empty marketplace source means the marketplace is built in (claude-plugins-official).
RECOMMENDED_PLUGINS=(
  "jame581/skillsmith|godot-prompter@skillsmith|Godot 4 skills: architecture, input, mobile export, responsive UI, save/load"
  "|code-review@claude-plugins-official|parallel review of a change for bugs and edge cases"
  "|commit-commands@claude-plugins-official|commit / push / PR helpers"
  "|security-guidance@claude-plugins-official|warns about secrets and unsafe patterns while editing"
  "|skill-creator@claude-plugins-official|create project skills (e.g. 'add enemy', 'add level')"
)
EXTRA_PLUGINS=(
  "|supabase@claude-plugins-official|roadmap phase 5: database, auth, edge functions"
  "|firebase@claude-plugins-official|roadmap phase 4: analytics, Crashlytics, Remote Config"
  "willibrandon/pixel-plugin|pixel-plugin|pixel art and sprite sheets through Aseprite"
)

usage() { sed -n '2,15p' "$0"; }

MODE="agents"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --recommended) MODE="recommended" ;;
    --all) MODE="all" ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $arg" >&2; usage; exit 1 ;;
  esac
done

install_agents() {
  mkdir -p "$TARGET_AGENTS"
  for source in "$SOURCE_AGENTS"/*.md; do
    local name target
    name="$(basename "$source")"
    target="$TARGET_AGENTS/$name"
    if [[ -f "$target" && $FORCE -eq 0 ]] && ! cmp -s "$source" "$target"; then
      echo "  skip   $name (edited locally; use --force to overwrite)"
      continue
    fi
    cp "$source" "$target"
    echo "  agent  $name"
  done
}

install_plugins() {
  local entry source plugin why
  for entry in "$@"; do
    IFS='|' read -r source plugin why <<< "$entry"
    if [[ -n "$source" ]]; then
      claude plugin marketplace add "$source" --scope local >/dev/null 2>&1 || true
    fi
    if claude plugin install "$plugin" --scope local >/dev/null 2>&1; then
      echo "  plugin $plugin — $why"
    else
      echo "  FAILED plugin $plugin (install manually: claude plugin install $plugin)" >&2
    fi
  done
}

install_godot_mcp() {
  if ! command -v npx >/dev/null; then
    echo "  FAILED mcp godot: Node.js (npx) is required" >&2
    return
  fi
  local godot="${GODOT:-$(command -v godot || true)}"
  if [[ -z "$godot" ]]; then
    echo "  FAILED mcp godot: set GODOT=/path/to/Godot 4.5.2 and re-run" >&2
    return
  fi
  claude mcp remove godot --scope local >/dev/null 2>&1 || true
  claude mcp add godot --scope local -e GODOT_PATH="$godot" -- npx -y @coding-solo/godot-mcp >/dev/null
  echo "  mcp    godot — run the project, read debug output, inspect scenes ($godot)"
}

echo "Agents -> .claude/agents"
install_agents

if [[ "$MODE" != "agents" ]]; then
  if ! command -v claude >/dev/null; then
    echo "error: Claude Code CLI 'claude' not found" >&2
    exit 1
  fi
  echo "Plugins (local scope)"
  install_plugins "${RECOMMENDED_PLUGINS[@]}"
  [[ "$MODE" == "all" ]] && install_plugins "${EXTRA_PLUGINS[@]}"
  echo "MCP servers (local scope)"
  install_godot_mcp
fi

echo "Done. Restart Claude Code to pick up the changes."
