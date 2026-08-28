# KAMPANYA KAMERA10 — devir kapısı: istasyon yerine KAMERA

**Tarih:** 2026-08-25 · **n = 5** (tek kol) · kullanıcı isteği

---

## 0 · SORU

Kullanıcı (2026-08-25): *"detection modeli üst üste 10 kare algılarsa gps
güdümünden görsel güdüme geçelim. eğer detection modeli üst üste 20 kare
algılamaz ise de görselden gps güdümüne geçelim."*

---

## 1 · DEĞİŞİKLİK — tek satır

Kamera kapısı ZATEN kodda yazılıydı, kapalıydı. Sayılar da zaten 10/20'ydi.

| dosya | ne değişti |
|---|---|
| `dow/ayarlar.py` | `DEVIR_ISTASYONDAN` varsayılanı `True` → **`False`** |
| `dow/gorus/dedektor.py` | ölü sabit `DEVIR_MENZIL_M` **silindi** (§5.12) |
| `tests/test_dow.py` | B10 gerçek tavana bağlandı; B13 yeni varsayılana |
| `dow/panel.py` + `dow/web/index.html` | canlı aç/kapa düğmesi (§6) |

Güdüm YASASINA dokunulmadı. Değişen yalnız FAZ GEÇİŞİ tetiği.

```
KAMERA kapısı:  _kilit >= DEVIR_KARE(10)   -> GORSEL
geri dönüş   :  _kayip >= KAYIP_KARE(20)   -> ISTASYON   (yalnız hibrit kipte)
```

Sayaçlar ÇIKARIM başına artar (`_cikarim_yapildi` kapısı), kontrol tiki
başına DEĞİL. Ölçülen çıkarım hızı 8.9 Hz →
**10 kare = 1.12 s · 20 kare = 2.25 s**.

## 1.1 · EMNİYET TAVANI

Kamera kapısının önünde GPS menzil kontrolü YOK. Tek tavan `ibvs.gecerli()`:

| süzgeç | eşik |
|---|---|
| güven | ≥ 0.40 |
| kutu | ≥ 8 px |
| **menzil** | **3 m ≤ R ≤ 50 m** |

Ölçüldü (2026-08-25): 20 px = 49.9 m GEÇER · 14 px = 71.2 m ELENİR ·
400 px = 2.5 m ELENİR (dev yanlış-pozitif). Bekçi **B10** bunu sınar.

---

## 2 · ÇEVRİMDIŞI KESTİRİM (§2: KANIT DEĞİL, beklenti)

KANAL_D loglarında "10 ardışık tespit ilk ne zaman olurdu":

| koşu | kamera kapısı | menzil | gerçekleşen (istasyon) | menzil |
|---|---|---|---|---|
| D_1 | 9.0 s | 12.3 m | 9.2 s | 12.4 m |
| D_2 | 7.5 s | 17.4 m | 16.4 s | 12.8 m |
| D_3 | 11.2 s | 12.3 m | 13.3 s | 12.9 m |
| D_4 | 6.8 s | 20.8 m | 16.6 s | 12.9 m |

→ devir **2-10 s erken**, **≤8 m daha uzakta** bekleniyor.

⚠ Kestirimin sınırı: o loglarda araç istasyon yörüngesindeydi. Kamera
kapısıyla uçuş yolu DEĞİŞİR, sonraki tespit istatistiği de değişir.

**Kayıp serileri** (aynı loglar): GORSEL fazındayken en uzun tespitsiz
seri 4-7 kare — 20'nin çok altında. Geri dönüş kapısının ateşlemesi
beklenmiyor; güvenlik ağı olarak duruyor.

---

## 3 · ⚠ §5.10 ETKİ ALANI

| etkilenebilecek davranış | neden | ölçüt |
|---|---|---|
| erken devir | araç oturmadan hücuma geçer | `devir_menzil`, `ist_hata_min` |
| isabet | uzaktan hücum = kafa kafaya buluşma | `imha`, `en_yakin_m` |
| salınım | 36 px kutuda merkez gürültüsü büyük | `roll_p90`, `cx_donus_s` |
| görsel temas | uzakta tespit %50 @40 m → kör süre | `gorsel_tespit_yuzde`, `kutu_yasi_p90` |
| faz yo-yo | 20-kayıp ateşler, 10-tespit geri alır | `faz_gecis_n` (çevrimdışı) |
| yanlış-pozitif kilidi | 10 ardışık sahte kutu → hayalete güdüm | `devir_menzil` + kareler gözle |

