"""Observador opcional do áudio já existente: dados limitados, trabalho fora do callback."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from contextlib import contextmanager

from nora.acustica import MAX_QUADROS, EnvelopeTemporal, Medidor, temporizar
from nora.emocao import emocoes_em
from nora.falhas_hud import registrar

_contexto = threading.local()


@contextmanager
def contexto_fala(texto: str, emocao: str = "", texto_depois: bool = False):
    """O texto que vai tocar (para estimar as palavras) e, se souber, a emoção da fala. No
    diálogo em streaming o texto ainda não existe ao começar (`texto_depois`): as palavras chegam
    alinhadas pela própria voz (`ReproducaoHUD.alinhar`) e, se o alinhamento não vier, são
    estimadas no fim com o texto completo (`ReproducaoHUD.definir_texto`)."""
    anterior = (
        getattr(_contexto, "texto", ""),
        getattr(_contexto, "emocao", ""),
        getattr(_contexto, "texto_depois", False),
    )
    _contexto.texto, _contexto.emocao, _contexto.texto_depois = texto, emocao, texto_depois
    try:
        yield
    finally:
        _contexto.texto, _contexto.emocao, _contexto.texto_depois = anterior


def _atraso(tempo):
    try:
        valor = float(tempo.outputBufferDacTime - tempo.currentTime)
        return min(2.0, max(0.0, valor)) if math.isfinite(valor) else 0.0
    except (AttributeError, TypeError, ValueError):
        return 0.0


class ReproducaoHUD:
    def __init__(self, dono, pcm: bytes | None, taxa: int, canais: int):
        self.dono, self.pcm, self.taxa, self.canais = dono, pcm, taxa, canais
        self.streaming = pcm is None
        self.id = dono.ponte._id_reproducao + 1
        dono.ponte._id_reproducao = self.id
        self.duracao = len(pcm or b"") / (2 * canais * taxa) * 1000
        self.recebidos = 0
        self.epoca = dono.ponte._epoca_privacidade
        texto = getattr(_contexto, "texto", "")
        self.texto_pendente = texto if not dono.ponte.estado["privacidade"] else ""
        depois = getattr(_contexto, "texto_depois", False) and not dono.ponte.estado["privacidade"]
        self.envelope_temporal = (
            EnvelopeTemporal(taxa, canais)
            if self.streaming and (self.texto_pendente or depois)
            else None
        )
        self.tempos = None
        emocoes = emocoes_em(texto)
        self.emocao = getattr(_contexto, "emocao", "") or (emocoes[0].nome if emocoes else "neutra")
        self.entregas: deque = deque(maxlen=4)
        self.ultima = None
        self.encerrada = False
        self.anunciada = False
        self.ultimo_envio = -1.0
        self.medidor = Medidor()

    def entregar(self, inicio: int, fim: int, tempo=None):
        if not self.encerrada:
            self.entregas.append((inicio, fim, time.monotonic() + _atraso(tempo)))
            self.dono.sinal.set()

    def entregar_pcm(self, pcm: bytes, inicio: int, fim: int, tempo=None):
        """Streaming: cópia de no máximo 2048 quadros, inclusive zeros de espera da rede."""
        if self.encerrada:
            return
        quadro = 2 * self.canais
        corte = max(0, len(pcm) // quadro - MAX_QUADROS)
        self.entregas.append(
            (
                min(fim, inicio + corte),
                fim,
                time.monotonic() + _atraso(tempo) + corte / self.taxa,
                bytes(pcm[corte * quadro :]),
            )
        )
        self.dono.sinal.set()

    def receber_pcm(self, pcm: bytes):
        """Linha do download, não callback: somente duração e RMS de 20 ms são retidos."""
        if self.encerrada:
            return
        self.recebidos += len(pcm) // (2 * self.canais)
        self.duracao = self.recebidos / self.taxa * 1000
        if self.envelope_temporal is not None:
            self.envelope_temporal.alimentar(pcm)

    def alinhar(self, palavras: list[dict]):
        """Palavras com o tempo real dado pela voz (alinhamento do ElevenLabs): substituem a
        estimativa. Saem na HUD só com o conteúdo visível (a privacidade é checada ao publicar)."""
        if self.encerrada or not palavras:
            return
        # Privado (ou opt-in revogado depois que esta fala começou): as palavras nem ficam
        # guardadas no backend, não só deixam de ser publicadas.
        if (
            self.dono.ponte.estado["privacidade"]
            or self.dono.ponte._epoca_privacidade != self.epoca
        ):
            return
        self.envelope_temporal = None
        self.texto_pendente = ""
        fim = max(p["fim_ms"] for p in palavras)
        self.tempos = {
            "duracao_ms": round(max(self.duracao, fim), 3),
            "precisao": "alinhada",
            "palavras": palavras,
        }
        self.dono.sinal.set()

    def definir_texto(self, texto: str):
        """Reserva do alinhamento: o texto completo, para estimar as palavras no fim."""
        if self.envelope_temporal is not None and not self.dono.ponte.estado["privacidade"]:
            self.texto_pendente = texto

    def concluir_tempos(self):
        if self.envelope_temporal is not None and self.texto_pendente and not self.encerrada:
            self.tempos = self.envelope_temporal.finalizar(self.texto_pendente)
        self.envelope_temporal = None
        self.texto_pendente = ""
        self.dono.sinal.set()

    def encerrar(self):
        self.encerrada = True
        self.pcm = b""
        self.tempos = None
        self.texto_pendente = ""
        self.envelope_temporal = None
        self.entregas.clear()
        self.ultima = None
        self.dono.sinal.set()


class AnalisadorHUD:
    def __init__(self, ponte):
        self.ponte = ponte
        self.microfone: deque = deque(maxlen=4)
        self.reproducao: ReproducaoHUD | None = None
        self.medidor_mic = Medidor()
        self.ultimo_mic = self.ultima_oferta_mic = -1.0
        self.sinal = threading.Event()
        self.parado = False
        self.thread = threading.Thread(target=self._rodar, name="nora-hud-acustica", daemon=True)
        self.thread.start()

    def preparar(self, pcm, taxa, canais):
        if self.reproducao is not None:
            self.reproducao.encerrar()
        atual = ReproducaoHUD(self, pcm, taxa, canais)
        self.reproducao = atual
        self.microfone.clear()
        self.sinal.set()
        return atual

    def micro(self, pcm, taxa, canais):
        agora = time.monotonic()
        if agora - self.ultima_oferta_mic < 0.05 or self.ponte._reproduzindo:
            return
        self.ultima_oferta_mic = agora
        self.microfone.append((pcm[: MAX_QUADROS * 2 * canais], taxa, canais, agora))
        self.sinal.set()

    def _voz(self, agora):
        atual = self.reproducao
        if atual is None or atual.encerrada:
            return
        while atual.entregas and atual.entregas[0][2] <= agora:
            atual.ultima = atual.entregas.popleft()
        if atual.ultima is None or agora - atual.ultimo_envio < 0.05:
            return
        inicio, fim, quando = atual.ultima[:3]
        passados = max(0, int((agora - quando) * atual.taxa))
        if atual.streaming:
            recebido = atual.ultima[3]
            tocados = min(len(recebido) // (2 * atual.canais), passados)
            if (
                not tocados
                or agora - quando > len(recebido) / (2 * atual.canais * atual.taxa) + 0.1
            ):
                return
            pcm = recebido[: tocados * 2 * atual.canais]
            quadro = min(fim, inicio + tocados)
        else:
            quadro = min(fim, inicio + passados)
            if quadro >= fim:
                return
            comeco = max(0, quadro - MAX_QUADROS)
            pcm = (atual.pcm or b"")[comeco * 2 * atual.canais : quadro * 2 * atual.canais]
        if not self.ponte._trava.acquire(blocking=False):
            return
        try:
            if (
                atual.encerrada
                or not self.ponte._reproduzindo
                or self.ponte._id_reproducao != atual.id
            ):
                return
            if not atual.anunciada:
                self.ponte.publicar("emocao", nome=atual.emocao)
                atual.anunciada = True
            if atual.tempos is not None:
                if (
                    self.ponte._epoca_privacidade == atual.epoca
                    and not self.ponte.estado["privacidade"]
                ):
                    if self.ponte.publicar("fala_temporizada", id=atual.id, **atual.tempos):
                        atual.tempos = None
                else:
                    atual.tempos = None
        finally:
            self.ponte._trava.release()
        dt = 0.05 if atual.ultimo_envio < 0 else agora - atual.ultimo_envio
        medidas = atual.medidor.medir(pcm, atual.taxa, atual.canais, dt)
        if atual.encerrada or self.reproducao is not atual:
            return
        self.ponte.publicar(
            "acustica",
            fonte="voz",
            ativo=True,
            reproducao_id=atual.id,
            posicao_ms=round(quadro / atual.taxa * 1000, 3),
            duracao_ms=round(atual.duracao, 3),
            **medidas,
        )
        atual.ultimo_envio = agora

    def _micro(self, agora):
        if self.ponte._reproduzindo or not self.microfone or agora - self.ultimo_mic < 0.05:
            return
        pcm, taxa, canais, recebido = self.microfone.pop()
        self.microfone.clear()
        if agora - recebido > 0.3:
            return
        dt = 0.05 if self.ultimo_mic < 0 else agora - self.ultimo_mic
        medidas = self.medidor_mic.medir(pcm, taxa, canais, dt)
        self.ponte.publicar(
            "acustica",
            fonte="microfone",
            ativo=True,
            reproducao_id=0,
            posicao_ms=0.0,
            duracao_ms=0.0,
            **medidas,
        )
        self.ultimo_mic = agora

    def _rodar(self):
        while not self.parado:
            self.sinal.wait(0.01)
            self.sinal.clear()
            try:
                atual = self.reproducao
                if (
                    atual is not None
                    and atual.texto_pendente
                    and not atual.streaming
                    and not atual.encerrada
                ):
                    texto = atual.texto_pendente
                    atual.texto_pendente = ""
                    tempos = temporizar(texto, atual.pcm or b"", atual.taxa, atual.canais)
                    if not atual.encerrada and self.ponte._epoca_privacidade == atual.epoca:
                        atual.tempos = tempos
                agora = time.monotonic()
                self._voz(agora)
                self._micro(agora)
            except Exception as erro:  # visualização nunca interrompe STT, LLM, TTS ou áudio
                registrar("hud_audio.rodar", erro)

    def encerrar(self):
        self.parado = True
        if self.reproducao is not None:
            self.reproducao.encerrar()
        self.microfone.clear()
        self.sinal.set()
        self.thread.join(timeout=0.5)
