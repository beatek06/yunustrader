"""Portfoy Dinleme Ajani - Telegram'dan gelen AL/SAT mesajlarini okuyup
portfoyu gunceller. Sadece requests kullanir, LLM cagrisi yapmaz.

Mesaj formati: "AL NVDA 2 227.5"  veya  "SAT BTC 0.0005 95000"
"""
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfoy

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET_PATH = Path(__file__).resolve().parent.parent / "data" / "telegram_offset.txt"

ISLEM_DESENI = re.compile(r"^(AL|SAT)\s+([A-Za-z0-9]+)\s+([\d.,]+)\s+([\d.,]+)", re.IGNORECASE)


def son_offset_oku() -> int:
    if OFFSET_PATH.exists():
        icerik = OFFSET_PATH.read_text().strip()
        return int(icerik) if icerik else 0
    return 0


def offset_kaydet(offset: int) -> None:
    OFFSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_PATH.write_text(str(offset))


def mesaj_gonder(chat_id: str, metin: str) -> None:
    requests.post(f"{API_URL}/sendMessage", data={"chat_id": chat_id, "text": metin}, timeout=15)


def calistir() -> None:
    offset = son_offset_oku()
    yanit = requests.get(
        f"{API_URL}/getUpdates", params={"offset": offset + 1, "timeout": 0}, timeout=15
    ).json()

    for guncelleme in yanit.get("result", []):
        offset = guncelleme["update_id"]
        mesaj = guncelleme.get("message", {})
        metin = (mesaj.get("text") or "").strip()
        gonderen_chat_id = str(mesaj.get("chat", {}).get("id", ""))

        if not metin or not gonderen_chat_id:
            continue

        eslesme = ISLEM_DESENI.match(metin)
        if eslesme:
            yon, sembol, miktar_str, fiyat_str = eslesme.groups()
            miktar = float(miktar_str.replace(",", "."))
            fiyat = float(fiyat_str.replace(",", "."))
            sonuc = portfoy.islem_uygula(sembol, yon, miktar, fiyat)
            mesaj_gonder(gonderen_chat_id, sonuc)
        else:
            mesaj_gonder(
                gonderen_chat_id,
                "Anlamadim. Format: 'AL SEMBOL MIKTAR FIYAT' veya 'SAT SEMBOL MIKTAR FIYAT'\n"
                "Ornek: AL NVDA 2 227.5\n"
                "Chat ID: " + gonderen_chat_id,
            )

    offset_kaydet(offset)


if __name__ == "__main__":
    calistir()