---

## 4 · ÖLÇÜTLER VE KARAR KURALI — koşmadan ÖNCE ilan (§4)

**BİRİNCİL:** `imha`. Kullanıcının cümlesi *"vurabiliyor muyuz"*.

**TEMEL ÇİZGİ** (KANAL_D, istasyon kapısı, AYNI düzeltilmiş kanal, n=4):

| | değer |
|---|---|
| imha | 4/4 |
| süre medyanı | 18.2 s |
| devir | 14.75 s @ 14.25 m |
| en yakın | 0.70 m |
| roll p90 | 3.15° |
| görsel tespit | %82.4 |

**MEKANİZMA KAPISI (§5.1):** `devir_sebep == "kamera"`. `"istasyon"` çıkan
koşu GEÇERSİZDİR.

**KARAR:**
- 5/5 veya 4/5 imha → kapı çalışıyor, kalıcı hâle getirmeyi öner
- ≤2/5 → geri al (`DOW_DEVIR_ISTASYON=1`)
- 3/5 → ARA VERİ, n artır

⚠ **§5.4 UYARISI:** n=5 tek kol; temel çizgi AYRI oturumda ölçüldü,
dönüşümlü A/B DEĞİL. Sonuç "ara veri" statüsündedir. Kesin hüküm için
dönüşümlü 4+4 gerekir ve rapor bunu açıkça söyleyecek.

---

## 5 · SONUÇ (n=5, hepsi geçerli)

### §5.1 MEKANİZMA KAPISI — GEÇTİ
5/5 koşuda `devir_sebep == "kamera"`. İstasyon hatası koşuların 4'ünde
33-65 m'de kaldı (istasyon kapısının eşiği 8 m) — o kapı ateşleyemezdi.

| ölçüt | **KAMERA (10/20)** n=5 | İSTASYON n=4 |
|---|---|---|
| ⭐ **imha** | **5/5** | 4/4 |
| temas | 5/5 | 4/4 |
| **süre medyanı** | **10.9 s** | 18.2 s |
| **devir** | **7.4 s @ 13.4 m** | 14.8 s @ 14.2 m |
| en yakın | 0.97 m | 0.70 m |
| görsel faz süresi | 5.0 s | 3.8 s |
| görsel tespit | %77.9 | %82.4 |
| kutu yaşı p90 | 0.47 s | 0.37 s |
| **\|roll\| p90** | **20.20°** | 3.15° |
| **roll işaret dönüşü /s** | **0.27** | **0.27** |
| cx dönüşü /s | 0.29 | 0.16 |
| çıkarım Hz | 9.2 | 8.9 |
| kontrol Hz | 45.9 | 44.0 |
| **faz yo-yo (geri dönüş)** | **3 (2 koşuda)** | 0 |

Koşu koşu süre: 33.3 · 10.7 · 9.4 · 29.6 · 10.9 s
Koşu koşu devir: 9.9 · 7.2 · 4.6 · 10.4 · 7.4 s

### 5.1 · ⭐ SÜRE YARIYA İNDİ
Devir 14.8 → 7.4 s, toplam süre 18.2 → 10.9 s. Sebep açık: araç artık
istasyona oturmayı beklemiyor, hedefi 10 kare üst üste gördüğü an hücuma
geçiyor.

### 5.2 · ⚠ |roll| 6.4 KAT ARTTI — AMA SALINIM DEĞİL (§5.11)

`roll_p90` yalnız GORSEL fazında ölçülüyor, yani §5.9 karışım tuzağı YOK.
Artış gerçek. Ama **salınım ölçütü olan işaret değişim hızı İKİ KOLDA DA
0.27/s** — aynı.

