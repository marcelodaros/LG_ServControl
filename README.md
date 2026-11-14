# LG ServControl

Controle remoto da LG no navegador do celular, com as teclas comuns **e as Teclas de Serviço** (IN-START, EZ-ADJUST) do controle de fábrica que os técnicos usam. O app roda no seu computador e envia os comandos à TV por um **emissor infravermelho Wi‑Fi da Tuya**, pela rede de casa, sem passar pela nuvem.

> ⚠️ **Os Menus de Serviço alteram configurações de fábrica da TV** (região, painel, modo hotel e outras). Um ajuste errado pode deixar a TV inutilizável. Anote os valores antes de mudar qualquer coisa e só altere o que você conhece. Você usa por sua conta e risco.

## O que o app faz

- **Controle completo**: ligar, entrada, números, volume, mudo, canais, home, configurações, voltar, guia, info, direcional com OK e mídia.
- **Modelo da TV**: você digita o código do modelo (ex.: `OLED55C1PSA`) ou escolhe linha + ano.
- **Modo Serviço**: libera IN-START e EZ-ADJUST depois de uma confirmação, mostra a senha de cada menu e desliga sozinho após 5 minutos sem uso.
- **Reaprender tecla**: se alguma tecla não funcionar na sua TV, o emissor copia o sinal de um controle infravermelho de verdade.

## O que você precisa

### Hardware recomendado

