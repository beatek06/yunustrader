"""Portfoy durumunu (config/portfolio.json) okuyup guncelleyen yardimci modul.
Token/LLM cagrisi yapmaz - saf dosya okuma/yazma islemidir.
"""
import json
from datetime import date
from pathlib import Path

PORTFOLIO_PATH = Path(__file__).resolve().parent.parent / "config" / "portfolio.json"


def portfoy_yukle() -> dict:
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def portfoy_kaydet(veri: dict) -> None:
    veri["son_guncelleme"] = date.today().isoformat()
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def islem_uygula(sembol: str, yon: str, miktar: float, fiyat: float, para_birimi: str = "USD") -> str:
    """yon: 'AL' veya 'SAT'. Pozisyonu gunceller ve ortalama maliyeti yeniden hesaplar."""
    veri = portfoy_yukle()
    pozisyonlar = veri["pozisyonlar"]
    sembol = sembol.upper()
    yon = yon.upper()

    if sembol not in pozisyonlar:
        if yon == "SAT":
            return f"HATA: '{sembol}' portfoyde yok, satis islenemedi."
        pozisyonlar[sembol] = {
            "ad": sembol,
            "miktar": 0.0,
            "birim": "adet",
            "ortalama_maliyet": 0.0,
            "maliyet_para_birimi": para_birimi,
            "yfinance_ticker": None,
            "otomatik_analiz": False,
        }

    pos = pozisyonlar[sembol]
    eski_miktar = pos["miktar"]
    eski_maliyet = pos["ortalama_maliyet"]

    if yon == "AL":
        yeni_miktar = eski_miktar + miktar
        if yeni_miktar > 0:
            pos["ortalama_maliyet"] = (
                (eski_miktar * eski_maliyet) + (miktar * fiyat)
            ) / yeni_miktar
        pos["miktar"] = yeni_miktar
        sonuc = f"{sembol}: {miktar} adet {fiyat} {para_birimi} fiyatindan alindi. Yeni miktar: {yeni_miktar}"
    elif yon == "SAT":
        if miktar > eski_miktar:
            return f"HATA: '{sembol}' icin elinde {eski_miktar} var, {miktar} satilamaz."
        pos["miktar"] = eski_miktar - miktar
        sonuc = f"{sembol}: {miktar} adet {fiyat} {para_birimi} fiyatindan satildi. Kalan miktar: {pos['miktar']}"
    else:
        return f"HATA: gecersiz islem yonu '{yon}' (AL veya SAT olmali)."

    portfoy_kaydet(veri)
    return sonuc


def ozet_metni() -> str:
    veri = portfoy_yukle()
    satirlar = ["Mevcut portfoy:"]
    for sembol, pos in veri["pozisyonlar"].items():
        satirlar.append(
            f"- {pos['ad']} ({sembol}): {pos['miktar']} {pos['birim']}, "
            f"ort. maliyet {pos['ortalama_maliyet']} {pos.get('maliyet_para_birimi', '')}"
        )
    return "\n".join(satirlar)


if __name__ == "__main__":
    print(ozet_metni())
