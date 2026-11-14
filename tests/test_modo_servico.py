import pytest
from fastapi.testclient import TestClient

from lg_servcontrol.app import create_app
from lg_servcontrol.emissor_ir import EmissorIRFalso

CONFIRMACAO = {"confirmo_risco": True}


class RelogioFalso:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += segundos


def _hex_no_ar(pulsos):
    bits = "".join("1" if espaco > 1000 else "0" for espaco in pulsos[3:3 + 64:2])
    return f"{int(bits, 2):08X}"


@pytest.fixture
def emissor():
    return EmissorIRFalso()


@pytest.fixture
def relogio():
    return RelogioFalso()


@pytest.fixture
def cliente(emissor, relogio, tmp_path):
    app = create_app(emissor=emissor, caminho_estado=tmp_path / "estado.json", relogio=relogio)
    cliente = TestClient(app)
    cliente.put("/api/modelo", json={"codigo": "OLED55C1PSA"})
    return cliente


def test_modo_servico_comeca_desativado(cliente):
    estado = cliente.get("/api/modo-servico").json()

    assert estado["ativo"] is False
    assert estado["teclas"] == []


def test_tecla_de_servico_e_recusada_fora_do_modo_servico(cliente, emissor):
    resposta = cliente.post("/api/teclas/IN_START/enviar")

    assert resposta.status_code == 403
    assert resposta.json()["erro"] == "modo_servico_inativo"
    assert emissor.tentativas == 0


def test_ativar_exige_confirmar_o_risco(cliente):
    resposta = cliente.post("/api/modo-servico/ativar", json={})

    assert resposta.status_code == 422
    assert cliente.get("/api/modo-servico").json()["ativo"] is False


def test_ativar_sem_modelo_da_tv_e_recusado(emissor, relogio):
    cliente = TestClient(create_app(emissor=emissor, relogio=relogio))

    resposta = cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO)

    assert resposta.status_code == 409
    assert resposta.json()["erro"] == "modelo_nao_escolhido"


def test_modo_servico_ativo_mostra_teclas_e_senhas_do_modelo(cliente):
    estado = cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO).json()

    assert estado["ativo"] is True
    assert estado["segundos_restantes"] == 300
    assert {t["tecla"] for t in estado["teclas"]} >= {"IN_START", "EZ_ADJUST"}
    menus = {m["menu"]: m["senhas"] for m in estado["menus"]}
    assert "0413" in menus["In-Start"]
    assert menus["EZ-Adjust"]


@pytest.mark.parametrize("tecla, codigo", [("IN_START", "20DFDF20"), ("EZ_ADJUST", "20DFFF00")])
def test_tecla_de_servico_no_modo_servico_gera_o_codigo_ir_lg(cliente, emissor, tecla, codigo):
    cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO)

    resposta = cliente.post(f"/api/teclas/{tecla}/enviar")

    assert resposta.status_code == 200
    assert len(emissor.enviados) == 1
    assert _hex_no_ar(emissor.enviados[0].pulsos()) == codigo


def test_modo_servico_expira_apos_5_minutos_sem_tecla_de_servico(cliente, emissor, relogio):
    cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO)
    relogio.avancar(301)

    assert cliente.get("/api/modo-servico").json()["ativo"] is False
    assert cliente.post("/api/teclas/IN_START/enviar").status_code == 403
    assert emissor.tentativas == 0


def test_cada_tecla_de_servico_reinicia_a_contagem(cliente, relogio):
    cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO)
    relogio.avancar(200)
    cliente.post("/api/teclas/IN_START/enviar")
    relogio.avancar(200)

    estado = cliente.get("/api/modo-servico").json()
    assert estado["ativo"] is True
    assert estado["segundos_restantes"] == 100
    assert cliente.post("/api/teclas/EZ_ADJUST/enviar").status_code == 200


def test_tecla_comum_nao_reinicia_a_contagem(cliente, relogio):
    cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO)
    relogio.avancar(200)
    cliente.post("/api/teclas/OK/enviar")
    relogio.avancar(101)

    assert cliente.get("/api/modo-servico").json()["ativo"] is False


def test_desativar_manualmente(cliente, emissor):
    cliente.post("/api/modo-servico/ativar", json=CONFIRMACAO)

    estado = cliente.post("/api/modo-servico/desativar").json()

    assert estado["ativo"] is False
    assert cliente.post("/api/teclas/IN_START/enviar").status_code == 403
    assert emissor.tentativas == 0


def test_teclas_de_servico_nao_aparecem_na_lista_de_teclas_comuns(cliente):
    teclas = {t["tecla"] for t in cliente.get("/api/teclas").json()}

    assert "IN_START" not in teclas


def test_pagina_tem_o_modo_servico_com_aviso_de_risco(cliente):
    html = cliente.get("/").text

    assert 'id="painel-servico"' in html
    assert 'id="confirmar-servico"' in html
    assert "fábrica" in html
