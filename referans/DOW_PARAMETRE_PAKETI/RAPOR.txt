# DRONES OF WAR — ARAÇ PARAMETRELERİ (ölçülmüş)

Gazebo eşleştirmesi için. **Her satırda: değer + birim + kaç örnek + nasıl elde
edildiği.** Tahmin yok. Ölçülemeyenler açıkça işaretli ve *neden* ölçülemediği
yazılı.

**Ölçüm kaynakları**

1. **`zarf_olcum.py` / `zarf_olcum2.py` / `zarf_olcum3.py`** — aracı
   `/api/manuel` üzerinden **doğrudan kumanda çubuğu** komutuyla
   (throttle/pitch/roll/yaw, −1..+1) zarf sınırlarına dayadık. Bu yol güdümün
   hız clamp'lerini **tamamen atlar** → istenen "(b) aracın gerçek zarfı".
2. Oyunun `get_debug_truth` kanalı (bozulmamış ground truth), sunucu içinde
   **30 Hz** kaydediliyor. Güdüme girmez, yalnız ölçüm.
3. 882 s'lik normal görev kaydı (26381 örnek) + 207 görsel faz logu
   (12562 tespitli kare).

---

## ⚠ BULGU 1 — (a) ile (b) arasında 3.3 kat fark var

| | yatay ivme | eşdeğer yatış |
|---|---|---|
| **(a)** clamp `MAX_ACCEL=12` iken ölçülen | 11.96 m/s² | 49–51° |
| **(a)** clamp 20'ye çıkarılınca | 31.67 m/s² | ~72° |
| **(b) clamp'siz, doğrudan çubukla** | **39.22 m/s²** | **76°** |

12'de ölçülen 11.96 tam clamp'e dayanıyordu — **aracın limiti değil, bizimkiydi.**

Güdüme etkisi doğrudan (ω = a/V):
- clamp 12 ile 18.3 m/s'de → **37.6 °/s** (ölçülen %99: 37.9 — birebir)
- clamp'siz 19 m/s'de → **118 °/s**

Hedefi takip için gereken **33–36 °/s**. Yani **3.3 kat pay varmış** ve biz
kendi clamp'imizle boğuyormuşuz.

## BULGU 2 — Kamera tilt açısı DOĞRU (25°), önceki iddia GERİ ÇEKİLDİ

| | değer | nasıl |
|---|---|---|
| kodun varsaydığı (`CENTER_ELEV_DEG`) | **+25°** (yukarı) | Gazebo `iris_cam` modelinden miras |
| **ölçülen** | **+22.9°** (medyan), %25–75: 18.6–25.3 | 188 kare, yalnız \|roll\|<8° ∧ \|pitch\|<8°. `tilt = elev − sapma − pitch` |
| fark | **2.1°** → **DOĞRULANDI** | |

⚠ **DÜZELTME (2026-08-15):** Bu raporun ilk sürümünde "kamera tilt'i −8.3°,
kod 33° yanlış" yazıyordu. **O ölçüm hatalıydı ve geri çekildi.**
Sebep: IBVS logundaki `cx, cy` pikselleri **640×480** dedektör kadrajında
(ölçüldü: cx 32–613, cy 141–406), ama hesapta **1920×1080** ekran yakalamasının
intrinsikleri kullanılmıştı (fy = 531.36, merkez 540). Yanlış merkez + yanlış
odak uzaklığı ~31°'lik sahte bir sapma üretti.
Doğru intrinsiklerle (CY = 240, fy = 236.1) sonuç **+22.9°** ve kodun
varsayımıyla uyumlu.

**Sonuç: kamera tarafında düzeltilecek bir şey YOK.**

---|---|---|
| kodun varsaydığı (`CENTER_ELEV_DEG`) | **+25°** (yukarı) | Gazebo'nun `iris_cam` modelinden **miras alınmış** |
| **sapma** | **33.3°** | |

Bağımsız iki doğrulama:
- `eps_elev` medyanı **−28.4°** (12562 kare) — hiç düzelmiyor, sabit kalıyor
- `cy` medyanı **211 px** (kadraj merkezi 540) → hedef merkezin **+31.8°** üstünde

Yani hedef, görsel fazın tamamı boyunca kadrajın ~32° yukarısında oturuyor ve
güdüm bunu düzeltmiyor — çünkü kamerayı 25° yukarı bakıyor sanıp aracı hedefin
altına konumlandırıyor.

---

## 1. AVCI DRONE

### Kimlik

| parametre | değer | nasıl |
|---|---|---|
| **araç tipi** | **MULTIROTOR — kanıtlandı** | Saf roll testi: burun **0°** döndü, hız vektörü **78°** döndü. Yan uçabiliyor → fixed-wing olamaz. Ayrıca V≈0'da yerinde yaw yapabiliyor (163 °/s) |
| kütle | **ÖLÇÜLEMEDİ** | SDK açmıyor. Dolaylı: itki/ağırlık oranı ≈ (32.5+9.81)/9.81 = **4.3** (max dikey ivmeden) |
| boyut | **ÖLÇÜLEMEDİ** | SDK açmıyor |

