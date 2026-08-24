# KAMPANYA HZ4 — GÖRÜŞ ZİNCİRİ HIZI

**Tarih:** 2026-08-24 · **Kol başına n = 4** · 8 uçuş × 150 s

---

## 0 · NEREDEN ÇIKTI

Kullanıcı, **aynı `talon_v5` modelini** başka bir makinede
`avci-drone-yer-kontrol` deposunun `model-fps` branch'iyle koşan bir
arkadaşında **kesintisiz takip** gördü ve şunu söyledi:

> *"bak şimdi modelde bir sorun yok başka şeylerde sorun var... burdaki
> arayüzden baktığımızda çok daha kesintisiz bir takibe ulaşabiliyoruz."*

O sistemle bizimki karşılaştırıldı. Ölçülen fark tablosu:

| # | onlarda | bizde | etki |
|---|---|---|---|
| 1 | çıkarım tavanı **YOK** → 21 FPS | tavan 10 Hz → **9.2 Hz** | 2.3× az örnek |
| 2 | yakalama tavanı **YOK** | tavan 15 Hz | kare kaynağı kilitli |
| 3 | predict `conf` = 0.10, takipçi süzer | `conf` = 0.40 kapı | zayıf kutu atılıyor |
| 4 | HybridSort var | takipçi yok (22 Ağu'da çıkarıldı) | delik kapanmıyor |
| 5 | TensorRT `.engine` 13.1 ms | PyTorch `.pt` | — bkz. aşağıda |
| 6 | kutu okuma tek numpy aktarımı | kutu başına 5 aktarım | ölçüldü: 0.035 ms, ihmal |

**5. satır bizde GEÇERSİZ:** onların `.pt`'si 113.5 ms, bizimki **18.4 ms**
(imgsz 1920 fp16, ölçüldü) — yani bizim `.pt` onların `.engine`'inden hızlı.
Aradaki fark, fp16'nın canlıya uygulanmadığı hatanın bizde düzeltilmiş
olmasından geliyor. Onlardaki "7 kat" bizde tekrarlanamaz.

**6. satır ölçüldü ve ihmal edilebilir çıktı:** onların yorumu kare başına
8-15 kutu varsayıyor; bizde conf 0.10'da bile medyan **1 kutu**. Kazanç
0.035 ms/kare (40 ms'nin %0.09'u). Değişiklik yine de girdi — bit bit aynı
çıktı veriyor (bench: 25/25 karede fark yok).

**Sonuç:** bizde asıl darboğaz **kendi koyduğumuz tavan**. Ölçülen maliyetler:

| aşama | gerçek maliyet | tavanımız | ulaşılan |
|---|---|---|---|
| ekran yakalama | 4-7 ms (>140 Hz olabilir) | 15 Hz | 15 Hz |
| çıkarım (uçuşta) | 35-47 ms (~24 Hz olabilir) | 10 Hz | **9.2 Hz** |

Dört BOSLUK koşusunda ulaşılan hız 9.19 / 9.25 / 9.27 / 9.24 Hz — bu
sabitlik donanımın değil, tavanın imzası.

---

## 1 · TEK DEĞİŞKEN

**Görüş zinciri hızı.** Yakalama ve çıkarım tavanı BİRLİKTE hareket eder:
çıkarımı yakalamanın üstüne çıkarmak aynı kareyi ikinci kez taramak demektir
(bedelli hiçlik). Bu yüzden ikisi tek mekanizmadır, iki değişken değil.

| kol | yakalama | çıkarım | not |
|---|---|---|---|
| **K** (kontrol) | 15 Hz | 10 Hz | bugünkü |
| **H** (deney) | 20 Hz | 20 Hz | kullanıcının gördüğü sistemin hızı (21 FPS) |

Deney kolu neden 20, "sınırsız" değil? Çünkü kıyas noktası, kullanıcının
çalışır gördüğü sistemin ölçülmüş hızıdır. "Olabildiğince hızlı" bir hedef
değil, bir kaza.

**Takipçi bu kampanyada KAPALI** (`DOW_TAKIP=0`) — tek değişken (§4).

**Dönüşümlü:** K, H, K, H, K, H, K, H (sim kayması iki kolu eşit etkilesin).

---

## 2 · ÖLÇÜTLER — KOŞMADAN ÖNCE İLAN EDİLDİ

### Birincil
**KÖR SÜRE ORANI** = kutu yaşı > 0.3 s olan zamanın payı.

Kullanıcının cümlesi (§5.5 — ölçüt kullanıcının hedefinden türetilir):
> *"DETECTİON MODELİ ÇOK KESİK KESİK ÇALIŞIYOR TAKİP SÜREKLİLİĞİ YOK"*

"Kesik kesik" = kutunun bayatladığı zaman. Oran, süre tabanlı olduğu için
çıkarım hızından bağımsızdır — kare sayan bir ölçüt deney kolunu haksız
yere ödüllendirirdi (daha çok kare = daha çok "tespit").

### Geçerlilik eşi (§5.2)
**Bu değer KÖTÜ bir sebeple de düşer mi?** Evet: hedefi hiç aramayan, uzakta
duran bir koşuda kör süre düşük görünebilir. Zorunlu eşi:
* görsel temas oranı (GORSEL fazda geçen süre)
* gerçek tespit % (truth doğrulamalı)

İkisinden biri kontrol kolunun altındaysa kör süre kazancı SAYILMAZ.

### Mekanizma kapısı (§5.1)
`cikarim.csv`'den **ulaşılan** çıkarım Hz. Deney kolunda **< 12 Hz** ise o
koşu veri noktası değil, **GEÇERSİZ koşudur**. (Ö6'da bu kapı olmadığı için
sahte tablo raporlanmıştı.)

### ⛔ Regresyon (§5.10)
**`ist_hata_m` — ISTASYON fazı istasyon tutma hatası.**

Etki alanı tablosu:

| etkilenebilecek davranış | neden etkilenebilir | nerede sınanır |
|---|---|---|
| GPS istasyon tutma | YOLO ve oyun aynı GPU'da; çıkarım hızlanınca oyun aç kalır | her koşunun ISTASYON fazı |
| kontrol bant genişliği | çıkarım kontrol döngüsünü bloke ediyorsa | `ist_hata_son5s`, v_istek doyumu |
| ekran yakalama ↔ oyun çizimi | her XGetImage oyunun boru hattını senkrona zorlar | koşu başına ulaşılan yakalama Hz |

⚠ 22 Ağustos'ta (GA04 vs GV11) tavan kalkınca istasyon hatası
**5.3 m → 25.3 m**, ≤15 m oranı **%88 → %2** olmuştu ve `v_istek` 120 s
boyunca 33 m/s tavanında doyumda kalmıştı. O ölçüm ESKİ panelle (saniyede
180-330 ekran kopyalama) ve fp32 YOLO ile (60 ms) yapıldı; ikisi de artık
düzeltildi, ama **bu varsayım sınanmadan doğru kabul edilmez.**

### Salınım (§4 — salınım ölçülmeden "iyileşti" denmez)
* `cx` işaret değişimi / s
* roll işaret değişimi / s ve |roll| p90
* görsel temas kesintisi sayısı ve süresi

---

## 3 · KARAR KURALI (sonuçtan ÖNCE yazıldı)

1. **Mekanizma kapısı geçilmezse** (deney kolu < 12 Hz) → kampanya
   GEÇERSİZ, sonuç raporlanmaz.
2. Kapı geçilirse:
   * kör süre oranı **deney kolunda daha düşük** VE her iki geçerlilik eşi
     kontrol kolunun ALTINDA değilse VE `ist_hata_m` regresyonu yoksa
     → **20/20 tavanı GİRER**.
   * kör süre iyileşti ama `ist_hata_m` bozulduysa → **karar kullanıcının**;
     sayı gizlenmez, ödünleşim yazılır.
   * kör süre iyileşmediyse → tavan KALIR, hipotez çürüdü ve bu yazılır.
3. n = 4/kol. Altındaki her sayı **"ARA VERİ, karar değil"** diye
   etiketlenir (§5.4).

---

## 4 · SONUÇ

*(koşu bitince doldurulacak — sonuca bakıp ölçüt seçmek yasak, §5.6)*

---

## 5 · KAMPANYA OLAYI — İLK DENEME ÇÖKTÜ (2026-08-24)

İlk deneme 8 uçuşun **1'ini** koşabildi. Sebep sessizce aranmadı, bulundu (§7):

**Kontrol koşusu k01 hedefi VURDU ve görev tamamlandı.** Oyun
`MISSION COMPLETED` ekranına düştü; o ekranda **SDK 12345 portu kapanıyor**
ve `'E'` (drone spawn) hiçbir şey yapmıyor. `_yeni_gorev` 4 kez boşuna 'E'
denedi, sonra 2 dakikalık tam yeniden başlatmaya gitti, o da bu ekrandan
çıkamadı → kalan 7 koşu "hazırlık: BAŞARISIZ".

**Çare:** ekran görüntüsüyle doğrulandı — bu ekranda **PLAY AGAIN**
(1920×1080'de 1530, 940) tıklanınca görev yeniden başlıyor, ardından `'E'`
ile SDK portu **açılıyor**. Süre ~15 s (tam yeniden başlatma ~2 dk).
`araclar/kadraj.py::gorev_bitti_mi` + `gorev_yeniden_oyna` eklendi ve
`_yeni_gorev`'in EN BAŞINA bağlandı.

**⛔ İLK YAZDIĞIM TANIMA KURALI TERS ÇALIŞIYORDU** — görev-sonunu `False`,
Press-E'yi `True` sanıyordu. Gerçek ekranlarda sınayınca yakalandı; eşikler
dört ekrandan ölçülüp yeniden yazıldı:

| ekran | sol_alt_std | ust_koyu | karar |
|---|---|---|---|
| GÖREV-SONU | 15.4 | 0.000 | ✔ True |
| PRESS-E | 11.6 | 0.372 | ✔ False |
| FPV (uçuşta) 1 | 38.2 | 0.000 | ✔ False |
| FPV (uçuşta) 2 | 40.4 | 0.000 | ✔ False |

Kural: uçuşta DEĞİLİZ (`sol_alt_std < 25`) VE pusula bandı YOK (`< 0.10`).

**Ders:** sistem artık hedefi düzenli vuruyor; her isabet görevi bitiriyor.
Kurtarma yolu olmadan hiçbir çok-uçuşlu kampanya tamamlanamaz.
