"""Mapa da memória: uma página HTML que mostra o grafo do Second Brain como uma rede de
neurônios. Arquivo único, sem bibliotecas de fora e sem internet: abre no navegador, longe do
processo da Nora (a animação nunca disputa tempo com a voz).

Leitura visual (legenda na própria página):
- cor do corpo do nó = área da memória; halo = tom da conversa (as cores da HUD);
- tamanho = número de ligações (com limite); pulso = memória atualizada nos últimos 7 dias;
- as ligações reais surgem aos poucos ao abrir (animação; nenhuma memória é criada).
"""

from __future__ import annotations

from pathlib import Path

_PAGINA = Path(__file__).with_name("mapa_memoria.html")


def pagina(dados_json: str, mostrar_texto: bool = False) -> str:
    """A página com o grafo embutido. O JSON vai dentro de <script>: todo "<" vira \\u003c (JSON
    válido), para nenhum texto de memória fechar o script ou abrir outro."""
    seguro = dados_json.replace("<", "\\u003c")
    modelo = _PAGINA.read_text(encoding="utf-8")
    return modelo.replace("__DADOS__", seguro).replace(
        "__MOSTRAR__", "true" if mostrar_texto else "false"
    )
