# A Sirketi (kisisel)

Kural tabanli, ucretsiz calisan kisisel teknik analiz + portfoy takip sistemi.
GitHub Actions uzerinde bulutta calisir, bilgisayarinin acik olmasina gerek yoktur.
Hicbir LLM/API cagrisi yapmaz, sadece ucretsiz piyasa verisi (yfinance) ve Telegram kullanir.

## Nasil calisir

- **scripts/teknik_analiz.py** — watchlist.json'daki semboller icin RSI/SMA/MACD hesaplar.
- **scripts/karar_ajani.py** — bu sinyalleri ve mevcut portfoyu birlestirip Turkce ozet + gerekirse "SATIS ONERISI" bolumu uretir.
- **scripts/telegram_bildirim.py** — ozeti Telegram'a gonderir.
- **scripts/telegram_dinle.py** — Telegram'a yazdigin "AL/SAT" mesajlarini okuyup portfoyu gunceller.
- **.github/workflows/bildirim.yml** — her gun Zurich saatiyle 12:00 ve 19:00'da yukaridaki zinciri calistirir.
- **.github/workflows/portfoy_dinle.yml** — her 15 dakikada bir Telegram mesajlarini kontrol eder.

## Kurulum

### 1. GitHub'a yukle

```
cd C:\Users\yunus\a-sirketi
git init
git add .
git commit -m "ilk kurulum"
```

Sonra github.com'da **private** bir repo olustur (orn. `a-sirketi`), ve:

```
git remote add origin https://github.com/KULLANICI_ADIN/a-sirketi.git
git branch -M main
git push -u origin main
```

`.env` dosyasi `.gitignore` icinde oldugu icin repo'ya gitmez, token'in guvende kalir.

### 2. GitHub Secrets ekle

Repo sayfasinda **Settings > Secrets and variables > Actions > New repository secret** ile su 2 secret'i ekle:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

(Degerleri `.env` dosyandan kopyalayabilirsin.)

### 3. Chat ID'yi bul

Telegram'da botuna (@yunustrader_bot) herhangi bir mesaj at (orn. "merhaba").
Bot sana chat ID'ni yaniti icinde soyleyecek. Bu degeri hem `.env` dosyana
hem de GitHub secret'ina (`TELEGRAM_CHAT_ID`) ekle.

### 4. Test et

Repo'ya push ettikten sonra GitHub'da **Actions** sekmesine git, "Piyasa Bildirimi"
workflow'unu sec, **Run workflow** ile elle bir kere calistirip Telegram'a
mesaj gelip gelmedigini kontrol edebilirsin (saat kontrolu devre disi kalmaz,
ama `workflow_dispatch` ile manuel tetiklendiginde de zaman kontrolu uygulanir —
test icin `scripts/zaman_kontrol.py` icindeki HEDEF_SAATLER degerini gecici
olarak su anki saate cekebilirsin).

## Portfoyu elle guncellemek

`config/portfolio.json` dosyasini direkt duzenleyebilirsin. Ozellikle:
- `GOLD_ETC`, `SILVER_ETC`, `SWISSQOIN` icin otomatik veri yok, degerlerini
  elle guncellemen gerekir.
- Gercek alis maliyetini biliyorsan `ortalama_maliyet` alanlarini duzelt
  (su an ekran goruntusundeki anlik fiyatlardan tahmini dolduruldu).

## Telegram uzerinden islem bildirme

Bota su formatta mesaj at:

```
AL NVDA 2 227.5
SAT BTC 0.0005 95000
```

Bot portfoyu otomatik gunceller ve sonucu sana yazar (en gec 15 dakika icinde,
`portfoy_dinle.yml` calisma sikligina bagli).

## Limitler / bilinen kisitlar

- Piyasa verisi yfinance uzerinden ucretsiz ama gecikmeli/en iyi caba (best-effort) saglanir.
- Hicbir emir otomatik verilmez, sadece oneri/bildirim uretilir — al/sat kararini hep sen verirsin.
- Gold/Silver ETC ve Swissqoin icin otomatik fiyat/sinyal yoktur.
