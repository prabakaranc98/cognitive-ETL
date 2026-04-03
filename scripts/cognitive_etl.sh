#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/cognitive_etl.sh test
  ./scripts/cognitive_etl.sh sync
  ./scripts/cognitive_etl.sh build
  ./scripts/cognitive_etl.sh refresh
  ./scripts/cognitive_etl.sh serve [port]
  ./scripts/cognitive_etl.sh all [port]

Commands:
  test      Run local smoke tests.
  sync      Pull fresh data from Notion using .env credentials.
  build     Rebuild the static storefront into dist/.
  refresh   Run test + sync + build.
  serve     Serve dist/ locally on 127.0.0.1. Default port: 4323.
  all       Run refresh and then serve.
EOF
}

env_value() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1) }' .env
}

require_env() {
  if [[ ! -f .env ]]; then
    echo "Missing .env. Copy .env.example to .env first." >&2
    exit 1
  fi

  if [[ -z "$(env_value NOTION_API_KEY)" ]]; then
    echo "Missing NOTION_API_KEY in .env." >&2
    exit 1
  fi
}

run_tests() {
  python -m unittest discover -s tests -v
}

run_sync() {
  require_env
  python scripts/sync_notion.py
}

run_build() {
  python scripts/build_site.py
}

run_serve() {
  local port="${1:-4323}"
  echo "Serving dist/ on http://127.0.0.1:${port}"
  (
    cd dist
    python3 -m http.server "$port" --bind 127.0.0.1
  )
}

main() {
  local command="${1:-refresh}"

  case "$command" in
    test)
      run_tests
      ;;
    sync)
      run_sync
      ;;
    build)
      run_build
      ;;
    refresh)
      run_tests
      run_sync
      run_build
      ;;
    serve)
      run_serve "${2:-4323}"
      ;;
    all)
      run_tests
      run_sync
      run_build
      run_serve "${2:-4323}"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: $command" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
