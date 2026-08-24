# KAMPANYA ISP — GÖRÜŞ İŞ PARÇACIĞI

**Tarih:** 2026-08-24 · **Kol başına n = 4** · 8 uçuş · dönüşümlü I,K,I,K…

---

## 0 · HZ4 NE ÖĞRETTİ

HZ4 kampanyası "tavanı kaldıralım" hipotezini sınadı ve **kendi
açıklamamı çürüttü.**

Tavanların gerekçesi olarak 22 Ağustos'ta şunu yazmıştım: *"YOLO ve oyun
aynı GPU'da; çıkarım hızlanınca oyun aç kalır."* HZ4 verisi bunun asıl
mekanizma OLMADIĞINI gösterdi:

| | KONTROL 15/10 | DENEY 20/20 |
|---|---|---|
| ulaşılan çıkarım | 9.27 Hz | 16.21 Hz ✔ |
| **kontrol döngüsü** | **40.3 Hz** | **22.3 Hz** ⛔ |
| çıkarım süresi | 36.7 ms | 50.8 ms |
| görsel devir | 23.1 s / 14.5 m | **hiç olmadı** |
| ISTASYON hata | 8.25 m | 16.53 m |
| isabet | **1** (en yakın 1.23 m) | 0 (en yakın 6.21 m) |

Kontrol döngüsü neredeyse YARIYA düştü. Sebep GPU değil, **blokaj**:
bizde `beyin.gorsel_tik()` kontrol döngüsünün İÇİNDE çağrılıyor, yani
her çıkarımda güdüm 37-51 ms boyunca DURUYOR. Çıkarımı sıklaştırmak
doğrudan kontrol bant genişliğini yiyor.

16.2 × 50.8 ms = saniyenin **%82'si** YOLO'da (kontrolde %34).

**Tavan bir çözüm değil, bu blokajın semptomuymuş.**

---

## 1 · ONLARIN MİMARİSİ

`avci-drone-yer-kontrol` `model-fps`, `web/server.py`:

```python
threading.Thread(target=kontrol_dongusu, daemon=True).start()    # time.sleep(0.02) = 50 Hz
threading.Thread(target=dedektor_dongusu, daemon=True).start()   # tavan YOK
```

`dedektor_dongusu` sonu: *"kare varsa inference kendi hizinda pace'lenir
(GPU ~30-60 FPS); ekstra sleep YOK"*. Güdüm, dedektörün son çıktısını
`AlgiHatti.son_cikti()` ile **kilitli anlık görüntüden** okur.

Yani onlarda tavan olmamasının sebebi hızlı GPU değil — **YOLO'nun güdümü
hiç bloke etmemesi.**

---

## 2 · BİZDE YAPILAN

`Ayar.GORUS_ISP` (kill-switch, **varsayılan KAPALI**):

* **AÇIK:** `beyin.gorsel_tik()` görüş iş parçacığında koşar; kontrol
  döngüsü `_gorus["tespit"]`i kilitli okur, YOLO'yu BEKLEMEZ.
* **KAPALI:** eski yol bit bit aynı (bekçi B43).

**Yarış koşulu çareleri:**
* `Beyin._kilit_g` (RLock) — `gorsel_tik` gövdesi ve faz geçişindeki
  `iz.sifirla()` / `kilit.reset()` aynı kilit altında (bekçi B45).
* **SDK soketi tek iş parçacığında kalır**: görüş yalnız ham sonucu
  kuyruğa koyar; `cikarim.csv` satırını (truth kanalına dokunduğu için)
  kontrol döngüsü kurar (bekçi B44).
* İki YOLO aynı anda koşmaz — panel dedektörü `GORSEL_AKTIF` iken zaten
  kapalı (bekçi B43).

**DUMAN TESTİ (n=1, karar değil):** kontrol döngüsü 22.3 → **46.9 Hz**,
görsel devir 15.3 s / 14.0 m, **isabet 1**, en yakın **0.47 m**.

---

## 3 · ÖLÇÜTLER — KOŞMADAN ÖNCE İLAN EDİLDİ

