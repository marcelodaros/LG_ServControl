"""Configuração inicial do Emissor IR (Tuya IR01) — rodar uma única vez.

    python -m lg_servcontrol.configurar

Descobre device ID, local key, IP, versão do protocolo e tipo de controle do IR01,
grava `emissor_ir.json` e faz um envio de teste da tecla POWER.
"""

import json
import subprocess
import sys
from pathlib import Path

from lg_servcontrol.codigos_ir import codigo_da_tecla
from lg_servcontrol.configuracao import CAMINHO_PADRAO, ConfiguracaoEmissorIR
from lg_servcontrol.emissor_ir import ErroComunicacaoEmissorIR

DEVICES_JSON = Path("devices.json")
CATEGORIA_CONTROLE_IR = "wnykq"  # categoria Tuya de controle remoto universal IR

INSTRUCOES_TUYA = """
Para obter a local key do IR01 é preciso uma conta de desenvolvedor Tuya (gratuita):

  1. Garanta que o IR01 já está pareado no app Smart Life (ou Tuya Smart) e funcionando.
  2. Crie uma conta em https://platform.tuya.com e entre.
  3. Cloud › Development › Create Cloud Project:
       - Development Method: Smart Home
       - Data Center: o mesmo da sua conta do app (no Brasil, normalmente "Western America")
  4. No projeto: Devices › Link App Account › Add App Account, e escaneie o QR code
     pelo app Smart Life (Eu › ícone de leitura no canto superior).
  5. Em Overview, copie o Access ID e o Access Secret.

Em seguida vou rodar o assistente da tinytuya (`python -m tinytuya wizard`). Ele pede o
Access ID, o Access Secret e a região, e gera o arquivo devices.json com as local keys.
Responda "Y" quando ele perguntar se deve procurar os dispositivos na rede local.
"""


def perguntar(texto: str, padrao: str | None = None) -> str:
    sufixo = f" [{padrao}]" if padrao else ""
    resposta = input(f"{texto}{sufixo}: ").strip()
    return resposta or (padrao or "")


def sim(texto: str, padrao: bool = True) -> bool:
    resposta = perguntar(f"{texto} (s/n)", "s" if padrao else "n").lower()
    return resposta.startswith("s")


def passo(titulo: str) -> None:
    print(f"\n=== {titulo} ===")


def obter_devices_json() -> list[dict]:
    if DEVICES_JSON.exists() and sim(f"Encontrei {DEVICES_JSON}. Usar esse arquivo?"):
        return json.loads(DEVICES_JSON.read_text("utf-8"))
    print(INSTRUCOES_TUYA)
    input("Pressione Enter quando tiver o Access ID e o Access Secret em mãos…")
    subprocess.run([sys.executable, "-m", "tinytuya", "wizard"], check=False)
    if not DEVICES_JSON.exists():
        sys.exit(f"O assistente não gerou {DEVICES_JSON}. Revise os passos acima e tente de novo.")
    return json.loads(DEVICES_JSON.read_text("utf-8"))


def escolher_dispositivo(dispositivos: list[dict]) -> dict:
    if not dispositivos:
        sys.exit("Nenhum dispositivo na conta Tuya. O IR01 está pareado no app Smart Life?")
    for i, d in enumerate(dispositivos, 1):
        marca = "  ← controle IR" if d.get("category") == CATEGORIA_CONTROLE_IR else ""
        print(f"  {i}. {d.get('name') or '(sem nome)'} — {d.get('id')}{marca}")
    sugestao = next(
        (i for i, d in enumerate(dispositivos, 1) if d.get("category") == CATEGORIA_CONTROLE_IR), 1
    )
    while True:
        escolha = perguntar("Número do Emissor IR (IR01)", str(sugestao))
        if escolha.isdigit() and 1 <= int(escolha) <= len(dispositivos):
            return dispositivos[int(escolha) - 1]
        print("Escolha um número da lista.")


VERSOES_PROTOCOLO = (3.3, 3.4, 3.5)


