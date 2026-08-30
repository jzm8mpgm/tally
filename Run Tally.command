#!/bin/zsh
#
# Double-click this file to run Tally from source.
#
# It creates a virtual environment beside the code the first time, installs
# the two dependencies, and starts the app. Afterwards it takes a second.
# This Terminal window stays open so that any error is visible and can be
# copied into a bug report.

cd "$(dirname "$0")" || exit 1

# A menu bar app needs a "framework build" of Python. macOS's own always is;
# Homebrew and Anaconda builds usually are, but not always — so prefer the
# system one, which is the safest bet.
PY=/usr/bin/python3
[ -x "$PY" ] || PY=$(command -v python3)

if [ -z "$PY" ]; then
    echo "No python3 found."
    echo "Install Apple's command line tools with:  xcode-select --install"
    echo
    read "?Press return to close."
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Setting up — first run only, takes about a minute."
    "$PY" -m venv .venv || exit 1
fi
source .venv/bin/activate

python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r requirements.txt || {
    echo
    echo "Could not install the dependencies. The error is above."
    read "?Press return to close."
    exit 1
}

echo
echo "Starting Tally. Look for the tally mark in your menu bar."
echo "To quit: the ... menu in the panel, right-click the menu bar icon,"
echo "or press Ctrl-C in this window."
echo
python3 -m tally

echo
echo "Tally has quit. You can close this window."
