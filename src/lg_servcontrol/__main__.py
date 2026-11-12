"""Sobe o servidor. Até existir o Emissor IR real (#3), usa um emissor que só registra no log."""

import logging
import os

import uvicorn

from lg_servcontrol.app import create_app
from lg_servcontrol.codigos_ir import CodigoIR
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
    uvicorn.run(create_app(emissor=EmissorIRDeLog()), host="0.0.0.0", port=porta)


if __name__ == "__main__":
    main()
