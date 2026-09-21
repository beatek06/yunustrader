"""Portfoy durumunu (config/portfolio.json) okuyup guncelleyen yardimci modul.
Token/LLM cagrisi yapmaz - saf dosya okuma/yazma islemidir. Her islemden
once pozisyonun onceki halini data/islem_gecmisi.json'a kaydeder, boylece
'IPTAL' komutuyla son islem geri alinabilir.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PORTFOLIO_PATH = BASE_DIR / "config" / "portfolio.json"
GECMIS_PATH = BASE_DIR / "data" / "islem_gecmisi.json"
GECMIS_LIMITI = 20  # bellek/dosya sismesin diye son N islem tutulur


def portfoy_yukle() -> dict:
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def portfoy_kaydet(veri: dict) -> None:
    veri["son_guncelleme"] = date.today().isoformat()
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def gecmis_yukle() -> list:
    if GECMIS_PATH.exists():
        icerik = GECMIS_PATH.read_text(encoding="utf-8").strip()
        return json.loads(icerik) if icerik else []
    return []


def gecmis_kaydet(gecmis: list) -> None:
    GECMIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GECMIS_PATH, "w", encoding="utf-8") as f:
        json.dump(gecmis[-GECMIS_LIMITI:], f, ensure_ascii=False, indent=2)


def islem_uygula(sembol: str, yon: str, miktar: float, fiyat: float, para_birimi: str = "USD") -> str:
    """yon: 'AL' veya 'SAT'. Pozisyonu gunceller, ortalama maliyeti yeniden
    hesaplar ve islemi gecmise (geri alinabilsin diye) kaydeder."""
    veri = portfoy_yukle()
    pozisyonlar = veri["pozisyonlar"]
    sembol = sembol.upper()
    yon = yon.upper()

    onceki_durum = dict(pozisyonlar[sembol]) if sembol in pozisyonlar else None

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

    gecmis = gecmis_yukle()
    gecmis.append({
        "zaman": datetime.now(timezone.utc).isoformat(),
        "sembol": sembol,
        "yon": yon,
        "miktar": miktar,
        "fiyat": fiyat,
        "onceki_durum": onceki_durum,  # None ise bu islem yeni pozisyon acmisti
    })
    gecmis_kaydet(gecmis)

    portfoy_kaydet(veri)
    return sonuc


def son_islemi_geri_al() -> str:
    gecmis = gecmis_yukle()
    if not gecmis:
        return "Geri alinacak islem bulunamadi."

    son = gecmis.pop()
    veri = portfoy_yukle()
    pozisyonlar = veri["pozisyonlar"]
    sembol = son["sembol"]

    if son["onceki_durum"] is None:
        pozisyonlar.pop(sembol, None)
    else:
        pozisyonlar[sembol] = son["onceki_durum"]

    portfoy_kaydet(veri)
    gecmis_kaydet(gecmis)

    return (
        f"Geri alindi: '{son['yon']} {son['sembol']} {son['miktar']} @ {son['fiyat']}' "
        f"islemi iptal edildi, pozisyon eski haline dondu."
    )


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
