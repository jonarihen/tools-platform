#!/bin/bash
# Generates public/manifest.json from tools/*/meta.json
# Run during development or CI — entrypoint.sh regenerates at container start.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$SCRIPT_DIR/tools"
MANIFEST="$SCRIPT_DIR/public/manifest.json"

tools_json="[]"

for meta in "$TOOLS_DIR"/*/meta.json; do
  [ -f "$meta" ] || continue
  slug=$(basename "$(dirname "$meta")")

  # Skip hidden tools
  if jq -e '.hidden == true' "$meta" > /dev/null 2>&1; then
    continue
  fi

  tools_json=$(echo "$tools_json" | jq --argjson tool "$(jq --arg slug "$slug" '. + {slug: $slug}' "$meta")" '. + [$tool]')
done

echo "$tools_json" | jq '.' > "$MANIFEST"
echo "Manifest generated: $(echo "$tools_json" | jq 'length') tools → $MANIFEST"