### Hız zarfı

| parametre | (a) yazılım sınırı | (b) ÖLÇÜLEN ZARF | örnek | nasıl |
|---|---|---|---|---|
| max yatay hız | GPS 18.0 / görsel seyir 24.0 / terminal 18.0 m/s | **34.6 m/s** | 106 | Tam pitch 4 s, 118.5 m yol. Birden çok koşuda 34.6–34.7 → **sert tavan**, sürükleme limiti değil |
| max tırmanma | **6.0** (GPS) / **3.0** (görsel) / **5.0** (terminal) m/s | **33.7 m/s** tepe · **30.2 m/s** sürekli | 79 | Tam throttle 3 s: 60.2 → 150.7 m (90.5 m). Ham irtifadan doğrulandı |
| max alçalma | aynı clamp'ler | **−5.6 m/s** tepe · **−3.2 m/s** sürekli | 79 | Tam aşağı 3 s: 166.9 → 157.1 m |

⚠ **BULGU 3 — dikey eksende 11 kat boğuyoruz.** Yazılım tavanı görsel fazda
**3.0 m/s**, aracın yapabildiği **33.7 m/s**. Kamera tilt'i doğru olduğuna göre
(BULGU 2) dikey nişan hatasının kaynağı kamera değil; ama hatayı kapatacak
dikey yetki de bu clamp yüzünden yok.
(`gps_guidance.py:292 VZ_MAX=6.0` · `bbox_ibvs.py:126 VZ_MAX=3.0` ·
`bbox_ibvs.py:321 VZ_MAX_TERM=5.0`)

⚠ **Tırmanma/alçalma 6 kat asimetrik.** İki bağımsız yolla doğrulandı
(hız türevi + ham irtifa farkı).

### İvme zarfı

| parametre | değer | örnek | nasıl |
|---|---|---|---|
| **max yatay ivme** | **39.22 m/s²** | 106 | Saf roll (pitch bırakılmış), 6 s |
| aynı, ilk testte | 35.91 m/s² | 78 | tam sol roll 3 s |
| sağ/sol farkı | 31.75 vs 35.91 (%12) | 78+79 | simetri kontrolü |
| **eşdeğer yatış** | **76°** | | atan(39.22/9.81) |
| max dikey ivme | 32.5 m/s² | 79 | tam throttle |
| **doyum** | **EVET, doydu** | | 12 s sürekli roll: ivme 30.5 → 12.2 → 6.8 m/s² düşüyor, çünkü 34.6 m/s hız tavanına dayanınca o yönde ivmelenemiyor. Yani sınırlayan ivme değil HIZ TAVANI |
| **jerk** | ~**170 m/s³** (dolaylı) | | 39.22 / 0.211 s zaman sabiti. Doğrudan jerk limiti bilinmiyor |

### Dönüş kabiliyeti

| parametre | değer | örnek | nasıl |
|---|---|---|---|
| **hız vektörü dönüş hızı** | medyan 4.0 · %95 **55.5** · **max 61.1 °/s** | 106 | **Saf roll** (pitch bırakılmış), hız 26.8–40.0 m/s |
| teorik kontrol | 67.0 °/s | | a/V = 39.22/33.6 — ölçümle uyumlu |
| **güdüm hızımızda (19 m/s)** | **118 °/s** | | a/V = 39.22/19 |
| **burun (yaw) dönüş hızı** | medyan **163** · max **214 °/s** | 35 | Yerinde tam yaw, API'den yaw okundu |
| yaw komut tavanı (bizim) | 120 °/s | | `YAW_RATE_MAX_DEG` |

⚠ İlk testte 30.4 °/s çıkmıştı — o test **kusurluydu** (pitch de tam ileriydi,
ivmenin çoğu hızlanmaya gitti). Düzeltilmiş test **61.1 °/s** veriyor.

### (a) YAZILIMDA UYGULADIĞIMIZ TÜM SINIRLAR — tek tabloda

