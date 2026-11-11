"""Dates in Portuguese: finds dates in a text ("21/11", "12 de março") and the period a question
talks about ("amanhã", "sexta", "semana que vem", "em dezembro"), for the memory agenda.

All in pure functions that take today's date: easy to test and with no hidden clock.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta

MESES = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
NOMES_DOS_MESES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
DIAS_DA_SEMANA = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}
NOMES_DOS_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

_MES = "|".join(MESES)
_NUMERICA = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
_POR_EXTENSO = re.compile(rf"\b(\d{{1,2}})(?:º|o)? de ({_MES})(?: de (\d{{4}}))?\b")
_DIA_SOLTO = re.compile(r"\bdia (\d{1,2})\b")
_SO_MES = re.compile(rf"\b(?:em|de|no mes de) ({_MES})\b")
_ANUAL = re.compile(r"aniversari|todo ano|todos os anos|anualmente")


@dataclass(frozen=True)
class Evento:
    id: int
    data: date
    texto: str
    anual: bool = False
    area: str = ""
    fato_id: int | None = None


def _texto(texto: str) -> str:
    """Lowercase and without accents, for comparison ("março" and "marco", "terça" and "terca").
    Keeps punctuation, which separates the dates ("21/11")."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return " ".join("".join(c for c in sem_acento if not unicodedata.combining(c)).split())


def _data_valida(ano: int, mes: int, dia: int) -> date | None:
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _mais_perto(mes: int, dia: int, hoje: date) -> date | None:
    """The date with that day and month closest to today (last year, this one or the next)."""
    candidatas = [_data_valida(hoje.year + delta, mes, dia) for delta in (-1, 0, 1)]
    candidatas = [c for c in candidatas if c]
    return min(candidatas, key=lambda c: abs((c - hoje).days)) if candidatas else None


def _ano(texto: str | None, mes: int, dia: int, hoje: date) -> date | None:
    if texto:
        ano = int(texto)
        return _data_valida(ano + 2000 if ano < 100 else ano, mes, dia)
    return _mais_perto(mes, dia, hoje)


def datas_no_texto(texto: str, hoje: date) -> list[tuple[date, bool]]:
    """Dates written in a text, as (date, whether it repeats every year). Without a year, uses the
    one closest to today. Birthdays and "todo ano" are yearly."""
    limpo = _texto(texto)
    anual = bool(_ANUAL.search(limpo))
    achadas: list[date] = []
    for dia, mes, ano in _NUMERICA.findall(limpo):
        data = _ano(ano, int(mes), int(dia), hoje)
        if data:
            achadas.append(data)
    for dia, mes, ano in _POR_EXTENSO.findall(limpo):
        data = _ano(ano, MESES[mes], int(dia), hoje)
        if data:
            achadas.append(data)
    return [(data, anual) for data in dict.fromkeys(achadas)]


