"""Datas em português: acha datas num texto ("21/11", "12 de março") e o período de que uma
pergunta fala ("amanhã", "sexta", "semana que vem", "em dezembro"), para a agenda da memória.

Tudo em funções puras, que recebem o dia de hoje: fácil de testar e sem relógio escondido.
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
    """Minúsculas e sem acento, para comparar ("março" e "marco", "terça" e "terca"). Mantém a
    pontuação, que separa as datas ("21/11")."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return " ".join("".join(c for c in sem_acento if not unicodedata.combining(c)).split())


def _data_valida(ano: int, mes: int, dia: int) -> date | None:
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _mais_perto(mes: int, dia: int, hoje: date) -> date | None:
    """A data com esse dia e mês mais perto de hoje (ano passado, este ou o próximo)."""
    candidatas = [_data_valida(hoje.year + delta, mes, dia) for delta in (-1, 0, 1)]
    candidatas = [c for c in candidatas if c]
    return min(candidatas, key=lambda c: abs((c - hoje).days)) if candidatas else None


def _ano(texto: str | None, mes: int, dia: int, hoje: date) -> date | None:
    if texto:
        ano = int(texto)
        return _data_valida(ano + 2000 if ano < 100 else ano, mes, dia)
    return _mais_perto(mes, dia, hoje)


def datas_no_texto(texto: str, hoje: date) -> list[tuple[date, bool]]:
    """Datas escritas num texto, como (data, se repete todo ano). Sem ano, usa a mais perto de
    hoje. Aniversários e "todo ano" são anuais."""
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
    """O período de que a pergunta fala, como (primeiro dia, último dia), ou None se ela não
    fala de nenhum."""
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
        if hoje.weekday() == 6:  # domingo: o fim de semana é hoje
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
    """Em que dia o evento cai no período (eventos anuais caem todo ano), ou None."""
    if not evento.anual:
        return evento.data if inicio <= evento.data <= fim else None
    for ano in range(inicio.year, fim.year + 1):
        dia = 28 if (evento.data.month, evento.data.day) == (2, 29) else evento.data.day
        data = _data_valida(ano, evento.data.month, dia)
        if data and inicio <= data <= fim:
            return data
    return None


def quando(data: date, hoje: date) -> str:
    """'sábado, 21/11/2026 (daqui a 3 dias)', para a nota que a Nora lê."""
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
    """Uma data escrita à mão: '21/11/2026', '21/11', '2026-11-21' ou '21 de novembro'."""
    texto = texto.strip()
    try:
        return date.fromisoformat(texto)
    except ValueError:
        pass
    achadas = datas_no_texto(texto, hoje)
    return achadas[0][0] if achadas else None
