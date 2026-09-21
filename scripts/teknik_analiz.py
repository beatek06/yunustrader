"""Teknik + Temel Analiz Ajani.
Ucretsiz yfinance verisiyle RSI, SMA, MACD (teknik) ve P/E, buyume, analist
konsensusu (temel, sadece hisseler icin) hesaplayip tek bir toplam skor uretir.
Hicbir LLM/Claude cagrisi yapmaz - token maliyeti sifirdir.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

import temel_analiz

BASE_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = BASE_DIR / "config" / "watchlist.json"
SIGNALS_PATH = BASE_DIR / "data" / "sinyaller.json"


def rsi_hesapla(kapanis: pd.Series, periyot: int = 14) -> float:
    delta = kapanis.diff()
    kazanc = delta.clip(lower=0)
    kayip = -delta.clip(upper=0)
    ort_kazanc = kazanc.rolling(periyot).mean()
    ort_kayip = kayip.rolling(periyot).mean()
    rs = ort_kazanc / ort_kayip.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else None


def macd_hesapla(kapanis: pd.Series):
    ema12 = kapanis.ewm(span=12, adjust=False).mean()
    ema26 = kapanis.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sinyal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(sinyal.iloc[-1])


def teknik_skor_hesapla(rsi, fiyat, sma20, sma50, macd_pozitif_kesisim) -> int:
    skor = 0
    if rsi is not None:
        if rsi < 30:
            skor += 1
        elif rsi > 70:
            skor -= 1

    if fiyat and sma20 and sma50:
        if fiyat > sma20 > sma50:
            skor += 1
        elif fiyat < sma20 < sma50:
            skor -= 1

    if macd_pozitif_kesisim is True:
        skor += 1
    elif macd_pozitif_kesisim is False:
        skor -= 1

    return skor


def sembol_analiz_et(ticker: str, tur: str = "hisse") -> dict | None:
    veri = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
    if veri.empty or len(veri) < 30:
        return None

    kapanis = veri["Close"]
    if isinstance(kapanis, pd.DataFrame):
        kapanis = kapanis.iloc[:, 0]

    son_fiyat = float(kapanis.iloc[-1])
    sma20 = float(kapanis.rolling(20).mean().iloc[-1])
    sma50 = float(kapanis.rolling(50).mean().iloc[-1]) if len(kapanis) >= 50 else None
    rsi = rsi_hesapla(kapanis)
    macd, macd_sinyal = macd_hesapla(kapanis)
    macd_pozitif_kesisim = macd > macd_sinyal

    teknik_skoru = teknik_skor_hesapla(rsi, son_fiyat, sma20, sma50, macd_pozitif_kesisim)

    temel_skoru = 0
    temel_aciklama = "kripto icin temel analiz uygulanmaz"
    if tur == "hisse":
        try:
            temel_veri = temel_analiz.temel_veri_al(ticker)
            temel_skoru, temel_aciklama = temel_analiz.temel_skor_ve_aciklama(temel_veri)
        except Exception as e:
            temel_aciklama = f"temel veri alinamadi ({e})"

    return {
        "tur": tur,
        "son_fiyat": round(son_fiyat, 4),
        "sma20": round(sma20, 4) if sma20 else None,
        "sma50": round(sma50, 4) if sma50 else None,
        "rsi14": round(rsi, 2) if rsi is not None else None,
        "macd": round(macd, 4),
        "macd_sinyal": round(macd_sinyal, 4),
        "macd_pozitif_kesisim": macd_pozitif_kesisim,
        "teknik_skoru": teknik_skoru,
        "temel_skoru": temel_skoru,
        "temel_aciklama": temel_aciklama,
        "toplam_skor": teknik_skoru + temel_skoru,
    }


def calistir(watchlist_path: Path = WATCHLIST_PATH, output_path: Path = SIGNALS_PATH) -> dict:
    with open(watchlist_path, "r", encoding="utf-8") as f:
        watchlist = json.load(f)

    sonuclar = {}
    for kayit in watchlist["semboller"]:
        sembol = kayit["sembol"]
        ticker = kayit["yfinance_ticker"]
        tur = kayit.get("tur", "hisse")
        try:
            analiz = sembol_analiz_et(ticker, tur)
            sonuclar[sembol] = analiz if analiz else {"hata": "yetersiz veri"}
        except Exception as e:
            sonuclar[sembol] = {"hata": str(e)}

    cikti = {
        "olusturulma_zamani": datetime.now(timezone.utc).isoformat(),
        "sinyaller": sonuclar,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    return cikti


if __name__ == "__main__":
    print(json.dumps(calistir(), ensure_ascii=False, indent=2))
