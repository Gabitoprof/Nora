"""Ponto de entrada do nora.exe (PyInstaller): o mesmo `nora` da linha de comando."""

import sys

from nora.cli import main

if __name__ == "__main__":
    # Saída redirecionada (arquivo, pipe, script de homologação): sempre UTF-8. Sem isso o Windows
    # usa a página de código antiga e os acentos chegam quebrados ("Vers\ufffdo"). No console, o
    # Windows já mostra os acentos certos.
    for fluxo in (sys.stdout, sys.stderr):
        if fluxo is not None and not fluxo.isatty():
            fluxo.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
