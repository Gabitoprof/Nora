"""Curadoria da memória: depois de cada troca, o modelo local anota o que vale lembrar sobre a
pessoa (fatos duradouros, datas, planos e acontecimentos marcantes). Roda em segundo plano."""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from datetime import date, datetime
from typing import NamedTuple

from nora.agenda import NOMES_DOS_DIAS, datas_no_texto
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
faz aniversário em 12 de março", "{usuario} tem um gato", "Em 05/03/2026 o gato de {usuario} \
fugiu e voltou sozinho para casa").
- Ponha a data quando ela for dita; para acontecimentos, use a data de hoje ({hoje}) se nada \
indicar outra.
- Quando o fato tiver um dia (compromisso, prova, consulta, viagem, aniversário, data \
comemorativa, acontecimento), ponha esse dia também em "data", no formato AAAA-MM-DD. Hoje é \
{dia_da_semana}, {hoje}: calcule a partir daí "amanhã", "sexta", "dia 21", "semana que vem". \
Escreva a data também no texto do fato (ex.: "{usuario} tem prova de cálculo em 21/11/2026"). \
Não ponha "data" só porque a conversa aconteceu hoje: um pedido, uma ideia ou um plano sem dia \
marcado ficam sem data.
- Use "anual": true para o que se repete todo ano (aniversários, datas comemorativas).
- Ignore cumprimentos, perguntas gerais, conhecimento sobre o mundo, humor passageiro sem \
motivo e o que a assistente disse sobre si mesma.
- Não invente: só o que {usuario} disse ou confirmou.
- Se não houver nada que valha guardar, devolva a lista vazia.
- Dê a cada fato uma área curta, em minúsculas (ex.: "saúde", "trabalho", "estudos", \
"família", "pets"). Áreas que já existem: {areas}. Use uma delas quando o assunto couber; se \
for um assunto novo, crie uma área nova.

Além dos fatos, anote o que {usuario} ensinar sobre o jeito de a assistente falar:
- "pronuncias": quando {usuario} corrigir como a assistente fala uma palavra (ex.: "você fala \
houje, o certo é ôje"; "fala Nóra, com o aberto"), anote a palavra escrita normalmente e como \
falar, escrita do jeito que soa (ex.: {{"palavra": "hoje", "fala": "ôje"}}).
- "preferencias": quando {usuario} pedir uma mudança duradoura no jeito de responder (ex.: "não \
repita minha pergunta", "seja mais direta", "me chama de você"), anote uma frase curta no \
imperativo, dirigida à assistente (ex.: "Não repita a pergunta antes de responder."). Pedidos \
só para aquela resposta não contam.
- Também em "preferencias": o que a reação de {usuario} ao TOM da resposta anterior da \
assistente mostrar, mesmo sem pedido direto. As etiquetas entre chaves na resposta anterior \
({{risada}}, {{carinhosa}}, {{empolgada}}...) mostram a emoção que a voz usou. Ex.: riu de uma \
brincadeira sobre estudos → "Brincadeiras sobre estudos funcionam com {usuario}."; reclamou de \
exagero ("calma", "menos") → "Seja menos expressiva."; se abriu depois de um tom carinhoso → \
"Quando {usuario} estiver chateado, use um tom carinhoso." Só anote quando a reação for clara.
- A fala de {usuario} vem de transcrição de voz: se ela estiver sem sentido ou incompleta \
("aqui assim", "e então o"), é erro de transcrição. Não anote preferência nem fato por ela.

Apagar e corrigir:
- "esquecer": quando {usuario} pedir para apagar ou esquecer algo, ou corrigir uma informação \
("não é cálculo 1, é outra matéria"; "apaga isso"; "esquece que eu disse X"), escreva o fato \
ERRADO ou a apagar, do jeito que ele estaria anotado (ex.: "{usuario} tem prova de cálculo 1 na \
PUCMG em 21/11/2026"). Numa correção, ponha também o fato certo em "fatos". Nunca anote o \
próprio pedido de apagar como fato.

