import logging
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from lg_servcontrol.codigos_ir import TECLAS_COMUNS, TeclaDesconhecida, codigo_da_tecla
from lg_servcontrol.configuracao import ConfiguracaoEmissorIR, ConfiguracaoInvalida, carregar
from lg_servcontrol.emissor_ir import EmissorIR, ErroComunicacaoEmissorIR

log = logging.getLogger("lg_servcontrol")


def montar_app(
    caminho_config: Path,
    fabrica_emissor: Callable[[ConfiguracaoEmissorIR], EmissorIR],
) -> FastAPI:
    """Lê a configuração do Emissor IR e monta o app; configuração ruim não impede a subida."""
    try:
        config = carregar(caminho_config)
    except ConfiguracaoInvalida as erro:
        log.warning("Emissor IR não configurado: %s", erro)
        return create_app(emissor=None, problema_configuracao=str(erro))
    return create_app(emissor=fabrica_emissor(config))


def create_app(emissor: EmissorIR | None, problema_configuracao: str | None = None) -> FastAPI:
    app = FastAPI(title="LG ServControl")

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
