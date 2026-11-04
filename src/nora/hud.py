"""Ponte local opcional: eventos SSE de apresentação, sem outro mic/cérebro/TTS.

O núcleo nunca espera clientes. As filas são limitadas e clientes lentos recebem o estado
atual ao reconectar. Somente campos públicos enumerados são aceitos; texto/notas exigem
consentimento da sessão e não são persistidos. O servidor usa apenas a biblioteca padrão.
"""

from __future__ import annotations

import hmac
import json
import math
import mimetypes
import queue
import secrets
import threading
import time
from array import array
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit

CONTRATO = json.loads(Path(__file__).with_name("hud_contrato.json").read_text(encoding="utf-8"))
VERSAO = CONTRATO["versao"]
LIMITE_EVENTO = CONTRATO["limite_evento"]
ESTADOS = frozenset(CONTRATO["estados"])
CAMPOS = {tipo: set(campos) for tipo, campos in CONTRATO["campos"].items()}


class Evento(TypedDict):
    versao: int
    sequencia: int
    tipo: str
    dados: dict
    instante: str


class PonteHUD:
    """Estado efêmero de apresentação. Publicar é best-effort e nunca faz I/O."""

    def __init__(self, nome: str = "Nora", capacidade: int = 64) -> None:
        self._trava = threading.RLock()
        self._filas: set[queue.Queue] = set()
        self.capacidade = max(1, min(capacidade, 256))
        self._ultimo_nivel: dict[str, float] = {}
        self.conversa = None
        self._reproduzindo = False
        self.estado = {
            "versao": VERSAO,
            "sequencia": 0,
            "estado": "desconectado",
            "conectado": False,
            "nome": nome[:200],
            "modelo": "",
            "origem": "",
            "voz": "",
            "emocao": "neutra",
            "nivel_audio": 0.0,
            "texto": "",
            "notas": [],
            "relatorio": None,
            "privacidade": True,
            "latencia_ms": None,
        }

    def snapshot(self) -> dict:
        with self._trava:
            return json.loads(json.dumps(self.estado))

    def assinar(self) -> queue.Queue:
        with self._trava:
            if len(self._filas) >= 8:
                raise ValueError("Limite de clientes HUD alcançado")
            fila: queue.Queue = queue.Queue(maxsize=self.capacidade)
            self._filas.add(fila)
            return fila

    def remover(self, fila: queue.Queue) -> None:
        with self._trava:
            self._filas.discard(fila)

    def publicar(self, tipo: str, **dados) -> bool:
        if not self._trava.acquire(blocking=False):
            return False
        try:
            if tipo not in CAMPOS or not dados.keys() <= CAMPOS[tipo]:
                return False
            if tipo in ("texto_visivel", "notas") and self.estado["privacidade"]:
                return False
            try:
                if (
                    len(json.dumps(dados, ensure_ascii=False, allow_nan=False).encode("utf-8"))
                    > LIMITE_EVENTO - 1024
                ):
                    return False
            except (ValueError, TypeError):
                return False
            if tipo == "nivel_audio":
                nivel, fonte = dados.get("nivel"), dados.get("fonte")
                if (
                    isinstance(nivel, bool)
                    or not isinstance(nivel, (int, float))
                    or not math.isfinite(nivel)
                    or not 0 <= nivel <= 1
                    or fonte not in ("microfone", "voz")
                ):
                    return False
                agora = time.monotonic()
                if agora - self._ultimo_nivel.get(fonte, -1) < 0.05:
                    return False
                self._ultimo_nivel[fonte] = agora
                self.estado["nivel_audio"] = nivel
            elif tipo in ESTADOS:
                if self._reproduzindo and tipo not in ("falando", "desconectado", "erro"):
                    return False
                self.estado["estado"] = tipo
                if tipo == "desconectado":
                    self.estado.update(
                        conectado=False, texto="", notas=[], nivel_audio=0.0, privacidade=True
                    )
                    self.conversa = None
            elif tipo == "notas":
                notas = dados.get("notas")
                if not isinstance(notas, list) or len(notas) > 12:
                    return False
                if any(
                    not isinstance(n, dict)
                    or set(n) != {"titulo", "caminho"}
                    or not all(isinstance(v, str) for v in n.values())
                    or len(n["titulo"]) > 200
                    or len(n["caminho"]) > 500
                    for n in notas
                ):
                    return False
                self.estado["notas"] = notas
            elif tipo == "latencia":
                if type(dados.get("ms")) is not int or not 0 < dados["ms"] < 3_600_000:
                    return False
                self.estado["latencia_ms"] = dados["ms"]
            elif tipo == "privacidade":
                if type(dados.get("privacidade")) is not bool:
                    return False
                self.estado["privacidade"] = dados["privacidade"]
            elif tipo == "texto_visivel":
                texto = dados.get("texto")
                if not isinstance(texto, str) or not isinstance(dados.get("acumular", False), bool):
                    return False
                self.estado["texto"] = (
                    self.estado["texto"] + texto if dados.get("acumular") else texto
                )[-6000:]
                # Um cliente lento pode perder eventos; o próximo texto recupera o conteúdo.
                dados = {"texto": self.estado["texto"], "acumular": False}
            else:
                chave = {
                    "emocao": ("emocao", "nome"),
                    "modelo_ativo": ("modelo", "modelo"),
                    "origem_resposta": ("origem", "origem"),
                    "voz_ativa": ("voz", "motor"),
                }.get(tipo)
                if chave:
                    valor = dados.get(chave[1])
                    if not isinstance(valor, str) or len(valor) > 200:
                        return False
                    self.estado[chave[0]] = valor
                if tipo == "relatorio_pronto":
                    self.estado["relatorio"] = dados
            self.estado["sequencia"] += 1
            evento: Evento = {
                "versao": VERSAO,
                "sequencia": self.estado["sequencia"],
                "tipo": tipo,
                "dados": dados,
                "instante": datetime.now(UTC).isoformat(),
            }
            for fila in tuple(self._filas):
                if fila.full():
                    try:
                        fila.get_nowait()
                    except queue.Empty:
                        pass
                try:
                    fila.put_nowait(evento)
                except queue.Full:
                    pass
            return True
        finally:
            self._trava.release()

    def anexar(self, conversa) -> None:
        self.privacidade(False)
        self.conversa = conversa
        with self._trava:
            self.estado.update(conectado=True, texto="", notas=[], privacidade=True)
            self.estado["nome"] = conversa.config.assistente.nome[:200]
        self.publicar("modelo_ativo", modelo=conversa.config.modelo_local.modelo)
        self.publicar("voz_ativa", motor=conversa.config.voz.motor)
        self.publicar("ociosa")
        m = getattr(conversa, "melhorias", None)
        if m is not None:
            pendentes = m.nao_mostrados()
            if pendentes:
                data, _, quantas = pendentes[-1]
                self.publicar("relatorio_pronto", data=data, propostas=quantas)

    def privacidade(self, visivel: bool) -> None:
        with self._trava:
            self.estado.update(privacidade=not visivel, texto="", notas=[])
            # Nada pessoal já enfileirado pode chegar após a confirmação de ocultar.
            for fila in self._filas:
                with fila.mutex:
                    fila.queue.clear()
        self.publicar("privacidade", privacidade=not visivel)

    def notas(self) -> list[dict]:
        conversa = self.conversa
        if self.estado["privacidade"] or conversa is None or not conversa.config.notas.pasta:
            return []
        raiz = Path(conversa.config.notas.pasta).resolve()
        notas = []
        for trecho in list(conversa.trechos_de_notas)[:12]:
            caminho = (raiz / trecho.caminho).resolve()
            if caminho.is_relative_to(raiz):
                notas.append({"titulo": trecho.titulo[:200], "caminho": trecho.caminho[:500]})
        return notas

    def propostas(self) -> list[dict]:
        m = getattr(self.conversa, "melhorias", None)
        if m is None:
            return []
        return [
            {"id": p.id, "titulo": p.titulo, "status": p.status}
            for p in m.propostas(("proposta",))[:50]
        ]

    def decidir(self, dados: dict) -> dict:
        if (
            dados.get("confirmar") is not True
            or dados.get("acao") not in ("aprovar", "recusar", "adiar")
            or type(dados.get("id")) is not int
        ):
            raise ValueError("Decisão exige número, ação válida e confirmação explícita")
        m = getattr(self.conversa, "melhorias", None)
        if m is None:
            raise ValueError("Auto-melhoria indisponível")
        feita = m.decidir(dados["id"], dados["acao"], "usuário (HUD local)")
        if feita is None:
            raise ValueError("Proposta já decidida ou inexistente")
        self.publicar("proposta_melhoria", id=feita.id, titulo=feita.titulo, status=feita.status)
        return {"id": feita.id, "status": feita.status}


