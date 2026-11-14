"""Configuração do Emissor IR, gravada pelo script `python -m lg_servcontrol.configurar`."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

CAMINHO_PADRAO = Path(os.environ.get("LG_SERVCONTROL_CONFIG", "emissor_ir.json"))

COMO_CONFIGURAR = "Rode `python -m lg_servcontrol.configurar` para configurar o Emissor IR."


class ConfiguracaoInvalida(Exception):
    pass


@dataclass(frozen=True)
class ConfiguracaoEmissorIR:
    modo: str
    device_id: str
    ip: str
    local_key: str
    versao: float
    tipo_controle: int

    def gravar(self, caminho: Path) -> None:
        caminho.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n", "utf-8")


_OBRIGATORIOS = ("device_id", "ip", "local_key", "versao", "tipo_controle")


def carregar(caminho: Path) -> ConfiguracaoEmissorIR:
    if not caminho.exists():
        raise ConfiguracaoInvalida(f"Arquivo {caminho} não encontrado. {COMO_CONFIGURAR}")
    try:
        dados = json.loads(caminho.read_text("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        raise ConfiguracaoInvalida(f"{caminho} não é um JSON válido ({erro}). {COMO_CONFIGURAR}") from None
    if not isinstance(dados, dict):
        raise ConfiguracaoInvalida(f"{caminho} deve conter um objeto JSON. {COMO_CONFIGURAR}")

    faltando = [campo for campo in _OBRIGATORIOS if not dados.get(campo)]
    if faltando:
        raise ConfiguracaoInvalida(
            f"{caminho} sem o(s) campo(s): {', '.join(faltando)}. {COMO_CONFIGURAR}"
        )

    modo = dados.get("modo", "local")
    if modo != "local":
        raise ConfiguracaoInvalida(f"Modo '{modo}' ainda não suportado; use 'local'.")
    if dados["tipo_controle"] not in (1, 2):
        raise ConfiguracaoInvalida("tipo_controle deve ser 1 (DPS 201/202) ou 2 (DPS 1-13).")

    try:
        return ConfiguracaoEmissorIR(
            modo=modo,
            device_id=str(dados["device_id"]),
            ip=str(dados["ip"]),
            local_key=str(dados["local_key"]),
            versao=float(dados["versao"]),
            tipo_controle=int(dados["tipo_controle"]),
        )
    except (TypeError, ValueError) as erro:
        raise ConfiguracaoInvalida(f"Valor inválido em {caminho}: {erro}. {COMO_CONFIGURAR}") from None
