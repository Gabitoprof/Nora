"""Voice diagnostics: the model that actually spoke, the continuity state and the times of the last
answer. It goes to the log (`nora.voz`) and to `<dados>/diagnostico_voz.json`, which
`nora --verificar` shows. Only numbers, model names and error types: never the conversation text
nor keys.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path

ARQUIVO = "diagnostico_voz.json"
log = logging.getLogger("nora.voz")

# ElevenLabs continuity: the intonation carrying from one sentence to the next.
# v4: one connection per conversation; HTTP: with the previous sentence (previous_text)
ATIVA = "ativa"
DESATIVADA = "desativada"  # continuidade = false in the config
NAO_SUPORTADA = "não suportada"  # the model refused the previous sentence (HTTP)
ERRO = "erro"  # the dialogue (v4) failed and Nora fell back


@dataclass
class MedidaDaVoz:
    modelo: str  # what actually spoke (e.g. eleven_v4_turbo, or the fallback)
    via: str  # "dialogo" (WebSocket v4), "http" or "http (reserva)"
    continuidade: str
    pedido_ate_primeiro_pcm_ms: int | None = None
    pedido_ate_reproducao_ms: int | None = None
    silencio_entre_trechos_ms: int = 0  # gaps from missing audio, summed
    maior_silencio_ms: int = 0
    alinhamento: bool = False  # per-character alignment arrived (real words in the HUD)
    erro: str = ""  # error type/code, with no personal text
    quando: str = ""
    geracoes: int = 0  # synthesis requests in this answer (v4: 1 turn; HTTP: 1 per batch)
    reservas: list[str] = field(default_factory=list)  # reason for each switch to the fallback


def _ms(inicio: float | None, fim: float | None) -> int | None:
    if inicio is None or fim is None:
        return None
    return max(0, round((fim - inicio) * 1000))


def _curto(motivo: str) -> str:
    """Fallback reason for the log: a short line (the messages carry no conversation text)."""
    return " ".join(str(motivo).split())[:160]


def medir_locutor(locutor, modelo: str, via: str, continuidade: str) -> MedidaDaVoz:
    """The measurement of an answer spoken through the HTTP path (sentence by sentence)."""
    return MedidaDaVoz(
        modelo=modelo,
        via=via,
        continuidade=continuidade,
        pedido_ate_primeiro_pcm_ms=_ms(locutor.primeiro_pedido, locutor.primeiro_audio),
        pedido_ate_reproducao_ms=_ms(locutor.primeiro_pedido, locutor.inicio_som),
        silencio_entre_trechos_ms=round(locutor.silencio_ms),
        maior_silencio_ms=round(locutor.maior_silencio_ms),
        geracoes=locutor.geracoes,
    )


def medir_turno(turno, modelo: str, continuidade: str, erro: str = "") -> MedidaDaVoz:
    """The measurement of an answer spoken through the dialogue (v4)."""
    audio = turno.audio
    return MedidaDaVoz(
        modelo=modelo,
        via="dialogo",
        continuidade=continuidade,
        pedido_ate_primeiro_pcm_ms=_ms(turno.pedido, turno.primeiro_pcm),
        pedido_ate_reproducao_ms=_ms(turno.pedido, audio.inicio_som),
        silencio_entre_trechos_ms=round(audio.silencio_ms),
        maior_silencio_ms=round(audio.maior_silencio_ms),
        alinhamento=turno.recebeu_alinhamento,
        erro=erro,
        geracoes=1,
    )


def registrar(pasta_dados: Path, medida: MedidaDaVoz) -> None:
    """Stores the last measurement and writes a log line. Never raises."""
    medida.quando = datetime.now().isoformat(timespec="seconds")
    log.info(
        "voz: modelo=%s via=%s continuidade=%s primeiro_pcm=%sms reproducao=%sms "
        "silencio=%sms (maior %sms) alinhamento=%s geracoes=%s%s%s",
        medida.modelo,
        medida.via,
        medida.continuidade,
        medida.pedido_ate_primeiro_pcm_ms,
        medida.pedido_ate_reproducao_ms,
        medida.silencio_entre_trechos_ms,
        medida.maior_silencio_ms,
        "sim" if medida.alinhamento else "não",
        medida.geracoes,
        f" erro={medida.erro}" if medida.erro else "",
        "".join(f" reserva={_curto(m)!r}" for m in medida.reservas),
    )
    try:
        pasta_dados.mkdir(parents=True, exist_ok=True)
        (pasta_dados / ARQUIVO).write_text(
            json.dumps(asdict(medida), ensure_ascii=False, indent=1), encoding="utf-8"
        )
    except OSError:
        pass


def ler(pasta_dados: Path) -> MedidaDaVoz | None:
    try:
        dados = json.loads((pasta_dados / ARQUIVO).read_text(encoding="utf-8"))
        conhecidos = {f.name for f in fields(MedidaDaVoz)}  # file from an earlier version
        return MedidaDaVoz(**{k: v for k, v in dados.items() if k in conhecidos})
    except (OSError, ValueError, TypeError):
        return None


def resumo(medida: MedidaDaVoz) -> str:
    """A readable line for --verificar and --medir."""
    partes = [f"{medida.modelo} ({medida.via})", f"continuidade {medida.continuidade}"]
    if medida.pedido_ate_primeiro_pcm_ms is not None:
        partes.append(f"primeiro áudio em {medida.pedido_ate_primeiro_pcm_ms} ms")
    if medida.pedido_ate_reproducao_ms is not None:
        partes.append(f"tocando em {medida.pedido_ate_reproducao_ms} ms")
    partes.append(
        f"silêncio entre trechos {medida.silencio_entre_trechos_ms} ms "
        f"(maior {medida.maior_silencio_ms} ms)"
    )
    partes.append("palavras alinhadas" if medida.alinhamento else "palavras estimadas")
    if medida.geracoes:
        partes.append(f"{medida.geracoes} {'geração' if medida.geracoes == 1 else 'gerações'}")
    if medida.erro:
        partes.append(f"erro: {medida.erro}")
    for motivo in medida.reservas:
        partes.append(f"reserva: {_curto(motivo)}")
    return ", ".join(partes)
