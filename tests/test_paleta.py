"""A paleta de emoções é uma só (hud/paleta.json), para a HUD e o Second Brain."""

import re

from nora.emocao import EMOCOES
from nora.paleta import cor, cores_por_emocao, grupo, paleta


def test_toda_emocao_da_nora_tem_cor():
    for nome in EMOCOES:
        assert nome in paleta()["aliases"], f"{nome} sem cor em hud/paleta.json"
    for nome, valor in cores_por_emocao().items():
        assert re.fullmatch(r"#[0-9A-F]{6}", valor), nome


def test_cores_do_prompt_da_hud():
    # Tabela do prompt da HUD v0.4.0: calma turquesa, tristeza lavanda, curiosidade terracota.
    assert cor("calma") == "#66D4CB"
    assert cor("triste") == "#AA9ACF"
    assert cor("curiosa") == "#DF876A"
    assert cor("séria") == cor("seria") == "#80A8F6"
    assert cor("alegre") == cor("empolgada") == "#F0C66A"
    assert cor("carinhosa") == "#E3A4BD"
    assert cor("desconhecida") == cor("neutra") == "#C9C9C9"
    assert grupo("Curiosa") == "curiosidade"


def test_cada_grupo_tem_cor_e_dinamica():
    dados = paleta()
    assert set(dados["aliases"].values()) <= set(dados["cores"])
    assert set(dados["cores"]) == set(dados["dinamica"])
