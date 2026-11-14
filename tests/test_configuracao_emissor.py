import json

from fastapi.testclient import TestClient

from lg_servcontrol.app import montar_app
from lg_servcontrol.emissor_ir import EmissorIRFalso

CONFIG_VALIDA = {
    "modo": "local",
    "device_id": "abc123",
    "ip": "192.168.0.50",
    "local_key": "chave-local-123",
    "versao": 3.3,
    "tipo_controle": 1,
}


class FabricaFalsa:
    def __init__(self, emissor):
        self.emissor = emissor
        self.configs = []

    def __call__(self, config):
        self.configs.append(config)
        return self.emissor


def _gravar(tmp_path, conteudo):
    caminho = tmp_path / "emissor_ir.json"
    caminho.write_text(conteudo if isinstance(conteudo, str) else json.dumps(conteudo))
    return caminho


def test_sem_arquivo_de_configuracao_o_emissor_aparece_como_nao_configurado(tmp_path):
    fabrica = FabricaFalsa(EmissorIRFalso())
    cliente = TestClient(montar_app(tmp_path / "nao_existe.json", fabrica))

    estado = cliente.get("/api/emissor/estado").json()

    assert estado["estado"] == "nao_configurado"
    assert "configurar" in estado["mensagem"]
    assert fabrica.configs == []


def test_sem_configuracao_enviar_tecla_falha_sem_tocar_no_emissor(tmp_path):
    emissor = EmissorIRFalso()
    cliente = TestClient(montar_app(tmp_path / "nao_existe.json", FabricaFalsa(emissor)))

    resposta = cliente.post("/api/teclas/POWER/enviar")

    assert resposta.status_code == 503
    assert resposta.json()["erro"] == "emissor_ir_nao_configurado"
    assert emissor.tentativas == 0


def test_configuracao_sem_campo_obrigatorio_e_invalida_e_nomeia_o_campo(tmp_path):
    config = {k: v for k, v in CONFIG_VALIDA.items() if k != "local_key"}
    cliente = TestClient(montar_app(_gravar(tmp_path, config), FabricaFalsa(EmissorIRFalso())))

    estado = cliente.get("/api/emissor/estado").json()

    assert estado["estado"] == "nao_configurado"
    assert "local_key" in estado["mensagem"]


def test_configuracao_com_json_quebrado_e_invalida(tmp_path):
    cliente = TestClient(montar_app(_gravar(tmp_path, "{nao é json"), FabricaFalsa(EmissorIRFalso())))

    assert cliente.get("/api/emissor/estado").json()["estado"] == "nao_configurado"


def test_configuracao_valida_e_entregue_a_fabrica_e_o_envio_usa_o_emissor(tmp_path):
    emissor = EmissorIRFalso()
    fabrica = FabricaFalsa(emissor)
    cliente = TestClient(montar_app(_gravar(tmp_path, CONFIG_VALIDA), fabrica))

    resposta = cliente.post("/api/teclas/POWER/enviar")

    assert resposta.status_code == 200
    assert len(emissor.enviados) == 1
    assert fabrica.configs[0].device_id == "abc123"
    assert fabrica.configs[0].ip == "192.168.0.50"


def test_emissor_que_responde_aparece_como_conectado(tmp_path):
    cliente = TestClient(montar_app(_gravar(tmp_path, CONFIG_VALIDA), FabricaFalsa(EmissorIRFalso())))

    assert cliente.get("/api/emissor/estado").json()["estado"] == "conectado"


def test_emissor_que_nao_responde_aparece_como_desconectado(tmp_path):
    emissor = EmissorIRFalso(falhar=True)
    cliente = TestClient(montar_app(_gravar(tmp_path, CONFIG_VALIDA), FabricaFalsa(emissor)))

    estado = cliente.get("/api/emissor/estado").json()

    assert estado["estado"] == "desconectado"
    assert estado["mensagem"]
