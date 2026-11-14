"""Códigos IR das teclas LG (protocolo NEC, endereço 0x04, 38 kHz)."""

from dataclasses import dataclass

ENDERECO_LG = 0x04

# Comandos NEC das teclas conhecidas. Cresce com os próximos tickets.
COMANDOS_LG: dict[str, int] = {
    "POWER": 0x08,
}

_CABECALHO = [9000, 4500]
_MARCA = 560
_ESPACO_0 = 560
_ESPACO_1 = 1690
# Silêncio após a marca final: fecha o quadro em pares marca/espaço, como o Emissor IR espera.
_SILENCIO_FINAL = 30000


@dataclass(frozen=True)
class CodigoIR:
    protocolo: str
    endereco: int
    comando: int

    def bytes_nec(self) -> list[int]:
        return [
            self.endereco,
            ~self.endereco & 0xFF,
            self.comando,
            ~self.comando & 0xFF,
        ]

    def pulsos(self) -> list[int]:
        """Durações em microssegundos, alternando marca e espaço."""
        pulsos = list(_CABECALHO)
        for byte in self.bytes_nec():
            for i in range(8):
                bit = (byte >> i) & 1
                pulsos += [_MARCA, _ESPACO_1 if bit else _ESPACO_0]
        pulsos += [_MARCA, _SILENCIO_FINAL]
        return pulsos


class TeclaDesconhecida(KeyError):
    pass


def codigo_da_tecla(tecla: str) -> CodigoIR:
    try:
        comando = COMANDOS_LG[tecla]
    except KeyError:
        raise TeclaDesconhecida(tecla) from None
    return CodigoIR("NEC", ENDERECO_LG, comando)
