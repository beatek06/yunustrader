"""Temel Analiz - yfinance'in ucretsiz sagladigi sirket verileriyle
(P/E, buyume, analist konsensusu, hedef fiyat) basit ama kurallara dayali
bir temel analiz skoru ve kisa aciklama uretir. Sadece hisseler icin
anlamlidir; kripto icin uygulanmaz.
"""
import yfinance as yf


def temel_veri_al(ticker: str) -> dict:
    bilgi = yf.Ticker(ticker).info
    return {
        "pe": bilgi.get("trailingPE"),
        "forward_pe": bilgi.get("forwardPE"),
        "gelir_buyumesi": bilgi.get("revenueGrowth"),
        "kar_buyumesi": bilgi.get("earningsGrowth"),
        "analist_notu": bilgi.get("recommendationMean"),
        "hedef_fiyat": bilgi.get("targetMeanPrice"),
        "guncel_fiyat": bilgi.get("currentPrice") or bilgi.get("regularMarketPrice"),
    }


def temel_skor_ve_aciklama(temel: dict) -> tuple[int, str]:
    skor = 0
    notlar = []

    pe = temel.get("pe")
    if pe and pe > 0:
        if pe < 25:
            skor += 1
            notlar.append(f"P/E {pe:.1f} (ucuz/makul)")
        elif pe > 45:
            skor -= 1
            notlar.append(f"P/E {pe:.1f} (pahali)")
        else:
            notlar.append(f"P/E {pe:.1f} (notr)")

    buyume = temel.get("gelir_buyumesi")
    if buyume is not None:
        if buyume > 0.08:
            skor += 1
            notlar.append(f"gelir buyumesi %{buyume*100:.0f} (guclu)")
        elif buyume < 0:
            skor -= 1
            notlar.append(f"gelir buyumesi %{buyume*100:.0f} (daralma)")

    kar = temel.get("kar_buyumesi")
    if kar is not None:
        if kar > 0.08:
            skor += 1
            notlar.append(f"kar buyumesi %{kar*100:.0f} (guclu)")
        elif kar < 0:
            skor -= 1
            notlar.append(f"kar buyumesi %{kar*100:.0f} (daralma)")

    analist = temel.get("analist_notu")
    if analist is not None:
        if analist <= 2.3:
            skor += 1
            notlar.append("analist konsensusu Al yonlu")
        elif analist >= 3.5:
            skor -= 1
            notlar.append("analist konsensusu Sat yonlu")

    hedef = temel.get("hedef_fiyat")
    guncel = temel.get("guncel_fiyat")
    if hedef and guncel:
        fark_yuzde = ((hedef - guncel) / guncel) * 100
        if fark_yuzde > 8:
            skor += 1
            notlar.append(f"analist hedef fiyati %{fark_yuzde:.0f} yukarida")
        elif fark_yuzde < -5:
            skor -= 1
            notlar.append(f"analist hedef fiyati %{fark_yuzde:.0f} asagida")

    aciklama = ", ".join(notlar) if notlar else "yeterli temel veri yok"
    return skor, aciklama


if __name__ == "__main__":
    for t in ["NVDA", "AAPL"]:
        veri = temel_veri_al(t)
        s, a = temel_skor_ve_aciklama(veri)
        print(t, s, a)
