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
  sync      Pull fresh data from Notion using configured env values or .env.
  build     Rebuild the static storefront into dist/.
  refresh   Run test + sync + build.
  serve     Serve dist/ locally on 127.0.0.1. Default port: 4323.
  all       Run refresh and then serve.
EOF
}

env_value() {
  local key="$1"
  local env_current="${!key:-}"
  if [[ -n "$env_current" ]]; then
    printf '%s\n' "$env_current"
    return 0
  fi

  if [[ -f .env ]]; then
    awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1) }' .env
  fi
}

require_env() {
  local missing=()

  for key in NOTION_API_KEY SOURCES_DB_ID ATOMS_DB_ID ARTIFACTS_DB_ID; do
    if [[ -z "$(env_value "$key")" ]]; then
      missing+=("$key")
    fi
  done

  if (( ${#missing[@]} > 0 )); then
    echo "Missing required configuration: ${missing[*]}" >&2
    echo "Provide them via .env or exported environment variables." >&2
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
