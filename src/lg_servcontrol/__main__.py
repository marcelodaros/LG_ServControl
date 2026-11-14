"""Sobe o servidor.

Usa o Emissor IR configurado em `emissor_ir.json` (ver `python -m lg_servcontrol.configurar`).
Com LG_SERVCONTROL_SIMULAR=1, usa um emissor simulado que só registra no log.
"""

import logging
import os

import uvicorn

from lg_servcontrol.app import create_app, montar_app
from lg_servcontrol.codigos_ir import CodigoIR
from lg_servcontrol.configuracao import CAMINHO_ESTADO, CAMINHO_PADRAO
from lg_servcontrol.emissor_ir import EmissorIRFalso

log = logging.getLogger("lg_servcontrol")


class EmissorIRDeLog(EmissorIRFalso):
    def enviar(self, codigo: CodigoIR) -> None:
        super().enviar(codigo)
        log.warning(
            "Emissor IR simulado: %s endereço=0x%02X comando=0x%02X",
            codigo.protocolo, codigo.endereco, codigo.comando,
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    porta = int(os.environ.get("PORT", "8000"))
    if os.environ.get("LG_SERVCONTROL_SIMULAR") == "1":
        app = create_app(emissor=EmissorIRDeLog(), caminho_estado=CAMINHO_ESTADO)
    else:
        from lg_servcontrol.emissor_local import EmissorIRLocal

        app = montar_app(CAMINHO_PADRAO, EmissorIRLocal, caminho_estado=CAMINHO_ESTADO)
    uvicorn.run(app, host="0.0.0.0", port=porta)


if __name__ == "__main__":
    main()
