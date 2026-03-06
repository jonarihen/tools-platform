#!/bin/bash
set -e

TOOLS_DIR="/usr/share/nginx/html/tools"
MANIFEST="/usr/share/nginx/html/manifest.json"

generate_manifest() {
  echo "Scanning tools directory..."
  echo "[" > "$MANIFEST"
  first=true

  for meta in "$TOOLS_DIR"/*/meta.json; do
    [ -f "$meta" ] || continue
    dir=$(dirname "$meta")
    slug=$(basename "$dir")

    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> "$MANIFEST"
    fi

    # Inject the slug into the JSON
    jq --arg slug "$slug" '. + {slug: $slug}' "$meta" >> "$MANIFEST"
    echo "  Found tool: $slug"
  done

  echo "]" >> "$MANIFEST"
  echo "Manifest generated with $(grep -c '"slug"' "$MANIFEST" 2>/dev/null || echo 0) tools"
}

generate_manifest

# Hand off to nginx
exec "$@"