def _fim_do_mes(dia: date) -> date:
    proximo = date(dia.year + dia.month // 12, dia.month % 12 + 1, 1)
    return proximo - timedelta(days=1)


def intervalo_da_pergunta(texto: str, hoje: date) -> tuple[date, date] | None:
    """The period the question talks about, as (first day, last day), or None if it mentions
    none."""
    t = _texto(texto)
    dias: list[date] = []

    def periodo(inicio: date, fim: date) -> None:
        dias.extend([inicio, fim])

    relativos = {
        "depois de amanha": 2,
        "anteontem": -2,
        "amanha": 1,
        "ontem": -1,
        "hoje": 0,
    }
    resto = t
    for palavra, delta in relativos.items():
        if re.search(rf"\b{palavra}\b", resto):
            dias.append(hoje + timedelta(days=delta))
            resto = re.sub(rf"\b{palavra}\b", " ", resto)
    segunda = hoje - timedelta(days=hoje.weekday())
    if re.search(r"\b(semana que vem|proxima semana)\b", t):
        periodo(segunda + timedelta(days=7), segunda + timedelta(days=13))
    elif re.search(r"\b(essa|esta|nessa|nesta) semana\b", t):
        periodo(hoje, segunda + timedelta(days=6))
    elif re.search(r"\bsemana passada\b", t):
        periodo(segunda - timedelta(days=7), segunda - timedelta(days=1))
    if re.search(r"\bfim de semana\b|\bfinal de semana\b", t):
        if hoje.weekday() == 6:  # Sunday: the weekend is today
            periodo(hoje, hoje)
        else:
            sabado = hoje + timedelta(days=(5 - hoje.weekday()) % 7)
            periodo(sabado, sabado + timedelta(days=1))
    if re.search(r"\b(mes que vem|proximo mes)\b", t):
        inicio = _fim_do_mes(hoje) + timedelta(days=1)
        periodo(inicio, _fim_do_mes(inicio))
    elif re.search(r"\b(esse|este|nesse|neste) mes\b", t):
        periodo(hoje, _fim_do_mes(hoje))
    for nome, numero in DIAS_DA_SEMANA.items():
        achado = re.search(rf"\b(proxima |proximo )?{nome}(-feira| feira)?( que vem)?\b", t)
        if achado and not re.search(rf"\b{nome}\w* passad", t):
            avanco = (numero - hoje.weekday()) % 7
            if avanco == 0 and (achado.group(1) or achado.group(3)):
                avanco = 7
            dias.append(hoje + timedelta(days=avanco))
        elif re.search(rf"\b{nome}(-feira| feira)? passad", t):
            dias.append(hoje - timedelta(days=(hoje.weekday() - numero) % 7 or 7))
    dias.extend(data for data, _ in datas_no_texto(texto, hoje))
    if not _POR_EXTENSO.search(t):
        for mes in _SO_MES.findall(t):
            inicio = _mais_perto(MESES[mes], 1, hoje) or hoje
            periodo(inicio, _fim_do_mes(inicio))
    for dia in _DIA_SOLTO.findall(t):
        data = _data_valida(hoje.year, hoje.month, int(dia))
        if data and data < hoje - timedelta(days=7):
            proximo = _fim_do_mes(hoje) + timedelta(days=1)
            data = _data_valida(proximo.year, proximo.month, int(dia))
        if data:
            dias.append(data)
    return (min(dias), max(dias)) if dias else None


def ocorrencia(evento: Evento, inicio: date, fim: date) -> date | None:
    """Which day the event falls on in the period (yearly events fall every year), or None."""
    if not evento.anual:
        return evento.data if inicio <= evento.data <= fim else None
    for ano in range(inicio.year, fim.year + 1):
        dia = 28 if (evento.data.month, evento.data.day) == (2, 29) else evento.data.day
        data = _data_valida(ano, evento.data.month, dia)
        if data and inicio <= data <= fim:
            return data
    return None


def quando(data: date, hoje: date) -> str:
    """'sábado, 21/11/2026 (daqui a 3 dias)', for the note Nora reads."""
    distancia = (data - hoje).days
    if distancia == 0:
        perto = "hoje"
    elif distancia == 1:
        perto = "amanhã"
    elif distancia == -1:
        perto = "ontem"
    elif distancia > 0:
        perto = f"daqui a {distancia} dias"
    else:
        perto = f"há {-distancia} dias"
    return f"{NOMES_DOS_DIAS[data.weekday()]}, {data:%d/%m/%Y} ({perto})"


def ler_data(texto: str, hoje: date) -> date | None:
    """A hand-written date: '21/11/2026', '21/11', '2026-11-21' or '21 de novembro'."""
    texto = texto.strip()
    try:
        return date.fromisoformat(texto)
    except ValueError:
        pass
    achadas = datas_no_texto(texto, hoje)
    return achadas[0][0] if achadas else None


# --- date math --------------------------------------------------------------------------------
# The model gets today's date, but gets the math wrong ("daqui a 23 dias" came out with the wrong
# day and weekday). Here the code does the math and hands it over ready for the model to speak.

_NUMEROS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13,
    "catorze": 14, "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40,
    "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100,
    "cento": 100, "duzentos": 200, "trezentos": 300, "quatrocentos": 400, "quinhentos": 500,
}  # fmt: skip
_PALAVRA_NUMERO = "|".join(sorted(_NUMEROS, key=len, reverse=True))
_NUMERO = rf"\d{{1,4}}|(?:{_PALAVRA_NUMERO})(?: e (?:{_PALAVRA_NUMERO}))*"
_UNIDADE = r"dias?|semanas?|mes|meses|anos?"
_FUTURO = re.compile(rf"\b(?:daqui a|daqui|dentro de|em)\s+({_NUMERO})\s+({_UNIDADE})\b")
# "E daqui a 24?" right after "daqui a 23 dias": the unit comes from the previous question.
_SEM_UNIDADE = re.compile(rf"\b(?:daqui a|daqui|dentro de)\s+({_NUMERO})\s*(?:[?.!]|$)")
_PASSADO = re.compile(
    rf"\b(?:ha|faz)\s+({_NUMERO})\s+({_UNIDADE})\b|\b({_NUMERO})\s+({_UNIDADE})\s+atras\b"
)