| sabit | değer | dosya:satır | (b) aracın zarfı | oran |
|---|---|---|---|---|
| `MAX_ACCEL` | 12.0 m/s² | gps_guidance:303 + bbox_ibvs:369 | 39.22 | **3.3×** |
| `V_MAX` (GPS fazı) | 18.0 m/s | gps_guidance:302 | 34.6 | 1.9× |
| `V_TOPLAM_MAX` (görsel seyir) | 24.0 m/s | bbox_ibvs:153 | 34.6 | 1.4× |
| `V_TERMINAL` | 18.0 m/s | bbox_ibvs | 34.6 | 1.9× |
| `VZ_MAX` (GPS fazı) | 6.0 m/s | gps_guidance:292 | 33.7 | 5.6× |
| `VZ_MAX` (görsel faz) | **3.0 m/s** | bbox_ibvs:126 | 33.7 | **11.2×** |
| `VZ_MAX_TERM` | 5.0 m/s | bbox_ibvs:321 | 33.7 | 6.7× |
| `YAW_RATE_MAX_DEG` | 120 °/s | bbox_ibvs:115 | 214 | 1.8× |
| `K_YAW` | 1.0 (tam düzeltme) | bbox_ibvs:90 | — | — |

### Kontrol arayüzü ve gecikme

| parametre | değer | nasıl |
|---|---|---|
| güdüm arayüzü | **hız setpoint** (vx, vy, vz + yaw) | `send_velocity()` |
| manuel arayüz | **kumanda çubuğu** (throttle/pitch/roll/yaw) | `set_control_surfaces()`. Attitude/rate arayüzü **yok** |
| güdüm döngüsü | 20 Hz (GPS) · **62 Hz** (görsel) | log zaman damgalarının medyanı |
| truth telemetri | ~30 Hz | kayıt frekansı |
| bozulmuş hedef kanalı | 5 Hz | SDK belgesi + ölçüm |
| **ölü zaman** (komut → ivme %10) | **46 ms** | Basamak testi: roll 0→1 anlık |
| **zaman sabiti** (ivme %63) | **211 ms** | aynı test |

---

## 2. HEDEF İHA (Talon)

| parametre | değer | örnek | nasıl |
|---|---|---|---|
| seyir hızı | **17.98 m/s, SABİT** | 24682 | Pencere testi: pencere büyüdükçe std 1.102 → 0.054, ortalama sabit → yayılım tamamen ölçüm gürültüsü |
| bağımsız kontrol | **17.98 m/s** | | toplam yol ÷ toplam süre (türevden geçmez) |
| manevrada yavaşlama | **YOK — %0.8** | 11961 | düz 18.07 / dönüşte 17.93. Gürültü tabanı (std 0.108) içinde |
| yörünge | **oval / yarış pisti (stadyum)** | | Yön–yol eğrisi: tur başına iki basamak. Ne kare ne daire |
| tur uzunluğu | **530 m** | 14.98 tur | |
| tur süresi | **29.5 s** | | |
| saha boyutu | 97.7 m × 219.8 m | | |
| dönüş yarıçapı | **51 m** (medyan) | | ω/V. Medyan kullanıldı; max tekil gürültüye takılıyor |
| dönüş hızı | **20.1 °/s** medyan · %99 tepe 45 °/s | | |
| yolun düz kısmı | **%52** | | <8 °/s olan zaman oranı %55.4 ile örtüşüyor |
| düz blok süresi | **8.2 s** | 56 blok | |
| irtifa | **85–95 m**, yayılım 10.5 m | 24682 | **SABİT DEĞİL**, hafif dalgalı |
| kanat açıklığı | **1.78 m** | | mesh ölçümü (177.89 cm) |
| gövde uzunluğu | **1.10 m** | | mesh (109.92 cm) |
| yükseklik | **0.33 m** | | mesh bounds Z |
| çarpışma yarıçapı | **< 4.22 m** (üst sınır) | | Tüm kayıtlarda en yakın geçiş 4.22 m ve **isabet olmadı** → yarıçap bundan küçük. Kesin değer için isabet gerekiyor |
| bizden kaçıyor mu | **HAYIR** | | Kendi rotasını uçuyor, bizi yok sayıyor |

⚠ **`target.speed` (v[26]) daima 0** — konum değişirken bile. O alan
doldurulmuyor; hız truth konumdan türetilmek zorunda. (Kendi aracımızın
v[22] alanı dolu ama **cm/s** biriminde.)

---

## 3. KAMERA

| parametre | değer | nasıl |
|---|---|---|
| yatay FOV | **122.0709°** | En küçük kareler, motorun `ProjectWorldLocationToScreen` çıktısından. Artık **0.001 px** |
| dikey FOV | **90.93°** | aynı çözüm |
| çözünürlük | **1920 × 1080** | ekran yakalama |
| iç parametreler | fx = fy = **531.36**, cx = 960, cy = 540 | aynı çözüm |
| kare hızı (dedektör) | 15–30 FPS, değişken | ölçüm |
| montaj | **sabit, gimbal YOK** | |
| **tilt açısı (montaj)** | **+22.9°** yukarı, %25–75: 18.6–25.3 | **188 kare**, yalnız \|roll\|<8° ∧ \|pitch\|<8°. 640×480 dedektör intrinsikleriyle (CY=240, fy=236.1) |
| kodun varsaydığı | +25° — **2.1° fark, DOĞRULANDI** | `CENTER_ELEV_DEG` |

