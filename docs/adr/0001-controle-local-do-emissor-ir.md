# Controle do Emissor IR só pela rede local

O app comanda o Emissor IR (Tuya IR01) diretamente pela rede local via `tinytuya`, usando a local key extraída uma única vez pela conta de desenvolvedor Tuya, em vez de chamar a Tuya Cloud API a cada comando. Escolhemos isso pela latência menor (um controle remoto precisa ser imediato) e por funcionar sem internet, aceitando que o protocolo local não é oficialmente suportado e pode quebrar com atualizações de firmware.

## Consequences

- **Não há alternativa pela nuvem.** A Tuya Cloud API como opção manual (#8) foi descartada em 2026-11-14, depois que o controle local foi confirmado na TV real. Se uma atualização de firmware quebrar o controle local, o #8 pode ser reaberto.
- A conta de desenvolvedor Tuya só é usada uma vez, pelo script de configuração, para obter a local key.
- Todas as teclas (Comuns e de Serviço) seguem por IR; controle via rede da própria TV (webOS) foi deixado de fora.
