import pytest
from fastapi.testclient import TestClient

from lg_servcontrol.app import create_app
from lg_servcontrol.emissor_ir import EmissorIRFalso

# Códigos NEC das Teclas Comuns da LG, no formato hexadecimal em que os bits saem
# no ar (o mesmo usado em bases públicas de códigos LG, ex.: POWER = 20DF10EF).
CODIGOS_LG = {
    "POWER": "20DF10EF",
    "INPUT": "20DFD02F",
    "1": "20DF8877",
    "2": "20DF48B7",
    "3": "20DFC837",
    "4": "20DF28D7",
    "5": "20DFA857",
    "6": "20DF6897",
    "7": "20DFE817",
    "8": "20DF18E7",
    "9": "20DF9867",
    "0": "20DF08F7",
    "VOL_MAIS": "20DF40BF",
    "VOL_MENOS": "20DFC03F",
    "CANAL_MAIS": "20DF00FF",
    "CANAL_MENOS": "20DF807F",
    "MUDO": "20DF906F",
    "CIMA": "20DF02FD",
    "BAIXO": "20DF827D",
    "ESQUERDA": "20DFE01F",
    "DIREITA": "20DF609F",
    "OK": "20DF22DD",
    "VOLTAR": "20DF14EB",
    "HOME": "20DF3EC1",
    "CONFIGURACOES": "20DFC23D",
    "GUIA": "20DFD52A",
    "INFO": "20DF55AA",
    "PLAY": "20DF0DF2",
    "PAUSA": "20DF5DA2",
    "PARAR": "20DF8D72",
    "AVANCAR": "20DF718E",
    "RETROCEDER": "20DFF10E",
}


def _hex_no_ar(pulsos: list[int]) -> str:
    """Lê os 32 bits na ordem em que são transmitidos e devolve em hexadecimal."""
    bits = "".join("1" if espaco > 1000 else "0" for espaco in pulsos[3:3 + 64:2])
    return f"{int(bits, 2):08X}"


@pytest.fixture
def emissor():
    return EmissorIRFalso()


@pytest.fixture
def cliente(emissor):
    return TestClient(create_app(emissor=emissor))


def test_api_lista_todas_as_teclas_comuns(cliente):
    teclas = cliente.get("/api/teclas").json()

    assert {t["tecla"] for t in teclas} == set(CODIGOS_LG)
    for tecla in teclas:
        assert tecla["rotulo"]
        assert tecla["grupo"]


@pytest.mark.parametrize("tecla, codigo_esperado", CODIGOS_LG.items())
def test_cada_tecla_comum_gera_o_codigo_ir_lg(cliente, emissor, tecla, codigo_esperado):
    resposta = cliente.post(f"/api/teclas/{tecla}/enviar")

    assert resposta.status_code == 200
    assert len(emissor.enviados) == 1
    assert _hex_no_ar(emissor.enviados[0].pulsos()) == codigo_esperado


def test_pagina_tem_um_botao_para_cada_tecla_comum(cliente):
    html = cliente.get("/").text

    for tecla in CODIGOS_LG:
        assert f'data-tecla="{tecla}"' in html
