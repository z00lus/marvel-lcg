#!/usr/bin/env bash

set -Eeuo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

python_command="${MARVEL_LCG_PYTHON:-python3}"
virtualenv_dir="$project_dir/.venv"
virtualenv_python="$virtualenv_dir/bin/python"

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

command -v "$python_command" >/dev/null 2>&1 || \
    fail "Python 3 was not found. Install Python 3.10 or newer."

if ! "$python_command" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    fail "Python 3.10 or newer is required. Found: $($python_command --version 2>&1)"
fi

if [[ ! -x "$virtualenv_python" ]]; then
    printf 'Creating Python virtual environment in .venv...\n'
    "$python_command" -m venv "$virtualenv_dir" || \
        fail "Could not create .venv. On Debian/Ubuntu, install python3-venv and try again."
fi

if ! "$virtualenv_python" -c \
    'import aiohttp, colorama, numpy, packaging, PIL, requests, typing_extensions' \
    >/dev/null 2>&1; then
    printf 'Installing Python dependencies...\n'
    "$virtualenv_python" -m pip install -r requirements.txt
fi

if ! "$virtualenv_python" -c \
    'import socket; sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM); sock.bind(("127.0.0.1", 2345)); sock.close()' \
    >/dev/null 2>&1; then
    fail "Port 2345 is already in use. Stop the previous Marvel LCG instance with Ctrl+C, then try again."
fi

frontend_needs_build=false
while IFS= read -r -d '' typescript_file; do
    javascript_file="${typescript_file%.ts}.js"
    if [[ ! -f "$javascript_file" || "$typescript_file" -nt "$javascript_file" ]]; then
        frontend_needs_build=true
        break
    fi
done < <(find public/js -type f -name '*.ts' ! -name '*.d.ts' -print0)

if [[ public/js/tsconfig.json -nt public/js/marvel/marvel.js ]]; then
    frontend_needs_build=true
fi

if [[ "$frontend_needs_build" == true ]]; then
    printf 'Compiling the web frontend...\n'
    if command -v tsc >/dev/null 2>&1; then
        tsc --project public/js/tsconfig.json
    elif command -v npm >/dev/null 2>&1; then
        npm exec --yes --package=typescript -- tsc --project public/js/tsconfig.json
    else
        fail "TypeScript is required. Install Node.js (which includes npm) and try again."
    fi
fi

if [[ ! -d assets ]]; then
    printf '\nNote: assets/ is missing; card images will be downloaded and cached as needed.\n' >&2
    printf 'The optional assets bundle adds local sounds and textures.\n' >&2
fi

printf '\nStarting Marvel LCG at http://127.0.0.1:2345/\n'
printf 'Press Ctrl+C to stop it.\n\n'

exec "$virtualenv_python" -u main.py "$@"
