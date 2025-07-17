"""
ai_api.py

Core logic for interacting with the OpenAI Assistants API and maintaining
per‑chat history files.
"""

import os
import re
import time

from openai import OpenAI
from config import OPENAI_API_KEY
from log_config import logger

MODEL = "o3-mini"
CHAT_DIR = "converted_chats"
ASSISTANT_FILE = "assistant_id.txt"
FILE_CACHE_DIR = "file_cache"

client = OpenAI(api_key=OPENAI_API_KEY)
os.makedirs(FILE_CACHE_DIR, exist_ok=True)


def _get_cached_file_id(chat_id: int) -> str | None:
    path = os.path.join(FILE_CACHE_DIR, f"cache_{chat_id}.txt")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    return None


def _cache_file_id(chat_id: int, file_id: str) -> None:
    path = os.path.join(FILE_CACHE_DIR, f"cache_{chat_id}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(file_id)


def clear_file_cache(chat_id: int) -> None:
    path = os.path.join(FILE_CACHE_DIR, f"cache_{chat_id}.txt")
    if os.path.exists(path):
        os.remove(path)


def refresh_chat_file(chat_id: int) -> str:
    """
    Force-upload the chat file for a given chat ID, update the cached file ID,
    and return a success or error message.
    """
    try:
        file_path = _chat_file(chat_id)
        if not os.path.exists(file_path):
            return "❌ No chat history file found."

        file_obj = client.files.create(
            file=open(file_path, "rb"),
            purpose="assistants"
        )
        _cache_file_id(chat_id, file_obj.id)
        return f"✅ New file uploaded. ID: {file_obj.id}"
    except Exception as e:
        logger.exception("Failed to refresh chat file")
        return f"❌ Upload failed: {e}"


def _get_or_create_assistant_id() -> str:
    """
    Return a cached assistant ID if it exists; otherwise create a new
    assistant, cache its ID, and return it.
    """
    if os.path.exists(ASSISTANT_FILE):
        assistant_id = open(ASSISTANT_FILE, "r", encoding="utf-8").read().strip()
        logger.info("Using cached assistant ID: %s", assistant_id)
        return assistant_id

    logger.info("Creating new assistant...")
    assistant = client.beta.assistants.create(
        name="Telegram Chat Analyst",
        instructions=(
            "You are an assistant that analyzes a Telegram group chat conversation provided as a plain text file. "
            "You must answer questions based only on the contents of that file. "
            "The chat log is formatted as one message per line, in the following structure: "
            "YYYY-MM-DD Username: Message text "
            "Each line contains the date, the full name of the message sender, and the message itself. "
            "There is no additional metadata. "
            "Be concise and factual. If possible, refer to relevant message dates when giving answers. "
            "If the information is not found in the log, say that directly. "
            "Do not guess or assume anything outside of the provided text file."
        ),
        tools=[{"type": "file_search"}],
        model=MODEL,
    )

    with open(ASSISTANT_FILE, "w", encoding="utf-8") as fh:
        fh.write(assistant.id)

    logger.info("New assistant created and cached: %s", assistant.id)
    return assistant.id


ASSISTANT_ID = _get_or_create_assistant_id()


def _chat_file(chat_id: int) -> str:
    """
    Return the absolute path to the history file for a given chat.
    """
    os.makedirs(CHAT_DIR, exist_ok=True)
    return os.path.join(CHAT_DIR, f"chat_{chat_id}.txt")


def append_message(chat_id: int, user_name: str, text: str, date) -> None:
    """
    Append a message to the corresponding chat history file in the format
    'YYYY‑MM‑DD User: message'.
    """
    path = _chat_file(chat_id)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{date.strftime('%Y-%m-%d')} {user_name}: {text.strip()}\n")
    logger.debug("Appended message to %s: %s %s", path, user_name, text.strip())


def _clean_response(content: str) -> str:
    """
    Remove internal citation markers produced by the Assistants API.
    """
    return re.sub(r".*?", "", content).strip()


def analyze_history(chat_id: int, question: str) -> str:
    """
    Analyze the chat history for the given chat ID using a cached file ID,
    or upload the local chat file if no cache exists. Returns the assistant's
    answer or an error message.
    """
    try:
        file_id = _get_cached_file_id(chat_id)

        if not file_id:
            file_path = _chat_file(chat_id)
            if not os.path.exists(file_path):
                return "⚠️ No chat history found. Use /refresh to upload it."

            # Try to upload the file now
            file_obj = client.files.create(
                file=open(file_path, "rb"),
                purpose="assistants"
            )
            file_id = file_obj.id
            _cache_file_id(chat_id, file_id)
            logger.info("📄 Chat file for chat_id=%s uploaded and cached: %s", chat_id, file_id)
        else:
            logger.info(f'Using previously cached file: {file_id}')

        thread = client.beta.threads.create()

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question,
            attachments=[{
                "file_id": file_id,
                "tools": [{"type": "file_search"}],
            }],
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        while True:
            status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if status.status == "completed":
                break
            if status.status in {"failed", "cancelled"}:
                error = getattr(status, "last_error", None)
                details = f"{error}" if error else "no details"
                logger.error("❌ Run failed | chat_id=%s | run_id=%s | reason: %s", chat_id, run.id, details)
                return f"Run failed: {details}"
            time.sleep(1)

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for message in reversed(messages.data):
            if message.role == "assistant":
                logger.info(f'Response successfully generated: {message.content[0].text.value}')
                return _clean_response(message.content[0].text.value)

        return "⚠️ Assistant did not return a response."
    except Exception as exc:
        logger.exception("Error during analyze_history for chat_id=%s", chat_id)
        return f"❌ Processing error: {exc}"
