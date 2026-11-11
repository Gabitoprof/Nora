"""Memory map: an HTML page that shows the Second Brain graph as a network of neurons. A single
file, with no outside libraries and no internet: it opens in the browser, away from Nora's
process (the animation never competes for time with the voice).

Visual reading (legend on the page itself):
- node body color = memory area; halo = conversation tone (the HUD colors);
- size = number of links (capped); pulse = memory updated in the last 7 days;
- the real links appear gradually on opening (animation; no memory is created).
"""

from __future__ import annotations

from pathlib import Path

_PAGINA = Path(__file__).with_name("mapa_memoria.html")


def pagina(dados_json: str, mostrar_texto: bool = False) -> str:
    """The page with the embedded graph. The JSON goes inside <script>: every "<" becomes \\u003c
    (valid JSON), so no memory text closes the script or opens another."""
    seguro = dados_json.replace("<", "\\u003c")
    modelo = _PAGINA.read_text(encoding="utf-8")
    return modelo.replace("__DADOS__", seguro).replace(
        "__MOSTRAR__", "true" if mostrar_texto else "false"
    )
