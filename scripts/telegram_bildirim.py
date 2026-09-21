"""Telegram Bildirim - son_oneri.txt icerigini Telegram'a gonderir."""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
MESAJ_PATH = BASE_DIR / "data" / "son_oneri.txt"


def gonder() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    metin = MESAJ_PATH.read_text(encoding="utf-8")

    yanit = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": metin},
        timeout=15,
    )
    yanit.raise_for_status()


if __name__ == "__main__":
    gonder()
