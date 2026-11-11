"""Loads and validates Nora's config.

Order: config/nora.toml (default) -> config/local.toml (personal, outside Git)
-> environment variables and .env (secrets).
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    """Missing or invalid config."""


@dataclass(frozen=True)
class Assistente:
    nome: str
    palavra_de_ativacao: str
    idioma: str
    pronuncia: str


@dataclass(frozen=True)
class Persona:
    descricao: str
    humor: float
    formalidade: float
    respostas_curtas: bool


@dataclass(frozen=True)
class Emocao:
    ativa: bool = True
    intensidade: float = 0.5
    reacoes_por_resposta: int = 1


@dataclass(frozen=True)
class Ouvido:
    motor: str
    url: str
    idioma: str


@dataclass(frozen=True)
class VozKokoro:
    url: str
    voz: str
    velocidade: float


@dataclass(frozen=True)
class VozPiper:
    url: str
    voz: str
    velocidade: float = 1.0
    variacao: float = 0.0  # Piper's noise_scale; 0 = the model's default
    variacao_ritmo: float = 0.0  # Piper's noise_w_scale; 0 = the model's default


@dataclass(frozen=True)
class VozElevenLabs:
    voz_id: str
    modelo: str


@dataclass(frozen=True)
class VozComfyUI:
    url: str
    fluxo: Path
    espera_s: float
    campo: str


REALCES_DE_PERGUNTA = ("", "duplo", "invertido", "exclamado")
MOTORES_DE_VOZ = ("kokoro", "piper", "elevenlabs", "comfyui")


@dataclass(frozen=True)
class Voz:
    motor: str
    reserva: str
    realce_pergunta: str
    pronuncias: dict[str, str]
    kokoro: VozKokoro
    piper: VozPiper
    elevenlabs: VozElevenLabs
    comfyui: VozComfyUI


@dataclass(frozen=True)
class Escuta:
    limiar: float
    silencio_ms: int
    janela_s: float
    pausar_microfone: bool


@dataclass(frozen=True)
class Memoria:
    ativa: bool
    modelo_embeddings: str
    curadoria: bool
    fatos_por_pergunta: int
    similaridade_minima: float
    trocas_por_pergunta: int
    agenda_dias: int = 7


@dataclass(frozen=True)
class AutoMelhoria:
    ativa: bool = True
    hora_relatorio: str = "20:00"  # HH:MM, local time of the daily report
    min_ocorrencias: int = 3  # fewer than this in a day does not become a proposal
    latencia_resposta_ms: int = 2500  # until the first chunk of the answer
    latencia_ouvido_ms: int = 1500  # transcription
    latencia_voz_ms: int = 2000  # from the first ready sentence until speech starts
    dias_de_eventos: int = 30  # older events are deleted when the day closes
    notificar: bool = True  # Windows notification when the report is ready
    # abrir: opens the .md; terminal: shows the full text in the conversation
    apresentar: str = "abrir"


@dataclass(frozen=True)
class Notas:
    pasta: Path | None = None  # the Obsidian vault; None = no notes
    trechos_por_pergunta: int = 3
    similaridade_minima: float = 0.5
    ignorar: tuple[str, ...] = ()
    atualizar_ao_abrir: bool = True


@dataclass(frozen=True)
class Audio:
    microfone: str
    alto_falante: str
    prioridade: bool
    volume_outros: float
    silencio_inicial_ms: int = 0


@dataclass(frozen=True)
class ModeloLocal:
    provedor: str
    modelo: str
    keep_alive: str
    temperatura: float
    pensar: bool


@dataclass(frozen=True)
class ModeloNuvem:
    provedor: str
    rapido: str
    pesado: str
    esforco_rapido: str = "low"
    esforco_pesado: str = "medium"


@dataclass(frozen=True)
class ModeloOpenAI:
    rapido: str = "gpt-5.5"
    pesado: str = "gpt-5.5"
    esforco_rapido: str = "low"
    esforco_pesado: str = "medium"


MODOS_DO_ROTEADOR = ("automatico", "local", "nuvem")
NUVENS = ("openai", "anthropic")
ESFORCOS = ("low", "medium", "high", "xhigh", "max")
ESFORCOS_OPENAI = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class Roteador:
    modo: str = "automatico"
    escalar: bool = True
    triagem: bool = True
    complexas: str = "openai"  # who answers the complex ones; the other cloud is the fallback


@dataclass(frozen=True)
class Config:
    assistente: Assistente
    nome_usuario: str
    persona: Persona
    ouvido: Ouvido
    voz: Voz
    audio: Audio
    escuta: Escuta
    memoria: Memoria
    emocao: Emocao
    modelo_local: ModeloLocal
    modelo_nuvem: ModeloNuvem
    modelo_openai: ModeloOpenAI
    roteador: Roteador
    pasta_dados: Path
    ollama_host: str
    tem_chave_anthropic: bool
    arquivos: tuple[Path, ...]
    chave_elevenlabs: str = field(default="", repr=False)
    chave_anthropic: str = field(default="", repr=False)
    chave_openai: str = field(default="", repr=False)
    notas: Notas = field(default_factory=Notas)
    auto_melhoria: AutoMelhoria = field(default_factory=AutoMelhoria)


def _apresentar(valor: str) -> str:
    valor = valor.strip().lower()
    if valor not in ("abrir", "terminal"):
        raise ConfigError(
            f'[auto_melhoria] apresentar deve ser "abrir" ou "terminal", veio {valor!r}.'
        )
    return valor


def _auto_melhoria(dados: dict[str, Any]) -> AutoMelhoria:
    secao = "auto_melhoria"
    hora = _campo(dados, secao, "hora_relatorio", str).strip()
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
        raise ConfigError(
            f'[{secao}] hora_relatorio deve ser "HH:MM" (ex.: "20:00"), veio {hora!r}.'
        )
    inteiros = {}
    for chave in (
        "min_ocorrencias",
        "latencia_resposta_ms",
        "latencia_ouvido_ms",
        "latencia_voz_ms",
        "dias_de_eventos",
    ):
        inteiros[chave] = _campo(dados, secao, chave, int)
        if inteiros[chave] < 1:
            raise ConfigError(f"[{secao}] {chave} deve ser 1 ou mais.")
    return AutoMelhoria(
        ativa=_campo(dados, secao, "ativa", bool),
        hora_relatorio=hora,
        notificar=_campo(dados, secao, "notificar", bool),
        apresentar=_apresentar(_campo(dados, secao, "apresentar", str)),
        **inteiros,
    )


def _notas(dados: dict[str, Any], raiz: Path) -> Notas:
    texto = _campo(dados, "notas", "pasta", str).strip()
    pasta = None
    if texto:
        pasta = Path(texto).expanduser()
        if not pasta.is_absolute():
            pasta = raiz / pasta
    ignorar = _campo(dados, "notas", "ignorar", list)
    if not all(isinstance(item, str) for item in ignorar):
        raise ConfigError('[notas] ignorar deve ser uma lista de pastas, como ["Diário"].')
    trechos = _campo(dados, "notas", "trechos_por_pergunta", int)
    if trechos < 0:
        raise ConfigError("[notas] trechos_por_pergunta não pode ser negativo.")
    return Notas(
        pasta=pasta,
        trechos_por_pergunta=trechos,
        similaridade_minima=_entre_0_e_1(
            "notas", "similaridade_minima", _campo(dados, "notas", "similaridade_minima", float)
        ),
        ignorar=tuple(ignorar),
        atualizar_ao_abrir=_campo(dados, "notas", "atualizar_ao_abrir", bool),
    )


def mesclar(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Merges two config dictionaries; the keys from `extra` win."""
    resultado = dict(base)
    for chave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(resultado.get(chave), dict):
            resultado[chave] = mesclar(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado


def ler_env(caminho: Path) -> dict[str, str]:
    """Reads a simple .env file (CHAVE=valor, # comments)."""
    if not caminho.is_file():
        return {}
    valores = {}
    # utf-8-sig: Notepad may save with a BOM, which would stick to the first key's name
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip("\"'")
    return valores


def _ler_toml(caminho: Path) -> dict[str, Any]:
    try:
        with caminho.open("rb") as arquivo:
            return tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise ConfigError(f"Erro de sintaxe em {caminho}: {erro}") from erro


def _campo(dados: dict[str, Any], secao: str, chave: str, tipo: type) -> Any:
    atual: Any = dados
    for parte in secao.split("."):
        atual = atual.get(parte) if isinstance(atual, dict) else None
    if not isinstance(atual, dict) or chave not in atual:
        raise ConfigError(f"Falta a chave '{chave}' na seção [{secao}].")
    valor = atual[chave]
    if tipo is float and isinstance(valor, int) and not isinstance(valor, bool):
        valor = float(valor)
    if not isinstance(valor, tipo) or (tipo is float and isinstance(valor, bool)):
        raise ConfigError(f"[{secao}] {chave} deve ser {tipo.__name__}, veio {valor!r}.")
    return valor


def _velocidade(dados: dict[str, Any], secao: str) -> float:
    velocidade = _campo(dados, secao, "velocidade", float)
    if not 0.5 <= velocidade <= 2.0:
        raise ConfigError(f"[{secao}] velocidade deve ficar entre 0.5 e 2.0, veio {velocidade}.")
    return velocidade


def _esforco(
    dados: dict[str, Any], chave: str, secao: str = "modelos.nuvem", validos=ESFORCOS
) -> str:
    valor = _campo(dados, secao, chave, str)
    if valor not in validos:
        raise ConfigError(f"[{secao}] {chave} deve ser um de {validos}, veio {valor!r}.")
    return valor


def _roteador(dados: dict[str, Any]) -> Roteador:
    modo = _campo(dados, "roteador", "modo", str)
    if modo not in MODOS_DO_ROTEADOR:
        raise ConfigError(f"[roteador] modo deve ser um de {MODOS_DO_ROTEADOR}, veio {modo!r}.")
    complexas = _campo(dados, "roteador", "complexas", str)
    if complexas not in NUVENS:
        raise ConfigError(f"[roteador] complexas deve ser um de {NUVENS}, veio {complexas!r}.")
    return Roteador(
        modo=modo,
        escalar=_campo(dados, "roteador", "escalar", bool),
        triagem=_campo(dados, "roteador", "triagem", bool),
        complexas=complexas,
    )


def _variacao(dados: dict[str, Any], chave: str) -> float:
    valor = _campo(dados, "voz.piper", chave, float)
    if not 0.0 <= valor <= 2.0:
        raise ConfigError(f"[voz.piper] {chave} deve ficar entre 0 e 2 (0 = padrão), veio {valor}.")
    return valor


def _silencio(dados: dict[str, Any]) -> int:
    ms = _campo(dados, "audio", "silencio_inicial_ms", int)
    if not 0 <= ms <= 2000:
        raise ConfigError(f"[audio] silencio_inicial_ms deve ficar entre 0 e 2000, veio {ms}.")
    return ms


def _entre_0_e_1(secao: str, chave: str, valor: float) -> float:
    if not 0.0 <= valor <= 1.0:
        raise ConfigError(f"[{secao}] {chave} deve ficar entre 0.0 e 1.0, veio {valor}.")
    return valor


def _temperatura(valor: float) -> float:
    if not 0.0 <= valor <= 2.0:
        raise ConfigError(f"[modelos.local] temperatura deve ficar entre 0.0 e 2.0, veio {valor}.")
    return valor


def _ler_voz(dados: dict[str, Any], raiz: Path) -> Voz:
    motor = _campo(dados, "voz", "motor", str)
    if motor not in MOTORES_DE_VOZ:
        raise ConfigError(
            f"[voz] motor deve ser um de {', '.join(MOTORES_DE_VOZ)}; veio {motor!r}."
        )
    reserva = _campo(dados, "voz", "reserva", str).strip()
    if reserva and reserva not in MOTORES_DE_VOZ:
        raise ConfigError(
            f"[voz] reserva deve ser vazia ou um de {', '.join(MOTORES_DE_VOZ)}; veio {reserva!r}."
        )
    velocidade = _velocidade(dados, "voz.kokoro")
    realce = _campo(dados, "voz", "realce_pergunta", str).strip()
    if realce not in REALCES_DE_PERGUNTA:
        opcoes = ", ".join(repr(r) for r in REALCES_DE_PERGUNTA)
        raise ConfigError(f"[voz] realce_pergunta deve ser um de {opcoes}; veio {realce!r}.")
    pronuncias = dados.get("voz", {}).get("pronuncias", {})
    if not isinstance(pronuncias, dict) or not all(
        isinstance(chave, str) and isinstance(valor, str) for chave, valor in pronuncias.items()
    ):
        raise ConfigError('[voz.pronuncias] deve ter linhas como "palavra" = "como falar".')
    return Voz(
        motor=motor,
        realce_pergunta=realce,
        pronuncias={chave.strip(): valor for chave, valor in pronuncias.items() if chave.strip()},
        reserva=reserva if reserva != motor else "",
        kokoro=VozKokoro(
            url=_campo(dados, "voz.kokoro", "url", str),
            voz=_campo(dados, "voz.kokoro", "voz", str),
            velocidade=velocidade,
        ),
        piper=VozPiper(
            url=_campo(dados, "voz.piper", "url", str),
            voz=_campo(dados, "voz.piper", "voz", str),
            velocidade=_velocidade(dados, "voz.piper"),
            variacao=_variacao(dados, "variacao"),
            variacao_ritmo=_variacao(dados, "variacao_ritmo"),
        ),
        elevenlabs=VozElevenLabs(
            voz_id=_campo(dados, "voz.elevenlabs", "voz_id", str).strip(),
            modelo=_campo(dados, "voz.elevenlabs", "modelo", str),
        ),
        comfyui=VozComfyUI(
            url=_campo(dados, "voz.comfyui", "url", str),
            fluxo=_caminho(_campo(dados, "voz.comfyui", "fluxo", str), raiz),
            espera_s=_campo(dados, "voz.comfyui", "espera_s", float),
            campo=_campo(dados, "voz.comfyui", "campo", str).strip(),
        ),
    )


def _caminho(texto: str, raiz: Path) -> Path:
    caminho = Path(texto)
    return caminho if caminho.is_absolute() else raiz / caminho


def carregar(raiz: Path = RAIZ, ambiente: dict[str, str] | None = None) -> Config:
    """Reads the config files from `raiz` and returns a validated Config."""
    ambiente = {**ler_env(raiz / ".env"), **(os.environ if ambiente is None else ambiente)}

    padrao = Path(ambiente.get("ELLA_CONFIG") or raiz / "config/nora.toml")
    if not padrao.is_file():
        raise ConfigError(f"Arquivo de config não encontrado: {padrao}")
    dados = _ler_toml(padrao)
    arquivos = [padrao]

    local = raiz / "config/local.toml"
    if local.is_file():
        dados = mesclar(dados, _ler_toml(local))
        arquivos.append(local)

    nome = _campo(dados, "assistente", "nome", str).strip()
    if not nome:
        raise ConfigError("[assistente] nome não pode ficar vazio.")

    pasta_dados = Path(_campo(dados, "caminhos", "dados", str))
    if not pasta_dados.is_absolute():
        pasta_dados = raiz / pasta_dados

    return Config(
        assistente=Assistente(
            nome=nome,
            palavra_de_ativacao=_campo(dados, "assistente", "palavra_de_ativacao", str),
            idioma=_campo(dados, "assistente", "idioma", str),
            pronuncia=_campo(dados, "assistente", "pronuncia", str).strip(),
        ),
        nome_usuario=_campo(dados, "usuario", "nome", str).strip(),
        persona=Persona(
            descricao=_campo(dados, "persona", "descricao", str),
            humor=_entre_0_e_1("persona", "humor", _campo(dados, "persona", "humor", float)),
            formalidade=_entre_0_e_1(
                "persona", "formalidade", _campo(dados, "persona", "formalidade", float)
            ),
            respostas_curtas=_campo(dados, "persona", "respostas_curtas", bool),
        ),
        ouvido=Ouvido(
            motor=_campo(dados, "ouvido", "motor", str),
            url=_campo(dados, "ouvido", "url", str),
            idioma=_campo(dados, "ouvido", "idioma", str),
        ),
        voz=_ler_voz(dados, raiz),
        escuta=Escuta(
            limiar=_entre_0_e_1("escuta", "limiar", _campo(dados, "escuta", "limiar", float)),
            silencio_ms=_campo(dados, "escuta", "silencio_ms", int),
            janela_s=_campo(dados, "escuta", "janela_s", float),
            pausar_microfone=_campo(dados, "escuta", "pausar_microfone", bool),
        ),
        memoria=Memoria(
            ativa=_campo(dados, "memoria", "ativa", bool),
            modelo_embeddings=_campo(dados, "memoria", "modelo_embeddings", str),
            curadoria=_campo(dados, "memoria", "curadoria", bool),
            fatos_por_pergunta=_campo(dados, "memoria", "fatos_por_pergunta", int),
            similaridade_minima=_entre_0_e_1(
                "memoria",
                "similaridade_minima",
                _campo(dados, "memoria", "similaridade_minima", float),
            ),
            trocas_por_pergunta=_campo(dados, "memoria", "trocas_por_pergunta", int),
            agenda_dias=_campo(dados, "memoria", "agenda_dias", int),
        ),
        emocao=Emocao(
            ativa=_campo(dados, "emocao", "ativa", bool),
            intensidade=_entre_0_e_1(
                "emocao", "intensidade", _campo(dados, "emocao", "intensidade", float)
            ),
            reacoes_por_resposta=_campo(dados, "emocao", "reacoes_por_resposta", int),
        ),
        audio=Audio(
            microfone=_campo(dados, "audio", "microfone", str),
            alto_falante=_campo(dados, "audio", "alto_falante", str),
            prioridade=_campo(dados, "audio", "prioridade", bool),
            volume_outros=_entre_0_e_1(
                "audio", "volume_outros", _campo(dados, "audio", "volume_outros", float)
            ),
            silencio_inicial_ms=_silencio(dados),
        ),
        modelo_local=ModeloLocal(
            provedor=_campo(dados, "modelos.local", "provedor", str),
            modelo=_campo(dados, "modelos.local", "modelo", str),
            keep_alive=_campo(dados, "modelos.local", "keep_alive", str),
            temperatura=_temperatura(_campo(dados, "modelos.local", "temperatura", float)),
            pensar=_campo(dados, "modelos.local", "pensar", bool),
        ),
        modelo_nuvem=ModeloNuvem(
            provedor=_campo(dados, "modelos.nuvem", "provedor", str),
            rapido=_campo(dados, "modelos.nuvem", "rapido", str),
            pesado=_campo(dados, "modelos.nuvem", "pesado", str),
            esforco_rapido=_esforco(dados, "esforco_rapido"),
            esforco_pesado=_esforco(dados, "esforco_pesado"),
        ),
        modelo_openai=ModeloOpenAI(
            rapido=_campo(dados, "modelos.openai", "rapido", str),
            pesado=_campo(dados, "modelos.openai", "pesado", str),
            esforco_rapido=_esforco(dados, "esforco_rapido", "modelos.openai", ESFORCOS_OPENAI),
            esforco_pesado=_esforco(dados, "esforco_pesado", "modelos.openai", ESFORCOS_OPENAI),
        ),
        roteador=_roteador(dados),
        notas=_notas(dados, raiz),
        auto_melhoria=_auto_melhoria(dados),
        pasta_dados=pasta_dados,
        ollama_host=ambiente.get("OLLAMA_HOST") or "http://127.0.0.1:11434",
        tem_chave_anthropic=bool(ambiente.get("ANTHROPIC_API_KEY")),
        chave_elevenlabs=ambiente.get("ELEVENLABS_API_KEY", ""),
        chave_anthropic=ambiente.get("ANTHROPIC_API_KEY", ""),
        chave_openai=ambiente.get("OPENAI_API_KEY", ""),
        arquivos=tuple(arquivos),
    )
