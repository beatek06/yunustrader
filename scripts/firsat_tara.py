"""Firsat Tarama Ajani - portfoy disindaki genis bir aday havuzunu
(config/firsat_havuzu.json) teknik_analiz ile tarar, halihazirda elde
tutulanlari eler ve en yuksek toplam skora sahip 5 tanesini kisa
gerekcesiyle birlikte data/firsatlar.json'a yazar.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portfoy
import teknik_analiz

BASE_DIR = Path(__file__).resolve().parent.parent
HAVUZ_PATH = BASE_DIR / "config" / "firsat_havuzu.json"
HAM_CIKTI_PATH = BASE_DIR / "data" / "firsat_ham.json"
CIKTI_PATH = BASE_DIR / "data" / "firsatlar.json"

EN_IYI_KAC_TANE = 5


def kisa_gerekce(sembol: str, s: dict) -> str:
    parcalar = [f"RSI {s.get('rsi14')}"]
    if s.get("macd_pozitif_kesisim"):
        parcalar.append("MACD pozitif")
    if s.get("tur") == "hisse" and s.get("temel_aciklama") and "yeterli temel veri yok" not in s["temel_aciklama"]:
        ilk_not = s["temel_aciklama"].split(",")[0]
        parcalar.append(ilk_not)
    return ", ".join(parcalar)


def calistir() -> list:
    ham = teknik_analiz.calistir(watchlist_path=HAVUZ_PATH, output_path=HAM_CIKTI_PATH)
    pf = portfoy.portfoy_yukle()["pozisyonlar"]

    adaylar = []
    for sembol, s in ham["sinyaller"].items():
        if "hata" in s:
            continue
        elindeki = pf.get(sembol)
        if elindeki and elindeki.get("miktar", 0) > 0:
            continue  # zaten portfoyde var, firsat listesine girmez
        adaylar.append((sembol, s))

    adaylar.sort(key=lambda x: x[1]["toplam_skor"], reverse=True)
    secilenler = adaylar[:EN_IYI_KAC_TANE]

    sonuc = [
        {
            "sembol": sembol,
            "son_fiyat": s["son_fiyat"],
            "toplam_skor": s["toplam_skor"],
            "gerekce": kisa_gerekce(sembol, s),
        }
        for sembol, s in secilenler
    ]

    CIKTI_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CIKTI_PATH, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    return sonuc


if __name__ == "__main__":
    print(json.dumps(calistir(), ensure_ascii=False, indent=2))
