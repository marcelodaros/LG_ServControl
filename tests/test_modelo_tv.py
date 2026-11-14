import pytest
from fastapi.testclient import TestClient

from lg_servcontrol.app import create_app
from lg_servcontrol.emissor_ir import EmissorIRFalso


@pytest.fixture
def caminho_estado(tmp_path):
    return tmp_path / "estado.json"


@pytest.fixture
def cliente(caminho_estado):
    return TestClient(create_app(emissor=EmissorIRFalso(), caminho_estado=caminho_estado))


def test_sem_modelo_salvo_a_api_informa_que_nao_ha_modelo(cliente):
    assert cliente.get("/api/modelo").json() == {"modelo": None}


@pytest.mark.parametrize(
    "codigo, linha, ano",
    [
        ("OLED55C1PSA", "OLED", 2021),
        ("OLED65G4", "OLED", 2024),
        ("oled 77 cx psa", "OLED", 2020),
        ("55UN7300PSA", "UHD", 2020),
        ("50UQ8050PSB", "UHD", 2022),
        ("65QNED80URA", "QNED", 2023),
        ("55NANO75UPA", "NanoCell", 2021),
        ("55SM8600PSA", "NanoCell", 2019),
        ("43LM6300PSB", "Full HD", 2019),
    ],
)
def test_codigo_do_modelo_e_decifrado_em_linha_e_ano(cliente, codigo, linha, ano):
    resposta = cliente.post("/api/modelo/decodificar", json={"codigo": codigo})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["linha"], corpo["ano"]) == (linha, ano)


def test_decifrar_nao_salva_o_modelo(cliente):
    cliente.post("/api/modelo/decodificar", json={"codigo": "OLED55C1PSA"})

    assert cliente.get("/api/modelo").json() == {"modelo": None}


@pytest.mark.parametrize("codigo", ["ABC123", "", "SAMSUNG55", "OLED55"])
def test_codigo_nao_reconhecido_e_sinalizado(cliente, codigo):
    resposta = cliente.post("/api/modelo/decodificar", json={"codigo": codigo})

    assert resposta.status_code == 422
    assert resposta.json()["erro"] == "codigo_nao_reconhecido"


def test_salvar_por_codigo_guarda_codigo_linha_e_ano(cliente):
    resposta = cliente.put("/api/modelo", json={"codigo": "OLED55C1PSA"})

    assert resposta.status_code == 200
    modelo = cliente.get("/api/modelo").json()["modelo"]
    assert (modelo["codigo"], modelo["linha"], modelo["ano"]) == ("OLED55C1PSA", "OLED", 2021)
    assert modelo["descricao"]


def test_salvar_por_codigo_nao_reconhecido_e_recusado(cliente):
    resposta = cliente.put("/api/modelo", json={"codigo": "ABC123"})

    assert resposta.status_code == 422
    assert resposta.json()["erro"] == "codigo_nao_reconhecido"
    assert cliente.get("/api/modelo").json() == {"modelo": None}


def test_escolha_por_linha_e_ano(cliente):
    resposta = cliente.put("/api/modelo", json={"linha": "QNED", "ano": 2022})

    assert resposta.status_code == 200
    modelo = cliente.get("/api/modelo").json()["modelo"]
    assert (modelo["codigo"], modelo["linha"], modelo["ano"]) == (None, "QNED", 2022)


@pytest.mark.parametrize("escolha", [{"linha": "Plasma", "ano": 2020}, {"linha": "OLED", "ano": 1999}, {}])
def test_escolha_invalida_e_recusada(cliente, escolha):
    resposta = cliente.put("/api/modelo", json=escolha)

    assert resposta.status_code == 422
    assert cliente.get("/api/modelo").json() == {"modelo": None}


def test_opcoes_de_linha_e_ano_para_a_lista(cliente):
    opcoes = cliente.get("/api/modelo/opcoes").json()

    assert {"OLED", "QNED", "NanoCell", "UHD", "Full HD"} <= set(opcoes["linhas"])
    assert 2016 in opcoes["anos"] and 2024 in opcoes["anos"]


def test_modelo_persiste_entre_reinicios_do_servidor(caminho_estado):
    TestClient(create_app(emissor=EmissorIRFalso(), caminho_estado=caminho_estado)).put(
        "/api/modelo", json={"codigo": "55UN7300PSA"}
    )

    reiniciado = TestClient(create_app(emissor=EmissorIRFalso(), caminho_estado=caminho_estado))

    assert reiniciado.get("/api/modelo").json()["modelo"]["codigo"] == "55UN7300PSA"


def test_trocar_o_modelo_substitui_o_anterior(cliente):
    cliente.put("/api/modelo", json={"codigo": "OLED55C1PSA"})
    cliente.put("/api/modelo", json={"linha": "UHD", "ano": 2018})

    modelo = cliente.get("/api/modelo").json()["modelo"]
    assert (modelo["linha"], modelo["ano"]) == ("UHD", 2018)


def test_pagina_tem_a_escolha_do_modelo_com_a_dica(cliente):
    html = cliente.get("/").text

    assert 'id="escolher-modelo"' in html
    assert "Informações da TV" in html
    assert "etiqueta" in html
