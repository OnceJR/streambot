import os
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped
from config import Config
import subprocess
import logging

# Configura el cliente de Pyrogram y PyTgCalls
client = Client("my_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
pytgcalls = PyTgCalls(client)
queue = []  # Cola de reproducción

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para mostrar botones de control
def get_control_buttons():
    buttons = [
        [
            InlineKeyboardButton("⏸ Pause", callback_data="pause"),
            InlineKeyboardButton("▶️ Resume", callback_data="resume"),
        ],
        [
            InlineKeyboardButton("⏹ Stop", callback_data="stop"),
            InlineKeyboardButton("⏭ Skip", callback_data="skip"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# Función para reproducir video
async def play_video(chat_id, url):
    try:
        logger.info(f"Iniciando reproducción para URL: {url}")
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-i", url,
                "-f", "mpegts",
                "-codec:v", "mpeg2video",
                "-codec:a", "mp2",
                "-r", "30",
                "pipe:1"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await pytgcalls.join_group_call(chat_id, AudioVideoPiped(process.stdout))
        return "Reproduciendo video."
    except Exception as e:
        logger.error(f"Error en ffmpeg: {e}")
        return f"Error al reproducir video: {e}"

# Comando /play para iniciar la reproducción
@client.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        await message.reply_text("Por favor, proporciona un enlace para reproducir.")
        return
    url = message.command[1]
    chat_id = Config.CHAT_IDS[0]  # Usa el primer chat por defecto
    queue.append(url)  # Agrega el URL a la cola
    if len(queue) == 1:  # Si es el primer elemento en la cola, inicia la reproducción
        msg = await play_video(chat_id, url)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("Añadido a la cola de reproducción.", reply_markup=get_control_buttons())

# Comando /stop para detener la reproducción
@client.on_message(filters.command("stop"))
async def stop(_, message):
    await pytgcalls.leave_group_call(Config.CHAT_IDS[0])
    queue.clear()  # Vacía la cola
    await message.reply_text("Reproducción detenida y cola vaciada.", reply_markup=get_control_buttons())

# Manejo de los botones de control
@client.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    if data == "pause":
        await pytgcalls.pause_stream(Config.CHAT_IDS[0])
        await callback_query.answer("Reproducción pausada.")
    elif data == "resume":
        await pytgcalls.resume_stream(Config.CHAT_IDS[0])
        await callback_query.answer("Reproducción reanudada.")
    elif data == "stop":
        await pytgcalls.leave_group_call(Config.CHAT_IDS[0])
        queue.clear()
        await callback_query.answer("Reproducción detenida.")

# Mensaje de bienvenida
WELCOME_MESSAGE = """
🎉 ¡Bienvenido al bot de streaming de video! 🎉

Usa los siguientes comandos para interactuar conmigo:
- **/play <URL>** - Para reproducir video desde un enlace.
- **/stop** - Para detener la reproducción y limpiar la cola.

¡Espero que disfrutes del contenido! 📹
"""

async def send_welcome_message():
    # Envía el mensaje de bienvenida a todos los chats configurados
    for chat_id in Config.CHAT_IDS:
        await client.send_message(chat_id, WELCOME_MESSAGE)

# Función principal para iniciar el cliente y enviar el mensaje de bienvenida
async def main():
    await client.start()
    await pytgcalls.start()
    await send_welcome_message()
    await idle()  # Mantiene el bot en ejecución

# Ejecuta el bot
client.run(main())
