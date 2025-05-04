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
import pytz

# —————— CARREGAR VARIÁVEIS DE AMBIENTE ——————
load_dotenv()

# —————— CONFIGURAÇÕES ——————
TOKEN             = os.getenv("DISCORD_TOKEN")
GUILD_ID          = int(os.getenv("GUILD_ID"))
CLIP_CHANNEL_ID   = int(os.getenv("CLIP_CHANNEL_ID"))
CHAT_CHANNEL_ID   = int(os.getenv("CHAT_CHANNEL_ID"))
STATUS_CHANNEL_ID = int(os.getenv("STATUS_CHANNEL_ID"))
STATUS_URL        = os.getenv("STATUS_URL")

TWITCH_CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME      = os.getenv("TWITCH_USERNAME")
CHECK_INTERVAL       = 60

# —————— LOGGING ——————
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GolpeBaixoBot")

# —————— FLASK ——————
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("PING RECEBIDO: GET /")
    return "Bot do Golpe Baixo está vivo, manda a cachaça!"

def start_flask():
    app.run(host="0.0.0.0", port=8080)

flask_thread = Thread(target=start_flask)
flask_thread.start()

# —————— BOT DISCORD ——————
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

def get_latest_clip():
    try:
        token = get_twitch_oauth_token()
        if not token:
            return None
        url = f'https://api.twitch.tv/helix/clips?broadcaster_id={get_broadcaster_id()}&first=1'
        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data")
        return data[0] if data else None
    except Exception as e:
        logger.error(f"[get_latest_clip] Erro ao pegar clip: {e}")
        return None

def get_broadcaster_id():
    try:
        token = get_twitch_oauth_token()
        if not token:
            return None
        url = f'https://api.twitch.tv/helix/users?login={TWITCH_USERNAME}'
        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {token}'
        }
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()['data'][0]['id']
    except Exception as e:
        logger.error(f"[get_broadcaster_id] Erro: {e}")
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

# ——— TAREFAS ———

last_clip_id = None
notified_live = False  # Marcador para verificar se já notificou que está ao vivo

@tasks.loop(seconds=CHECK_INTERVAL)
async def monitor_twitch():
    global last_clip_id, notified_live

    # Timezone de Brasília
    br_tz = pytz.timezone('America/Sao_Paulo')
    br_time = datetime.now(br_tz).strftime('%H:%M:%S')

    # Verificar se está ao vivo
    if is_live():
        if not notified_live:  # Envia o embed somente se não tiver sido notificado ainda
            embed = discord.Embed(title="🔴 Golpe Baixo está AO VIVO!", description=f"Acesse agora: https://twitch.tv/{TWITCH_USERNAME}", color=0x9146FF)
            embed.set_footer(text=f"Início detectado: {br_time}")
            canal = bot.get_channel(STATUS_CHANNEL_ID)
            if canal:
                await canal.send(embed=embed)
            notified_live = True  # Marca como notificado
    else:
        if notified_live:  # Se estava ao vivo e agora foi offline, resetamos o estado
            notified_live = False  # Reseta para poder notificar quando voltar ao vivo

    # Verificar novo clipe
    clip = get_latest_clip()
    if clip:
        # Só envia o embed do clipe se for um novo clipe
        if clip["id"] != last_clip_id:
            canal = bot.get_channel(CLIP_CHANNEL_ID)
            if canal:
                embed = discord.Embed(title="📹 Novo clipe disponível!", url=clip["url"], description=clip["title"], color=0x1DB954)
                embed.set_footer(text=f"Publicado: {br_time}")
                await canal.send(embed=embed)
            last_clip_id = clip["id"]  # Atualiza o ID do último clipe enviado
        else:
            logger.info("Nenhum novo clipe detectado.")
    else:
        logger.info("Sem clipes novos.")

@bot.event
async def on_ready():
    logger.info(f'✅ Bot conectado como {bot.user}')
    monitor_twitch.start()

@bot.event
async def on_message(message):
    try:
        if message.author == bot.user:
            return

        for key, resp in respostas.items():
            if key in message.content.lower() and message.channel.id == CHAT_CHANNEL_ID:
                await message.channel.send(resp)
                break

        await bot.process_commands(message)
    except Exception as e:
        logger.error(f"[on_message] Erro: {e}")

try:
    bot.run(TOKEN)
except Exception as e:
    logger.critical(f"[bot.run] Erro ao iniciar o bot: {e}")
