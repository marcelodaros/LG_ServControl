"""Porta do Emissor IR e a implementação falsa usada nos testes."""

from typing import Protocol

from lg_servcontrol.codigos_ir import CodigoIR


class ErroComunicacaoEmissorIR(Exception):
    """O Emissor IR não pôde ser alcançado ou recusou o comando."""


class EmissorIR(Protocol):
    def enviar(self, codigo: CodigoIR) -> None:
        """Transmite o Código IR; lança ErroComunicacaoEmissorIR em falha."""

    def aprender(self, timeout_s: float) -> CodigoIR | None:
        """Captura um Código IR de um controle real; None se expirar."""

    def verificar(self) -> None:
        """Confirma que o Emissor IR responde; lança ErroComunicacaoEmissorIR se não."""


class EmissorIRFalso:
    """Registra os Códigos IR enviados; pode simular falha e aprendizado."""

    def __init__(self, falhar: bool = False, aprendido: CodigoIR | None = None):
        self.falhar = falhar
        self.aprendido = aprendido
        self.enviados: list[CodigoIR] = []
        self.tentativas = 0

    def enviar(self, codigo: CodigoIR) -> None:
        self.tentativas += 1
        if self.falhar:
            raise ErroComunicacaoEmissorIR("Emissor IR falso configurado para falhar")
        self.enviados.append(codigo)

    def aprender(self, timeout_s: float) -> CodigoIR | None:
        return self.aprendido

    def verificar(self) -> None:
        if self.falhar:
            raise ErroComunicacaoEmissorIR("Emissor IR falso configurado para falhar")
