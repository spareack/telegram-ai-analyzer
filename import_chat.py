import json
import os
import glob
from log_config import logger


RAW_DIR = "raw_chats"
OUT_DIR = "converted_chats"
os.makedirs(OUT_DIR, exist_ok=True)


def convert_file(file_path: str, bot_id: str) -> None:
    """
    Convert a single Telegram chat export (result.json format) to plain text format.
    Saves output to 'converted_chats/chat_<id>.txt' and deletes the original file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        output = os.path.join(OUT_DIR, f"chat_{data['id']}.txt")

        with open(output, 'w', encoding='utf-8') as out:
            for msg in data.get("messages", []):
                if bot_id in msg.get('from_id', ''):
                    continue

                if msg.get("type") == "message":
                    date = msg.get("date", "").split("T")[0]
                    sender = msg.get("from", "Unknown")
                    text = msg.get("text", "")

                    if text == '':
                        continue

                    if isinstance(text, list):
                        text = ''.join(
                            t if isinstance(t, str) else t.get('text', '')
                            for t in text
                        )
                    text = text.replace('\n', '. ')
                    out.write(f"{date} {sender}: {text}\n")

        os.remove(file_path)
        logger.info(f"[✓] Converted and deleted: {file_path} → {output}")

    except Exception as e:
        logger.error(f"[!] Failed to convert {file_path}: {e}")


def convert_all_raw_chats(bot_id: str) -> None:
    """
    Convert all JSON files in 'raw_chats/' directory and delete originals.
    """
    files = glob.glob(os.path.join(RAW_DIR, "*.json"))
    if not files:
        logger.info("No files found in raw_chats/")
        return

    for path in files:
        convert_file(path, bot_id)
