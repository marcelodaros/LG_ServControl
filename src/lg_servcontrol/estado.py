"""Estado do app guardado em um único arquivo JSON (Modelo da TV, Códigos IR aprendidos)."""

import json
from pathlib import Path

from lg_servcontrol.codigos_ir import CodigoIRAprendido


class EstadoPersistido:
    """Dicionário salvo em disco a cada mudança; sem caminho, fica só em memória."""

    def __init__(self, caminho: Path | None):
        self._caminho = caminho
        self._dados: dict = {}
        if caminho and caminho.exists():
            self._dados = json.loads(caminho.read_text("utf-8"))

    def ler(self, chave: str, padrao=None):
        return self._dados.get(chave, padrao)

    def gravar(self, chave: str, valor) -> None:
        self._dados[chave] = valor
        if self._caminho:
            self._caminho.write_text(
                json.dumps(self._dados, indent=2, ensure_ascii=False) + "\n", "utf-8"
            )


class RepositorioAprendidos:
    """Códigos IR aprendidos por tecla; têm precedência sobre os gerados."""

    def __init__(self, estado: EstadoPersistido):
        self._estado = estado

    def _todos(self) -> dict[str, list[int]]:
        return dict(self._estado.ler("aprendidos", {}))

    def codigo(self, tecla: str) -> CodigoIRAprendido | None:
        pulsos = self._todos().get(tecla)
        return CodigoIRAprendido(pulsos) if pulsos else None

    def teclas(self) -> set[str]:
        return set(self._todos())

    def salvar(self, tecla: str, codigo: CodigoIRAprendido) -> None:
        todos = self._todos()
        todos[tecla] = codigo.pulsos()
        self._estado.gravar("aprendidos", todos)

    def remover(self, tecla: str) -> bool:
        todos = self._todos()
        existia = todos.pop(tecla, None) is not None
        self._estado.gravar("aprendidos", todos)
        return existia
