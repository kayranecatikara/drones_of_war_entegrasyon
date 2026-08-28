# GERÇEK SİSTEM — donanım zinciri, ölçülen sayılar, açık sorular

**Yarışma:** TEKNOFEST **Savaşan İHA AVCI DRONE Yarışması** (2026)
⚠ "Savaşan İHA Yarışması" AYRI bir yarışmadır — karıştırmayın.

**Bu belge neden var:** simülatör (DoW/UE5) ile gerçek sistem arasındaki
farkları tek yerde tutmak. Aynı bilgiyi tekrar tekrar aramamak için.

**Son güncelleme:** 2026-08-26

---

## 0 · ETİKETLEME KURALI

Her satır işaretlidir:

| işaret | anlamı |
|---|---|
| ⭐ÖLÇÜLDÜ | kendi donanımımızda, kendi ölçümümüzle |
| 📄BELGE | TEKNOFEST resmî dokümanından |
| 👤TAKIM | takım arkadaşlarından (Kayra) alınan bilgi |
| 🔢TÜRETİLDİ | ölçülen/belgelenen sayılardan hesaplandı |
| ❓AÇIK | henüz bilinmiyor |


---

## 0.5 · ⚠⚠ 2026-08-26 ÖLÇÜM RAPORU — ÖNCEKİ SAYILARIN DÜZELTMESİ

`Kamera_Olcum_Raporu.pdf` (ölçüm ekibi, Windows, 26 Ağustos 2026) bu
belgedeki bazı sayıları ÇÜRÜTTÜ. Aşağısı esastır:

| büyüklük | bu belgede yazan (ESKİ) | ⭐ÖLÇÜLEN (GEÇERLİ) |
|---|---|---|
| kaynak standardı | PAL | **NTSC** (29.2 fps sayılarak ölçüldü) |
| çalışılan kare | 720x576 @25 | **640x480 @29.2** |
| fx | 187.4 (türetilmişti) | **171.3 px** (ölçüldü, 8 aralık, 0.41 px saçılma) |
| FOV | 125° (belge) | **122 ± 6°** — belge DOĞRULANDI |
| MENZIL_C | ~345 px·m | **314 px·m** |
| tilt | 25° (belge) / 26.5° (sim) | **22 ± 2°** — İKİSİ DE YÜKSEK |
| lens projeksiyonu | "varil distorsiyonlu" sanılıyordu | **DELİK-İĞNE** (k1 = 0.006 ± 0.034, sıfırdan ayırt edilemiyor) |

⭐ **En önemli iki düzeltme:**

1. **Lens merkezde REKTİLİNEER.** `kamera.py`'nin delik-iğne modeli
   ÇALIŞIYOR. Benim "fisheye olabilir, 11° hata verir" uyarım
   ÇÜRÜDÜ — en azından kadrajın orta %28'inde.
   ⚠ Ama kenarlar HİÇ ÖLÇÜLMEDİ; çarpıklık ağırlıklı olarak orada olur.

2. **TILT yazılımda 3-4° FAZLA.** `TILT_DEG = 26.5` ölçüm aralığının
   (22 ± 2°) dışında. Doküman 25° de dışında.

⛔ **BU SAYILAR DOĞRUDAN KODA GİRİLMEZ** (ölçüm raporunun kendi uyarısı).
   Sim davranışının bozulmadığı kanıtlanmadan değişiklik yapılmaz.

### Hâlâ ölçülmemiş olanlar

- **fy, cy** → `fx/fy` oranı BİLİNMİYOR (piksel kare mi?)
- uçtan uca gecikme (⭐ AYRI OLARAK ~200 ms ölçüldü, §5)
- kare varış düzeni
- RF bozulması / açık alan ham kaydı
- kadraj KENARLARINDA çarpıklık

**Belirsizliği bitiren yol:** satranç tahtası kalibrasyonu — masa
büyüklüğünde yer yeter, kadrajın %100'ünü kapsar, tilt hassasiyeti
±3° yerine ~0.1°, ve `fx, fy, cx, cy` + çarpıklık katsayılarını
birlikte verir. Betikler ve desen ölçüm klasöründe hazır.

### 🔢 640x480'e göre hedef piksel tablosu (C = 314 px·m)

| menzil | kutu genişliği |
|---|---|
| 50 m | 6.3 px |
| 30 m | 10.5 px |
| 20 m | 15.7 px |
| 15 m | 20.9 px |
| **10 m** (istasyon eğik menzili) | **31.4 px** |
| 4 m | 78.5 px |

→ §3.5'teki hüküm DEĞİŞMEDİ: güvenilir tespit ~20 m ve içerisi,
   istasyon menzilinde (10 m, 31 px) rahat çalışır.

### NTSC / çözünürlük seçimi

