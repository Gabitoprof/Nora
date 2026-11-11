"""nora.exe entry point (PyInstaller): the same `nora` as the command line."""

import sys

from nora.cli import main

if __name__ == "__main__":
    # Redirected output (file, pipe, acceptance script): always UTF-8. Without it Windows
    # uses the old code page and accents arrive broken ("Vers\ufffdo"). In the console,
    # Windows already shows the accents correctly.
    for fluxo in (sys.stdout, sys.stderr):
        if fluxo is not None and not fluxo.isatty():
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
