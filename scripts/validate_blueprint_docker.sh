#!/usr/bin/env bash
set -euo pipefail

IMAGE="ghcr.io/home-assistant/home-assistant:stable"
BLUEPRINT_PATH="${1:-blueprints/automation/energy_backfill.yaml}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; install Docker Desktop and retry" >&2
  exit 1
fi

if [ ! -f "$BLUEPRINT_PATH" ]; then
  echo "Blueprint not found: $BLUEPRINT_PATH" >&2
  exit 1
fi

docker run --rm \
  -v "$PWD":/workspace \
  -w /workspace \
  "$IMAGE" \
  python3 scripts/ha_blueprint_validate.py "$BLUEPRINT_PATH"
