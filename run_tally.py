"""Entry point for the packaged app.

PyInstaller wants a script rather than a module, so this is all it is.
"""

import sys

from tally.app import main

if __name__ == "__main__":
    sys.exit(main())