| rol | ölçüt |
|---|---|
| **BİRİNCİL** | kör süre oranı (kutu yaşı > 0.3 s olan zamanın payı) |
| **MEKANİZMA (§5.1)** | deney kolunda kontrol döngüsü **≥ 35 Hz** VE çıkarım **≥ 10 Hz**; geçilmezse koşu GEÇERSİZ |
| **GEÇERLİLİK EŞİ (§5.2)** | görsel temas oranı + tespit% |
| **⛔ REGRESYON (§5.10)** | `ist_hata_m` istasyon tutma |
| **İKİNCİL** | isabet, en_yakın_m, görsel devir menzili |
| **SALINIM (§4)** | roll işaret değişimi/s, \|roll\| p90, cx işaret değişimi/s |

**Tek değişken:** mimari. Takipçi KAPALI (`DOW_TAKIP=0`) her iki kolda.

### Etki alanı tablosu (§5.10)

| etkilenebilecek davranış | neden | nerede sınanır |
|---|---|---|
| GPS istasyon tutma | kontrol bant genişliği değişiyor | her koşunun ISTASYON fazı |
| kutu yaşı | çıkarım artık kontrol tikinden bağımsız | birincil ölçüt |
| görüş durumu tutarlılığı | iki iş parçacığı aynı durumu elliyor | bekçi B45 + kesinti sayısı |
| telemetri/CSV bütünlüğü | iki iş parçacığı yazarsa bozulur | bekçi B44 (yapısal garanti) |

---

## 4 · KARAR KURALI (sonuçtan ÖNCE)

1. Mekanizma kapısı geçilmezse → kampanya GEÇERSİZ.
2. Geçilirse:
   * kör süre **deney kolunda düşük** VE geçerlilik eşleri kontrolün
     altında değil VE `ist_hata_m` bozulmadı → **GORUS_ISP AÇILIR**.
   * kör süre iyileşti ama istasyon bozulduysa → **karar kullanıcının**.
   * iyileşme yoksa → KAPALI kalır, hipotez çürüdü ve yazılır.
3. n = 4/kol; altındaki her sayı "ARA VERİ, karar değil" (§5.4).

---

## 5 · SONUÇ

*(koşu bitince doldurulacak)*

---

## 6 · KAMPANYA OLAYI — GÖREV-SONU EKRANI, ÜÇ YANLIŞ DENEME

ISP'nin ilk denemesi **4 koşu üst üste** "hazırlık: BAŞARISIZ" verdi ve
kurtarma **hiç tetiklenmedi**. İki ayrı hata vardı:

**(a) Yanlış yere bağlanmıştı.** Kurtarmayı `kosu.py::_yeni_gorev`'e
koymuştum — o, TEK SÜRECİN İÇİNDEKİ koşular arası çalışır. Kampanyada her
koşu **ayrı süreçtir** ve engel `kadraj.py::hazirla()`dadır. Oraya taşındı.

**(b) Tanıma kuralı üç kez yanlış yazıldı.** Hepsi kayıtta duruyor çünkü
üçü de aynı sınıf hatanın farklı yüzü:

| # | kural | neden düştü |
|---|---|---|
| 1 | "ortada parlak yazı bandı" | MISSION COMPLETED yazısı kum rengi arazide DÜŞÜK kontrastlı — hiç yakalamadı |
| 2 | "üst pusula bandında koyu piksel < 0.10" | **SAHNEYE bağlı**: bir karede üst bant gökyüzü (0.000 ✔), diğerinde koyu tepeler (0.193 ✗) |
| 3 | "PLAY AGAIN bölgesinde >195 parlak piksel" | doğru ÖĞE, **yanlış eşik**: ham piksellerde düğme yazısı en fazla **191**. Kayıtlı JPEG'de sıkıştırma artefaktı 195'i aşırıyordu → **test geçiyor, canlı düşüyordu** |

**Doğrusu — FARK TABANLI kural:** PLAY AGAIN düğmesinin bölgesi, AYNI
YÜKSEKLİKTEKİ boş şeritle kıyaslanır (eşik 170).

