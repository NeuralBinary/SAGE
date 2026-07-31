#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required: https://docs.docker.com/get-docker/" >&2
  exit 1
fi
docker compose -f docker-compose.quickstart.yml up --build -d --wait
docker compose -f docker-compose.quickstart.yml exec -T sage \
  sage-doctor --url http://127.0.0.1:8080
echo
echo "SAGE is ready at http://127.0.0.1:8080"
echo "API docs: http://127.0.0.1:8080/docs"
echo "Try: docker compose -f docker-compose.quickstart.yml exec -T sage sage-demo --url http://127.0.0.1:8080"
