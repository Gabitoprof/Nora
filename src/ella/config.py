"""Carrega e valida a config da Ella.

Ordem: config/ella.toml (padrão) -> config/local.toml (pessoal, fora do Git)
-> variáveis de ambiente e .env (segredos).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    """Config ausente ou inválida."""


@dataclass(frozen=True)
class Assistente:
    nome: str
    palavra_de_ativacao: str
    idioma: str


@dataclass(frozen=True)
class Persona:
    descricao: str
    humor: float
    formalidade: float
    respostas_curtas: bool


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


@dataclass(frozen=True)
class VozElevenLabs:
    voz_id: str
    modelo: str


MOTORES_DE_VOZ = ("kokoro", "piper", "elevenlabs")


@dataclass(frozen=True)
class Voz:
    motor: str
    kokoro: VozKokoro
    piper: VozPiper
    elevenlabs: VozElevenLabs


@dataclass(frozen=True)
class Escuta:
    limiar: float
    silencio_ms: int
    janela_s: float


@dataclass(frozen=True)
class Audio:
    microfone: str
    alto_falante: str


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


@dataclass(frozen=True)
class Config:
    assistente: Assistente
    nome_usuario: str
    persona: Persona
    ouvido: Ouvido
    voz: Voz
    audio: Audio
    escuta: Escuta
    modelo_local: ModeloLocal
    modelo_nuvem: ModeloNuvem
    pasta_dados: Path
    ollama_host: str
    tem_chave_anthropic: bool
    arquivos: tuple[Path, ...]
    chave_elevenlabs: str = field(default="", repr=False)


def mesclar(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    """Junta dois dicionários de config; as chaves de `extra` vencem."""
    resultado = dict(base)
    for chave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(resultado.get(chave), dict):
            resultado[chave] = mesclar(resultado[chave], valor)
        else:
            resultado[chave] = valor
    return resultado


def ler_env(caminho: Path) -> dict[str, str]:
    """Lê um arquivo .env simples (CHAVE=valor, # comentários)."""
    if not caminho.is_file():
        return {}
    valores = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
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


def _entre_0_e_1(secao: str, chave: str, valor: float) -> float:
    if not 0.0 <= valor <= 1.0:
        raise ConfigError(f"[{secao}] {chave} deve ficar entre 0.0 e 1.0, veio {valor}.")
    return valor


def _temperatura(valor: float) -> float:
    if not 0.0 <= valor <= 2.0:
        raise ConfigError(f"[modelos.local] temperatura deve ficar entre 0.0 e 2.0, veio {valor}.")
    return valor


def _ler_voz(dados: dict[str, Any]) -> Voz:
    motor = _campo(dados, "voz", "motor", str)
    if motor not in MOTORES_DE_VOZ:
        raise ConfigError(
            f"[voz] motor deve ser um de {', '.join(MOTORES_DE_VOZ)}; veio {motor!r}."
        )
    velocidade = _campo(dados, "voz.kokoro", "velocidade", float)
    if not 0.5 <= velocidade <= 2.0:
        raise ConfigError(f"[voz.kokoro] velocidade deve ficar entre 0.5 e 2.0, veio {velocidade}.")
    return Voz(
        motor=motor,
        kokoro=VozKokoro(
            url=_campo(dados, "voz.kokoro", "url", str),
            voz=_campo(dados, "voz.kokoro", "voz", str),
            velocidade=velocidade,
        ),
        piper=VozPiper(
            url=_campo(dados, "voz.piper", "url", str),
            voz=_campo(dados, "voz.piper", "voz", str),
        ),
        elevenlabs=VozElevenLabs(
            voz_id=_campo(dados, "voz.elevenlabs", "voz_id", str).strip(),
            modelo=_campo(dados, "voz.elevenlabs", "modelo", str),
        ),
    )


def carregar(raiz: Path = RAIZ, ambiente: dict[str, str] | None = None) -> Config:
    """Lê os arquivos de config a partir de `raiz` e devolve uma Config validada."""
    ambiente = {**ler_env(raiz / ".env"), **(os.environ if ambiente is None else ambiente)}

    padrao = Path(ambiente.get("ELLA_CONFIG") or raiz / "config/ella.toml")
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
        voz=_ler_voz(dados),
        escuta=Escuta(
            limiar=_entre_0_e_1("escuta", "limiar", _campo(dados, "escuta", "limiar", float)),
            silencio_ms=_campo(dados, "escuta", "silencio_ms", int),
            janela_s=_campo(dados, "escuta", "janela_s", float),
        ),
        audio=Audio(
            microfone=_campo(dados, "audio", "microfone", str),
            alto_falante=_campo(dados, "audio", "alto_falante", str),
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
        ),
        pasta_dados=pasta_dados,
        ollama_host=ambiente.get("OLLAMA_HOST") or "http://127.0.0.1:11434",
        tem_chave_anthropic=bool(ambiente.get("ANTHROPIC_API_KEY")),
        chave_elevenlabs=ambiente.get("ELEVENLABS_API_KEY", ""),
        arquivos=tuple(arquivos),
    )
