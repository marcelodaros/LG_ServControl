"""Emissor IR real: Tuya IR01 controlado pela rede local via tinytuya (ADR 0001)."""

import logging
import time

from tinytuya.Contrib.IRRemoteControlDevice import IRRemoteControlDevice

from lg_servcontrol.codigos_ir import CodigoIR, CodigoIRAprendido
from lg_servcontrol.configuracao import ConfiguracaoEmissorIR
from lg_servcontrol.emissor_ir import ErroComunicacaoEmissorIR

TIMEOUT_CONEXAO_S = 3
log = logging.getLogger("lg_servcontrol")


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


# Erros da tinytuya que significam "não deu para falar com o IR01": falha de conexão,
# timeout, inalcançável, chave ou versão erradas. Outros (ex.: 900, resposta que não é
# JSON) mostram que o IR01 respondeu — emissores IR não têm estado para informar.
_ERROS_DE_CONEXAO = {"901", "902", "905", "914"}


def _sem_conexao(resultado) -> str | None:
    if isinstance(resultado, dict) and str(resultado.get("Err")) in _ERROS_DE_CONEXAO:
        return _falhou(resultado)
    return None


def _codigo_aprendido(valor) -> CodigoIRAprendido | None:
    """Converte o base64 reportado pelo IR01; None se vazio ou só zeros."""
    if not isinstance(valor, str) or not valor:
        return None
    try:
        pulsos = IRRemoteControlDevice.base64_to_pulses(valor)
    except Exception:
        return None
    if not pulsos or not any(pulsos) or len(pulsos) < 4:
        return None
    return CodigoIRAprendido(pulsos)


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

    def enviar(self, codigo: CodigoIR | CodigoIRAprendido) -> None:
        base64 = IRRemoteControlDevice.pulses_to_base64(codigo.pulsos())
        self._dispositivo.ultimo_resultado = None
        try:
            self._dispositivo.send_button(base64)
        except OSError as erro:
            raise ErroComunicacaoEmissorIR(str(erro)) from erro
        problema = _falhou(self._dispositivo.ultimo_resultado)
        if problema:
            raise ErroComunicacaoEmissorIR(problema)

    def aprender(self, timeout_s: float) -> CodigoIRAprendido | None:
        """Põe o IR01 em modo de aprendizado e espera o código chegar (DPS 202 ou 2).

        Não usa o `receive_button` da tinytuya: sem socket persistente a conexão
        fecha logo após o comando de estudo e o código, que chega segundos depois,
        se perde. O IR01 também pode reportar um código vazio (só zeros), que é
        ignorado enquanto houver tempo.
        """
        dispositivo = self._dispositivo
        dispositivo.set_socketPersistent(True)
        dispositivo.set_socketTimeout(1)
        try:
            dispositivo.study_end()
            dispositivo.study_start()
            fim = time.monotonic() + timeout_s
            while time.monotonic() < fim:
                resposta = dispositivo._send_receive(None)
                if resposta is None:
                    continue
                problema = _sem_conexao(resposta)
                if problema:
                    raise ErroComunicacaoEmissorIR(problema)
                dps = resposta.get("dps", {}) if isinstance(resposta, dict) else {}
                log.info("Aprendizado: IR01 reportou %s", {k: str(v)[:40] for k, v in dps.items()} or resposta)
                for dp in (IRRemoteControlDevice.DP_LEARNED_ID, IRRemoteControlDevice.DP_LEARNED_REPORT):
                    codigo = _codigo_aprendido(dps.get(dp))
                    if codigo:
                        return codigo
            return None
        except OSError as erro:
            raise ErroComunicacaoEmissorIR(str(erro)) from erro
        finally:
            try:
                dispositivo.study_end()
            except OSError:
                pass
            dispositivo.set_socketTimeout(TIMEOUT_CONEXAO_S)
            dispositivo.set_socketPersistent(False)

    def verificar(self) -> None:
        try:
            resultado = self._dispositivo.status()
        except OSError as erro:
            raise ErroComunicacaoEmissorIR(str(erro)) from erro
        problema = _sem_conexao(resultado)
        if problema:
            raise ErroComunicacaoEmissorIR(problema)
