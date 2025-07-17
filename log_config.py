import logging

logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    file_handler = logging.FileHandler("bot.log", encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # optional: also log to console
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