⚠ Motor 2D koordinatları **1536×864** mantıksal uzayda döndürüyor, pencere
1920×1080. Oran tam **1.25** = Windows DPI ölçeği. Çarpılmadan ekrana oturmuyor.

---

## 4. ORTAM

| parametre | değer | nasıl |
|---|---|---|
| **rüzgâr** | **YOK** | Nötr çubukla 9.7 s: yatay sürüklenme **0.06 m** (0.01 m/s), max hız 0.03 m/s |
| **yerçekimi** | **ÖLÇÜLEMEDİ** — denendi, model geçersiz | İki yol denendi. (1) Serbest düşüş: araç throttle −1'de **aktif frenliyor** (alçalma 2.92 m/s, dikey ivme 3.33 m/s²) → serbest düşüş yok. (2) Koordineli dönüş `g = a/tan(yatış)`: **üç farklı yatışta üç farklı sonuç** verdi — 18°→11.37, 33°→13.93, 51°→4.42 m/s² (yayılım 9.5). Basit yatış modeli bu uçuş modelinde geçerli değil. **Tek ölçümle 11.34 çıkmıştı, doğrulanınca çürüdü — o sayıyı kullanmayın** |
| **hava yoğunluğu / sürükleme** | **AERODİNAMİK SÜRÜKLEME MODELLENMİYOR** | 33.4 m/s'den çubuk nötr bırakılıp 7 s süzüldü (234 örnek). Yavaşlama modeli **a ~ V^0.03** — yani hızdan bağımsız, sabit. Aerodinamik sürükleme olsaydı üs ~2 olurdu. Araç **aktif frenliyor** (ivme 0.9 → 10.1 → 1.1 m/s² tepe yapıp iniyor: hız kontrolcüsü imzası). Dolayısıyla hava yoğunluğu bu araç için **anlamlı bir parametre değil** |
| GPS bozulması | **VAR** | Hedef kanalında gürültü, kayma, dropout, ~1 s gecikme. `get_active_corruption()` ile doğrulandı |
| temiz veri kanalı | `get_debug_truth()` | Yarışmada kullanılmaz, yalnız ölçüm |

---

## 5. GAZEBO İLE KIYAS

| | Gazebo | DoW (biz) |
|---|---|---|
| avcı tipi | quadcopter | **multirotor (kanıtlandı)** |
| avcı max yanal ivme | 9.81 m/s² (45°) | **39.22 m/s² (76°)** |
| avcı max hız | 24 m/s | **34.6 m/s** |
| avcı hız vek. dönüşü | 31 °/s (18 m/s'de) | **118 °/s** (19 m/s'de, zarfla) |
| hedef hızı | 15.1 m/s | **17.98 m/s** |
| hedef dönüş yarıçapı | 37 m | **51 m** |
| hedef dönüş hızı | 21.5 °/s | **20.1 °/s** |
| hedef manevrada yavaşlar mı | hayır | hayır |
| hız oranı (biz/hedef) | 1.59× | 1.19× *(clamp'le)* → **1.92×** *(zarfla)* |
| kamera FOV | 125° | 122.07° |
| çözünürlük | 640×480 | **1920×1080** |
| kamera tilt | 25° yukarı (gerçek) | **8.3° aşağı** |
| tespit sürekliliği | 50 m'de %11–16 | **kadrajdayken %100** |
| rüzgâr | yok | **yok** |
| menzil bilgisi | kutu boyutundan R≈160/kutu | aynı formül, aynı sabit |
| görsel fazda GPS | yok | yok |

**Sonuç:** avcımızın fiziksel zarfı Gazebo'nunkinden **4 kat** güçlü
(39.22 vs 9.81 m/s²), hız üstünlüğümüz de aslında onlarınkinden yüksek
(1.92 vs 1.59). Ama iki hata bunu görünmez kılmış: `MAX_ACCEL=12` clamp'i ve
Gazebo'dan miras alınan 25°'lik kamera tilt varsayımı.

---

## 6. HÂLÂ ÖLÇÜLEMEYENLER (3 satır)

Tahmin etmedim:

1. **kütle ve boyut** — SDK açmıyor. Dolaylı olarak yalnız itki/ağırlık
   oranı çıkarılabildi (~4.3).
2. **yerçekimi** — iki bağımsız yol denendi (serbest düşüş + koordineli
   dönüş), ikisi de çalışmadı. Uçuş modeli basit tilt-thrust multirotor
   fiziğine uymuyor. (Hava yoğunluğu sorusu ise CEVAPLANDI: sürükleme
   modellenmiyor.)
3. **çarpışma yarıçapının kesin değeri** — yalnız üst sınır (< 4.22 m).
   Kesin değer için bir isabet gerekiyor.
