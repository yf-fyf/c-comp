#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IMAGE="${IMAGE:-incremental-c-rv64:latest}"

docker build \
  -t "$IMAGE" \
  -f "$ROOT_DIR/docker/rv64/Dockerfile" \
  "$ROOT_DIR/docker/rv64"

run_args=(--rm -v "$ROOT_DIR:/work" -w /work)
if [ -t 0 ] && [ -t 1 ]; then
  run_args=(-it "${run_args[@]}")
fi

if [ "$#" -eq 0 ]; then
  docker run "${run_args[@]}" "$IMAGE" bash
else
  docker run "${run_args[@]}" "$IMAGE" "$@"
fi