**Emissor IR Wi‑Fi Tuya IR01** ("Controle Inteligente Infravermelho Smart Home Wi‑Fi Tuya IR01"), vendido por exemplo na [KaBuM!](https://www.kabum.com.br/produto/1056447). É o aparelho usado no desenvolvimento e testado com uma LG OLED55C1PSA (2021).

- Wi‑Fi **2,4 GHz**, infravermelho 38 kHz, alcance de até 10 m.
- Alimentação por USB‑C (5 V, 1 A). Qualquer carregador de celular serve.
- Outros emissores IR Tuya (categoria "controle remoto universal", `wnykq`) provavelmente funcionam, mas não foram testados.

Também é preciso:

- Uma **TV LG** com receptor infravermelho (praticamente todas).
- Um **computador** (macOS, Linux ou Windows) com **Python 3.11 ou mais novo**, ligado na mesma rede de casa que o emissor. Ele precisa ficar ligado enquanto você usa o app.
- Um **celular** com o app **Smart Life** (Android ou iOS).
- Uma conta gratuita na **plataforma de desenvolvedor da Tuya**, usada **uma única vez** para obter a chave local do emissor.

## Passo a passo

### 1. Pareie o emissor no Smart Life

1. Ligue o IR01 na tomada e instale o app **Smart Life**.
2. No app, toque em **+ › Adicionar dispositivo** e siga o pareamento na sua rede Wi‑Fi **2,4 GHz**.
3. Teste: crie um controle de TV LG no app e veja se ele liga a TV. Assim você sabe que o emissor está bem posicionado.

> Use o **Smart Life** (ou o **Tuya Smart**). Apps de outras marcas com o mesmo aparelho, como o "KaBuM! Smart", **não** conseguem ser vinculados à plataforma de desenvolvedor no passo 4. Se o emissor estiver em outro app, remova de lá e pareie de novo pelo Smart Life.

### 2. Baixe o projeto e instale

```bash
git clone https://github.com/marcelodaros/LG_ServControl.git
cd LG_ServControl
python3 -m venv .venv
```

macOS e Linux:

```bash
.venv/bin/pip install -e .
```

Windows (PowerShell):

```powershell
.venv\Scripts\pip install -e .
```

> Confira a versão com `python3 --version`. Se for menor que 3.11, instale uma mais nova (no macOS, por exemplo, `brew install python@3.13` e use `python3.13 -m venv .venv`).

Nos comandos a seguir, troque `.venv/bin/python` por `.venv\Scripts\python` no Windows.

### 3. Crie o projeto na plataforma de desenvolvedor da Tuya

1. Crie uma conta em **https://platform.tuya.com** e entre.
2. Vá em **Cloud › Development › Create Cloud Project**:
   - **Development Method**: Smart Home
   - **Data Center**: o mesmo da sua conta do Smart Life. No Brasil, normalmente **Western America**.
3. Ative o serviço **IoT Core** (plano **Trial Edition**, gratuito): **Cloud › Cloud Services › IoT Core**. Depois confira em **Service API**, no projeto, se ele está autorizado.
4. No projeto, abra **Devices › Link App Account › Add App Account** e leia o QR code pelo Smart Life (aba **Eu**, ícone de leitura no canto superior).
5. Em **Overview**, anote o **Access ID** e o **Access Secret**.

### 4. Configure o emissor (uma vez)

```bash
.venv/bin/python -m lg_servcontrol.configurar
```

O script guia cada etapa:

1. Roda o assistente da `tinytuya`, que pede:
   - **API Key**: o **Access ID**
   - **API Secret**: o **Access Secret**
   - **Device ID**: o ID de qualquer aparelho da conta (aparece em **Devices › All Devices** no projeto), ou `scan`
   - **Região**: `us` para Western America
2. Lista seus aparelhos com o emissor IR já pré-selecionado.
3. Procura o emissor na rede. Se não achar, ele pede o IP: veja o IP do emissor na lista de aparelhos conectados do seu roteador.
4. Descobre a versão do protocolo e o tipo de controle.
5. Grava a configuração em `emissor_ir.json` e envia um **POWER de teste**. Aponte o emissor para a TV: ela deve ligar ou desligar.

### 5. Suba o app

```bash
.venv/bin/python -m lg_servcontrol
```

No celular, ligado à mesma rede, abra `http://IP-DO-COMPUTADOR:8000`. Para descobrir o IP do computador:

- macOS: `ipconfig getifaddr en0`
- Linux: `hostname -I`
- Windows: `ipconfig` (campo "Endereço IPv4")

> Dica: no celular, use "Adicionar à tela de início" para abrir o controle como um app.

### 6. Use

1. **Escolha o modelo da TV** na primeira abertura. O código fica na etiqueta atrás da TV ou em **Configurações › Suporte › Informações da TV**. Se o código não for reconhecido, escolha linha + ano na lista.
2. **Controle a TV** pelas teclas da tela.
3. **Modo Serviço**: toque em **MODO SERVIÇO** no fim do controle, leia o aviso e confirme. O painel vermelho mostra IN-START, EZ-ADJUST e a senha de cada menu (normalmente **0413**). Digite a senha pelos números do app.
4. **Ajustes** (link no topo): troque o modelo e reaprenda teclas. Para reaprender, use um **controle infravermelho**. O **Magic Remote** (o controle com ponteiro das LG mais novas) envia por Bluetooth e não serve.

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| A tela mostra "Emissor IR não configurado" | Rode o passo 4. O arquivo `emissor_ir.json` precisa estar na pasta de onde você sobe o app. |
| "Device Unreachable" ou "O Emissor IR não respondeu" | Confira se o IP do emissor mudou (fixe o IP no roteador) e se o computador alcança o emissor (`ping IP-DO-EMISSOR`). |
| O script não acha o emissor na rede | Roteadores com isolamento de clientes Wi‑Fi (ex.: UniFi, redes de convidados) bloqueiam a descoberta. Digite o IP quando o script pedir. Se nem o `ping` responder, desligue o isolamento ou ligue o computador numa rede que alcance o emissor pelo roteador. |
| Erro `28841002 IoT Core service subscription has expired` | Assine ou renove o IoT Core (Trial) na plataforma Tuya (passo 3.3) e rode o script de novo. |
| `iot.tuya.com` não abre | A plataforma agora fica em `platform.tuya.com`. |
| O teste do POWER não fez nada | Aponte o emissor direto para a TV, sem obstáculos. Se o emissor foi pareado de novo, a chave local mudou: rode o passo 4 outra vez. |
| A senha 0413 não abre o menu | Tente 0000. |
| Reaprender dá "tempo esgotado" | Use um controle infravermelho a poucos centímetros do emissor. O Magic Remote não funciona. |

## Arquivos locais

Estes arquivos ficam na pasta do projeto, fora do git, e **não devem ser compartilhados**: guardam a chave local do emissor e as credenciais da Tuya.

| Arquivo | Conteúdo |
|---|---|
| `emissor_ir.json` | IP, ID, chave local, versão e tipo de controle do emissor |
| `devices.json`, `tinytuya.json`, `snapshot.json`, `tuya-raw.json` | Gerados pelo assistente da `tinytuya` |
| `estado.json` | Modelo da TV e teclas reaprendidas |

Variáveis de ambiente opcionais:

| Variável | Para quê |
|---|---|
| `PORT` | Porta do servidor (padrão `8000`) |
| `LG_SERVCONTROL_CONFIG` | Outro caminho para `emissor_ir.json` |
| `LG_SERVCONTROL_ESTADO` | Outro caminho para `estado.json` |
| `LG_SERVCONTROL_SIMULAR=1` | Roda sem emissor: os comandos só aparecem no log |

## Para desenvolvedores

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
LG_SERVCONTROL_SIMULAR=1 .venv/bin/python -m lg_servcontrol
```

- Vocabulário do domínio: [`GLOSSARY.md`](GLOSSARY.md)
- Decisões de arquitetura: [`docs/adr/`](docs/adr/)
- Os testes passam pela API HTTP com um emissor falso; não precisam do aparelho.

## Licença

[MIT](LICENSE). O software é fornecido "como está", sem garantias: veja o aviso sobre os Menus de Serviço no início deste README.
