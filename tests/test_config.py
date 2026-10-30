import pytest

from ella import __version__
from ella.cli import main, saudacao
from ella.config import RAIZ, ConfigError, carregar, ler_env, mesclar


def test_config_padrao_do_repositorio_carrega(criar_raiz):
    raiz = criar_raiz()
    config = carregar(raiz, ambiente={})
    assert config.assistente.nome == "Ella"
    assert config.nome_usuario == ""
    assert config.modelo_local.provedor == "ollama"
    assert config.modelo_local.pensar is False
    assert 0.0 <= config.persona.humor <= 1.0
    assert config.pasta_dados == raiz / "data"
    assert not config.tem_chave_anthropic


def test_config_real_carrega():
    assert carregar(RAIZ).assistente.nome


def test_local_toml_sobrepoe_so_o_que_define(criar_raiz):
    raiz = criar_raiz(local='[usuario]\nnome = "Gabriel"\n[persona]\nhumor = 0.8\n')
    config = carregar(raiz, ambiente={})
    assert config.nome_usuario == "Gabriel"
    assert config.persona.humor == 0.8
    assert config.persona.formalidade == 0.3
    assert len(config.arquivos) == 2


def test_humor_fora_da_faixa_e_recusado(criar_raiz):
    raiz = criar_raiz(local="[persona]\nhumor = 2\n")
    with pytest.raises(ConfigError, match="humor"):
        carregar(raiz, ambiente={})


def test_nome_vazio_e_recusado(criar_raiz):
    raiz = criar_raiz(local='[assistente]\nnome = "  "\n')
    with pytest.raises(ConfigError, match="nome"):
        carregar(raiz, ambiente={})


def test_tipo_errado_e_recusado(criar_raiz):
    raiz = criar_raiz(local='[persona]\nrespostas_curtas = "sim"\n')
    with pytest.raises(ConfigError, match="respostas_curtas"):
        carregar(raiz, ambiente={})


def test_env_define_chave_e_host(criar_raiz):
    raiz = criar_raiz(env="# comentário\nANTHROPIC_API_KEY=abc\nOLLAMA_HOST='http://pc:11434'\n")
    config = carregar(raiz, ambiente={})
    assert config.tem_chave_anthropic
    assert config.ollama_host == "http://pc:11434"


def test_variavel_de_ambiente_vence_o_env(criar_raiz):
    raiz = criar_raiz(env="OLLAMA_HOST=http://do-arquivo:1\n")
    config = carregar(raiz, ambiente={"OLLAMA_HOST": "http://do-sistema:2"})
    assert config.ollama_host == "http://do-sistema:2"


def test_sem_arquivo_de_config(tmp_path):
    with pytest.raises(ConfigError, match="não encontrado"):
        carregar(tmp_path, ambiente={})


def test_mesclar_e_ler_env(tmp_path):
    assert mesclar({"a": {"x": 1, "y": 2}}, {"a": {"y": 3}}) == {"a": {"x": 1, "y": 3}}
    assert ler_env(tmp_path / "nao-existe") == {}


def test_hello_world(criar_raiz, capsys):
    raiz = criar_raiz()
    assert saudacao(carregar(raiz, ambiente={})) == f"Olá! Eu sou a Ella, versão {__version__}."
    com_nome = carregar(criar_raiz(local='[usuario]\nnome = "Gabriel"\n'), ambiente={})
    assert saudacao(com_nome).startswith("Olá, Gabriel! Eu sou a Ella")
    assert main([]) == 0
    assert "Eu sou a" in capsys.readouterr().out