_ponte: PonteHUD | None = None


def emitir(tipo: str, **dados) -> None:
    """Uma HUD indisponível ou um observador defeituoso nunca interrompe a Nora."""
    if _ponte is not None:
        try:
            _ponte.publicar(tipo, **dados)
        except Exception:
            pass


def anexar(conversa) -> None:
    if _ponte is not None:
        try:
            _ponte.anexar(conversa)
        except Exception:
            pass


def atualizar_notas() -> None:
    if _ponte is not None:
        try:
            emitir("notas", notas=_ponte.notas())
        except Exception:
            pass


def reproducao(ativa: bool) -> None:
    if _ponte is None:
        return
    try:
        _ponte._reproduzindo = ativa
        if ativa:
            emitir("falando")
        else:
            conversa = _ponte.conversa
            estado = (
                "modo_jogo"
                if getattr(getattr(conversa, "cerebro", None), "jogo", False)
                else ("pensando" if getattr(conversa, "ocupada", False) else "ouvindo")
            )
            # Leitura simples: o callback de áudio nunca espera o lock de uma apresentação.
            if _ponte.estado["estado"] != "erro":
                emitir(estado)
            emitir("nivel_audio", nivel=0.0, fonte="voz")
    except Exception:
        pass  # falha de visualização nunca chega ao callback de áudio


