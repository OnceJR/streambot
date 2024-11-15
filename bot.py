import os
from pyrogram import Client, idle, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioVideoPiped, AudioPiped
from config import Config
import ffmpeg

client = Client("my_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
pytgcalls = PyTgCalls(client)
queue = []  # Cola de reproducción


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


async def play_media(chat_id, url, is_video=False):
    try:
        if is_video:
            stream = AudioVideoPiped(url)
        else:
            process = ffmpeg.input(url).output("pipe:1", format="opus", acodec="libopus").run_async(pipe_stdout=True)
            stream = AudioPiped(process.stdout)

        await pytgcalls.join_group_call(chat_id, stream)
        return "Reproduciendo video." if is_video else "Reproduciendo audio."
    except Exception as e:
        return f"Error al reproducir: {e}"


@client.on_message(filters.command("play"))
async def play(_, message):
    chat_id = Config.CHAT_IDS[0]
    if message.reply_to_message and message.reply_to_message.video:
        # Si es un video enviado directamente
        file_id = message.reply_to_message.video.file_id
        file_path = await client.download_media(file_id)
        queue.append({"path": file_path, "is_video": True})
    elif len(message.command) >= 2:
        # Si es un enlace
        url = message.command[1]
        queue.append({"path": url, "is_video": url.endswith(('.mp4', '.mkv', '.avi'))})
    else:
        await message.reply_text("Por favor, proporciona un enlace o responde con un archivo de video.")
        return

    if len(queue) == 1:
        item = queue[0]
        msg = await play_media(chat_id, item["path"], item["is_video"])
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("Añadido a la cola de reproducción.", reply_markup=get_control_buttons())


@client.on_message(filters.command("skip"))
async def skip(_, message):
    chat_id = Config.CHAT_IDS[0]
    if len(queue) > 1:
        queue.pop(0)
        next_item = queue[0]
        msg = await play_media(chat_id, next_item["path"], next_item["is_video"])
        await message.reply_text(msg, reply_markup=get_control_buttons())
    else:
        await message.reply_text("No hay más elementos en la cola.", reply_markup=get_control_buttons())


@client.on_message(filters.command("stop"))
async def stop(_, message):
    chat_id = Config.CHAT_IDS[0]
    await pytgcalls.leave_group_call(chat_id)
    queue.clear()
    await message.reply_text("Reproducción detenida y cola vaciada.", reply_markup=get_control_buttons())


@client.on_callback_query()
async def callback_handler(client, callback_query):
    chat_id = Config.CHAT_IDS[0]
    data = callback_query.data
    if data == "pause":
        await pytgcalls.pause_stream(chat_id)
        await callback_query.answer("Reproducción pausada.")
    elif data == "resume":
        await pytgcalls.resume_stream(chat_id)
        await callback_query.answer("Reproducción reanudada.")
    elif data == "stop":
        await pytgcalls.leave_group_call(chat_id)
        queue.clear()
        await callback_query.answer("Reproducción detenida.")
    elif data == "skip":
        if len(queue) > 1:
            queue.pop(0)
            next_item = queue[0]
            msg = await play_media(chat_id, next_item["path"], next_item["is_video"])
            await callback_query.message.reply_text(msg, reply_markup=get_control_buttons())
            await callback_query.answer("Siguiente en la cola.")
        else:
            await callback_query.answer("No hay más elementos en la cola.")


WELCOME_MESSAGE = """
🎉 ¡Bienvenido al bot de streaming! 🎉

Comandos:
- **/play <URL>** - Reproducir un enlace de audio o video.
- **Responde a un video** - Reproducir un video enviado.
- **/pause** - Pausar reproducción.
- **/resume** - Reanudar reproducción.
- **/stop** - Detener reproducción.
- **/skip** - Pasar al siguiente.

¡Disfruta! 🎥🎶
"""


async def send_welcome_message():
    for chat_id in Config.CHAT_IDS:
        await client.send_message(chat_id, WELCOME_MESSAGE)


async def main():
    await client.start()
    await pytgcalls.start()
    await send_welcome_message()
    await idle()


client.run(main())
