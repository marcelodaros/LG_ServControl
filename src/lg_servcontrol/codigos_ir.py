"""Códigos IR das teclas LG (protocolo NEC, endereço 0x04, 38 kHz)."""

from dataclasses import dataclass

ENDERECO_LG = 0x04

@dataclass(frozen=True)
class Tecla:
    tecla: str
    comando: int
    rotulo: str
    grupo: str


# Teclas Comuns do controle LG convencional (comando NEC, endereço 0x04).
TECLAS_COMUNS: tuple[Tecla, ...] = (
    Tecla("POWER", 0x08, "Ligar/desligar", "topo"),
    Tecla("INPUT", 0x0B, "Entrada", "topo"),
    *(Tecla(str(n), 0x10 + n, str(n), "numeros") for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0)),
    Tecla("VOL_MAIS", 0x02, "Volume +", "volume"),
    Tecla("VOL_MENOS", 0x03, "Volume −", "volume"),
    Tecla("MUDO", 0x09, "Mudo", "volume"),
    Tecla("CANAL_MAIS", 0x00, "Canal +", "canal"),
    Tecla("CANAL_MENOS", 0x01, "Canal −", "canal"),
    Tecla("HOME", 0x7C, "Home", "atalhos"),
    Tecla("CONFIGURACOES", 0x43, "Configurações", "atalhos"),
    Tecla("GUIA", 0xAB, "Guia", "atalhos"),
    Tecla("INFO", 0xAA, "Info", "atalhos"),
    Tecla("CIMA", 0x40, "Cima", "navegacao"),
    Tecla("BAIXO", 0x41, "Baixo", "navegacao"),
    Tecla("ESQUERDA", 0x07, "Esquerda", "navegacao"),
    Tecla("DIREITA", 0x06, "Direita", "navegacao"),
    Tecla("OK", 0x44, "OK", "navegacao"),
    Tecla("VOLTAR", 0x28, "Voltar", "navegacao"),
    Tecla("RETROCEDER", 0x8F, "Retroceder", "midia"),
    Tecla("PLAY", 0xB0, "Play", "midia"),
    Tecla("PAUSA", 0xBA, "Pausa", "midia"),
    Tecla("PARAR", 0xB1, "Parar", "midia"),
    Tecla("AVANCAR", 0x8E, "Avançar", "midia"),
)

COMANDOS_LG: dict[str, int] = {t.tecla: t.comando for t in TECLAS_COMUNS}

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


@dataclass(frozen=True)
class CodigoIRAprendido:
    """Código IR capturado de um controle real, guardado como o sinal bruto."""

    pulsos_brutos: tuple[int, ...]
    protocolo: str = "aprendido"

    def __init__(self, pulsos):
        object.__setattr__(self, "pulsos_brutos", tuple(int(p) for p in pulsos))
        object.__setattr__(self, "protocolo", "aprendido")

    def pulsos(self) -> list[int]:
        return list(self.pulsos_brutos)


class TeclaDesconhecida(KeyError):
    pass


def codigo_da_tecla(tecla: str) -> CodigoIR:
    try:
        comando = COMANDOS_LG[tecla]
    except KeyError:
        raise TeclaDesconhecida(tecla) from None
    return CodigoIR("NEC", ENDERECO_LG, comando)
