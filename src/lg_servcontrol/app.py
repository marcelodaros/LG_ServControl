import logging
import time
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from lg_servcontrol.codigos_ir import (
    COMANDOS_LG,
    ENDERECO_LG,
    TECLAS_COMUNS,
    CodigoIR,
    TeclaDesconhecida,
    codigo_da_tecla,
)
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
from lg_servcontrol.estado import EstadoPersistido, RepositorioAprendidos
from lg_servcontrol.modo_servico import (
    TECLAS_DE_SERVICO,
    ModoServico,
    entrada_para,
    tecla_de_servico,
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


TEMPO_APRENDIZADO_S = 15


class EscolhaDoModelo(BaseModel):
    codigo: str | None = None
    linha: str | None = None
    ano: int | None = None


class CodigoDoModelo(BaseModel):
    codigo: str = ""


class AtivacaoModoServico(BaseModel):
    confirmo_risco: bool = False


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
    relogio: Callable[[], float] = time.monotonic,
) -> FastAPI:
    app = FastAPI(title="LG ServControl")
    estado = EstadoPersistido(caminho_estado)
    repositorio = RepositorioModelo(estado)
    aprendidos = RepositorioAprendidos(estado)
    modo_servico = ModoServico(relogio)

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

    def _descrever(teclas) -> list[dict]:
        com_aprendido = aprendidos.teclas()
        return [
            {"tecla": t.tecla, "rotulo": t.rotulo, "grupo": t.grupo, "aprendida": t.tecla in com_aprendido}
            for t in teclas
        ]

    @app.get("/api/teclas")
    def listar_teclas():
        return _descrever(TECLAS_COMUNS)

    @app.get("/api/teclas/aprendiveis")
    def listar_teclas_aprendiveis():
        return _descrever((*TECLAS_COMUNS, *TECLAS_DE_SERVICO))

    def _tecla_existe(tecla: str) -> bool:
        return tecla in COMANDOS_LG or tecla_de_servico(tecla) is not None

    def _tecla_desconhecida(tecla: str) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"erro": "tecla_desconhecida", "mensagem": f"Tecla desconhecida: {tecla}"},
        )

    @app.post("/api/teclas/{tecla}/aprender")
    def aprender_tecla(tecla: str):
        if not _tecla_existe(tecla):
            return _tecla_desconhecida(tecla)
        if emissor is None:
            return _nao_configurado()
        try:
            codigo = emissor.aprender(TEMPO_APRENDIZADO_S)
        except ErroComunicacaoEmissorIR as erro:
            return JSONResponse(
                status_code=502,
                content={
                    "erro": "comunicacao_emissor_ir",
                    "mensagem": f"Falha ao falar com o Emissor IR: {erro}",
                },
            )
        if codigo is None:
            return JSONResponse(
                status_code=408,
                content={
                    "erro": "aprendizado_expirou",
                    "mensagem": f"Nenhum sinal recebido em {TEMPO_APRENDIZADO_S} s. Tente de novo.",
                },
            )
        aprendidos.salvar(tecla, codigo)
        return {"status": "aprendido", "tecla": tecla}

    @app.delete("/api/teclas/{tecla}/aprendido")
    def desfazer_aprendizado(tecla: str):
        if not _tecla_existe(tecla):
            return _tecla_desconhecida(tecla)
        aprendidos.remover(tecla)
        return {"status": "restaurado", "tecla": tecla}

    def _estado_modo_servico() -> dict:
        ativo = modo_servico.ativo()
        entrada = entrada_para(repositorio.atual()) if ativo else None
        return {
            "ativo": ativo,
            "segundos_restantes": modo_servico.segundos_restantes(),
            "teclas": [{"tecla": t.tecla, "rotulo": t.rotulo} for t in entrada.teclas] if entrada else [],
            "menus": (
                [{"menu": m.menu, "tecla": m.tecla, "senhas": list(m.senhas)} for m in entrada.menus]
                if entrada else []
            ),
        }

    @app.get("/api/modo-servico")
    def consultar_modo_servico():
        return _estado_modo_servico()

    @app.post("/api/modo-servico/ativar")
    def ativar_modo_servico(pedido: AtivacaoModoServico):
        if not pedido.confirmo_risco:
            return JSONResponse(
                status_code=422,
                content={
                    "erro": "confirmacao_necessaria",
                    "mensagem": "Confirme que entende o risco de alterar configurações de fábrica.",
                },
            )
        if entrada_para(repositorio.atual()) is None:
            return JSONResponse(
                status_code=409,
                content={"erro": "modelo_nao_escolhido", "mensagem": "Escolha o Modelo da TV primeiro."},
            )
        modo_servico.ativar()
        return _estado_modo_servico()

    @app.post("/api/modo-servico/desativar")
    def desativar_modo_servico():
        modo_servico.desativar()
        return _estado_modo_servico()

    def _enviar(codigo) -> JSONResponse | None:
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
        return None

    @app.post("/api/teclas/{tecla}/enviar")
    def enviar_tecla(tecla: str):
        servico = tecla_de_servico(tecla)
        if servico is not None:
            entrada = entrada_para(repositorio.atual())
            if not modo_servico.ativo():
                return JSONResponse(
                    status_code=403,
                    content={
                        "erro": "modo_servico_inativo",
                        "mensagem": "Ative o Modo Serviço para usar as Teclas de Serviço.",
                    },
                )
            if entrada is None or servico not in entrada.teclas:
                return JSONResponse(
                    status_code=403,
                    content={
                        "erro": "tecla_nao_aplicavel",
                        "mensagem": f"{servico.rotulo} não se aplica ao Modelo da TV escolhido.",
                    },
                )
            falha = _enviar(
                aprendidos.codigo(tecla) or CodigoIR("NEC", ENDERECO_LG, servico.comando)
            )
            if falha:
                return falha
            modo_servico.registrar_uso()
            return {"status": "enviado", "modo_servico": _estado_modo_servico()}

        try:
            codigo = aprendidos.codigo(tecla) or codigo_da_tecla(tecla)
        except TeclaDesconhecida:
            return _tecla_desconhecida(tecla)
        return _enviar(codigo) or {"status": "enviado"}

    return app
