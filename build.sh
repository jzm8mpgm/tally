#!/usr/bin/env bash
#
# Build Tally.app.
#
#   ./build.sh          build into dist/Tally.app
#   ./build.sh --zip    also produce dist/Tally.zip, ready to attach to a release
#
set -euo pipefail

cd "$(dirname "$0")"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "Tally is a Mac app — this needs to run on macOS." >&2
    exit 1
fi

VENV=".venv-build"

if [[ ! -d "$VENV" ]]; then
    echo "→ Creating build environment"
    python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "→ Installing dependencies"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r requirements-build.txt

echo "→ Drawing the app icon"
python3 tools/make_icon.py

echo "→ Running tests"
python3 -m unittest discover -s tests -t . --quiet

echo "→ Building Tally.app"
rm -rf build dist
pyinstaller --noconfirm --clean Tally.spec

# PyInstaller leaves the unbundled collection alongside the .app; it is
# duplicated inside the bundle and only confuses anyone who opens dist/.
rm -rf "dist/Tally"

if [[ "${1:-}" == "--zip" ]]; then
    echo "→ Zipping"
    ditto -c -k --sequesterRsrc --keepParent "dist/Tally.app" "dist/Tally.zip"
fi

echo
echo "Built dist/Tally.app"
echo "Drag it to /Applications. The first launch needs a right-click → Open,"
echo "because the app is not signed with an Apple Developer certificate."