Responda só com JSON no formato {{"fatos": [{{"texto": "...", "area": "...", \
"data": "AAAA-MM-DD ou vazio", "anual": false}}], "pronuncias": [{{"palavra": "...", \
"fala": "..."}}], "preferencias": ["..."], "esquecer": ["..."]}}."""


class FatoExtraido(NamedTuple):
    texto: str
    area: str = ""
    data: date | None = None
    anual: bool = False


class Curadoria(NamedTuple):
    """O que vale guardar de uma troca."""

    fatos: list[FatoExtraido]
    pronuncias: list[tuple[str, str]]  # (palavra, como falar)
    preferencias: list[str]
    esquecer: list[str] = []  # fatos que a pessoa pediu para apagar ou corrigiu


def _dia(hoje: str) -> date:
    try:
        return datetime.strptime(hoje, "%d/%m/%Y").date()
    except ValueError:
        return date.today()


def _ler_data(valor, texto: str, dia: date) -> tuple[date | None, bool]:
    """A data que o modelo deu ou, se faltou ou veio errada, a que estiver escrita no texto."""
    if isinstance(valor, str) and valor.strip():
        try:
            return date.fromisoformat(valor.strip()[:10]), False
        except ValueError:
            pass
    achadas = datas_no_texto(texto, dia)
    return (achadas[0][0], achadas[0][1]) if achadas else (None, False)


def extrair_fatos(*args, **kwargs) -> list[FatoExtraido]:
    """Só os fatos da troca (veja curar)."""
    return curar(*args, **kwargs).fatos


_RISADA = re.compile(r"k{3,}|\b(?:ha){2,}|\b(?:rs){2,}|\bhehe|\brisos?\b", re.IGNORECASE)


def _radicais(texto: str) -> set[str]:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return {palavra[:5] for palavra in re.findall(r"[a-z]{4,}", limpo)}


def _preferencia_tem_base(preferencia: str, pergunta: str) -> bool:
    """Uma preferência só vale se a fala dá base para ela: fala algo parecido ("seja mais
    direta" → "Seja mais direta."), é uma risada (reação ao tom) ou é uma fala de verdade (6
    palavras ou mais). Uma fala curta e sem relação ("Aqui assim.", erro de transcrição) virava
    preferência copiada dos exemplos da instrução."""
    if _RISADA.search(pergunta) or len(pergunta.split()) >= 6:
        return True
    return bool(_radicais(preferencia) & _radicais(pergunta))


def curar(
    config: Config,
    pergunta: str,
    resposta: str,
    hoje: str,
    areas: list[str] | tuple[str, ...] = (),
    timeout: float = 120.0,
    anterior: str = "",
) -> Curadoria:
    """Os fatos que valem guardar desta troca (com área e, se tiverem, data), as pronúncias
    corrigidas e as preferências sobre o jeito de falar."""
    usuario = config.nome_usuario or "a pessoa"
    dia = _dia(hoje)
    lista_areas = ", ".join(areas) if areas else "nenhuma ainda"
    pedido = urllib.request.Request(
        f"{config.ollama_host.rstrip('/')}/api/chat",
        data=json.dumps(
            {
                "model": config.modelo_local.modelo,
                "messages": [
                    {
                        "role": "system",
                        "content": INSTRUCAO.format(
                            usuario=usuario,
                            hoje=hoje,
                            dia_da_semana=NOMES_DOS_DIAS[dia.weekday()],
                            areas=lista_areas,
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Resposta anterior da assistente: {anterior}\n" if anterior else ""
                        )
                        + f"{usuario}: {pergunta}\nAssistente: {resposta}",
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
        dados = json.loads(conteudo)
        fatos = dados.get("fatos", [])
    except (json.JSONDecodeError, AttributeError):
        return Curadoria([], [], [], [])
    resultado = []
    for fato in fatos if isinstance(fatos, list) else []:
        if isinstance(fato, str):  # formato antigo, sem área nem data
            fato = {"texto": fato}
        elif not isinstance(fato, dict):
            continue
        texto = " ".join(str(fato.get("texto", "")).split())
        if not texto:
            continue
        data, anual_no_texto = _ler_data(fato.get("data"), texto, dia)
        anual = fato.get("anual") is True or anual_no_texto
        area = " ".join(str(fato.get("area", "")).split())
        resultado.append(FatoExtraido(texto, area, data, anual if data else False))
    pronuncias = []
    for item in dados.get("pronuncias", []) if isinstance(dados.get("pronuncias"), list) else []:
        if isinstance(item, dict):
            palavra = " ".join(str(item.get("palavra", "")).split())
            fala = " ".join(str(item.get("fala", "")).split())
            if palavra and fala and palavra.lower() != fala.lower():
                pronuncias.append((palavra, fala))
    preferencias = (
        [
            " ".join(item.split())
            for item in (dados.get("preferencias") or [])
            if isinstance(item, str) and item.strip()
        ]
        if isinstance(dados.get("preferencias"), list)
        else []
    )
    preferencias = [p for p in preferencias if _preferencia_tem_base(p, pergunta)]
    esquecer = (
        [
            " ".join(item.split())
            for item in (dados.get("esquecer") or [])
            if isinstance(item, str) and item.strip()
        ]
        if isinstance(dados.get("esquecer"), list)
        else []
    )
    return Curadoria(resultado, pronuncias, preferencias, esquecer)