def nivel_pcm(amostras: bytes, fonte: str) -> None:
    if _ponte is None or not amostras:
        return
    # Amostra no máximo 256 pontos; não envia nem guarda áudio bruto.
    valores = array("h")
    valores.frombytes(amostras[: len(amostras) // 2 * 2])
    passo = max(1, len(valores) // 256)
    pontos = valores[::passo]
    if pontos:
        emitir(
            "nivel_audio",
            nivel=min(1.0, math.sqrt(sum(v * v for v in pontos) / len(pontos)) / 32768),
            fonte=fonte,
        )


class ServidorHUD:
    def __init__(self, ponte: PonteHUD, porta: int = 8765, pasta: Path | None = None) -> None:
        self.ponte, self.token = ponte, secrets.token_urlsafe(32)
        self._pedidos: list[float] = []
        self._trava_pedidos = threading.Lock()
        self.pasta = (pasta or Path(__file__).resolve().parents[2] / "hud" / "dist").resolve()
        dono = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *args) -> None:
                pass  # URLs/corpos nunca são registrados

            def autorizado(self, mutacao=False) -> bool:
                permitido = f"127.0.0.1:{dono.porta}"
                host = self.headers.get("Host", "")
                origem = self.headers.get("Origin")
                if (
                    host != permitido
                    or origem not in (None, f"http://{permitido}")
                    or self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site")
                ):
                    return False
                if mutacao:
                    return hmac.compare_digest(self.headers.get("X-Nora-Token", ""), dono.token)
                return True

            def responder(self, status: int, dados: dict | bytes, tipo="application/json") -> None:
                corpo = (
                    dados
                    if isinstance(dados, bytes)
                    else json.dumps(dados, ensure_ascii=False, allow_nan=False).encode("utf-8")
                )
                self.send_response(status)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                    "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
                    "frame-ancestors 'none'",
                )
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self) -> None:
                if not self.autorizado():
                    self.responder(403, {"erro": "Origem local obrigatória"})
                    return
                rota = urlsplit(self.path).path
                try:
                    if rota == "/api/sessao":
                        self.responder(200, {"token": dono.token})
                    elif rota == "/api/estado":
                        self.responder(200, ponte.snapshot())
                    elif rota == "/api/propostas":
                        self.responder(200, {"propostas": ponte.propostas()})
                    elif rota == "/api/notas":
                        self.responder(200, {"notas": ponte.notas()})
                    elif rota == "/api/relatorio":
                        self.responder(200, {"relatorio": ponte.snapshot()["relatorio"]})
                    elif rota == "/api/eventos":
                        self.eventos()
                    elif rota.startswith("/api/"):
                        self.responder(404, {"erro": "Rota inexistente"})
                    else:
                        caminho = (
                            dono.pasta / ("index.html" if rota == "/" else rota.lstrip("/"))
                        ).resolve()
                        if not caminho.is_relative_to(dono.pasta) or not caminho.is_file():
                            self.responder(
                                404, {"erro": "Compile a HUD: cd hud && npm ci && npm run build"}
                            )
                            return
                        self.responder(
                            200,
                            caminho.read_bytes(),
                            {
                                ".js": "text/javascript",
                                ".css": "text/css",
                                ".html": "text/html",
                                ".json": "application/json",
                                ".svg": "image/svg+xml",
                            }.get(caminho.suffix.lower())
                            or mimetypes.guess_type(caminho)[0]
                            or "application/octet-stream",
                        )
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass
                except (OSError, ValueError):
                    self.responder(503, {"erro": "HUD temporariamente indisponível"})

            def eventos(self) -> None:
                try:
                    fila = ponte.assinar()
                except ValueError:
                    self.responder(429, {"erro": "Muitos clientes HUD"})
                    return
                try:
                    self.connection.settimeout(5)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()
                    estado = ponte.snapshot()
                    evento = {
                        "versao": VERSAO,
                        "sequencia": estado["sequencia"],
                        "tipo": "conectado",
                        "dados": estado,
                        "instante": datetime.now(UTC).isoformat(),
                    }
                    self.enviar_evento(evento)
                    while not dono.parado.is_set():
                        try:
                            evento = fila.get(timeout=1)
                            if evento["sequencia"] > estado["sequencia"]:
                                self.enviar_evento(evento)
                        except queue.Empty:
                            self.wfile.write(b": pulso\n\n")
                            self.wfile.flush()
                finally:
                    ponte.remover(fila)

            def enviar_evento(self, evento: dict) -> None:
                if evento["tipo"] in ("texto_visivel", "notas") and ponte.snapshot()["privacidade"]:
                    return
                self.wfile.write(
                    (
                        f"id: {evento['sequencia']}\ndata: "
                        + json.dumps(evento, ensure_ascii=False, allow_nan=False)
                        + "\n\n"
                    ).encode()
                )
                self.wfile.flush()

            def do_POST(self) -> None:
                if not self.autorizado(mutacao=True):
                    self.responder(403, {"erro": "Token e origem local obrigatórios"})
                    self.close_connection = True
                    return
                with dono._trava_pedidos:
                    agora = time.monotonic()
                    dono._pedidos = [p for p in dono._pedidos if agora - p < 1]
                    if len(dono._pedidos) >= 20:
                        self.responder(429, {"erro": "Muitos pedidos"})
                        self.close_connection = True
                        return
                    dono._pedidos.append(agora)
                try:
                    tamanho = int(self.headers.get("Content-Length", "0"))
                    if not 0 < tamanho <= 2048:
                        raise ValueError("Corpo inválido")
                    self.connection.settimeout(2)
                    dados = json.loads(self.rfile.read(tamanho))
                    if not isinstance(dados, dict):
                        raise ValueError("Corpo inválido")
                    if self.path == "/api/decisao":
                        self.responder(200, ponte.decidir(dados))
                    elif self.path == "/api/privacidade" and type(dados.get("visivel")) is bool:
                        ponte.privacidade(dados["visivel"])
                        self.responder(200, ponte.snapshot())
                    else:
                        self.responder(404, {"erro": "Rota inexistente"})
                except (ValueError, TypeError, OSError):
                    self.responder(400, {"erro": "Pedido inválido ou decisão indisponível"})
                    self.close_connection = True

        class HTTP(ThreadingHTTPServer):
            def __init__(self):
                self.vagas = threading.BoundedSemaphore(32)
                super().__init__(("127.0.0.1", porta), Handler)

            def process_request(self, request, client_address):
                if not self.vagas.acquire(blocking=False):
                    request.close()
                    return
                try:
                    super().process_request(request, client_address)
                except Exception:
                    self.vagas.release()
                    raise

            def process_request_thread(self, request, client_address):
                try:
                    super().process_request_thread(request, client_address)
                finally:
                    self.vagas.release()

        self.http = HTTP()
        self.http.daemon_threads = True
        self.porta = self.http.server_port
        self.parado = threading.Event()
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)

    def iniciar(self) -> ServidorHUD:
        self.thread.start()
        return self

    def parar(self) -> None:
        self.parado.set()
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.porta}"


def executar(config, ouvir: bool = False, porta: int = 8765, **opcoes) -> int:
    """Serve a interface; --hud usa exatamente o loop mãos livres existente."""
    global _ponte
    ponte = PonteHUD(config.assistente.nome)
    try:
        servidor = ServidorHUD(ponte, porta).iniciar()
    except (OSError, OverflowError, ValueError):
        print("[HUD] Porta indisponível; seguindo sem a interface visual.")
        if ouvir:
            from nora.maos_livres import conversar_maos_livres

            return conversar_maos_livres(config, **opcoes)
        return 1
    _ponte = ponte
    print(f"HUD local: {servidor.url} (Ctrl+C encerra)")
    try:
        if ouvir:
            from nora.maos_livres import conversar_maos_livres

            return conversar_maos_livres(config, **opcoes)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        _ponte = None
        servidor.parar()
