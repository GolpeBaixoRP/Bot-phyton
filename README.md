# 🤖 Bot do Golpe Baixo

Um bot feito para o Discord com integração automática com a Twitch do personagem Golpe Baixo, rodando com Flask + Discord.py. Ele faz:

- Envio de respostas automáticas no chat de texto do servidor
- Verificação de status online do bot e envio de embed no canal de status
- Monitoramento da Twitch e suporte para futuros recursos como envio automático de clipes
- Webserver embutido com Flask para manter o bot vivo no Replit ou RAPT

---

## ⚙️ Requisitos

- Python 3.10+
- Variáveis de ambiente configuradas
- Conta de desenvolvedor no Discord e na Twitch

---

## 📦 Instalação

1. Clone ou baixe este repositório
2. Crie um arquivo `.env` com as seguintes variáveis:

```env
DISCORD_TOKEN=seu_token_do_discord
GUILD_ID=000000000000000000
CLIP_CHANNEL_ID=000000000000000000
CHAT_CHANNEL_ID=000000000000000000
STATUS_CHANNEL_ID=000000000000000000
STATUS_URL=https://link-do-bot-que-sera-verificado.com

TWITCH_CLIENT_ID=sua_client_id
TWITCH_CLIENT_SECRET=sua_client_secret
TWITCH_USERNAME=seu_usuario_da_twitch
