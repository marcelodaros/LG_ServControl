"""Emissor IR real: Tuya IR01 controlado pela rede local via tinytuya (ADR 0001)."""

from tinytuya.Contrib.IRRemoteControlDevice import IRRemoteControlDevice

from lg_servcontrol.codigos_ir import CodigoIR
from lg_servcontrol.configuracao import ConfiguracaoEmissorIR
from lg_servcontrol.emissor_ir import ErroComunicacaoEmissorIR

TIMEOUT_CONEXAO_S = 3


class _DispositivoIR(IRRemoteControlDevice):
    """IRRemoteControlDevice que guarda o resultado do último envio.

    `send_button` descarta o retorno de `set_value`; sem isso não dá para saber
    se a conexão com o IR01 falhou.
    """

    ultimo_resultado = None

    def set_value(self, *args, **kwargs):
        self.ultimo_resultado = super().set_value(*args, **kwargs)
        return self.ultimo_resultado

    def set_multiple_values(self, *args, **kwargs):
        self.ultimo_resultado = super().set_multiple_values(*args, **kwargs)
        return self.ultimo_resultado


def _falhou(resultado) -> str | None:
    if isinstance(resultado, dict) and "Error" in resultado:
        return f"{resultado.get('Error')} (código {resultado.get('Err')})"
    return None


class EmissorIRLocal:
    def __init__(self, config: ConfiguracaoEmissorIR):
        self._dispositivo = _DispositivoIR(
            dev_id=config.device_id,
            address=config.ip,
            local_key=config.local_key,
            version=config.versao,
            control_type=config.tipo_controle,
            connection_timeout=TIMEOUT_CONEXAO_S,
            connection_retry_limit=1,
        )

    def enviar(self, codigo: CodigoIR) -> None:
        base64 = IRRemoteControlDevice.pulses_to_base64(codigo.pulsos())
        self._dispositivo.ultimo_resultado = None
        try:
            self._dispositivo.send_button(base64)
        except OSError as erro:
            raise ErroComunicacaoEmissorIR(str(erro)) from erro
        problema = _falhou(self._dispositivo.ultimo_resultado)
        if problema:
            raise ErroComunicacaoEmissorIR(problema)

    def aprender(self, timeout_s: float) -> CodigoIR | None:
        try:
            resposta = self._dispositivo.receive_button(timeout=timeout_s)
        except OSError as erro:
            raise ErroComunicacaoEmissorIR(str(erro)) from erro
        problema = _falhou(resposta)
        if problema:
            raise ErroComunicacaoEmissorIR(problema)
        if not isinstance(resposta, str):
            return None
        pulsos = IRRemoteControlDevice.base64_to_pulses(resposta)
        for nec in IRRemoteControlDevice.pulses_to_nec(pulsos):
            if nec["address"] is not None and nec["address"] < 256:
                return CodigoIR("NEC", nec["address"], nec["data"])
        return None

    def verificar(self) -> None:
        try:
            resultado = self._dispositivo.status()
        except OSError as erro:
            raise ErroComunicacaoEmissorIR(str(erro)) from erro
        problema = _falhou(resultado)
        if problema:
            raise ErroComunicacaoEmissorIR(problema)