| ekran | sağ_düğme | boş_şerit | fark | alt_std |
|---|---|---|---|---|
| GÖREV-SONU ×3 | 0.091 | 0.000 | **+0.091** | 15-17 |
| PRESS-E | 0.000 | 0.005 | −0.004 | 11.6 |
| FPV ×4 | 0.000-0.402 | 0.021-0.807 | −0.02…−0.40 | 36-43 |

Fark tabanlı olması **şart**: FPV'de düğme bölgesi de parlak olabiliyor
(0.402), ama o zaman yanındaki şerit DE parlak (0.807). Görev-sonunda
yalnız düğmenin olduğu yer parlak. Sahne parlaklığı ikisini eşit etkiler,
fark sabit kalır.

**Canlı doğrulandı:** `hazirla()` görev-sonunu tanıdı → PLAY AGAIN → 'E' →
SDK portu açıldı (41 s).

**Bekçi B46** eklendi: 3 görev-sonu + 5 negatif GERÇEK kare
(`tests/ekranlar/`). Dördüncü yanlış denemeyi bu yakalar.

**Ders:** ekran tanıma kuralı **arayüz öğesine** dayanmalı, sahneye değil;
ve eşik **canlı ham karede** doğrulanmalı — kayıtlı JPEG'de doğrulamak
yanıltıyor.

---

## 7 · ISP2 — VERİ KAYBI (§5.7) VE KURTARILAN ARA VERİ

**⛔ Kampanya betiğim 8 geçerli koşunun 6'sını YOK ETTİ.** `kosu.py` aynı
adla çağrıldığında `logs/<AD>/k01` ve `ozet.csv`'yi **ezer**; ben her uçuşu
`kosu.py ISP2_I 1 150` diye ayrı süreçte ama AYNI ADLA koştum. Kol başına
yalnız SON koşu kaldı.

`kosu.py` suçlu değil — o, `kosu.py AD 4 150` ile tek süreçte 4 uçuş
yazacak şekilde tasarlanmış. Ama A/B'de env dönüşümlü değişmeli, yani her
uçuş ayrı süreç OLMALI (§4). Doğru çözüm: **her koşuya ayrı ad**
(`ISP3_I_1`, `ISP3_I_2`, …). `hz_kiyas.py` artık glob deseni kabul ediyor.

**Kurtarılan ara veri** (log özet satırlarından; kör süre KURTARILAMADI):

| | DENEY (iş parçacığı) | KONTROL (tek döngü) |
|---|---|---|
| isabet | **4/4** | **4/4** |
| en yakın medyan | **0.46 m** | 0.94 m |
| ist_hata medyan | 8.77 m | 7.11 m (bir koşu 78 m aykırı) |
| tespit% medyan | **%32.3** | **%53.9** |
| koşu süresi | ~45 s (hızlı isabet) | ~150 s |

⚠ Bu sayılar **ARA VERİ**dir; birincil ölçüt (kör süre) yok.

### ⛔ DÜZELTME — "çıkarım 24 → 50 ms yavaşladı" YANLIŞTI

Önce şöyle yazmıştım: *"deney kolunda çıkarım 24 → 50 ms; sebep görüş
iş parçacığının üç işi birden yapması."* **Ölçüm bunu çürüttü.**

`det_ms` dağılımı **İKİ TEPELİ**, çünkü dedektör uyarlanabilir çözünürlük
kullanıyor (imgsz 960 ≈ 20 ms / imgsz 1920 ≈ 52 ms). Kol içi kıyas:

| | imgsz960 kolu | imgsz1920 kolu | yavaş kolun payı |
|---|---|---|---|
| KONTROL | 19.8 ms | 51.3 ms | %46 |
| DENEY | 21.9 ms | 53.9 ms | %53 |

**Kol içinde fark yalnız %5-10.** Medyanın 24 → 50 sıçraması, yavaş kolun
payı %46'dan %53'e çıkınca medyanın TEPE DEĞİŞTİRMESİNDEN geliyor — gerçek
bir yavaşlama değil, ölçüt artefaktı.

