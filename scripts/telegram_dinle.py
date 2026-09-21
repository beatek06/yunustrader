"""Portfoy Dinleme Ajani - Telegram'dan gelen AL/SAT mesajlarini okuyup
portfoyu gunceller. LLM cagrisi yapmaz, sadece ucretsiz yfinance verisi kullanir.

Format esnektir:
  "AL NVDA 2 227.5"   -> NVDA'dan 2 adet, 227.5 fiyattan alindi
  "AL NVDA 2"         -> fiyat verilmezse anlik piyasa fiyati otomatik cekilir
  "aldim btc 0.001"   -> buyuk/kucuk harf ve "aldim/sattim" gibi cekimler de calisir
  "aldim nvda 100$"   -> tutar bazli: 100$'lik NVDA icin anlik fiyattan adet hesaplanir
"""
import os
import re
import sys
from pathlib import Path

import requests
import yfinance as yf
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfoy

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET_PATH = BASE_DIR / "data" / "telegram_offset.txt"

# AL / SAT ve "aldim", "aliyorum", "sattim", "satiyorum" gibi cekimlerini kabul eder.
# Fiyat kismi opsiyoneldir.
ISLEM_DESENI = re.compile(
    r"^(AL\w*|SAT\w*)\s+([A-Za-z0-9]+)\s+([\d.,]+)(?:\s+([\d.,]+))?",
    re.IGNORECASE,
)

# Tutar bazli format: "aldim nvda 100$" / "AL BTC 50 usd" / "sattim eth 30 chf"
PARA_BIRIMLERI = {
    "$": "USD", "usd": "USD", "dolar": "USD",
    "chf": "CHF", "fr": "CHF",
    "eur": "EUR", "€": "EUR",
    "tl": "TRY", "₺": "TRY", "try": "TRY",
}
TUTAR_DESENI = re.compile(
    r"^(AL\w*|SAT\w*)\s+([A-Za-z0-9]+)\s+([\d.,]+)\s*(\$|€|₺|usd|dolar|chf|fr|eur|tl|try)(?:\W|$)",
    re.IGNORECASE,
)


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


def ticker_bul(sembol: str) -> str:
    """Sembol icin yfinance ticker'ini config dosyalarindan veya mevcut
    portfoyden bulmaya calisir, bulamazsa sembolun kendisini dener."""
    sembol = sembol.upper()

    pf = portfoy.portfoy_yukle()["pozisyonlar"]
    if sembol in pf and pf[sembol].get("yfinance_ticker"):
        return pf[sembol]["yfinance_ticker"]

    for dosya_adi in ("watchlist.json", "firsat_havuzu.json"):
        yol = BASE_DIR / "config" / dosya_adi
        if not yol.exists():
            continue
        import json

        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
        for kayit in veri.get("semboller", []):
            if kayit["sembol"].upper() == sembol:
                return kayit["yfinance_ticker"]

    return sembol


def canli_fiyat_al(sembol: str) -> float | None:
    ticker = ticker_bul(sembol)
    try:
        veri = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        if veri.empty:
            return None
        kapanis = veri["Close"]
        if hasattr(kapanis, "iloc") and kapanis.ndim > 1:
            kapanis = kapanis.iloc[:, 0]
        return float(kapanis.iloc[-1])
    except Exception:
        return None


def yon_normalize_et(ham_yon: str) -> str:
    return "AL" if ham_yon.upper().startswith("AL") else "SAT"


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

        tutar_eslesme = TUTAR_DESENI.match(metin)
        eslesme = ISLEM_DESENI.match(metin) if not tutar_eslesme else None

        if tutar_eslesme:
            ham_yon, sembol, tutar_str, birim_ham = tutar_eslesme.groups()
            yon = yon_normalize_et(ham_yon)
            tutar = float(tutar_str.replace(",", "."))
            para_birimi = PARA_BIRIMLERI.get(birim_ham.lower(), "USD")

            fiyat = canli_fiyat_al(sembol)
            if fiyat is None:
                mesaj_gonder(
                    gonderen_chat_id,
                    f"'{sembol}' icin anlik fiyat bulunamadi, tutar bazli islem yapilamadi. "
                    f"Miktari kendin yazabilirsin: orn. '{ham_yon} {sembol} 0.5'",
                )
                continue

            miktar = tutar / fiyat
            sonuc = portfoy.islem_uygula(sembol, yon, miktar, fiyat, para_birimi)
            mesaj_gonder(
                gonderen_chat_id,
                f"{sonuc}\n({tutar} {para_birimi} / anlik fiyat {fiyat:.4f} = {miktar:.6f} adet)",
            )
        elif eslesme:
            ham_yon, sembol, miktar_str, fiyat_str = eslesme.groups()
            yon = yon_normalize_et(ham_yon)
            miktar = float(miktar_str.replace(",", "."))

            if fiyat_str:
                fiyat = float(fiyat_str.replace(",", "."))
            else:
                fiyat = canli_fiyat_al(sembol)
                if fiyat is None:
                    mesaj_gonder(
                        gonderen_chat_id,
                        f"'{sembol}' icin anlik fiyat bulunamadi, lutfen fiyati elle yaz: "
                        f"orn. '{ham_yon} {sembol} {miktar_str} 100'",
                    )
                    continue

            sonuc = portfoy.islem_uygula(sembol, yon, miktar, fiyat)
            mesaj_gonder(gonderen_chat_id, sonuc)
        else:
            mesaj_gonder(
                gonderen_chat_id,
                "Anlamadim. Su formatlardan biriyle yaz:\n"
                "- AL SEMBOL MIKTAR [FIYAT]  (orn: AL NVDA 2   veya   sattim btc 0.001 95000)\n"
                "- AL SEMBOL TUTAR$  (orn: aldim nvda 100$  -> anlik fiyattan adet hesaplanir)\n"
                "Chat ID: " + gonderen_chat_id,
            )

    offset_kaydet(offset)


if __name__ == "__main__":
    calistir()
