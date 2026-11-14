from fastapi.testclient import TestClient

from lg_servcontrol.app import create_app
from lg_servcontrol.emissor_ir import EmissorIRFalso


def _cliente(emissor):
    return TestClient(create_app(emissor=emissor))


def test_power_envia_codigo_ir_nec_lg_ao_emissor():
    emissor = EmissorIRFalso()

    resposta = _cliente(emissor).post("/api/teclas/POWER/enviar")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "enviado"}
    assert len(emissor.enviados) == 1
    codigo = emissor.enviados[0]
    assert (codigo.protocolo, codigo.endereco, codigo.comando) == ("NEC", 0x04, 0x08)


def test_codigo_ir_de_power_tem_os_pulsos_nec_esperados():
    emissor = EmissorIRFalso()

    _cliente(emissor).post("/api/teclas/POWER/enviar")

    pulsos = emissor.enviados[0].pulsos()
    # cabeçalho NEC + 32 bits (marca + espaço) + marca final + silêncio final
    assert pulsos[:2] == [9000, 4500]
    assert len(pulsos) == 2 + 32 * 2 + 2
    # bytes enviados LSB primeiro: 0x04, 0xFB, 0x08, 0xF7
    bits = [1 if espaco > 1000 else 0 for espaco in pulsos[3:-2:2]]
    esperado = []
    for byte in (0x04, 0xFB, 0x08, 0xF7):
        esperado += [(byte >> i) & 1 for i in range(8)]
    assert bits == esperado
    assert pulsos[-2] == 560
    assert pulsos[-1] >= 20000


def test_um_pedido_gera_exatamente_um_envio():
    emissor = EmissorIRFalso()
    cliente = _cliente(emissor)

    cliente.post("/api/teclas/POWER/enviar")
    cliente.post("/api/teclas/POWER/enviar")

    assert len(emissor.enviados) == 2


def test_falha_do_emissor_vira_erro_de_comunicacao_sem_reenvio():
    emissor = EmissorIRFalso(falhar=True)

    resposta = _cliente(emissor).post("/api/teclas/POWER/enviar")

    assert resposta.status_code == 502
    assert resposta.json()["erro"] == "comunicacao_emissor_ir"
    assert emissor.tentativas == 1


def test_tecla_desconhecida_nao_envia_nada():
    emissor = EmissorIRFalso()

    resposta = _cliente(emissor).post("/api/teclas/NAO_EXISTE/enviar")

    assert resposta.status_code == 404
    assert emissor.tentativas == 0


def test_pagina_do_controle_tem_a_tecla_power():
    resposta = _cliente(EmissorIRFalso()).get("/")

    assert resposta.status_code == 200
    assert 'data-tecla="POWER"' in resposta.text
