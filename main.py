import discord
import requests
import asyncio
import time
import logging
import os
from dotenv import load_dotenv
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
from datetime import datetime
import pytz  # Nova importação para trabalhar com fusos horários

# ————————— CARREGAR VARIÁVEIS DE AMBIENTE —————————
load_dotenv()

# ————————— CONFIGURAÇÕES —————————
TOKEN             = os.getenv("DISCORD_TOKEN")
GUILD_ID          = int(os.getenv("GUILD_ID"))
CLIP_CHANNEL_ID   = int(os.getenv("CLIP_CHANNEL_ID"))
CHAT_CHANNEL_ID   = int(os.getenv("CHAT_CHANNEL_ID"))
STATUS_CHANNEL_ID = int(os.getenv("STATUS_CHANNEL_ID"))
STATUS_URL        = os.getenv("STATUS_URL")

TWITCH_CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME      = os.getenv("TWITCH_USERNAME")
CHECK_INTERVAL       = 60  # segundos (1 minuto)

# ————————— LOGGING —————————
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GolpeBaixoBot")

# ————————— FLASK —————————
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("PING RECEBIDO: GET /")
    return "Bot do Golpe Baixo está vivo, manda a cachaça!"

def start_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = Thread(target=start_flask)
flask_thread.start()

# ————————— BOT DISCORD —————————
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Frases automáticas
respostas = {
    "salve": "Opa, tá salvo! Mas manda uma dose pra mim, hein!",
    "opa": "Opa, chegou! Traz a cachaça!",
    "fala": "Fala, parceiro! Como tá o rolê?",
    "beleza": "Beleza, meu chapa! Vamos nessa!",
    "oi": "Oi, camarada! Bora tomar uma?",
}

# ——— FUNÇÕES TWITCH ———

def get_twitch_oauth_token():
    try:
        url = 'https://id.twitch.tv/oauth2/token'
        params = {
            'client_id': TWITCH_CLIENT_ID,
            'client_secret': TWITCH_CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }
        resp = requests.post(url, params=params)
        resp.raise_for_status()
        return resp.json().get('access_token')
    except Exception as e:
        logger.error(f"[OAuth] Erro ao pegar token Twitch: {e}")
        return None

def is_live():
    try:
        token = get_twitch_oauth_token()
        if not token:
            return False
        url = f'https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}'
        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get('data'))
    except Exception as e:
        logger.error(f"[is_live] Erro ao verificar se está ao vivo: {e}")
        return False

# Função para verificar se o bot está online ou offline a partir de uma URL
def check_bot_status():
    try:
        response = requests.get(STATUS_URL)
        if response.status_code == 200:
            return "Online"
        else:
            return "Offline"
    except requests.exceptions.RequestException as e:
        logger.error(f"[check_bot_status] Erro ao verificar status do bot: {e}")
        return "Offline"

# ——— TAREFAS ———

@tasks.loop(seconds=CHECK_INTERVAL)
async def update_bot_status():
    try:
        # Verificar o status do bot
        status = check_bot_status()

        # Criar embed
        # Usando timezone de Brasília
        br_tz = pytz.timezone('America/Sao_Paulo')
        br_time = datetime.now(br_tz).strftime('%H:%M:%S')

        embed = discord.Embed(title="Status do Bot", description=f"O bot está **{status}**.", color=0x00ff00 if status == "Online" else 0xff0000)
        embed.set_footer(text=f"Última atualização: {br_time}")

        # Enviar ou atualizar o embed no canal de status
        channel = bot.get_channel(STATUS_CHANNEL_ID)
        if channel:
            # Tentando encontrar o embed mais recente para editar
            async for message in channel.history(limit=1):
                await message.edit(embed=embed)
                break
            else:
                await channel.send(embed=embed)
        else:
            logger.warning("[update_bot_status] Canal de status não encontrado.")
    except Exception as e:
        logger.error(f"[update_bot_status] Erro: {e}")

# ——— EVENTOS ———

@bot.event
async def on_ready():
    logger.info(f'✅ Bot conectado como {bot.user}')
    try:
        update_bot_status.start()  # Começar a tarefa de atualização do status
    except Exception as e:
        logger.error(f"[on_ready] Erro ao iniciar tarefas: {e}")

@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return

        for key, resp in respostas.items():
            if key in message.content.lower():
                if message.channel.id == CHAT_CHANNEL_ID:
                    await message.channel.send(resp)
                break

        await bot.process_commands(message)
    except Exception as e:
        logger.error(f"[on_message] Erro: {e}")

# ——— INICIA BOT ———
try:
    bot.run(TOKEN)
except Exception as e:
    logger.critical(f"[bot.run] Erro ao iniciar o bot: {e}")
