import os
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped
from config import Config
import ffmpeg

# Configura el cliente de Pyrogram y PyTgCalls
client = Client("my_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
pytgcalls = PyTgCalls(client)
queue = []  # Cola de reproducción

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
        process = (
            ffmpeg.input(url)
            .output("pipe:1", format="mpegts", vcodec="libx264", acodec="aac", strict="experimental")
            .run_async(pipe_stdout=True)
        )
        await pytgcalls.join_group_call(chat_id, AudioVideoPiped(process.stdout))
        return "Reproduciendo video."
    except Exception as e:
        return f"Error al reproducir video: {e}"

# Comando /play para iniciar la reproducción
@client.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        await message.reply_text("Por favor, proporciona un enlace o archivo de video.")
        return
    url = message.command[1]
    chat_id = Config.CHAT_IDS[0]  # Usa el primer chat por defecto
    queue.append(url)  # Agrega el URL a la cola
    if len(queue) == 1:  # Si es el primer elemento en la cola, inicia la reproducción
        msg = await play_video(chat_id, url)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("Añadido a la cola de reproducción.", reply_markup=get_control_buttons())

# Función principal para iniciar el cliente y enviar el mensaje de bienvenida
async def main():
    await client.start()
    await pytgcalls.start()
    await idle()  # Mantiene el bot en ejecución

# Ejecuta el bot
client.run(main())
