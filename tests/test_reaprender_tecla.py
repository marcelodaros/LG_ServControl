import pytest
from fastapi.testclient import TestClient

from lg_servcontrol.app import create_app
from lg_servcontrol.codigos_ir import CodigoIRAprendido, codigo_da_tecla
from lg_servcontrol.emissor_ir import EmissorIRFalso

# Um sinal qualquer capturado de um controle real (não é NEC da LG).
SINAL_REAL = CodigoIRAprendido(pulsos=(3400, 1700, 420, 1300, 420, 420, 420, 1300, 420, 30000))


@pytest.fixture
def caminho_estado(tmp_path):
    return tmp_path / "estado.json"


@pytest.fixture
def emissor():
    return EmissorIRFalso(aprendido=SINAL_REAL)


@pytest.fixture
def cliente(emissor, caminho_estado):
    return TestClient(create_app(emissor=emissor, caminho_estado=caminho_estado))


def test_reaprender_captura_o_sinal_do_controle_real(cliente, emissor):
    resposta = cliente.post("/api/teclas/VOL_MAIS/aprender")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "aprendido"
    assert emissor.aprendizados == 1


def test_codigo_aprendido_substitui_o_gerado_nos_envios(cliente, emissor):
    cliente.post("/api/teclas/VOL_MAIS/aprender")

    cliente.post("/api/teclas/VOL_MAIS/enviar")

    assert emissor.enviados == [SINAL_REAL]


def test_outras_teclas_continuam_com_o_codigo_gerado(cliente, emissor):
    cliente.post("/api/teclas/VOL_MAIS/aprender")

    cliente.post("/api/teclas/VOL_MENOS/enviar")

    assert emissor.enviados == [codigo_da_tecla("VOL_MENOS")]


def test_codigo_aprendido_persiste_entre_reinicios(emissor, caminho_estado):
    TestClient(create_app(emissor=emissor, caminho_estado=caminho_estado)).post(
        "/api/teclas/OK/aprender"
    )
    outro_emissor = EmissorIRFalso()

    reiniciado = TestClient(create_app(emissor=outro_emissor, caminho_estado=caminho_estado))
    reiniciado.post("/api/teclas/OK/enviar")

    assert outro_emissor.enviados == [SINAL_REAL]


def test_aprender_nao_apaga_o_modelo_da_tv(cliente):
    cliente.put("/api/modelo", json={"codigo": "OLED55C1PSA"})

    cliente.post("/api/teclas/OK/aprender")

    assert cliente.get("/api/modelo").json()["modelo"]["codigo"] == "OLED55C1PSA"


def test_desfazer_volta_ao_codigo_gerado(cliente, emissor):
    cliente.post("/api/teclas/VOL_MAIS/aprender")

    resposta = cliente.delete("/api/teclas/VOL_MAIS/aprendido")
    cliente.post("/api/teclas/VOL_MAIS/enviar")

    assert resposta.status_code == 200
    assert emissor.enviados == [codigo_da_tecla("VOL_MAIS")]


def test_teclas_com_codigo_aprendido_sao_marcadas(cliente):
    cliente.post("/api/teclas/MUDO/aprender")

    teclas = {t["tecla"]: t["aprendida"] for t in cliente.get("/api/teclas").json()}

    assert teclas["MUDO"] is True
    assert teclas["POWER"] is False


def test_aprendizado_sem_sinal_expira_e_e_reportado(caminho_estado):
    emissor = EmissorIRFalso(aprendido=None)
    cliente = TestClient(create_app(emissor=emissor, caminho_estado=caminho_estado))

    resposta = cliente.post("/api/teclas/VOL_MAIS/aprender")
    cliente.post("/api/teclas/VOL_MAIS/enviar")

    assert resposta.status_code == 408
    assert resposta.json()["erro"] == "aprendizado_expirou"
    assert emissor.enviados == [codigo_da_tecla("VOL_MAIS")]


def test_aprender_tecla_desconhecida_e_recusado(cliente, emissor):
    resposta = cliente.post("/api/teclas/NAO_EXISTE/aprender")

    assert resposta.status_code == 404
    assert emissor.aprendizados == 0


def test_falha_do_emissor_ao_aprender_vira_erro_de_comunicacao(caminho_estado):
    emissor = EmissorIRFalso(falhar=True, aprendido=SINAL_REAL)
    cliente = TestClient(create_app(emissor=emissor, caminho_estado=caminho_estado))

    resposta = cliente.post("/api/teclas/OK/aprender")

    assert resposta.status_code == 502
    assert resposta.json()["erro"] == "comunicacao_emissor_ir"


def test_aprender_sem_emissor_configurado(caminho_estado):
    cliente = TestClient(
        create_app(emissor=None, problema_configuracao="sem config", caminho_estado=caminho_estado)
    )

    assert cliente.post("/api/teclas/OK/aprender").status_code == 503


def test_lista_de_teclas_aprendiveis_inclui_comuns_e_de_servico(cliente):
    teclas = {t["tecla"]: t for t in cliente.get("/api/teclas/aprendiveis").json()}

    assert "POWER" in teclas and "IN_START" in teclas
    assert teclas["IN_START"]["grupo"] == "servico"


def test_tecla_de_servico_aprendida_ainda_exige_modo_servico(cliente, emissor):
    cliente.put("/api/modelo", json={"codigo": "OLED55C1PSA"})
    cliente.post("/api/teclas/IN_START/aprender")

    recusada = cliente.post("/api/teclas/IN_START/enviar")
    cliente.post("/api/modo-servico/ativar", json={"confirmo_risco": True})
    aceita = cliente.post("/api/teclas/IN_START/enviar")

    assert recusada.status_code == 403
    assert aceita.status_code == 200
    assert emissor.enviados == [SINAL_REAL]


def test_pagina_tem_os_ajustes_com_reaprender(cliente):
    html = cliente.get("/").text

    assert 'id="ajustes"' in html
    assert "Reaprender" in html
