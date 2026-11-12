from importlib import resources

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from lg_servcontrol.codigos_ir import TeclaDesconhecida, codigo_da_tecla
from lg_servcontrol.emissor_ir import EmissorIR, ErroComunicacaoEmissorIR


def create_app(emissor: EmissorIR) -> FastAPI:
    app = FastAPI(title="LG ServControl")

    @app.get("/", response_class=HTMLResponse)
    def pagina() -> str:
        return resources.files("lg_servcontrol").joinpath("static/index.html").read_text("utf-8")

    @app.post("/api/teclas/{tecla}/enviar")
    def enviar_tecla(tecla: str):
        try:
            codigo = codigo_da_tecla(tecla)
        except TeclaDesconhecida:
            return JSONResponse(
                status_code=404,
                content={"erro": "tecla_desconhecida", "mensagem": f"Tecla desconhecida: {tecla}"},
            )
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
