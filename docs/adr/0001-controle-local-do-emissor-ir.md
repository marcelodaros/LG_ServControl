# Controle do Emissor IR pela rede local, com nuvem Tuya como alternativa manual

O app comanda o Emissor IR (Tuya IR01) diretamente pela rede local via `tinytuya`, usando a local key extraída uma única vez pela conta de desenvolvedor Tuya, em vez de chamar a Tuya Cloud API a cada comando. Escolhemos isso pela latência menor (um controle remoto precisa ser imediato) e por funcionar sem internet, aceitando que o protocolo local não é oficialmente suportado e pode quebrar com atualizações de firmware.

## Consequences

- Se o firmware do IR01 recusar comandos locais, a troca para a Tuya Cloud API é feita **manualmente** no arquivo de configuração. Não há fallback automático, para não mascarar falhas nem enviar o mesmo Código IR duas vezes.
- Todas as teclas (Comuns e de Serviço) seguem por IR; controle via rede da própria TV (webOS) foi deixado de fora.