Kamera NTSC yayınlıyor — bu bir SEÇİM DEĞİL, TESPİT (kamera ayarlarına
müdahalemiz yok). İyi tarafı: 30 fps > PAL'ın 25'i, tazelik lehimize.
Kötü tarafı: NTSC'de renk tonu kayabilir → eğitimde **hue jitter**
artırımı ile kapatılır.

⛔ Linux'ta kart 720x576@25 seçeneği de sunuyor — **KULLANILMAZ.**
   Kaynak NTSC iken 576 satır istemek, kartın 480 satırı yeniden
   örneklemesi demektir (sahte satır + hareket artefaktı).
   Doğrusu: **640x480** (4:3 NTSC'nin KARE PİKSELLİ biçimi) ya da
   **720x480** (BT.601, PAR 0.889 → piksel kare DEĞİL).
   Ölçüm 640x480'de yapıldı; kare piksel ihtimali yüksek ama
   `fy` ölçülmeden kesin değil.

---

## 1 · SİSTEM MİMARİSİ

Görüntü işleme **YERDE** yapılır. Drone'da hesaplama yoktur.

```
   ┌─ HAVA ────────────────────────────────────────────┐
   │  kamera (analog, öne 25° eğim, 125° FOV)          │
   │      ↓ kompozit analog video                      │
   │  2.5W VTX  ──────────────────────────►  5.8 GHz   │
   │  ELRS 2.4G alıcı  ◄───────────────────  2.4 GHz   │
   │      ↓ CRSF                                       │
   │  F4 uçuş kartı (Angle Mod)                        │
   └───────────────────────────────────────────────────┘
                    ▲                    │
              komut │                    │ video + telemetri
                    │                    ▼
   ┌─ YER ─────────────────────────────────────────────┐
   │  VRX (5.8 GHz alıcı)  ❓hangi model                │
   │      ↓ AV kablo                                   │
   │  EasierCAP / MacroSilicon MS210x  → /dev/video2   │
   │      ↓ YUYV 720x576 @25                           │
   │  A100'lü bilgisayar:  YOLO → güdüm → komut        │
   │      ↓ CRSF 40 Hz                                 │
   │  ELRS verici                                      │
   └───────────────────────────────────────────────────┘
```

⚠ Simde drone ile bilgisayar aynı makinedeydi (`drone_sdk` TCP ile oyuna).
Gerçekte iki ayrı radyo bağlantısı var ve ikisi de gecikme ekliyor.

---

## 2 · DONANIM

### 2.1 · Hava tarafı 📄BELGE

| kalem | değer |
|---|---|
| havada kalma | 25 dk |
| ağırlık | 1100 g |
| batarya | Li-ion 6S3P, 12 000 mAh |
| gövde çapı | 311 mm |
| **kamera FOV** | **125°** |
| **kamera çözünürlük** | **1500 TVL** (⚠ bkz. §3.3) |
| **kamera konumu** | **öne 25° eğim** |
| RF alıcı | ELRS 2.4G |
| video vericisi | **Analog 2.5W VTX** |
| kumanda protokolü | CRSF |
| komut gecikmesi | 10 ms + 7 ms alıcı |
| uçuş kartı | F4 (⛔ müdahale YASAK) |
| uçuş modu | Angle Mod |
| yatış / dikilme limiti | 60° / 60° |

⛔ Kamera markası/modeli **bilinmiyor** — drone takılı hâlde geldi.
   Ratel 2 sanılmıştı, o yalnız bir tahmindi. **Model önemli değil;
   davranışı ölçülecek** (§6).

### 2.2 · Yer tarafı ⭐ÖLÇÜLDÜ (`logs/olcum_kamera/`)

⭐ **TEK PARÇA CİHAZ.** Ayrı bir VRX + ayrı bir yakalama kartı YOK.
USB'ye takılan **tek bir 5.8 GHz alıcı** var; içinde hem alıcı hem
sayısallaştırıcı bulunuyor ve bilgisayara standart bir USB kamera (UVC)
gibi görünüyor. Sürücü gerektirmiyor.

```
ID 534d:0021 MacroSilicon MS210x Video Grabber [EasierCAP]
   → /dev/video2   ("USB Video", Bus 008)
```

⚠ Bu isim (`MS210x` / `EasierCAP`) cihazın **içindeki yonganın** kimliğidir,
ayrı bir ürün değildir. Bu sınıf USB VRX'lerin çoğu MacroSilicon yongası
kullanır ve USB tanımlayıcısında böyle görünür. **Fiziksel olarak elimizde
tek bir dongle var.**

⚠ `/dev/video0` **laptop'un kendi web kamerasıdır**
(`13d3:56a2 IMC Networks USB2.0 HD UVC WebCam`).
`cv2.VideoCapture(0)` YANLIŞ cihazı açar. Kart yolla açılmalı,
indeksle değil — USB takma sırası değişince sessizce web kamerasını
taramaya başlar.

### 2.3 · ⭐ÖLÇÜLDÜ — kartın verdiği formatlar

| format | boyut | kare hızı | değerlendirme |
|---|---|---|---|
| **YUYV** | **720x576** | **25** | ⭐ **NATİF — BUNU KULLAN (PAL)** |
| YUYV | 720x480 | 30 | NTSC modu |
| YUYV | 640x480 / 480x320 / 320x240 | 30 | küçültülmüş |
| MJPG | 1920x1080 | 30 | ⛔ **SAHTE** (bkz. aşağı) |
| MJPG | 1280x720 | 60 | ⛔ sahte + tekrar kare |
| MJPG | 720x576 | 60 | ⛔ kaynak 25 fps, yarısı tekrar |

⛔ **MJPG BÜYÜK BOYUTLARI KULLANILMAZ.** Analog kompozit sinyalin içinde
1920x1080'lik bilgi YOKTUR. Kart 720x576'yı içeride büyütür ve JPEG'e
sıkıştırır: **interpolasyon bulanıklığı + sıkıştırma artefaktı, sıfır
kazanç.** Büyütme gerekirse KENDİMİZ kontrollü yaparız.

Aynı şekilde 60 fps sahte: PAL kaynağı 25 fps, kalanı tekrar karedir.

**USB bant genişliği:** 720x576x2 bayt x 25 = **20.7 MB/s**.
USB 2.0'ın pratik ~35 MB/s'si içinde, sorun yok.

---

## 3 · GÖRÜNTÜ — sim ile gerçek arasındaki fark

### 3.1 · ⭐ÖLÇÜLDÜ — kaynak PAL, 720x576, 25 fps

`logs/olcum_kamera/01_ilk_kare.png` (720x576 RGB).

| | simülatör (DoW) | **gerçek** |
|---|---|---|
| çözünürlük | 1920x1080 | **720x576** |
| kare hızı | 60-120 (oyun) | **25** |
| standart | — | **PAL** |
| renk tonu kararlılığı | tam | PAL → kararlı (NTSC olsaydı kayardı) |
| gürültü | yok | RF'e ve menzile bağlı |
| gecikme | ~0 | **~200 ms** (§5) |

### 3.2 · 🔢TÜRETİLDİ — kamera geometrisi

125° FOV, 720 piksel genişlik, delik-iğne varsayımıyla:

```
fx = (720/2) / tan(125°/2) = 360 / 1.921 = 187.4 px
```

PAL 720x576 pikselleri **KARE DEĞİLDİR** (PAR ~ 1.067). 4:3 sensörden:

```
fy ~ 199.9 px          fx/fy = 0.937   → %6.7 fark
```

⛔ `dow/gorus/kamera.py:59`'daki `F_PX = 540.4  # fx = fy (kare piksel)`
   varsayımı GERÇEKTE GEÇERSİZDİR. Bu %6.7 kerteriz hesabına sistematik
   hata olarak girer.

Menzil sabiti (S = 1.718 m Talon kanat açıklığı, 1.07 = ölçülmüş bbox
taşma payı):

```
C = fx · S · 1.07 = 187.4 x 1.718 x 1.07 ~ 345 px·m       (sim: 997)
```

⚡ İlginç: `dow/gudum/ibvs.py:33` "FX=166.6/CX=320 @640" diyor — eski
GAZEBO geometrisi gerçek kameraya DoW'dan çok daha yakın. O dönemin
sabitleri çöp değil.

### 3.3 · ⚠ "1500 TVL" yazılıma ULAŞMIYOR

**TVL** = kameranın sensör+lensinin çözebildiği yatay detay, yani
kameranın KENDİ yeteneği. O detayın yazılıma ulaşması için tüm zinciri
geçmesi gerekir:

1. Kompozit kodlama — luma bant genişliği yatayda ~440-520 satırla sınırlı
   (kamera 1500 de olsa 3000 de olsa)
2. 5.8 GHz analog yayın — gürültü ekler
3. **MS210x sayısallaştırma — 720 piksel**

**Bağlayıcı kısıt kamera değil, 720 piksellik sayısallaştırma.**
Planlamayı §3.4'teki tabloya göre yapın, 1500 TVL'ye göre değil.

### 3.4 · 🔢TÜRETİLDİ — hedef kaç piksel olacak (p = 345/R)

| menzil | **gerçek (720x576)** | sim (1920x1080) |
|---|---|---|
| 50 m | **6.9 px** | 19.9 px |
| 30 m | **11.5 px** | 33.2 px |
| 20 m | **17.2 px** | 49.9 px |
| 15 m | **23.0 px** | 66.5 px |
| **10 m** (istasyon eğik menzili) | **34.5 px** | 99.7 px |
| 8 m | 43.1 px | 124.6 px |
| 4 m | 86 px | 249 px |

**Her şey 2.9 kat küçülüyor.**

### 3.5 · ⭐ SONUÇ — görsel devir menzili ~50 m'den ~20 m'ye iner

`dow/gorus/dedektor.py:99-105`'teki kendi eşleştirilmiş ölçümümüz
(n=788 kare) "ağın gördüğü piksel sayısı"na göre şunu diyor:

| ağın gördüğü kutu | tespit | gerçekte karşılık gelen menzil |
|---|---|---|
| 30-40 px | %89 | ~8-10 m |
| 22-30 px | %69 | ~11-15 m |
| 15-22 px | %87 | ~16-23 m |
| **< 15 px** | **%6** | **> 23 m** |

> **Güvenilir görsel tespit ~20 m ve içerisi. 30 m ötesi pratikte kör.**
> `DEVIR_MENZIL_M = 50.0` gerçekçi DEĞİL; ~20 m olmalı.

⭐ **İyi haber:** istasyon geometrimiz (`ISTASYON_MENZIL_M=8` arka,
oran 0.75 → 6 m alt, eğik menzil **10 m**) hedefi **34.5 px**'te tutuyor.
Orası rahat çalışır. Kaybedilen şey 20-50 m'lik ERKEN YAKALAMA bandı.

⚠ Bu yüzden **GPS fazı artık çok daha kritik.** GNSS karıştırma altında
   aracı 20 m'ye getiremezsek görsel faz hiç başlamaz.

### 3.6 · ⭐ÖLÇÜLDÜ — ham kareden gözlemler

`logs/olcum_kamera/01_ilk_kare.png`:

- **OSD AÇIK**: `C8 5945`, RSSI çubukları, `RSSI LOW`, `0.25A`, `1 mAh`,
  `4.08v`, `24.5v`, `LAT 0.0000000`, `LON 0.0000000`, `ANGL`, `ALT 0 M`,
  pusula şeridi (S W N), ev oku. Uçuş kartı OSD'si (Betaflight/INAV tarzı).
  → 👤TAKIM: **kapatılabiliyor.** Kapatılmalı (§4.2).
- **Lens belirgin VARİL DİSTORSİYONLU**: karedeki ahşap kirişler ve masa
  kenarları kavisli, köşelerde vinyetleme var.
  → ⛔ `kamera.py`'deki delik-iğne modeli kadraj kenarlarında hata verecek.
  → ❓ Kaç derece? Ölçüm bekliyor (§6.2).
- **Kalite bu karede iyi AMA TEMSİLİ DEĞİL**: tezgâhta, `0MW` (pit/sıfır
  güç) modunda, birkaç santimden alınmış. Gerçek uçuşta 100-500 m'de
  RF gürültüsü, kar, yatay çizgiler ve kopmalar olacak.
- Interlace (tarak) bu karede görünmüyor ama sahne DURAĞAN.

---

## 4 · KARARLAR

### 4.1 · ⭐ Kaynak ayarı

```
cihaz     : /dev/video2   (YOLLA aç, indeksle DEĞİL)
format    : YUYV
boyut     : 720 x 576
kare hızı : 25
tampon    : CAP_PROP_BUFFERSIZE = 1
```

### 4.2 · OSD KAPATILACAK

Sebep: `talon_v5` eğitilirken uğraşılan "OSD hard-negatif" yanlış-pozitif
sınıfını tamamen ortadan kaldırır. Bedava kazanç.
⚠ Kapatıldıktan sonra eğitim seti de OSD'siz olmalı.

### 4.3 · Kamera modeli kaynağa bağlı hale gelmeli

- `fx != fy` desteklenmeli (§3.2)
- `MENZIL_C` gibi piksel sabitleri yerine açısal formül:
  `R = S / (2·tan(alfa/2))` — çözünürlükten BAĞIMSIZ
- Lens projeksiyonu ölçülene kadar delik-iğne modeli ŞÜPHELİ

### 4.4 · Sim tavanları gerçekte GEÇERSİZ

`GORSEL_DET_HZ=10`, `PANEL_YAKALA_HZ=15`, `PANEL_DET_HZ=5` — hepsi
"ekran yakalama oyunun GPU'sunu senkrona zorluyor" darboğazına karşı
ayarlandı (`ayarlar.py:60-75`). Gerçekte oyun yok, GPU adanmış, yakalama
USB'den DMA ile geliyor. **Bu tavanlar sahada bedava başarımı yere bırakır.**

---

## 5 · ⛔ GECİKME — sistemin en büyük sorunu

### 5.0 · ⭐⭐ 2026-08-27 — KESİN ÖLÇÜM (n=900, üç kol, dönüşümlü)

`araclar/olcum/07_otomatik.py` · ArUco işaret yöntemi · `logs/gecikme/SONUC.txt`

**İKİ KAMPANYA, ALTI YÖNTEM, 1800 ÖLÇÜM.**

| kol | yöntem | n | medyan |
|---|---|---|---|
| **A** | taban, düz `cv2.read()` YUYV | 300 | **166 ms** |
| B | `BUFFERSIZE=1` (sürücü kabul etti: `geri okunan 1.0`) | 300 | 165 ms |
| C | boşaltma (drain) — kuyruktaki bayat kareleri at | 300 | 166 ms |
| D | **ffmpeg borusu** (`-fflags nobuffer -flags low_delay`) | 300 | 165 ms |
| E | **gst-launch borusu** (`io-mode=2`, `sync=false`) | 300 | 167 ms |
| F | **natif MJPG 640×480** | 300 | 165 ms |

> ⛔⛔ **HÜKÜM: YAZILIM TARAFINDA ALINACAK YOL KALMADI.**
> Altı yöntemin hepsi **1-2 ms** içinde aynı. Sürücü tamponu, kullanıcı
> tarafı boşaltma, OpenCV'yi tamamen atlayan iki ayrı harici boru hattı,
> ve sıkıştırılmış aktarım — **hiçbiri hiçbir şey değiştirmedi.**

#### ⛔ ÇÜRÜYEN HİPOTEZ — USB aktarım süresi

"640×480 YUYV = 614 KB/kare, USB 2.0'da ~18 ms sürer; MJPG'ye geçince
~50 KB olur ve ~15 ms kazanırız" diye tahmin edilmişti. **ÇÜRÜDÜ:**
MJPG kolu (F) tabanla aynı çıktı (165 vs 166 ms).

Bunun anlamı: **darboğaz aktarımdan ÖNCE**, cihazın kendi
sayısallaştırıcısında/tamponunda. Yükü küçültmek beklemeyi kısaltmıyor,
çünkü bekleme iletimde değil.

Bu, §6'daki ön teşhisi (kare varış düzeni: kuyruk sığ, %0 anlık kare)
bağımsız olarak **doğruluyor**. İki farklı yöntem aynı sonuca vardı.

**Dağılım dar** (%10-%90 arası yalnız ~30 ms): gecikme kararlı ve
sabit — rastgele takılma değil, **yapısal**.

#### 🔢 Kalan 166 ms nerede

| adım | tahmin | dayanak |
|---|---|---|
| kamera pozlama + kompozit kodlama | 10-20 ms | tipik analog FPV kamera |
| NTSC kare bütünlenmesi | ~33 ms | 29.97 fps, yapısal, kaçınılmaz |
| **VRX dongle iç tamponu** | **~90 ms** | ⭐ **kalan pay — baskın kalem** |
| monitör + pencere yöneticisi | 20-25 ms | güdüm bunu ÖDEMEZ |

**Güdümün gerçekte ödediği: ~140 ms.**
Tam döngü: 140 + YOLO(~15) + komut 40 Hz(25) + link(10+7) ≈ **200 ms**.

#### Sıradaki seçenekler — ikisi KAPANDI, biri kaldı

| yol | durum |
|---|---|
| Yazılım/sürücü/boru hattı ayarları | ⛔ **TÜKENDİ** — 6 yöntem, 1800 ölçüm, fark yok |
| Başka VRX donanımı | ⛔ **YOK** — yarışmada donanım değiştirilemiyor |
| ⭐ **Gecikme telafisi** (50 Hz telemetriyle ileri kestirim) | ✅ **TEK KALAN YOL** |

⭐ Telemetri **50 Hz ve taze**, video **140 ms bayat**. Kareyi işlerken
kullanılacak duruş "şu anki" değil, **kare çekildiği andaki** duruş
olmalı; sonra o kerteriz taze telemetriyle bugüne taşınmalı. Mevcut
"köprü" mekanizması (`kerteriz_piksel`) bunun tohumu.

### 5.1 · İLK (kaba) ÖLÇÜM: ~200 ms — elle, kronometreyle

Kronometre yöntemi (ekranda milisaniyeli kronometre → kamera ona bakıyor →
yakalanan karedeki sayı ile canlı sayı karşılaştırıldı):

> **kamera → ekranda görünene kadar ~200 ms**

### 5.2 · Neden kritik

Simde ölçülen `kutu yaşı` medyanı **0.040 s**. Gerçekte taşıma gecikmesi
tek başına bunun **5 katı**.

Kapanma hızı 25 m/s iken:
```
25 m/s x 0.20 s = 5.0 metre
```
Yani nişan aldığımız dünya **5 metre eski**. Angajman menzili ~10 m
olduğu için bu, menzilin YARISI kadar hata demektir.

### 5.3 · 🔢TÜRETİLDİ — dökümü (tahmin, doğrulanmalı)

| # | adım | tahmin | not |
|---|---|---|---|
| 1 | kamera pozlama + okuma + kompozit kodlama | 10-20 ms | veri sayfası bilinmiyor |
| 2 | VTX modülasyon + RF + VRX demodülasyon | **< 1 ms** | analog anlıktır |
| 3 | PAL kare bütünlenmesi | **20-40 ms** | yapısal, kaçınılmaz (25 fps) |
| 4 | **VRX dongle sayısallaştırma + iç tampon** | **~90 ms** | ⭐ ÖLÇÜLDÜ: BASKIN KALEM |
| 5 | V4L2 sürücü kuyruğu | **~0 ms** | ⛔ ÖLÇÜLDÜ (§5.0): katkısı YOK |
| 6 | OpenCV grab + renk çevrimi | 3-8 ms | |
| 7 | ekrana basma (monitör + pencere yöneticisi) | **16-40 ms** | ⚠ GÜDÜM BUNU ÖDEMEZ |

Orta değerler toplamı ~196 ms — ölçülen 200 ms ile tutarlı.

**Güdümün gerçekte ödediği:** 200 − ekran(~25) = **~175 ms**
**Tam döngü:** 175 + YOLO(~15) + komut(40 Hz → 25 ms) + link(10+7) =
**~230 ms** (foton → kanatçık)

### 5.4 · Ne yapılabilir

| çare | kazanç | bedel |
|---|---|---|
| `CAP_PROP_BUFFERSIZE=1` | **0-160 ms** | yok — ÖNCE BU DENENİR |
| GStreamer `drop=true max-buffers=1` | aynı, daha güvenilir | boru hattı karmaşıklığı |
| ekrana basmayı güdüm yolundan çıkar | ~25 ms | panel ayrı iş parçacığına |
| başka yakalama kartı | 40-120 ms | donanım değişikliği |
| **ileri kestirim (dead reckoning)** | gecikmeyi TELAFİ eder | karmaşıklık |

⭐ **En önemli fikir:** telemetri **50 Hz ve taze**, video **200 ms bayat**.
   Yani kareyi işlerken kullanılacak duruş, "şu anki" duruş DEĞİL,
   **kare çekildiği andaki** duruştur. Doğru yapı:
   1. duruşu zaman damgasıyla halka tampona yaz
   2. kare gelince `t_kare = t_varis − 175 ms` hesapla
   3. tampondan O ANA ait duruşu çek → kerteriz doğru çıkar
   4. o kerterizi bugüne kadar taze telemetriyle ileri taşı

   Mevcut "köprü" mekanizmanız (`kerteriz_piksel`) bunun tohumu.

---

## 5.5 · ⭐ AŞAMA 1 — bayatlığın gerçek bedeli (2026-08-27, çevrimdışı)

`araclar/olcum/08_bayatlik_olc.py` · 7 koşu, 657 ardışık kutu çifti

**Soru:** kareyi 145 ms geç işlersek hedef kadrajda ne kadar kaymış olur?
**Yöntem:** model değil DOĞRUDAN ölçüm — ardışık iki tespit arasında
kutunun kaç piksel kaydığına bakıldı, 145 ms'e ölçeklendi. Sonuçlar
AÇI olarak verildi (çözünürlükten bağımsız).

| | medyan | %90 | %95 | en kötü |
|---|---|---|---|---|
| yatay | **0.30°** | 1.17° | 1.76° | 6.43° |
| dikey | **0.97°** | 2.59° | 3.38° | 8.09° |

Gerçek kamerada (640×480, fx=171.3): yatay medyan **0.9 px**, %90 3.5 px.

**Hedefin kendi boyutuyla kıyas** (asıl anlamlı ölçü):

| menzil | n | %90 kayma (px) | kutu genişliği (px) | oran |
|---|---|---|---|---|
| 0-5 m | 38 | 13.8 | 125.6 | **0.11** |
| 5-8 m | 48 | 5.5 | 48.3 | **0.11** |
| 8-15 m | 250 | 3.7 | 27.3 | **0.13** |
| 15-25 m | 274 | 2.7 | 15.7 | 0.17 |
| 25-60 m | 47 | 3.7 | 7.4 | 0.50 |

⭐ **Angajman bandında (0-15 m) bayat kutu, hedefin kendi genişliğinin
yalnız %11-13'ü kadar kayıyor.** Yani 145 ms eski bir kutu hâlâ hedefin
İÇİNİ gösteriyor.

### ⛔ ÇÜRÜYEN KENDİ HÜKMÜM

"118 °/s dönüş × 0.145 s = **16.5° nişan hatası**, 5 m'de 1.4 m ıska"
demiştim. **ÇOK KARAMSARDI.** 118 °/s aracın *yapabildiği* azami dönüş;
gerçekte ölçülen yatış hızı medyan **3 °/s**, %90 **16 °/s**. Yani
145 ms'de yatış değişimi medyan 0.4°, %90 2.3°.

### ⚠ AMA BU SORUYU KAPATMIYOR — üç sınır

1. **Kapalı çevrim etkisi ölçülemedi.** Bu loglar gecikmesiz simden.
   Döngüye 145 ms girince araç SALINABİLİR (gecikmeli geri besleme),
   salınım da kaymayı büyütür. Bu geri besleme etkisi çevrimdışı
   analizde **görünmez**.
2. **Örnekleme yetersiz (§5.3).** `cikarim.csv` 9.2 Hz (108 ms), ölçülen
   pencere 145 ms → oran 1.3, §5.3'ün istediği 5 kat değil. Hızlı
   geçişler görünmüyor → sayı ALT SINIR.
3. **Geçerlilik eşi (§5.2).** Δ yalnız kutu İKİ karede de varken
   hesaplandı; tespitin koptuğu %45'lik kısım elendi ve onlar
   muhtemelen en hareketli anlar → yine ALT SINIR.

### Bundan çıkan karar

Gecikme telafisi **acil değil, ama gerekli olup olmadığı bilinmiyor.**
Doğru sıradaki soru "telafiyi nasıl yazarız" değil:

> **"145 ms gecikme, kapalı çevrimde gerçekten zarar veriyor mu?"**

Cevabı yalnız sime gecikme enjekte edip uçmak verir (§5.6).

---

## 6 · ÖLÇÜLECEKLER (henüz yapılmadı)

### 6.1 · Gecikme dökümü — hangi adım kaç ms
1. `CAP_PROP_BUFFERSIZE=1` ile kronometre testini TEKRARLA.
   Sayı çok düşerse → yazılım tamponu, BEDAVA düzeliyor.
   ~200'de kalırsa → kartın donanımı, farklı kart gerekir.
2. VRX'in AV çıkışını doğrudan analog monitöre/gözlüğe ver, aynı testi yap.
   Bu, kart+PC'yi tamamen atlar → aradaki fark kartın payıdır.

### 6.2 · ⭐ Lens projeksiyon eğrisi (en yüksek riskli bilinmeyen)
1. Drone'u duvardan **D = 2 m** uzağa, kamerası duvara dik sabitle
   (pervaneler SÖKÜLÜ).
2. Duvara optik eksenden itibaren yatayda **her 20 cm'de** işaret koy.
3. Bir kare kaydet, her işaretin **piksel x**'ini oku.
4. `theta = atan(X/D)`, `r = x − 360`.
5. `r` ~ `tan(theta)` ise **delik-iğne** (mevcut model doğru);
   `r` ~ `theta` (düz çizgi) ise **fisheye** (model değişmeli).
6. Dikeyde tekrarla → `fy` ve piksel kareliği.

Bu ölçüm aynı anda gerçek `fx`, `fy` ve gerçek FOV'u da verir.

### 6.3 · Kameranın gerçek eğimi 25° mi
Drone tam yatay bir yüzeyde, karşıda bilinen yükseklikte işaret;
işaretin `cy` pikselinden eğimi geri hesapla.
(Simde 26.5° ölçülmüştü, doküman 25 diyor, gerçekte üçüncü bir
değer olabilir.)

### 6.4 · Gerçek uçuş kaydı — EĞİTİM VERİSİ
OSD kapalı, dışarıda, 50-200 m'den, gökyüzü arka planlı.
Talon + FPV drone test uçuşlarında kayıt alınacak.
**Şu an elimizdeki tek kare tezgâhtan ve 0MW'den — temsili değil.**

---

## 7 · TELEMETRİ ve KOMUT 👤TAKIM

| kalem | değer | kaynak |
|---|---|---|
| **ELRS telemetri (hepsi)** | **50 Hz** | 👤 Kayra |
| **hedef aracın konumu (JSON)** | **5 Hz** | 👤 |
| komut gönderim hızı | **40 Hz** (1000 Hz'e kadar mümkün) | 👤 |
| protokol | ELRS / CRSF | 👤 + 📄 |
| komut gecikmesi | 10 ms + 7 ms alıcı | 📄 |

⭐ 50 Hz duruş verisi İYİ HABER: `los_seviye(cx, cy, roll, pitch)`
   hesabı için fazlasıyla yeterli (20 ms bayatlık → ~2° hata).
   Asıl sorun duruş değil, VİDEO gecikmesi (§5).

⚠ Hedef konumu 5 Hz = 200 ms. Hedef 18 m/s giderse iki güncelleme arası
   **3.6 m** yol alır. İstasyon tutma bunu tolere eder (simde 1 Hz'di),
   ama hedef HIZINI bu kanaldan türetmek gürültülü olur.

---

## 8 · YARIŞMA KOŞULLARI 📄BELGE + 👤TAKIM

- Müsabakada **tam otonom** uçuş zorunlu. Manuel yalnız test öncesinde.
- **GNSS karıştırma (jamming) altında** uçulacak. ❓Nasıl karıştırılacağı
  BİLİNMİYOR — GPS fazı "hassas" değil "dayanıklı" kurulmalı.
- Müsabaka bilgisayarı: **A100 GPU'lu**, organizasyon veriyor. 👤
- Hedef İHA: **X-UAV Talon 1718 mm** — simdekiyle AYNI. 📄
- Uçuş kartına müdahale YASAK. 📄

---

## 9 · A100 NE DEĞİŞTİRİYOR

| konu | RTX 4060 (geliştirme) | A100 (yarışma) |
|---|---|---|
| çıkarım süresi | 18.6 ms (fp16, imgsz 1920) | tahminen 6-10 ms |
| `GORSEL_DET_HZ=10` tavanı | oyunla GPU paylaşımı yüzünden zorunlu | **gereksiz** |
| model boyutu | YOLO11s mecburiyeti | **YOLO11l / 11x** rahat |
| büyütme (720 → 1440 tarama) | pahalı | **bedava** |

⭐ **Sıradaki en yüksek getirili deney:** 720x576'da hedef 17-35 piksel.
YOLO'nun en ince ızgarası stride-8; 17 px'lik hedef `imgsz=720`'de
~2x2 hücreye düşer. Kareyi 2 kat büyütüp beslersek 4x4 hücreye yayılır.
Yeni bilgi eklenmez ama ağa çalışacak yer açılır.
⚠ Bu bir ÇIKARIM ayarı değil, **EĞİTİM kararıdır** — model o ölçekte
eğitilmeliyse. Ölçülmeden hüküm kurulmaz.

---

## 10 · ⛔ EN BÜYÜK RİSK — eğitim domeni

Şu anki tüm eğitim verisi **UE5'in 1920x1080 temiz ekran görüntüleri.**
Müsabakada model ilk kez şunu görecek: **720x576 PAL, analog gürültülü,
RF bozulmalı, 2.9 kat küçük hedefli, 200 ms bayat.**

⚠ Aynı sınıftan bir hata ZATEN YAŞANDI: sadece kırmızı-mavi kanalların
yer değişmesi tespiti %68.6 → %32.1, imhayı 4/4 → 1/4 yaptı
(`docs/kampanya/KANAL_BGR_RGB.md`). **Domain farkı bundan çok daha büyük.**

Çare (müsabakadan ÖNCE yapılabilir):
1. **Test uçuşlarında kayıt al** — Talon uçtuğu her dakika etiketli veri.
   (👤 planlanıyor.)
2. **Çevirici** — sim karelerini analog zincirden geçirip eğitime kat.
   Artık elimizde GERÇEK bir referans kare var; çeviricinin parametreleri
   ona bakılarak ayarlanabilir.

---

## 11 · AÇIK SORULAR ❓

| # | soru | kime |
|---|---|---|
| 1 | EasierCAP'i besleyen VRX hangi model? Kaç anteni var? | takım |
| 2 | 5.8G USB dongle hâlâ planda mı, yoksa VRX+EasierCAP mi kesin? | takım |
| 3 | Telemetri JSON'ında zaman damgası var mı? | takım |
| 4 | Lens projeksiyon eğrisi (§6.2) | ölçüm |
| 5 | Gecikme dökümü (§6.1) | ölçüm |
| 6 | Kameranın gerçek eğimi (§6.3) | ölçüm |
| 7 | GNSS karıştırma nasıl olacak? | organizasyon |
| 8 | Müsabakada video kaydı alınabilir mi? | organizasyon |

---

## 12 · KAYNAKLAR

- TEKNOFEST 2026 Avcı Drone Bilgilendirme Dokümanı (6 sayfa)
- https://www.teknofest.org/tr/yarismalar/savasan-iha-avci-drone-yarismasi/
- `logs/olcum_kamera/` — 01_devices.txt, 01_lsusb.txt, 01_formats.txt,
  01_ilk_kare.png
- `docs/kampanya/KANAL_BGR_RGB.md` — domain hatasının bedeli
- `docs/GECIKME_2026_08_24.md` — simdeki gecikme teşhisi
