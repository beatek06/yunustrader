"""Zurich yerel saatine gore su an 12:00 veya 19:00 civari mi diye bakar.
Sadece standart kutuphane kullanir (kurulum gerektirmez), GitHub Actions'da
gereksiz pip install/analiz yapmamak icin bir on-kontrol (gate) olarak kullanilir.
"""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

HEDEF_SAATLER = (12, 19)
TOLERANS_DAKIKA = 7


def zaman_uygun_mu() -> bool:
    simdi = datetime.now(ZoneInfo("Europe/Zurich"))
    for saat in HEDEF_SAATLER:
        hedef = simdi.replace(hour=saat, minute=0, second=0, microsecond=0)
        fark_dakika = abs((simdi - hedef).total_seconds()) / 60
        if fark_dakika <= TOLERANS_DAKIKA:
            return True
    return False


if __name__ == "__main__":
    sys.exit(0 if zaman_uygun_mu() else 1)