def _numero(texto: str) -> int | None:
    if texto.isdigit():
        return int(texto)
    partes = [_NUMEROS.get(parte) for parte in texto.split(" e ")]
    return sum(partes) if partes and None not in partes else None


def _somar(hoje: date, quantidade: int, unidade: str) -> date | None:
    """`hoje` plus `quantidade` (negative = backwards) days, weeks, months or years. Month and year
    land on the last day of the month when the day does not exist (31/01 + 1 month = 28 or
    29/02)."""
    try:
        if unidade.startswith("dia"):
            return hoje + timedelta(days=quantidade)
        if unidade.startswith("semana"):
            return hoje + timedelta(weeks=quantidade)
        meses = quantidade * (12 if unidade.startswith("ano") else 1)
        indice = hoje.year * 12 + hoje.month - 1 + meses
        ano, mes = divmod(indice, 12)
        primeiro = date(ano, mes + 1, 1)
        return primeiro.replace(day=min(hoje.day, _fim_do_mes(primeiro).day))
    except (OverflowError, ValueError):
        return None


def _dia_por_extenso(data: date) -> str:
    semana = NOMES_DOS_DIAS[data.weekday()]
    semana += "" if data.weekday() >= 5 else "-feira"
    return f"{semana}, {data.day} de {NOMES_DOS_MESES[data.month - 1]} de {data.year}"


def _unidade(unidade: str) -> str:
    return unidade.replace("mes", "mês") if unidade == "mes" else unidade


def contas_de_data(texto: str, hoje: date, anterior: str | list[str] = "") -> list[str]:
    """The date calculations the question asks for, already done: "daqui a 24 dias", "há 2 semanas",
    "3 meses atrás" and the weekday of the dates mentioned ("25/12", "29 de novembro"). With
    `anterior` (the earlier questions, oldest to newest), "e daqui a 24?" uses the unit of the
    last one that had one ("daqui a 23 dias" → "e daqui a 24?" → "daqui a 50")."""
    limpo = _texto(texto)
    pedidos = [(achado.group(1), achado.group(2)) for achado in _FUTURO.finditer(limpo)]
    if not pedidos:
        anteriores = [anterior] if isinstance(anterior, str) else anterior
        antes = next(
            (a for a in map(_FUTURO.search, map(_texto, reversed(anteriores[-5:]))) if a), None
        )
        if antes:
            unidade = antes.group(2)
            pedidos = [(achado.group(1), unidade) for achado in _SEM_UNIDADE.finditer(limpo)]
    linhas: list[str] = []
    for numero, unidade in pedidos:
        quantidade = _numero(numero)
        data = _somar(hoje, quantidade, unidade) if quantidade else None
        if data:
            linhas.append(f"- daqui a {numero} {_unidade(unidade)}: {_dia_por_extenso(data)}")
    for achado in _PASSADO.finditer(limpo):
        numero, unidade = (
            (achado.group(1), achado.group(2)) if achado.group(1) else achado.group(3, 4)
        )
        quantidade = _numero(numero)
        data = _somar(hoje, -quantidade, unidade) if quantidade else None
        if data:
            linhas.append(f"- {numero} {_unidade(unidade)} atrás: {_dia_por_extenso(data)}")
    for data, _ in datas_no_texto(texto, hoje):
        linhas.append(f"- {data:%d/%m/%Y} cai num(a) {_dia_por_extenso(data)}")
    return list(dict.fromkeys(linhas))
