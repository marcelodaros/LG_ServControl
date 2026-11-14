"""Modelo da TV: decodificação do código LG, opções de linha + ano e persistência."""

import re
from dataclasses import asdict, dataclass

LINHAS = ("OLED", "QNED", "NanoCell", "UHD", "Full HD")
ANOS = tuple(range(2014, 2026))

# Letra de ano usada nos códigos das linhas LED (UHD, Full HD, NanoCell, QNED).
_ANO_POR_LETRA = {
    "B": 2014, "F": 2015, "H": 2016, "J": 2017, "K": 2018, "M": 2019,
    "N": 2020, "P": 2021, "Q": 2022, "R": 2023, "T": 2024, "A": 2025,
}
# Caractere de ano depois da série nos OLED (ex.: OLED55C1 → 2021, OLED65CX → 2020).
_ANO_OLED = {
    "6": 2016, "7": 2017, "8": 2018, "9": 2019, "X": 2020,
    "1": 2021, "2": 2022, "3": 2023, "4": 2024, "5": 2025,
}
# Letras que, no sufixo de NanoCell/QNED, vêm antes da letra de ano (ex.: 55NANO75UPA).
_PREFIXOS_SUFIXO = set("USZ")


class CodigoNaoReconhecido(ValueError):
    pass


class EscolhaInvalida(ValueError):
    pass


@dataclass(frozen=True)
class ModeloDaTV:
    linha: str
    ano: int
    codigo: str | None = None

    @property
    def descricao(self) -> str:
        return f"{self.codigo} ({self.linha}, {self.ano})" if self.codigo else f"{self.linha} {self.ano}"

    def como_json(self) -> dict:
        return {**asdict(self), "descricao": self.descricao}


def _normalizar(codigo: str) -> str:
    return re.sub(r"[\s\-./]", "", codigo or "").upper()


def _ano_do_sufixo(sufixo: str) -> int | None:
    if not sufixo:
        return None
    letra = sufixo[1] if sufixo[0] in _PREFIXOS_SUFIXO and len(sufixo) > 1 else sufixo[0]
    return _ANO_POR_LETRA.get(letra)


def decodificar(codigo: str) -> ModeloDaTV:
    """Decifra linha e ano a partir do padrão de nomes da LG."""
    c = _normalizar(codigo)

    if m := re.match(r"^OLED\d{2}[A-Z]([0-9X])", c):
        linha, ano = "OLED", _ANO_OLED.get(m.group(1))
    elif m := re.match(r"^\d{2}QNED\d{2,3}([A-Z]+)", c):
        linha, ano = "QNED", _ano_do_sufixo(m.group(1))
    elif m := re.match(r"^\d{2}NANO\d{2,3}([A-Z]+)", c):
        linha, ano = "NanoCell", _ano_do_sufixo(m.group(1))
    elif m := re.match(r"^\d{2}S([JKM])\d{4}", c):
        linha, ano = "NanoCell", _ANO_POR_LETRA.get(m.group(1))
    elif m := re.match(r"^\d{2}U([A-Z])\d{4}", c):
        linha, ano = "UHD", _ANO_POR_LETRA.get(m.group(1))
    elif m := re.match(r"^\d{2}L([A-Z])\d{3,4}", c):
        linha, ano = "Full HD", _ANO_POR_LETRA.get(m.group(1))
    else:
        linha, ano = None, None

    if linha is None or ano is None:
        raise CodigoNaoReconhecido(codigo)
    return ModeloDaTV(linha=linha, ano=ano, codigo=c)


def escolher(linha, ano) -> ModeloDaTV:
    if linha not in LINHAS or ano not in ANOS:
        raise EscolhaInvalida(f"{linha} {ano}")
    return ModeloDaTV(linha=linha, ano=ano)


class RepositorioModelo:
    """Guarda o Modelo da TV escolhido no estado do app."""

    def __init__(self, estado):
        self._estado = estado

    def atual(self) -> ModeloDaTV | None:
        dados = self._estado.ler("modelo")
        if not dados:
            return None
        return ModeloDaTV(dados["linha"], dados["ano"], dados.get("codigo"))

    def salvar(self, modelo: ModeloDaTV) -> None:
        self._estado.gravar(
            "modelo", {"linha": modelo.linha, "ano": modelo.ano, "codigo": modelo.codigo}
        )