**Ders:** iki tepeli dağılımda medyan raporlanmaz. `hz_kiyas.py` artık
ORTALAMA + iki kolun medyanı + yavaş kolun payını birlikte basıyor.

Yavaş kolun payının artması gerçek bir bulgudur ama sebebi farklı: deney
kolu hedefi daha sık kaybediyor (tespit% %54 → %32), kutu olmayınca
uyarlanabilir kural DAİMA 1920 seçiyor. Yani sebep hız değil, **tespit**.

### Gözlem: mimariyi YARIM taşımışım

Görüş iş parçacığı hâlâ ÜÇ işi birden yapıyor — ekran yakalama (20 Hz) +
YOLO + panele JPEG çizme. Onların mimarisinde bunlar AYRI:

| iş | onlarda | bizde (şimdi) |
|---|---|---|
| kare yakalama | `pencere_yakala` kendi thread'i | görüş thread'i |
| YOLO | `dedektor_dongusu` kendi thread'i | görüş thread'i |
| panel çizimi | HTTP handler (istek başına) | görüş thread'i |
| güdüm | `kontrol_dongusu` 50 Hz | kontrol döngüsü ✔ |

Yani asıl blokajı (güdüm ↔ YOLO) çözdüm ama görüş içindeki üçlü çekişme
duruyor. Tespit oranındaki düşüşün (%54 → %32) muhtemel sebebi bu.
**Sıradaki iş:** yakalamayı ve panel çizimini YOLO'dan ayırmak.

---

## 8 · ⛔ KENDİ TASARIM HATAM — İKİ DEĞİŞKEN (§4 İHLALİ)

ISP kampanyasını kurarken deney kolunda **iki şeyi birden** değiştirmişim:

| kol | GORUS_ISP | tavan |
|---|---|---|
| K (kontrol) | 0 | 15/10 |
| I (deney) | **1** | **20/20** |

Yani bu kampanya, tespit oranındaki düşüşün MİMARİDEN mi TAVANDAN mı
geldiğini **ayıramaz**. §4'ün ilk cümlesi "TEK DEĞİŞKEN" ve ben ihlal ettim.

HZ4 zaten (tek döngü, 20/20)'nin kötü olduğunu ölçmüştü. 2×2'nin durumu:

| | 15/10 Hz | 20/20 Hz |
|---|---|---|
| **tek döngü** | ✔ K — bugünkü | ✔ HZ4 deney — kötü |
| **iş parçacığı** | ⛔ **EKSİK** → kampanya ISPM | ✔ I |

**ISPM kampanyası** eksik hücreyi doldurur: `GORUS_ISP=1` ama tavan
kontrolle AYNI (15/10). Bu, mimarinin etkisini tavandan yalıtır.

### Yol boyunca çürüttüğüm iki kendi hipotezim

1. **"Görüş iş parçacığı SDK soketine dokunuyor, yarış koşulu var."**
   ÇÜRÜDÜ: `get_drone_rotation()` sokete gitmiyor — arka plandaki
   `_receive_loop` thread'inin doldurduğu telemetri sözlüğünü KİLİT ALTINDA
   okuyor (`dow/sdk/drone_sdk.py:318`). Görüş iş parçacığından çağrılması
   güvenli.

2. **"Çıkarım 24 → 50 ms yavaşladı, çünkü görüş thread'i üç iş yapıyor."**
   ÇÜRÜDÜ: dağılım iki tepeli, medyan tepe değiştiriyor; kol içi fark
   %5-10 (bkz. §7 düzeltmesi).

### Menzile göre kırılmış tespit (ARA VERİ, n=1/kol)

§5.9 gereği tür-içi kıyas — "karışım farklı" açıklamasını sınamak için:

| menzil | DENEY (I) | KONTROL (K) |
|---|---|---|
| 0-15 m | %49.0 | %66.7 |
| **15-30 m** | **%8.8** | **%43.0** |
| 30-60 m | %0 | %0 |

