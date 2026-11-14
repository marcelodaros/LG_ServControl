"""Catálogo de Modelos (Teclas e Senhas de Serviço) e o Modo Serviço."""

from collections.abc import Callable
from dataclasses import dataclass

from lg_servcontrol.codigos_ir import Tecla
from lg_servcontrol.modelo_tv import ModeloDaTV

DURACAO_MODO_SERVICO_S = 300

# Teclas de Serviço do Controle de Serviço da LG (NEC, endereço 0x04).
# Só entram teclas com código bem documentado. IN-STOP (que volta a TV ao estado
# de fábrica) e POWER ONLY ficam de fora até terem o código confirmado.
IN_START = Tecla("IN_START", 0xFB, "IN-START", "servico")
EZ_ADJUST = Tecla("EZ_ADJUST", 0xFF, "EZ-ADJUST", "servico")
TECLAS_DE_SERVICO: tuple[Tecla, ...] = (IN_START, EZ_ADJUST)


@dataclass(frozen=True)
class MenuDeServico:
    menu: str
    tecla: str
    senhas: tuple[str, ...]  # em ordem de tentativa


@dataclass(frozen=True)
class EntradaDoCatalogo:
    ano_inicial: int
    ano_final: int
    teclas: tuple[Tecla, ...]
    menus: tuple[MenuDeServico, ...]

    def vale_para(self, modelo: ModeloDaTV) -> bool:
        return self.ano_inicial <= modelo.ano <= self.ano_final


# Primeira versão: as mesmas teclas em todas as linhas; muda a ordem das senhas.
# 0413 é a Senha de Serviço mais citada para In-Start e EZ-Adjust na LG; algumas
# TVs webOS mais novas aceitam 0000.
CATALOGO: tuple[EntradaDoCatalogo, ...] = (
    EntradaDoCatalogo(
        2014, 2019, TECLAS_DE_SERVICO,
        (
            MenuDeServico("In-Start", "IN_START", ("0413", "0000")),
            MenuDeServico("EZ-Adjust", "EZ_ADJUST", ("0413", "0000")),
        ),
    ),
    EntradaDoCatalogo(
        2020, 2025, TECLAS_DE_SERVICO,
        (
            MenuDeServico("In-Start", "IN_START", ("0413", "0000")),
            MenuDeServico("EZ-Adjust", "EZ_ADJUST", ("0413", "0000")),
        ),
    ),
)


def entrada_para(modelo: ModeloDaTV | None) -> EntradaDoCatalogo | None:
    if modelo is None:
        return None
    return next((e for e in CATALOGO if e.vale_para(modelo)), None)


def tecla_de_servico(nome: str) -> Tecla | None:
    return next((t for t in TECLAS_DE_SERVICO if t.tecla == nome), None)


class ModoServico:
    """Estado temporário: ativo até DURACAO_MODO_SERVICO_S sem Tecla de Serviço."""

    def __init__(self, relogio: Callable[[], float]):
        self._relogio = relogio
        self._expira_em: float | None = None

    def ativo(self) -> bool:
        if self._expira_em is not None and self._relogio() >= self._expira_em:
            self._expira_em = None
        return self._expira_em is not None

    def ativar(self) -> None:
        self._expira_em = self._relogio() + DURACAO_MODO_SERVICO_S

    def desativar(self) -> None:
        self._expira_em = None

    def registrar_uso(self) -> None:
        if self.ativo():
            self.ativar()

    def segundos_restantes(self) -> int:
        if not self.ativo():
            return 0
        return max(0, round(self._expira_em - self._relogio()))
