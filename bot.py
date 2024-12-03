# Importa las bibliotecas necesarias
from telethon import TelegramClient, events, Button
import subprocess
import os
import math
import ffmpeg
import json

# Configuración del bot de Telegram
API_ID = '24738183'
API_HASH = '6a1c48cfe81b1fc932a02c4cc1d312bf'
BOT_TOKEN = '8100674706:AAGzf_JziSNHdJCHHTT4Z9cSWLvF03zF_yU'

# Límites y rutas
DOWNLOAD_PATH = "/path/to/downloads/"
COOKIES_PATH = "/path/to/cookies.txt"
MAX_TELEGRAM_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB

# Crear cliente del bot
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Función para obtener información del video usando FFprobe
def get_video_info(file_path):
    try:
        probe = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return json.loads(probe.stdout)
    except Exception as e:
        return {}

# Función para dividir videos que exceden el límite
def split_video(file_path, max_size):
    parts = []
    info = get_video_info(file_path)
    duration = float(info["format"]["duration"])
    total_size = os.path.getsize(file_path)
    num_parts = math.ceil(total_size / max_size)
    split_duration = duration / num_parts

    for i in range(num_parts):
        part_name = f"{file_path}_part{i + 1}.mp4"
        start_time = i * split_duration
        subprocess.run(
            [
                "ffmpeg",
                "-i", file_path,
                "-ss", str(start_time),
                "-t", str(split_duration),
                "-c", "copy",
                part_name
            ]
        )
        parts.append(part_name)
    return parts

# Evento de inicio
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond(
        "👋 ¡Hola! Soy un bot para descargar videos de Twitch. Envía el enlace del video y lo descargaré para ti.",
        buttons=[Button.inline("Ayuda", b"help")]
    )

# Evento para manejar enlaces de Twitch
@bot.on(events.NewMessage(pattern=r"https://www\.twitch\.tv/.*"))
async def handle_twitch_link(event):
    url = event.message.text
    msg = await event.respond("🔄 **Procesando el enlace...**")

    try:
        # Descargar el video con yt-dlp
        output_template = os.path.join(DOWNLOAD_PATH, "%(title)s.%(ext)s")
        subprocess.run(
            [
                "yt-dlp",
                "--cookies", COOKIES_PATH,
                "-o", output_template,
                url
            ],
            check=True
        )

        # Buscar el archivo descargado
        downloaded_file = max(
            [os.path.join(DOWNLOAD_PATH, f) for f in os.listdir(DOWNLOAD_PATH)],
            key=os.path.getctime
        )

        # Obtener información del video y miniatura
        video_info = get_video_info(downloaded_file)
        thumbnail = downloaded_file.replace(".mp4", ".jpg")
        subprocess.run(["ffmpeg", "-i", downloaded_file, "-vf", "thumbnail", "-frames:v", "1", thumbnail])

        # Dividir el video si excede el tamaño permitido
        if os.path.getsize(downloaded_file) > MAX_TELEGRAM_SIZE:
            parts = split_video(downloaded_file, MAX_TELEGRAM_SIZE)
        else:
            parts = [downloaded_file]

        # Actualizar mensaje y subir el video a Telegram
        await msg.edit("📤 **Subiendo video(s)...**")
        for i, part in enumerate(parts, start=1):
            await bot.send_file(
                event.chat_id,
                part,
                caption=f"🎥 **{video_info['format']['tags'].get('title', 'Video sin título')}**\n📅 {video_info['format']['tags'].get('date', 'Fecha desconocida')}\n⏱️ {round(float(video_info['format']['duration']) / 60, 2)} minutos",
                thumb=thumbnail,
                buttons=[Button.inline(f"Parte {i}/{len(parts)}", b"ignore")]
            )
        await msg.edit("✅ **Video(s) enviado(s) correctamente.**", buttons=[Button.inline("Ayuda", b"help")])

    except Exception as e:
        await msg.edit(f"❌ **Error al procesar el enlace:** {str(e)}")

# Evento para manejar botones
@bot.on(events.CallbackQuery(data=b"help"))
async def help(event):
    await event.edit(
        "📄 **Instrucciones:**\n"
        "1. Envía un enlace de Twitch.\n"
        "2. El bot descargará y optimizará el video.\n"
        "3. Si el video excede los 2 GB, será dividido en partes.\n"
        "4. El video se subirá a Telegram.",
        buttons=[Button.inline("Cerrar", b"close")]
    )

@bot.on(events.CallbackQuery(data=b"close"))
async def close(event):
    await event.delete()

# Iniciar el bot
print("Bot iniciado...")
bot.run_until_disconnected()
