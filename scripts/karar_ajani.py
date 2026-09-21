"""Karar Ajani - kural tabanli teknik + temel analiz sonuclarini portfoy
durumuyla birlestirip iki bolumluk Turkce rapor uretir:

  1) FIRSAT TARAMASI - portfoy disindaki adaylardan en iyi 5'i, kisa gerekceyle.
  2) PORTFOY ANALIZI - elde tutulan her pozisyon icin teknik+temel analiz
     birlestirilerek AL/SAT/TUT karari ve gerekcesi.

Hicbir LLM/API cagrisi yapmaz, tamamen ucretsiz ve kural tabanlidir.
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
FIRSATLAR_PATH = BASE_DIR / "data" / "firsatlar.json"
OUTPUT_PATH = BASE_DIR / "data" / "son_oneri.txt"


def karar_kelimesi(toplam_skor: int) -> str:
    if toplam_skor >= 3:
        return "AL"
    if toplam_skor <= -3:
        return "SAT"
    return "TUT"


def yorum_uret(toplam_skor: int) -> str:
    if toplam_skor >= 3:
        return "AL sinyali guclu"
    if toplam_skor == 1 or toplam_skor == 2:
        return "TUT (hafif pozitif)"
    if toplam_skor == 0:
        return "TUT (notr)"
    if toplam_skor == -1 or toplam_skor == -2:
        return "TUT (hafif negatif, izle)"
    return "SAT sinyali guclu"


def teknik_aciklama(s: dict) -> str:
    parcalar = []
    rsi = s.get("rsi14")
    if rsi is not None:
        if rsi < 30:
            parcalar.append(f"RSI {rsi} ile asiri satim bolgesinde")
        elif rsi > 70:
            parcalar.append(f"RSI {rsi} ile asiri alim bolgesinde")
        else:
            parcalar.append(f"RSI {rsi} notr bolgede")

    fiyat, sma20, sma50 = s.get("son_fiyat"), s.get("sma20"), s.get("sma50")
    if fiyat and sma20 and sma50:
        if fiyat > sma20 > sma50:
            parcalar.append("fiyat ortalamalarin uzerinde (yukselis trendi)")
        elif fiyat < sma20 < sma50:
            parcalar.append("fiyat ortalamalarin altinda (dusus trendi)")
        else:
            parcalar.append("ortalamalara gore karisik/yatay seyir")

    if s.get("macd_pozitif_kesisim") is True:
        parcalar.append("MACD pozitif kesisimde (momentum yukari)")
    elif s.get("macd_pozitif_kesisim") is False:
        parcalar.append("MACD negatif bolgede (momentum asagi)")

    return ", ".join(parcalar) if parcalar else "yeterli teknik veri yok"


def pozisyon_satiri(sembol: str, s: dict, pf: dict) -> tuple[str, bool]:
    """Tek bir pozisyon icin rapor metnini uretir. Ikinci deger, bunun bir
    'satis onerisi' olup olmadigini belirtir (ozet bolumunde tekrar vurgulamak icin)."""
    toplam_skor = s["toplam_skor"]
    karar = karar_kelimesi(toplam_skor)
    yorum = yorum_uret(toplam_skor)
    ad = pf.get(sembol, {}).get("ad", sembol)

    satirlar = [f"{ad} ({sembol}) - {yorum} | toplam skor {toplam_skor:+d}"]
    satirlar.append(f"Teknik: {teknik_aciklama(s)}.")

    if s.get("tur") == "hisse":
        satirlar.append(f"Temel: {s.get('temel_aciklama', 'veri yok')}.")
    else:
        satirlar.append("Temel: kripto icin temel analiz uygulanmaz, sadece teknik gostergeler kullanildi.")

    pozisyon = pf.get(sembol)
    satis_onerisi = False
    if pozisyon and pozisyon.get("miktar", 0) > 0:
        fark_yuzde = (
            (s["son_fiyat"] - pozisyon["ortalama_maliyet"]) / pozisyon["ortalama_maliyet"]
        ) * 100
        satirlar.append(
            f"Pozisyon: {pozisyon['miktar']} {pozisyon['birim']}, maliyete gore {fark_yuzde:+.1f}%. "
            f"Karar: {karar}."
        )
        satis_onerisi = karar == "SAT"
    else:
        satirlar.append(f"Pozisyon: elinde yok. Karar (izleme amacli): {karar}.")

    return "\n".join(satirlar), satis_onerisi


def firsat_bolumu_uret(firsatlar: list) -> list:
    satirlar = ["1) FIRSAT TARAMASI (portfoy disi, su anki en guclu 5 aday)", ""]
    if not firsatlar:
        satirlar.append("Su an one cikan net bir firsat bulunamadi.")
        return satirlar

    for i, f in enumerate(firsatlar, start=1):
        satirlar.append(f"{i}. {f['sembol']} ({f['son_fiyat']}) - {f['gerekce']}")
    return satirlar


def portfoy_bolumu_uret(sinyaller: dict, pf: dict) -> tuple[list, list]:
    satirlar = ["2) PORTFOY ANALIZI (temel + teknik birlesik)", ""]
    satis_onerileri = []

    for sembol, s in sinyaller.items():
        if "hata" in s:
            satirlar.append(f"{sembol}: veri alinamadi ({s['hata']})")
            satirlar.append("")
            continue

        metin, satis_onerisi = pozisyon_satiri(sembol, s, pf)
        satirlar.append(metin)
        satirlar.append("")

        if satis_onerisi:
            satis_onerileri.append(sembol)

    return satirlar, satis_onerileri


def calistir() -> str:
    with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
        sinyal_verisi = json.load(f)["sinyaller"]

    firsatlar = []
    if FIRSATLAR_PATH.exists():
        with open(FIRSATLAR_PATH, "r", encoding="utf-8") as f:
            firsatlar = json.load(f)

    pf = portfoy.portfoy_yukle()["pozisyonlar"]
    simdi = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%d.%m.%Y %H:%M")

    satirlar = [f"A Sirketi - Piyasa Raporu ({simdi} Zurich)", ""]
    satirlar.extend(firsat_bolumu_uret(firsatlar))
    satirlar.append("")

    portfoy_satirlari, satis_onerileri = portfoy_bolumu_uret(sinyal_verisi, pf)
    satirlar.extend(portfoy_satirlari)

    if satis_onerileri:
        satirlar.append(f"UYARI: {', '.join(satis_onerileri)} icin SAT sinyali uretildi, yukaridaki detaya bak.")
        satirlar.append("")

    satirlar.append("Not: Bu bir yatirim tavsiyesi degildir, kural tabanli otomatik ozet niteligindedir.")

    metin = "\n".join(satirlar)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(metin, encoding="utf-8")
    return metin


if __name__ == "__main__":
    print(calistir())
