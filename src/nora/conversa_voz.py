"""Conversa por voz (parte 2 da v0.1.0): aperta Enter, fala, e a Nora responde falando.

Ouvido (whisper-server), cérebro (Ollama) e voz (Piper) são serviços separados. A resposta é
cortada em frases enquanto o modelo escreve: uma linha sintetiza a próxima frase enquanto outra
toca a atual, então a Nora começa a falar antes de terminar de pensar.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import TextIO

from nora import audio
from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import Config
from nora.conversa import COMANDOS_SAIR, Conversa, nova_conversa, pede_retomada
from nora.emocao import FiltroDeTela, emocoes_em
from nora.frases import SeparadorDeFrases
from nora.hud import emitir
from nora.hud_audio import contexto_fala
from nora.melhorias import iniciar as iniciar_melhorias
from nora.melhorias import ler_entrada
from nora.ouvido import OuvidoWhisper, dica_do_ouvido
from nora.prioridade import abafar_outros
from nora.servico import ServicoIndisponivel
from nora.troca_voz import atender_pedido, pedido_de_voz
from nora.voz import (
    VozComReserva,
    VozElevenLabs,
    VozHTTP,
    VozTrocavel,
    achar_dialogo,
    com_pronuncias_aprendidas,
    em_partes,
)

_FIM = object()


def _e_pergunta(frase: str) -> bool:
    return frase.rstrip(" \"'”)»").endswith("?")


# Até quantos caracteres de frases que já estão esperando vão juntos num pedido à voz.
LIMITE_DO_LOTE = 400
# Quanto um pedido curto (abaixo de [voz] juntar_curta) espera a próxima frase para ir junto.
ESPERA_PARA_JUNTAR = 1.5


@dataclass
class Tempos:
    """Segundos de cada etapa de uma fala, contados a partir do fim da gravação."""

    transcricao: float = 0.0
    primeira_frase: float = 0.0
    comeco_da_voz: float = 0.0
    erros: list[str] = field(default_factory=list)


class Locutor:
    """Recebe frases e as fala em ordem: uma linha sintetiza, outra toca."""

    def __init__(
        self,
        voz: VozHTTP | VozElevenLabs | VozComReserva,
        tocar: Callable[[bytes], None],
        inicio: float,
        abafar=nullcontext,
        juntar: int = 0,
        espera: float = ESPERA_PARA_JUNTAR,
    ) -> None:
        self.voz = voz
        self.juntar = juntar
        self.espera = espera
        self.tocar = tocar
        self.inicio = inicio
        self.abafar = abafar
        self.tempos = Tempos()
        self._frases: queue.Queue = queue.Queue()
        self._audios: queue.Queue = queue.Queue(maxsize=2)
        self._sintese = threading.Thread(target=self._sintetizar, daemon=True)
        self._toque = threading.Thread(target=self._tocar, daemon=True)
        self._sintese.start()
        self._toque.start()

    def falar(self, frase: str) -> None:
        self._frases.put(frase)

    def cancelar(self) -> None:
        """Ctrl+C: o que já foi pedido termina de tocar (frase por frase não tem como cortar)."""

    def terminar(self) -> None:
        """Espera tudo o que foi pedido ser falado."""
        self._frases.put(_FIM)
        self._sintese.join()
        self._toque.join()

    def _sintetizar(self) -> None:
        """Sintetiza as frases em ordem. Se várias já estão esperando (a voz é mais lenta que
        o modelo, como no ComfyUI), junta-as num pedido só: menos pedidos, menos pausas."""
        acabou = False
        anterior = None
        while not acabou:
            frase = self._frases.get()
            if frase is _FIM:
                break
            lote = [frase]
            # Uma pergunta sempre fecha o pedido: com o "?" no fim, a voz sobe a entonação; no
            # meio do texto, muitos modelos achatam.
            while sum(len(f) for f in lote) < LIMITE_DO_LOTE and not _e_pergunta(lote[-1]):
                # Um pedido curto ("Hahaha, esse atchim!") espera um pouco a próxima frase: sozinho,
                # vira um áudio curto que acaba antes da próxima ficar pronta (pausa), e a voz
                # recomeça sem contexto (muda o tom).
                curto = sum(len(f) for f in lote) < self.juntar
                try:
                    proxima = (
                        self._frases.get(timeout=self.espera)
                        if curto
                        else self._frases.get_nowait()
                    )
                except queue.Empty:
                    break
                if proxima is _FIM:
                    acabou = True
                    break
                lote.append(proxima)
            if self.tempos.erros:
                continue
            if isinstance(anterior, audio.AudioEmPartes):
                anterior.baixado.wait()
            try:
                texto = " ".join(lote)
                anterior = em_partes(self.voz, texto)
                self._audios.put((anterior, texto))
            except ServicoIndisponivel as erro:
                self.tempos.erros.append(str(erro))
        self._audios.put(_FIM)

    def _tocar(self) -> None:
        item = self._audios.get()
        if item is _FIM:
            return
        with self.abafar():  # os outros programas ficam mais baixos enquanto ela fala
            while item is not _FIM:
                wav, texto = item
                em_streaming = isinstance(wav, audio.AudioEmPartes)
                if em_streaming:
                    wav.primeira.wait()
                if not self.tempos.comeco_da_voz:
                    self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
                try:
                    with contexto_fala(texto):
                        self.tocar(wav)
                except Exception as erro:  # um problema no alto-falante não derruba a conversa
                    self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")
                if em_streaming and wav.erro is not None:
                    self.tempos.erros.append(f"A voz parou no meio da frase: {wav.erro}")
                item = self._audios.get()


def texto_restante(frases: list[str], alinhados: list[str]) -> str | None:
    """O que falta falar depois do que o áudio já cobriu, cortado num limite de palavra.

    `alinhados` são os caracteres que o alinhamento do ElevenLabs já cobriu (áudio recebido, que
    vai tocar inteiro). A contagem usa só letras e números, sem as etiquetas de emoção ({calma}) e
    as audio tags ([happy]). Uma palavra pela metade é pulada (melhor que repetir o que já se
    ouviu). Devolve None se não houver limite confiável (sem alinhamento, ou contagem maior que o
    texto)."""

    def letras(texto: str):
        dentro = ""
        for i, c in enumerate(texto):
            if dentro:
                if c == dentro:
                    dentro = ""
                continue
            if c in "{[":
                dentro = "}" if c == "{" else "]"
                continue
            if c.isalnum():
                yield i

    cobertas = sum(1 for _ in letras("".join(alinhados)))
    if cobertas == 0:
        return None
    texto = " ".join(frases)
    posicoes = list(letras(texto))
    if cobertas > len(posicoes):
        return None
    if cobertas == len(posicoes):
        return ""
    corte = posicoes[cobertas - 1] + 1
    while corte < len(texto) and texto[corte].isalnum():  # termina a palavra começada
        corte += 1
    return texto[corte:].lstrip(" ,.;:!?")


class LocutorDialogo:
    """ElevenLabs v4 (diálogo): uma conexão só; cada frase vai assim que o cérebro a termina e o
    áudio toca conforme chega, numa reprodução contínua (sem um pedido nem um toque por frase).

    Mesma interface do `Locutor`. Se o diálogo falhar, o motivo fica em `motivo_reserva` e:
    - antes do 1º áudio: a reserva (HTTP, frase por frase) fala a resposta inteira;
    - depois de começar: a reserva continua do último limite de palavra que o alinhamento cobriu,
      sem repetir o que já foi ouvido, e só depois que o áudio recebido acabar de tocar;
    - sem limite confiável (sem alinhamento): a fala para de modo claro, `cortada` fica True e a
      resposta inteira pode ser repetida a pedido ("repete a resposta que caiu")."""

    def __init__(
        self,
        dialogo,
        transformar: Callable[[str], str],
        voz,
        tocar: Callable[[bytes], None],
        inicio: float,
        abafar=nullcontext,
        juntar: int = 0,
    ) -> None:
        self.dialogo, self.transformar, self.voz = dialogo, transformar, voz
        self.tocar, self.inicio, self.abafar, self.juntar = tocar, inicio, abafar, juntar
        self.tempos = Tempos()
        self.frases: list[str] = []
        self.reserva: Locutor | None = None
        self.motivo_reserva = ""
        self.emocao = ""
        self.turno = None
        self._toque: threading.Thread | None = None
        self.cortada = False  # caiu no meio sem limite confiável: a resposta pode ser repetida
        self.reservas: list[str] = []  # motivo de cada troca para a reserva (diagnóstico)
        try:
            # Abre (ou reaproveita) a conexão já, enquanto o cérebro ainda pensa.
            self.turno = dialogo.novo_turno()
        except ServicoIndisponivel as erro:
            self._para_reserva(erro)
        else:
            self._toque = threading.Thread(target=self._tocar, daemon=True, name="nora-v4-toque")
            self._toque.start()

    def falar(self, frase: str) -> None:
        if (
            self.reserva is None
            and not self.cortada
            and self.turno.erro is not None
            and not self.turno.cancelado
        ):
            self._seguir_na_reserva(self.turno.erro)
        if self.cortada:
            self.frases.append(frase)  # não fala mais; guarda para poder repetir
            return
        if self.reserva is not None:
            self.frases.append(frase)
            self.reserva.falar(frase)
            return
        if not self.frases:
            emocoes = emocoes_em(frase)
            self.emocao = emocoes[0].nome if emocoes else ""
        self.frases.append(frase)
        self.turno.audio.texto = " ".join(self.frases)  # estimativa, se não vier alinhamento
        self.turno.enviar(self.transformar(frase))

    def cancelar(self) -> None:
        """Barge-in: corta o áudio e fecha a conexão (a próxima resposta abre outra, limpa)."""
        if self.turno is not None:
            self.turno.cancelar()

    def terminar(self) -> None:
        if self.turno is not None and self.reserva is None and not self.cortada:
            self.turno.finalizar()
            if self._toque is not None:
                self._toque.join()
            if self.turno.erro is not None and not self.turno.cancelado:
                self._seguir_na_reserva(self.turno.erro)
        if self.reserva is not None:
            self.reserva.terminar()

    @property
    def texto(self) -> str:
        return " ".join(self.frases)

    def _seguir_na_reserva(self, erro: Exception) -> None:
        """O diálogo falhou: decide entre repetir tudo, continuar do limite ou parar."""
        if not self.turno.recebeu_audio:
            self._para_reserva(erro, repetir=True)
            return
        restante = texto_restante(self.frases, [c for c, _, _ in self.turno._caracteres])
        if restante is None:
            self.motivo_reserva = str(erro)
            self.reservas.append(f"{erro} (sem limite confiável: fala encerrada)")
            self.dialogo.usar_reserva(erro)
            self.cortada = True
            self.tempos.erros.append(
                "A voz caiu no meio da resposta e não dá para saber até onde você ouviu. "
                'Diga "repete a resposta que caiu" para ouvir de novo.'
            )
            return
        self._para_reserva(erro, depois_do_que_tocou=True)
        if restante:
            self.reserva.falar(restante)

    def _para_reserva(
        self, erro: Exception, repetir: bool = False, depois_do_que_tocou: bool = False
    ) -> None:
        self.motivo_reserva = str(erro)
        self.reservas.append(str(erro))
        self.dialogo.usar_reserva(erro)
        tocar = self.tocar
        if depois_do_que_tocou and self._toque is not None:
            toque, tocar_agora = self._toque, self.tocar

            def tocar(som, toque=toque, tocar_agora=tocar_agora):  # noqa: F811
                toque.join()  # o áudio do v4 já recebido termina antes; nada se sobrepõe
                tocar_agora(som)

        self.reserva = Locutor(self.voz, tocar, self.inicio, self.abafar, juntar=self.juntar)
        self.reserva.tempos = self.tempos
        if repetir:
            for frase in self.frases:
                self.reserva.falar(frase)

    def _tocar(self) -> None:
        som = self.turno.audio
        som.primeira.wait()
        if not self.turno.recebeu_audio:
            return  # falhou ou foi cancelado antes de qualquer som
        if not self.tempos.comeco_da_voz:
            self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
        with self.abafar(), contexto_fala("", emocao=self.emocao, texto_depois=True):
            try:
                self.tocar(som)
            except Exception as erro:  # um problema no alto-falante não derruba a conversa
                self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")


def abafador(config: Config):
    """O que fazer com os outros programas enquanto a Nora fala, conforme [audio] prioridade."""
    if not config.audio.prioridade:
        return nullcontext
    return lambda: abafar_outros(config.audio.volume_outros)


def responder_falando(conversa: Conversa, *args, **kwargs) -> Tempos:
    """Pede a resposta ao cérebro, mostra o texto e fala frase por frase enquanto ele escreve.
    Enquanto isso, `conversa.falando` fica ligado: o Second Brain e outras tarefas de fundo
    esperam a voz terminar (não disputam tempo com ela)."""
    conversa.falando = True
    try:
        return _responder_falando(conversa, *args, **kwargs)
    finally:
        conversa.falando = False


def _responder_falando(
    conversa: Conversa,
    voz,
    tocar: Callable[[bytes], None],
    texto: str,
    inicio: float,
    transcricao: float,
    escrever: Callable[..., None],
    medir: bool,
) -> Tempos:
    """Pede a resposta ao cérebro, mostra o texto e fala frase por frase enquanto ele escreve.
    Um pedido de troca de voz ("usa a voz do Piper") é atendido aqui, sem passar pelo cérebro."""
    pedido = pedido_de_voz(texto)
    if pedido:
        return trocar_de_voz(conversa, voz, tocar, texto, pedido, escrever)
    # "Repete a resposta que caiu": a última resposta cuja voz caiu sem limite confiável volta
    # a ser falada inteira, sem perguntar de novo ao cérebro.
    cortada = getattr(conversa, "fala_cortada", "")
    repetir = bool(cortada) and pede_retomada(texto)
    if repetir:
        conversa.fala_cortada = ""
    dialogo, transformar = achar_dialogo(voz)
    if dialogo is not None:  # ElevenLabs v4: diálogo em tempo real, uma conexão por conversa
        locutor = LocutorDialogo(
            dialogo, transformar, voz, tocar, inicio, abafador(conversa.config),
            juntar=conversa.config.voz.juntar_curta,
        )  # fmt: skip
    else:
        locutor = Locutor(
            voz, tocar, inicio, abafador(conversa.config), juntar=conversa.config.voz.juntar_curta
        )
    locutor.tempos.transcricao = transcricao
    separador = SeparadorDeFrases()
    escrever(f"{conversa.config.assistente.nome}: ", fim="")

    def falar(frases: list[str]) -> None:
        for frase in frases:
            if not locutor.tempos.primeira_frase:
                locutor.tempos.primeira_frase = time.perf_counter() - inicio
            locutor.falar(frase)

    tela = FiltroDeTela()  # a tela não mostra as etiquetas de emoção; a voz recebe tudo
    try:
        for pedaco in [cortada] if repetir else conversa.perguntar(texto):
            escrever(tela.alimentar(pedaco), fim="")
            falar(separador.alimentar(pedaco))
        escrever(tela.finalizar(), fim="")
        falar(separador.finalizar())
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    except KeyboardInterrupt:
        escrever("\n(interrompido)")
        locutor.cancelar()
        audio.parar_audio()
    escrever()
    locutor.terminar()
    if getattr(locutor, "cortada", False):
        conversa.fala_cortada = locutor.texto

    tempos = locutor.tempos
    medida = _diagnosticar(conversa, voz, locutor, dialogo)
    if dialogo is not None and dialogo.aviso:
        escrever(f"[voz reserva] {dialogo.aviso}")
        dialogo.aviso = ""
    _observar_voz(conversa, voz, tempos, bool(getattr(voz, "aviso", "")))
    for erro in dict.fromkeys(tempos.erros):
        escrever(f"[erro na voz] {erro}")
    for aviso in audio.avisos_de_saida():
        escrever(f"[som] {aviso}")
    if getattr(voz, "aviso", ""):
        escrever(f"[voz reserva] {voz.aviso}")
        voz.aviso = ""
    for aviso in conversa.avisos_do_cerebro():
        escrever(f"[cérebro] {aviso}")
    for aviso in conversa.avisos_pendentes():
        escrever(f"[memória] {aviso}")
    if medir:
        escrever(
            f"  [{conversa.origem}: transcrição {tempos.transcricao:.2f} s, "
            f"primeira frase {tempos.primeira_frase:.2f} s, "
            f"começou a falar em {tempos.comeco_da_voz:.2f} s, "
            f"lembrou {len(conversa.lembrancas)} fatos, {len(conversa.trechos)} trechos "
            f"e {len(conversa.trechos_de_notas)} notas]"
        )
        if medida is not None:
            escrever(f"  [voz: {resumo_da_voz(medida)}]")
    return tempos


def _nucleo(voz):
    """O motor de voz de dentro das camadas (pronúncias, troca, reserva, realce)."""
    for _ in range(10):
        proxima = getattr(voz, "principal", None) or getattr(voz, "voz", None)
        if proxima is None or isinstance(voz, VozElevenLabs):
            return voz
        voz = proxima
    return voz


def _diagnosticar(conversa: Conversa, voz, locutor, dialogo):
    """Grava o diagnóstico da voz desta resposta (ElevenLabs): modelo efetivo, continuidade e
    tempos. Sem texto da conversa. Devolve a medida (ou None, para as outras vozes)."""
    from nora import diagnostico_voz as diag

    config = conversa.config.voz.elevenlabs
    try:
        if dialogo is not None:
            turno = getattr(locutor, "turno", None)
            reserva = getattr(locutor, "reserva", None)
            if reserva is not None or turno is None:
                medida = diag.MedidaDaVoz(
                    modelo=dialogo.reserva.modelo,
                    via="http (reserva)",
                    continuidade=diag.ERRO,
                    erro=getattr(dialogo.sessao(), "ultimo_erro", "") or "diálogo indisponível",
                )
            else:
                continuidade = diag.ATIVA if dialogo.continuidade else diag.DESATIVADA
                medida = diag.medir_turno(turno, dialogo.modelo, continuidade)
        else:
            nucleo = _nucleo(voz)
            if not isinstance(nucleo, VozElevenLabs):
                return None
            if not config.continuidade:
                continuidade = diag.DESATIVADA
            else:
                continuidade = diag.ATIVA if nucleo.continuidade else diag.NAO_SUPORTADA
            medida = diag.MedidaDaVoz(modelo=nucleo.modelo, via="http", continuidade=continuidade)
        diag.registrar(conversa.config.pasta_dados, medida)
        return medida
    except Exception:
        return None


def resumo_da_voz(medida) -> str:
    from nora.diagnostico_voz import resumo

    return resumo(medida)


def _observar_voz(conversa: Conversa, voz, tempos: Tempos, usou_reserva: bool) -> None:
    """Tempos do ouvido e da voz e falhas da voz, para a auto-melhoria (sem texto)."""
    observador = getattr(conversa, "observador", None)
    motor = getattr(voz, "motor", "") or conversa.config.voz.motor
    if observador is None:
        return
    interacao = conversa.ultima_interacao
    if tempos.transcricao:
        observador.registrar(
            "stt",
            "transcricao",
            conversa.config.ouvido.motor,
            interacao,
            int(tempos.transcricao * 1000),
        )
    if tempos.comeco_da_voz and tempos.primeira_frase:
        espera = max(0.0, tempos.comeco_da_voz - tempos.primeira_frase)
        observador.registrar("tts", "voz", motor, interacao, int(espera * 1000))
    for _ in dict.fromkeys(tempos.erros):
        observador.registrar("tts", "erro_provedor", motor, interacao, status="sem voz")
    if usou_reserva:
        observador.registrar("tts", "erro_provedor", motor, interacao, status="reserva usada")


def trocar_de_voz(conversa: Conversa, voz, tocar, texto, pedido, escrever) -> Tempos:
    resposta, wav = atender_pedido(voz, pedido, conversa.config.voz.motor)
    emitir("voz_ativa", motor=getattr(voz, "motor", "") or conversa.config.voz.motor)
    escrever(f"{conversa.config.assistente.nome}: {resposta}")
    conversa.historico.registrar("usuario", texto)
    conversa.historico.registrar("assistente", resposta, modelo="comando de voz")
    tempos = Tempos()
    try:
        with contexto_fala(resposta):
            tocar(wav if wav is not None else voz.sintetizar(resposta))
    except Exception as erro:  # a conversa segue mesmo sem voz
        tempos.erros.append(str(erro))
        escrever(f"[erro na voz] {erro}")
    return tempos


def conversar_por_voz(
    config: Config,
    entrada: Callable[[str], str] = input,
    saida: TextIO | None = None,
    medir: bool = False,
    cerebro: CerebroLocal | None = None,
    ouvido: OuvidoWhisper | None = None,
    voz: VozHTTP | VozElevenLabs | VozComReserva | None = None,
    gravar: Callable[[Callable[[str], str]], bytes] | None = None,
    tocar: Callable[[bytes], None] | None = None,
    so_teclado: bool = False,
) -> int:
    """Conversa com resposta falada. Por padrão, Enter grava a fala e texto digitado vale como
    pergunta; com `so_teclado`, não usa microfone: a pessoa digita e a Nora responde falando."""
    saida = saida or sys.stdout
    conversa = nova_conversa(config, cerebro)
    ouvido = ouvido or OuvidoWhisper(config)
    voz = com_pronuncias_aprendidas(voz or VozTrocavel(config), conversa.memoria)
    microfone = audio.dispositivo(config.audio.microfone)
    gravar = gravar or (lambda entrada: audio.gravar_ate_enter(entrada, microfone))
    tocar = tocar or audio.tocador(config.audio)
    nome = config.assistente.nome

    def escrever(texto: str = "", fim: str = "\n") -> None:
        saida.write(texto + fim)
        saida.flush()

    escrever(f"Carregando {config.modelo_local.modelo} na memória...", fim="")
    try:
        escrever(f" pronto em {conversa.cerebro.aquecer():.1f} s.")
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    if so_teclado:
        escrever(f"Conversa com {nome}: digite e ela responde falando. 'sair' encerra.")
    else:
        escrever(
            f"Conversa por voz com {nome}. Aperte Enter, fale e aperte Enter de novo. "
            "Também dá para digitar. 'sair' encerra."
        )
    for aviso in conversa.avisos_pendentes():
        escrever(f"[memória] {aviso}")
    agendador = iniciar_melhorias(conversa, escrever)

    while True:
        try:
            comando = ler_entrada(
                entrada,
                "\nVocê: " if so_teclado else "\n[Enter para falar] ",
                agendador,
                lambda p: escrever(p, fim=""),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            escrever()
            break
        if comando.lower() in COMANDOS_SAIR:
            break
        if comando == "/limpar":
            conversa.limpar()
            escrever("(conversa reiniciada)")
            continue
        if so_teclado and not comando:
            continue

        try:
            if comando:
                texto, inicio, transcricao = comando, time.perf_counter(), 0.0
            else:
                wav = gravar(entrada)
                inicio = time.perf_counter()
                if audio.duracao_wav(wav) < 0.3:
                    escrever("(não ouvi nada)")
                    continue
                texto = ouvido.transcrever(wav, dica=dica_do_ouvido(conversa.config))
                transcricao = time.perf_counter() - inicio
                if not texto:
                    escrever(
                        "(não ouvi fala, só som ou silêncio; tente falar mais perto do microfone)"
                    )
                    continue
                escrever(f"Você: {texto}")
        except (ServicoIndisponivel, RuntimeError) as erro:
            escrever(f"[erro] {erro}")
            continue
        except KeyboardInterrupt:
            escrever("\n(cancelado)")
            continue

        responder_falando(conversa, voz, tocar, texto, inicio, transcricao, escrever, medir)
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    if agendador is not None:
        agendador.parar()
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