def detectar_versao(dev_id: str, ip: str, local_key: str) -> float | None:
    """Descobre a versão do protocolo Tuya do IR01.

    3.4 e 3.5 fazem um handshake que confirma a chave, então são testadas primeiro.
    Na 3.3 um emissor IR costuma não devolver estado nenhum (resposta vazia), o que
    não distingue chave certa de errada: se a conexão abre sem erro, aceita 3.3 e o
    envio de teste do POWER confirma.
    """
    import tinytuya

    def consultar(versao: float):
        dispositivo = tinytuya.Device(
            dev_id, ip, local_key, version=versao, connection_timeout=3, connection_retry_limit=1
        )
        try:
            return dispositivo.status()
        finally:
            dispositivo.close()

    for versao in (3.5, 3.4):
        resultado = consultar(versao)
        if isinstance(resultado, dict) and "Error" not in resultado:
            return versao

    resultado = consultar(3.3)
    if not (isinstance(resultado, dict) and "Error" in resultado):
        return 3.3
    return None


def localizar_na_rede(dispositivo: dict) -> tuple[str, float]:
    import tinytuya

    ip = dispositivo.get("ip") or ""
    versao = dispositivo.get("version") or ""
    if not ip:
        print("Procurando o IR01 na rede local (pode levar alguns segundos)…")
        achado = tinytuya.find_device(dispositivo["id"])
        ip = achado.get("ip") or ""
        versao = versao or (achado.get("version") or "")
    if not ip:
        print("Não encontrei o IP automaticamente (o roteador pode bloquear os anúncios).")
        print("Veja o IP do IR01 na lista de clientes do roteador.")
        ip = perguntar("IP do IR01")
    if not versao:
        print("Testando as versões do protocolo Tuya…")
        versao = detectar_versao(dispositivo["id"], ip, dispositivo["key"])
        if versao is None:
            sys.exit(
                f"O IR01 em {ip} não respondeu em nenhuma versão {VERSOES_PROTOCOLO}. "
                "Confira o IP e se a local key é a atual (ela muda quando o aparelho é pareado de novo)."
            )
    return ip, float(versao)


def detectar_tipo_controle(dev_id: str, ip: str, local_key: str, versao: float) -> int:
    from tinytuya.Contrib.IRRemoteControlDevice import IRRemoteControlDevice

    print("Detectando o tipo de controle do IR01…")
    dispositivo = IRRemoteControlDevice(
        dev_id=dev_id, address=ip, local_key=local_key, version=versao, connection_timeout=5
    )
    if dispositivo.control_type in (1, 2):
        return dispositivo.control_type
    print("Não consegui detectar. 1 = aparelhos mais antigos (DPS 201/202), 2 = mais novos (DPS 1-13).")
    return int(perguntar("Tipo de controle", "1"))


def testar(config: ConfiguracaoEmissorIR) -> bool:
    from lg_servcontrol.emissor_local import EmissorIRLocal

    emissor = EmissorIRLocal(config)
    try:
        emissor.verificar()
    except ErroComunicacaoEmissorIR as erro:
        print(f"✗ O IR01 não respondeu: {erro}")
        return False
    print("✓ O IR01 respondeu pela rede local.")
    input("Aponte o IR01 para a TV e pressione Enter para enviar POWER…")
    try:
        emissor.enviar(codigo_da_tecla("POWER"))
    except ErroComunicacaoEmissorIR as erro:
        print(f"✗ Falha ao enviar: {erro}")
        return False
    return sim("A TV ligou ou desligou?")


def main() -> None:
    print("Configuração do Emissor IR — LG ServControl")

    passo("1/4 Conta Tuya e local key")
    dispositivo = escolher_dispositivo(obter_devices_json())
    if not dispositivo.get("key"):
        sys.exit("Esse dispositivo veio sem local key no devices.json. Rode o assistente de novo.")

    passo("2/4 Localizando o IR01 na rede")
    ip, versao = localizar_na_rede(dispositivo)
    print(f"IP {ip}, protocolo {versao}")

    passo("3/4 Tipo de controle")
    tipo = detectar_tipo_controle(dispositivo["id"], ip, dispositivo["key"], versao)

    config = ConfiguracaoEmissorIR(
        modo="local",
        device_id=dispositivo["id"],
        ip=ip,
        local_key=dispositivo["key"],
        versao=versao,
        tipo_controle=tipo,
    )
    config.gravar(CAMINHO_PADRAO)
    print(f"Configuração gravada em {CAMINHO_PADRAO} (fora do git).")

    passo("4/4 Teste")
    if testar(config):
        print("\nTudo certo! Suba o app com: .venv/bin/python -m lg_servcontrol")
    else:
        print(
            "\nO teste não passou. Confira se o IR01 e o Mac estão na mesma rede Wi‑Fi e se o IP"
            " não mudou. Se o firmware recusar controle local, veja o ADR 0001 (o #8 pode ser reaberto)."
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
