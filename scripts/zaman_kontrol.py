"""Gunde bir kere ogle (12:00 sonrasi) ve bir kere aksam (19:00 sonrasi,
Zurich saatiyle) bildirimi gonderilmesini saglar.

GitHub Actions'in zamanlanmis (cron) tetikleyicileri dakika hassasiyetinde
calismaz, yuk altinda saatlerce gecikebilir. Bu yuzden 'su an tam 12:00 mi'
diye dar bir pencereye bakmak yerine, 'bugun bu slot icin gonderim yapildi mi'
durumunu (data/son_bildirim.json) takip eder - boylece cron ne zaman ateslenirse
ateslensin, slot saatini gectiyse ve bugun henuz gonderilmediyse mutlaka bir
kere calisir; ayni gun icinde ikinci kez tetiklenmez.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent
DURUM_PATH = BASE_DIR / "data" / "son_bildirim.json"

SLOTLAR = {"ogle": 12, "aksam": 19}


def _bugun() -> str:
    return datetime.now(ZoneInfo("Europe/Zurich")).date().isoformat()


def durum_yukle() -> dict:
    varsayilan = {"tarih": _bugun(), "gonderilenler": []}

    if not DURUM_PATH.exists():
        return varsayilan

    icerik = DURUM_PATH.read_text(encoding="utf-8").strip()
    if not icerik:
        return varsayilan

    durum = json.loads(icerik)
    if durum.get("tarih") != _bugun():
        return varsayilan  # gun degisti, sayaci sifirla

    return durum


def durum_kaydet(durum: dict) -> None:
    DURUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DURUM_PATH, "w", encoding="utf-8") as f:
        json.dump(durum, f, ensure_ascii=False, indent=2)


def gonderilecek_slot() -> str | None:
    """Su an saati gecmis ama bugun henuz gonderilmemis bir slot varsa
    adini dondurur (ogle/aksam), yoksa None."""
    simdi = datetime.now(ZoneInfo("Europe/Zurich"))
    durum = durum_yukle()

    for slot_adi, saat in SLOTLAR.items():
        if simdi.hour >= saat and slot_adi not in durum["gonderilenler"]:
            return slot_adi
    return None


def slot_isaretle(slot_adi: str) -> None:
    durum = durum_yukle()
    if slot_adi not in durum["gonderilenler"]:
        durum["gonderilenler"].append(slot_adi)
    durum_kaydet(durum)


if __name__ == "__main__":
    slot = gonderilecek_slot()
    if slot:
        print(slot)
        sys.exit(0)
    sys.exit(1)
