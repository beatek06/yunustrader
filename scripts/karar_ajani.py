"""Karar Ajani - kural tabanli teknik analiz + portfoy durumuna gore
Turkce oneri metni uretir. Hicbir LLM/API cagrisi yapmaz, tamamen ucretsizdir.
Mevcut portfoydeki pozisyonlardan satis sinyali veren varsa ayri bir
'Satis Onerisi' bolumunde acikca vurgular.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfoy

BASE_DIR = Path(__file__).resolve().parent.parent
SIGNALS_PATH = BASE_DIR / "data" / "sinyaller.json"
OUTPUT_PATH = BASE_DIR / "data" / "son_oneri.txt"

SATIS_ESIGI = -1  # bu skor ve altindaki, elde tutulan pozisyonlar satis onerisi olarak vurgulanir


def skor_hesapla(s: dict) -> int:
    skor = 0
    rsi = s.get("rsi14")
    if rsi is not None:
        if rsi < 30:
            skor += 1
        elif rsi > 70:
            skor -= 1

    fiyat, sma20, sma50 = s.get("son_fiyat"), s.get("sma20"), s.get("sma50")
    if fiyat and sma20 and sma50:
        if fiyat > sma20 > sma50:
            skor += 1
        elif fiyat < sma20 < sma50:
            skor -= 1

    if s.get("macd_pozitif_kesisim") is True:
        skor += 1
    elif s.get("macd_pozitif_kesisim") is False:
        skor -= 1

    return skor


def yorum_uret(skor: int) -> str:
    if skor >= 2:
        return "AL sinyali guclu"
    if skor == 1:
        return "Hafif pozitif, TUT/izle"
    if skor == 0:
        return "Notr"
    if skor == -1:
        return "Hafif negatif, TUT/izle"
    return "SAT sinyali guclu"


def calistir() -> str:
    with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
        veri = json.load(f)

    pf = portfoy.portfoy_yukle()["pozisyonlar"]
    simdi = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y %H:%M")

    satirlar = [f"A Sirketi - Piyasa Ozeti ({simdi} Zurich)", ""]
    satis_onerileri = []

    for sembol, s in veri["sinyaller"].items():
        if "hata" in s:
            satirlar.append(f"{sembol}: veri alinamadi ({s['hata']})")
            continue

        skor = skor_hesapla(s)
        yorum = yorum_uret(skor)
        pozisyon = pf.get(sembol)

        if pozisyon and pozisyon["miktar"] > 0:
            fark_yuzde = (
                (s["son_fiyat"] - pozisyon["ortalama_maliyet"]) / pozisyon["ortalama_maliyet"]
            ) * 100
            sahiplik = f" | Elinde: {pozisyon['miktar']} {pozisyon['birim']}, maliyete gore {fark_yuzde:+.1f}%"

            if skor <= SATIS_ESIGI:
                satis_onerileri.append(
                    f"- {pozisyon['ad']} ({sembol}): {yorum}, RSI {s.get('rsi14')}, "
                    f"maliyete gore {fark_yuzde:+.1f}%. Elindeki {pozisyon['miktar']} {pozisyon['birim']} "
                    f"icin kismen/tamamen satis degerlendirilebilir."
                )
        else:
            sahiplik = " | Elinde yok"

        satirlar.append(f"{sembol}: {s['son_fiyat']} | RSI {s.get('rsi14')} | {yorum}{sahiplik}")

    if satis_onerileri:
        satirlar.append("")
        satirlar.append("SATIS ONERISI (mevcut portfoyunden):")
        satirlar.extend(satis_onerileri)

    satirlar.append("")
    satirlar.append("Not: Bu bir yatirim tavsiyesi degildir, kural tabanli otomatik ozet niteligindedir.")

    metin = "\n".join(satirlar)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(metin, encoding="utf-8")
    return metin


if __name__ == "__main__":
    print(calistir())