Zaman serisi (k03, GORSEL fazı, ~9 Hz, `+` sağa yatış):
```
....++..++++++++++++++++++++++++++++++++++++++
```
46 örnekte tek işaret değişimi yok: roll +20°'ye çıkıyor ve 4.5 saniye
orada kalıyor. Bu **tek yönlü sürekli dönüş**, salınım değil.

**Sebep:** devir anında araç hedefin kuyruğunda DEĞİL (istasyon hatası
33-65 m). Görsel yasa önce hizalanmak için gerçek bir dönüş yapıyor.
İstasyon kolunda araç zaten kuyrukta olduğu için 4°'lik düzeltme yetiyor.
Dönüş yarıçapı R = V²/(g·tan θ): 22 m/s'de 4° → 706 m (neredeyse düz),
20° → 136 m. Yani geometri, kazanç kusuru değil.

### 5.3 · ⚠ FAZ YO-YO — KESTİRİMİM ÇÜRÜDÜ

Kampanya öncesi "geri dönüş kapısı ateşlemez" demiştim (§2 tahmini).
**Yanlış çıktı:** k01 ve k04'te GORSEL fazında tespitsiz seri 20 kareye
ulaştı ve araç GPS'e döndü (k01: ileri 3/geri 2, k04: ileri 2/geri 1).

Kestirimin hatası koşu planında yazılıydı: eski loglar İSTASYON
yörüngesinde alınmıştı; kamera kapısıyla uçuş yolu değişince tespit
istatistiği de değişti (görsel tespit %82 → %78, yo-yo koşularında %60-63).

**Yo-yo yapan iki koşu da vurdu** ama uzun sürdü (33.3 ve 29.6 s);
yo-yo yapmayan üçü 9.4-10.9 s. Yani yo-yo bedeli ~20 saniye.

### 5.4 · VURUŞ SINIFI — SINIFLANDIRICI EŞİĞİ HATALI (§5.6)

Otomatik sınıflandırıcı KAMERA kolunun 5'ini de "ŞANS" dedi; kararı tek
başına uydurduğum **%80 tespit eşiği** veriyordu (kol %75, kontrol %80).
Son 2 saniyenin gerçek sayıları iki kolda neredeyse aynı:
|cx| medyanı 31-72 px (kontrol 23-32), kutu düzgün büyüme %93-100
(kontrol %92-100). §5.6 gereği bu kendi lehime çevrilmedi, **eşik hatası
olarak raporlanıyor**.

Gözle inceleme (§2 video bacağı, k03 f0016→f0018 ve k02 f0020):
temas karesinde hedef kadrajı dolduruyor ve MERKEZDE, ufuk düzelmiş.
k03'teki 222 px sapma dönüş anındaydı, temas anında değil. Vuruşlar
kontrollü.

---

## 6 · KARAR

İlan edilen kural: *"5/5 veya 4/5 imha → kapı çalışıyor, kalıcı hâle
getirmeyi öner"*. Sonuç **5/5**.

**KAMERA KAPISI GİRER.** Birincil ölçütte en az eşit (5/5 vs 4/4), süreyi
yarıya indiriyor ve faz geçişini GPS'ten kurtarıyor (yarışma kuralı §10
açısından da doğru yön).

⚠ **§5.4 STATÜ: ARA VERİ.** n=5 tek kol; temel çizgi ayrı oturumda alındı,
dönüşümlü A/B değil. "Kesin daha iyi" demek için dönüşümlü 4+4 gerekir.

**AÇIK KALAN İKİ İŞ:**
1. `KAYIP_KARE=20` doğru sayı mı? Yo-yo 2/5 koşuda çıktı ve ~20 s'ye mal
   oldu. 30 veya 40 denenmeli (kolay A/B: `DOW_KAYIP_KARE`).
2. §5.12 — kamera kapısı kazandığına göre istasyon iskelesi
   (`_gelistirme_devir_hazir`, `DEVIR_ISTASYONDAN`, `DEVIR_IST_*`,
   `YARISMA_KIPI`) TAMAMEN çıkarılmalı. Güdüm yolunu değiştirdiği için
   kullanıcı onayı bekliyor.
