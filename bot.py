import os
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped, AudioPiped
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

# Función para reproducir audio/video
async def play_media(chat_id, url, is_video):
    try:
        if is_video:
            process = ffmpeg.input(url).output("pipe:1", format="mpegts").run_async(pipe_stdout=True, pipe_stderr=True)
            await pytgcalls.join_group_call(chat_id, AudioVideoPiped(process.stdout))
        else:
            process = ffmpeg.input(url).output("pipe:1", format="opus", acodec="libopus").run_async(pipe_stdout=True, pipe_stderr=True)
            await pytgcalls.join_group_call(chat_id, AudioPiped(process.stdout))
        return "Reproduciendo media."
    except Exception as e:
        return f"Error al reproducir: {e}"

# Comando /play para iniciar la reproducción
@client.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        await message.reply_text("Por favor, proporciona un enlace o archivo para reproducir.")
        return
    url = message.command[1]
    is_video = "video" in message.text.lower()  # Determina si es video basado en el comando
    chat_id = Config.CHAT_IDS[0]  # Usa el primer chat por defecto
    queue.append((url, is_video))  # Agrega el URL y el tipo a la cola
    if len(queue) == 1:  # Si es el primer elemento en la cola, inicia la reproducción
        msg = await play_media(chat_id, url, is_video)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("Añadido a la cola de reproducción.", reply_markup=get_control_buttons())

# Comando para recibir archivos directamente y reproducirlos
@client.on_message(filters.video | filters.audio)
async def receive_file(_, message):
    file_id = message.video.file_id if message.video else message.audio.file_id
    file_name = message.video.file_name if message.video else message.audio.file_name
    file_path = await client.download_media(file_id)
    is_video = bool(message.video)
    chat_id = Config.CHAT_IDS[0]  # Usa el primer chat por defecto

    # Agrega el archivo a la cola y confirma su recepción
    queue.append((file_path, is_video))
    await message.reply_text(f"Archivo '{file_name}' recibido y añadido a la cola.")

    # Reproduce si es el primer elemento en la cola
    if len(queue) == 1:
        msg = await play_media(chat_id, file_path, is_video)
        await message.reply_text(msg, reply_markup=get_control_buttons())

# Comando /skip para saltar al siguiente en la cola
@client.on_message(filters.command("skip"))
async def skip(_, message):
    if len(queue) > 1:
        queue.pop(0)  # Elimina el elemento actual de la cola
        next_url, is_video = queue[0]
        msg = await play_media(Config.CHAT_IDS[0], next_url, is_video)
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("No hay más elementos en la cola.", reply_markup=get_control_buttons())

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
    elif data == "skip":
        if len(queue) > 1:
            queue.pop(0)
            next_url, is_video = queue[0]
            msg = await play_media(Config.CHAT_IDS[0], next_url, is_video)
            await callback_query.message.reply_text(msg, reply_markup=get_control_buttons())
            await callback_query.answer("Siguiente en la cola.")
        else:
            await callback_query.answer("No hay más elementos en la cola.")

# Mensaje de bienvenida
WELCOME_MESSAGE = """
🎉 ¡Bienvenido al bot de streaming de audio y video! 🎉

Usa los siguientes comandos para interactuar conmigo:
- **/play <URL>** - Para reproducir audio o video desde un enlace.
- **/pause** - Para pausar la reproducción.
- **/resume** - Para reanudar la reproducción.
- **/stop** - Para detener la reproducción y limpiar la cola.
- **/skip** - Para saltar al siguiente en la cola.

¡Espero que disfrutes de la música y los videos! 🎶📹
"""

async def get_chat_ids():
    resolved_chat_ids = []
    for chat in Config.CHAT_IDS:
        if isinstance(chat, str) and chat.startswith("@"):
            resolved_chat = await client.get_chat(chat)
            resolved_chat_ids.append(resolved_chat.id)
        else:
            resolved_chat_ids.append(chat)
    return resolved_chat_ids

async def send_welcome_message():
    # Envía el mensaje de bienvenida a todos los chats configurados
    for chat_id in Config.CHAT_IDS:
        await client.send_message(chat_id, WELCOME_MESSAGE)

# Función principal para iniciar el cliente y enviar el mensaje de bienvenida
async def main():
    await client.start()
    Config.CHAT_IDS = await get_chat_ids()  # Resuelve los nombres de usuario a chat_id numéricos
    await pytgcalls.start()
    await send_welcome_message()
    await idle()  # Mantiene el bot en ejecución

# Ejecuta el bot
client.run(main())
