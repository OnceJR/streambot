import os
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped, AudioPiped
from config import Config
import ffmpeg

# Configura el cliente de Pyrogram y PyTgCalls
client = Client("vcplayerbot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
pytgcalls = PyTgCalls(client)

# Cola de reproducción
queue = []

# Función para mostrar botones de control
def get_control_buttons():
    buttons = [
        [InlineKeyboardButton("⏸ Pausa", callback_data="pause"),
         InlineKeyboardButton("▶️ Reanudar", callback_data="resume")],
        [InlineKeyboardButton("⏹ Detener", callback_data="stop"),
         InlineKeyboardButton("⏭ Siguiente", callback_data="skip")]
    ]
    return InlineKeyboardMarkup(buttons)

# Función para reproducir video
async def play_video(chat_id, url):
    try:
        process = (
            ffmpeg
            .input(url)
            .output("pipe:1", format="matroska", vcodec="libx264", acodec="aac", pix_fmt="yuv420p")
            .run_async(pipe_stdout=True)
        )
        await pytgcalls.join_group_call(chat_id, AudioVideoPiped(process.stdout))
        return "Reproduciendo video."
    except Exception as e:
        return f"Error al reproducir video: {e}"

# Comando /play para iniciar la reproducción de video
@client.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        await message.reply_text("Por favor, proporciona un enlace o archivo de video.")
        return
    url = message.command[1]
    chat_id = Config.CHAT_IDS[0]
    queue.append(url)
    if len(queue) == 1:
        msg = await play_video(chat_id, url)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("Añadido a la cola de reproducción.", reply_markup=get_control_buttons())

# Función principal para iniciar el cliente y enviar el mensaje de bienvenida
async def main():
    await client.start()
    await pytgcalls.start()
    await idle()

client.run(main())
