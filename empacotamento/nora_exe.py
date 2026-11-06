"""Ponto de entrada do nora.exe (PyInstaller): o mesmo `nora` da linha de comando."""

import sys

from nora.cli import main

if __name__ == "__main__":
    sys.exit(main())
