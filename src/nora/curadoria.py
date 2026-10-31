"""Curadoria da memória: depois de cada troca, o modelo local anota o que vale lembrar sobre a
pessoa (fatos duradouros, datas, planos e acontecimentos marcantes). Roda em segundo plano."""

from __future__ import annotations

import json
import urllib.request

from nora.config import Config
from nora.servico import enviar

INSTRUCAO = """Você cuida da memória de uma assistente pessoal. Leia a troca abaixo entre \
{usuario} e a assistente e anote o que vale lembrar sobre {usuario} em conversas futuras:

- fatos duradouros: preferências, gostos, rotina, trabalho, estudos, saúde, pessoas próximas, \
animais de estimação, lugares;
- datas importantes, planos e compromissos;
- acontecimentos marcantes da vida de {usuario} (algo que deu certo ou errado, um susto, uma \
conquista), com a data em que aconteceram.

Regras:
- Escreva cada fato numa frase curta, em terceira pessoa, começando pelo nome (ex.: "{usuario} \
faz aniversário em 31 de outubro", "{usuario} tem um cachorro", "Em 30/10/2026 o cachorro de \
{usuario} fugiu e foi encontrado num ponto de ônibus perto de casa").
- Ponha a data quando ela for dita; para acontecimentos, use a data de hoje ({hoje}) se nada \
indicar outra.
- Ignore cumprimentos, perguntas gerais, conhecimento sobre o mundo, humor passageiro sem \
motivo e o que a assistente disse sobre si mesma.
- Não invente: só o que {usuario} disse ou confirmou.
- Se não houver nada que valha guardar, devolva a lista vazia.

Responda só com JSON no formato {{"fatos": ["...", "..."]}}."""


def extrair_fatos(
    config: Config, pergunta: str, resposta: str, hoje: str, timeout: float = 120.0
) -> list[str]:
    usuario = config.nome_usuario or "a pessoa"
    pedido = urllib.request.Request(
        f"{config.ollama_host.rstrip('/')}/api/chat",
        data=json.dumps(
            {
                "model": config.modelo_local.modelo,
                "messages": [
                    {"role": "system", "content": INSTRUCAO.format(usuario=usuario, hoje=hoje)},
                    {
                        "role": "user",
                        "content": f"{usuario}: {pergunta}\nAssistente: {resposta}",
                    },
                ],
                "stream": False,
                "think": False,
                "format": "json",
                "keep_alive": config.modelo_local.keep_alive,
                "options": {"temperature": 0},
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    conteudo = json.loads(enviar("o Ollama", pedido, timeout))["message"]["content"]
    try:
        fatos = json.loads(conteudo).get("fatos", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    return [" ".join(str(f).split()) for f in fatos if isinstance(f, str) and f.strip()]
