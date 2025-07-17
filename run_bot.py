"""
run_bot.py

Telegram entry‑point.  Records every group message to a per‑chat file and
invokes `ai_api.analyze_history` when the bot is mentioned.
"""
import asyncio
import os
import requests

from telegram import Update, Bot
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from import_chat import convert_all_raw_chats
from log_config import logger
from config import TELEGRAM_TOKEN
import ai_api


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Respond to /start.
    """
    await update.message.reply_text(
        "Bot ready. Mention me in a group and ask your question about the chat history."
    )


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = int(str(update.effective_chat.id).removeprefix('-').removeprefix('100'))
    result = ai_api.refresh_chat_file(chat_id)
    await update.message.reply_text(result)


async def typing_loop(bot, chat_id, stop_event):
    """
    Send 'typing' action every few seconds until stop_event is set.
    """
    try:
        while not stop_event.is_set():
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except Exception as e:
        pass


async def handle_question(message, question, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = int(str(update.effective_chat.id).removeprefix('-').removeprefix('100'))

    logger.info(f'(chat: {chat_id}) question received: {message.text}')
    logger.info(f'start analyzing...')

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(context.bot, update.effective_chat.id, stop_typing))

    try:
        answer = await asyncio.to_thread(ai_api.analyze_history, chat_id, question)
    finally:
        stop_typing.set()
        await typing_task

    ai_api.append_message(
        chat_id=chat_id,
        user_name=message.from_user.full_name,
        text=message.text,
        date=message.date,
    )
    await message.reply_text(answer, reply_to_message_id=message.message_id)


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Log every incoming group message and, if the bot is mentioned, forward the
    user's question to the language model.
    """
    message = update.message
    if not message or not message.text:
        return

    bot_username = context.bot.username

    if f"@{bot_username}" in message.text:
        question = message.text.replace(f"@{bot_username}", "").strip()
        await handle_question(message, question, update, context)


async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    await handle_question(message, message.text.strip(), update, context)


def get_bot_id() -> int:
    """
    Retrieve the bot's Telegram ID using a direct API call to getMe.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("ok"):
            bot_id = data["result"]["id"]
            logger.info(f"Bot ID: {bot_id}")
            return bot_id
        else:
            logger.info("Failed to get bot ID:", data)
    except Exception as e:
        logger.error("Error while calling getMe:", e)
    return -1


def main() -> None:
    """
    Initialise the Telegram client and start polling.
    """
    bot_id = get_bot_id()

    raw_chats = os.listdir("raw_chats")
    if len(raw_chats) > 0:
        convert_all_raw_chats(str(bot_id))
        logger.info(f'{len(raw_chats)} raw chats converted successfully!')

    converted_chats = os.listdir("converted_chats")
    logger.info(f'{len(converted_chats)} cached chats detected ({converted_chats})')

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.add_handler(CommandHandler("ask", handle_ask))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_mention)
    )
    logger.info(f"Bot started... (ID: {bot_id})")
    app.run_polling()


if __name__ == "__main__":
    main()
