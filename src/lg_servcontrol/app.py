import logging
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from lg_servcontrol.codigos_ir import TECLAS_COMUNS, TeclaDesconhecida, codigo_da_tecla
from lg_servcontrol.configuracao import ConfiguracaoEmissorIR, ConfiguracaoInvalida, carregar
from lg_servcontrol.emissor_ir import EmissorIR, ErroComunicacaoEmissorIR
from lg_servcontrol.modelo_tv import (
    ANOS,
    LINHAS,
    CodigoNaoReconhecido,
    EscolhaInvalida,
    RepositorioModelo,
    decodificar,
    escolher,
)

log = logging.getLogger("lg_servcontrol")


def montar_app(
    caminho_config: Path,
    fabrica_emissor: Callable[[ConfiguracaoEmissorIR], EmissorIR],
    caminho_estado: Path | None = None,
) -> FastAPI:
    """Lê a configuração do Emissor IR e monta o app; configuração ruim não impede a subida."""
    try:
        config = carregar(caminho_config)
    except ConfiguracaoInvalida as erro:
        log.warning("Emissor IR não configurado: %s", erro)
        return create_app(
            emissor=None, problema_configuracao=str(erro), caminho_estado=caminho_estado
        )
    return create_app(emissor=fabrica_emissor(config), caminho_estado=caminho_estado)


class EscolhaDoModelo(BaseModel):
    codigo: str | None = None
    linha: str | None = None
    ano: int | None = None


class CodigoDoModelo(BaseModel):
    codigo: str = ""


def _codigo_nao_reconhecido(codigo: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "erro": "codigo_nao_reconhecido",
            "mensagem": f"Não reconheci o código '{codigo}'. Escolha a linha e o ano na lista.",
        },
    )


def create_app(
    emissor: EmissorIR | None,
    problema_configuracao: str | None = None,
    caminho_estado: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="LG ServControl")
    repositorio = RepositorioModelo(caminho_estado)

    @app.get("/api/modelo")
    def modelo_atual():
        modelo = repositorio.atual()
        return {"modelo": modelo.como_json() if modelo else None}

    @app.get("/api/modelo/opcoes")
    def opcoes_de_modelo():
        return {"linhas": list(LINHAS), "anos": list(ANOS)}

    @app.post("/api/modelo/decodificar")
    def decodificar_modelo(pedido: CodigoDoModelo):
        try:
            return decodificar(pedido.codigo).como_json()
        except CodigoNaoReconhecido:
            return _codigo_nao_reconhecido(pedido.codigo)

    @app.put("/api/modelo")
    def salvar_modelo(escolha: EscolhaDoModelo):
        try:
            if escolha.codigo:
                modelo = decodificar(escolha.codigo)
            else:
                modelo = escolher(escolha.linha, escolha.ano)
        except CodigoNaoReconhecido:
            return _codigo_nao_reconhecido(escolha.codigo)
        except EscolhaInvalida:
            return JSONResponse(
                status_code=422,
                content={"erro": "escolha_invalida", "mensagem": "Escolha uma linha e um ano da lista."},
            )
        repositorio.salvar(modelo)
        return {"modelo": modelo.como_json()}

    def _nao_configurado() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"erro": "emissor_ir_nao_configurado", "mensagem": problema_configuracao},
        )

    @app.get("/", response_class=HTMLResponse)
    def pagina() -> str:
        return resources.files("lg_servcontrol").joinpath("static/index.html").read_text("utf-8")

    @app.get("/api/emissor/estado")
    def estado_emissor():
        if emissor is None:
            return {"estado": "nao_configurado", "mensagem": problema_configuracao}
        try:
            emissor.verificar()
        except ErroComunicacaoEmissorIR as erro:
            return {"estado": "desconectado", "mensagem": f"O Emissor IR não respondeu: {erro}"}
        return {"estado": "conectado", "mensagem": "Emissor IR respondendo"}

    @app.get("/api/teclas")
    def listar_teclas():
        return [
            {"tecla": t.tecla, "rotulo": t.rotulo, "grupo": t.grupo} for t in TECLAS_COMUNS
        ]

    @app.post("/api/teclas/{tecla}/enviar")
    def enviar_tecla(tecla: str):
        try:
            codigo = codigo_da_tecla(tecla)
        except TeclaDesconhecida:
            return JSONResponse(
                status_code=404,
                content={"erro": "tecla_desconhecida", "mensagem": f"Tecla desconhecida: {tecla}"},
            )
        if emissor is None:
            return _nao_configurado()
        try:
            emissor.enviar(codigo)
        except ErroComunicacaoEmissorIR as erro:
            return JSONResponse(
                status_code=502,
                content={
                    "erro": "comunicacao_emissor_ir",
                    "mensagem": f"Falha ao falar com o Emissor IR: {erro}",
                },
            )
        return {"status": "enviado"}

    return app
