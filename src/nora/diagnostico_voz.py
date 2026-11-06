"""Diagnóstico da voz: o modelo que falou de fato, o estado da continuidade e os tempos da última
resposta. Vai para o log (`nora.voz`) e para `<dados>/diagnostico_voz.json`, que o
`nora --verificar` mostra. Só números, nomes de modelo e tipos de erro: nunca o texto da conversa
nem chaves.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

ARQUIVO = "diagnostico_voz.json"
log = logging.getLogger("nora.voz")

# Continuidade do ElevenLabs: a entonação seguindo de uma frase para a outra.
ATIVA = "ativa"  # v4: uma conexão por conversa; HTTP: com a frase anterior (previous_text)
DESATIVADA = "desativada"  # continuidade = false na config
NAO_SUPORTADA = "não suportada"  # o modelo recusou a frase anterior (HTTP)
ERRO = "erro"  # o diálogo (v4) falhou e a Nora caiu na reserva


@dataclass
class MedidaDaVoz:
    modelo: str  # o que falou de fato (ex.: eleven_v4_turbo, ou a reserva)
    via: str  # "dialogo" (WebSocket v4), "http" ou "http (reserva)"
    continuidade: str
    pedido_ate_primeiro_pcm_ms: int | None = None
    pedido_ate_reproducao_ms: int | None = None
    silencio_entre_trechos_ms: int = 0  # buracos por falta de áudio, somados
    maior_silencio_ms: int = 0
    alinhamento: bool = False  # chegou alinhamento por caractere (palavras reais na HUD)
    erro: str = ""  # tipo/código do erro, sem texto pessoal
    quando: str = ""


def _ms(inicio: float | None, fim: float | None) -> int | None:
    if inicio is None or fim is None:
        return None
    return max(0, round((fim - inicio) * 1000))


def medir_turno(turno, modelo: str, continuidade: str, erro: str = "") -> MedidaDaVoz:
    """A medida de uma resposta falada pelo diálogo (v4)."""
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
    )


def registrar(pasta_dados: Path, medida: MedidaDaVoz) -> None:
    """Grava a última medida e escreve uma linha no log. Nunca levanta erro."""
    medida.quando = datetime.now().isoformat(timespec="seconds")
    log.info(
        "voz: modelo=%s via=%s continuidade=%s primeiro_pcm=%sms reproducao=%sms "
        "silencio=%sms (maior %sms) alinhamento=%s%s",
        medida.modelo,
        medida.via,
        medida.continuidade,
        medida.pedido_ate_primeiro_pcm_ms,
        medida.pedido_ate_reproducao_ms,
        medida.silencio_entre_trechos_ms,
        medida.maior_silencio_ms,
        "sim" if medida.alinhamento else "não",
        f" erro={medida.erro}" if medida.erro else "",
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
        return MedidaDaVoz(**dados)
    except (OSError, ValueError, TypeError):
        return None


def resumo(medida: MedidaDaVoz) -> str:
    """Uma linha legível para o --verificar e o --medir."""
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
    if medida.erro:
        partes.append(f"erro: {medida.erro}")
    return ", ".join(partes)
