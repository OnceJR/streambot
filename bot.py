import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import InputAudioStream
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

# Función para reproducir audio
async def play_audio(chat_id, url):
    try:
        process = ffmpeg.input(url).output("pipe:1", format="opus", acodec="libopus").run_async(pipe_stdout=True)
        await pytgcalls.join_group_call(chat_id, InputAudioStream(process.stdout))
        return "Reproduciendo audio."
    except Exception as e:
        return f"Error al reproducir audio: {e}"

# Comando /play para iniciar la reproducción
@client.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        await message.reply_text("Por favor, proporciona un enlace o archivo de audio.")
        return
    url = message.command[1]
    chat_id = Config.CHAT_ID
    queue.append(url)  # Agrega el URL a la cola
    if len(queue) == 1:  # Si es el primer elemento en la cola, inicia la reproducción
        msg = await play_audio(chat_id, url)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("Añadido a la cola de reproducción.", reply_markup=get_control_buttons())

# Comando /skip para saltar al siguiente en la cola
@client.on_message(filters.command("skip"))
async def skip(_, message):
    if len(queue) > 1:
        queue.pop(0)  # Elimina el elemento actual de la cola
        next_url = queue[0]
        msg = await play_audio(Config.CHAT_ID, next_url)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("No hay más elementos en la cola.", reply_markup=get_control_buttons())

# Comando /stop para detener la reproducción
@client.on_message(filters.command("stop"))
async def stop(_, message):
    await pytgcalls.leave_group_call(Config.CHAT_ID)
    queue.clear()  # Vacía la cola
    await message.reply_text("Reproducción detenida y cola vaciada.", reply_markup=get_control_buttons())

# Manejo de los botones de control
@client.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    if data == "pause":
        await pytgcalls.pause_stream(Config.CHAT_ID)
        await callback_query.answer("Reproducción pausada.")
    elif data == "resume":
        await pytgcalls.resume_stream(Config.CHAT_ID)
        await callback_query.answer("Reproducción reanudada.")
    elif data == "stop":
        await pytgcalls.leave_group_call(Config.CHAT_ID)
        queue.clear()
        await callback_query.answer("Reproducción detenida.")
    elif data == "skip":
        if len(queue) > 1:
            queue.pop(0)
            next_url = queue[0]
            msg = await play_audio(Config.CHAT_ID, next_url)
            await callback_query.message.reply_text(msg, reply_markup=get_control_buttons())
            await callback_query.answer("Siguiente en la cola.")
        else:
            await callback_query.answer("No hay más elementos en la cola.")

# Iniciar el cliente y PyTgCalls
async def main():
    await client.start()
    await pytgcalls.start()
    print("Bot iniciado y listo para reproducir.")
    await client.idle()

client.run(main())