Karışım açıklaması **çürüdü**: fark bant İÇİNDE de var, hatta daha büyük.
Sebebin mimari mi tavan mı olduğu ISPM ile ayrılacak.

---

## 9 · SONUÇ — 2×2 (n=3/hücre, ARA VERİ)

⚠ İki koşu SDK yarışında kayboldu (aşağıda), n=4'e ulaşılamadı → §5.4
gereği **KARAR DEĞİL**.

| | **K** döngü 15/10 | **M** işprç 15/10 | **H** döngü 20/20 | **I** işprç 20/20 |
|---|---|---|---|---|
| kontrol döngüsü | 40.05 Hz | **47.20** | **22.30** ⛔ | **46.30** |
| çıkarım | 9.27 Hz | 7.02 | 16.16 | 12.26 |
| ⭐ kör süre | %31.5 | **%66.7** ⛔ | — | %29.9 |
| 🔒 GERÇEK tespit | **%45.2** | %37.3 | %28.0 | %41.0 |
| ⛔ ISTASYON hata | 8.41 m | 9.44 m | **16.68 m** | **7.69 m** |
| isabet | 1/1 | 1/1 | **0** | 1/1 |
| en yakın | 0.84 m | 0.82 m | 6.21 m | **0.79 m** |
| \|roll\| p90 | 16.08° | 8.19° | — | **2.46°** |

### Okuma

**MİMARİ TEK BAŞINA (M−K) İŞE YARAMIYOR, hatta kötü.** Kontrol döngüsü
+7.15 Hz kazanıyor ama kör süre %31.5 → %66.7'ye fırlıyor. Sebep
aritmetikte: eski tavanla görüş iş parçacığı yakalamayı 15 Hz'e sabitliyor
(`dt_yak` uykusu), çıkarım kapısı 10 Hz ile çarpışınca çıkarım
**9.27 → 7.02 Hz'e DÜŞÜYOR**. Mimari, eski tavanla kendi kendini boğuyor.

**TAVAN TEK BAŞINA (H−K) felaket** — bilinen: kontrol 22.3 Hz, isabet 0.

**İKİSİ BİRLİKTE (I−K) nötr-artı:** kör süre −1.6 puan, istasyon −0.72 m,
en yakın −0.05 m — hepsi gürültü içinde. Gürültü OLMAYAN iki şey:
kontrol döngüsü **+6.25 Hz** ve **|roll| p90 16.08° → 2.46°**.

### Karar kuralına göre

İlan edilen kural: *"kör süre düşük VE geçerlilik eşleri kontrolün ALTINDA
değilse → AÇILIR"*. Geçerlilik eşi **GERÇEK tespit %45.2 → %41.0**, yani
kontrolün ALTINDA. **Kural geçmiyor.** Sonuca bakıp kuralı değiştirmek
yasak (§5.6).

**ÖNERİ: `GORUS_ISP` KAPALI kalsın.** Mimari yalnız yüksek tavanla anlamlı;
o bileşimde de birincil ölçütte kazanç yok. Kontrol bant genişliği ve
sakinlik kazancı gerçek ama bedeli tespit oranı. **Karar kullanıcının.**

### ⛔ n=4'e ulaşılamama sebebi (düzeltildi)

Her kolda bir koşu **"SDK bağlanamadı"** ile düştü. Görev-sonu kurtarması
(PLAY AGAIN → 'E') drone'u doğuruyor ve HUD görünüyor — `hazirla()`
"UÇUŞTA" diyor — ama oyunun SDK dinleyicisi 12345 portunu **birkaç saniye
sonra** açıyor. Süreç o aralıkta bağlanmaya çalışıp ölüyordu.
**Bedeli: 8 koşunun 2'si (%25), ve kampanya karar veremez hale geldi.**

Çare: `kosu.py` artık bağlantıyı 24 saniyeye kadar yeniden deniyor.
Bu yalnız uçuş ÖNCESİ kurulum yoludur; güdüm davranışına dokunmaz.
