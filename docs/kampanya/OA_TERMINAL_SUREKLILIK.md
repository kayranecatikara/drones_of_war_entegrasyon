# KAMPANYA Ö-A — terminal süreklilik istisnası

**Tarih:** 2026-08-25 · **n = 4/kol** · 8 uçuş · **dönüşümlü A/B**

---

## 0 · TEŞHİS — sorun nereden bulundu

Kullanıcı (2026-08-25): *"hedef aracı bazen ilkte vuramıyoruz, manevra
yaptığı sıralarda aracı kaçırıyoruz bazen."*

KAMERA10 loglarında (5 koşu, 859 çıkarım) kayıplar ÜÇE ayrıldı
(`araclar/kayip_teshis.py`):

| sebep | ne demek | pay |
|---|---|---|
| A · kadraj dışı | hedef görüş konisinde değil → GÜDÜM | %19.0 |
| B · dedektör kör | kadrajda ama model kutu üretmedi → MODEL | %56.2 |
| C · kapı eledi | model buldu, süzgecimiz attı → **BİZİM KOD** | %24.7 |

Menzile göre ayrılınca (karıştırıcı kalkınca) asıl bulgu çıktı:

| menzil | tespit | `gecerli()` reddi |
|---|---|---|
| **0-3 m** | **%22.0** | **%38.0** |
| 3-6 m | %73.6 | **%0.0** |
| 6-10 m | %73.5 | %4.9 |

Uçurum tam `MENZIL_MIN_M = 3.0` sınırında. Yo-yo'yu tetikleyen üç uzun
kayıp serisinin üçü de "KAPI" cinsindendi; biri (k01 @ 24.6 s) tam
2.1 m'de başlıyordu.

**⚠ MANEVRA HAKKINDA DÜZELTME:** menzil sabitlendiğinde manevranın
(hedef |roll| > 10°) etkisi yakın menzilde kayboluyor (0-10 m: −0.4 puan).
Kullanıcının gözlemi gerçek ama sebebi manevranın kendisi değil: manevra
menzili açıyor, tespiti düşüren MENZİL. 30 m ötesinde tespit zaten %23.

---

## 1 · DEĞİŞİKLİK

Süzgeç SİLİNMEDİ — sebebi meşruydu (140 m'de dev yanlış-pozitif → menzil
1.3 m → tam hücum → araç yere çakılıyor; 2026-08-21, iki koşu "Player ☠").

**Ayırt edici fizik:** dev yanlış-pozitif YOKTAN var olur; gerçek hedef
BÜYÜYEREK gelir. `R < MENZIL_MIN_M` olan kutu ancak şu ikisi birden
sağlanırsa kabul edilir:

```
(a) son KABUL EDİLEN kutu taze          yaş <= KOPRU_S (1.0 s)
(b) yeni kutu ondan en fazla 2 kat büyük  boyut <= TERMINAL_BUYUME * son_w
```

Her iki girdi de PİKSEL/ZAMAN — GPS yok (§10 temiz).
Kill-switch `DOW_TERMINAL=0`. Mekanizma sütunu `terminal_kabul`.
Bekçi **B52**: kapalıyken bit bit eski davranış; 40→498 px sıçraması ve
bayat bağlam HÂLÂ reddediliyor (çakılma koruması ayakta).

---

## 2 · SONUÇ (n=4/kol, dönüşümlü)

### §5.1 MEKANİZMA KAPISI — GEÇTİ
`terminal_kabul` DENEY [2,2,4,4] · KONTROL [0,0,0,0] — sızıntı yok.

### GÜVENLİK (birincil — süzgeç gevşiyor)
`drone_yasadi` 4/4 vs 4/4 · `ihlal` yok. **Çakılma olmadı.**

| ölçüt | **DENEY (açık)** | KONTROL |
|---|---|---|
| ⭐ imha | 4/4 | 4/4 |
| **süre medyanı** | **10.8 s** | 31.0 s |
| **en yakın** | **0.66 m** | 0.84 m |
| **görsel faz** | **3.7 s** | 16.3 s |
| **görsel tespit** | **%87.2** | %66.8 |
| **kesinti süresi** | **0.4 s** | 5.2 s |
| **kutu yaşı p90** | **0.21 s** | 1.36 s |
| \|roll\| p90 | **6.5°** | 20.8° |
| cx dönüş/s | 0.30 | 0.40 |
| devir menzili | 13.3 m | 16.1 m |

### ⭐ SÖZ VERİLEN §5.10 SATIRI — YO-YO TAMAMEN KALKTI

| | DENEY | KONTROL |
|---|---|---|
| faz geri dönüşü (yo-yo) | **0** | 6 |
| GORSEL'de 20+ kayıp serisi | **0** | 6 |
| **<3 m tespit oranı** | **%59** | %18 |

Dört deney koşusunun **hepsinde** tam 1 ileri / 0 geri geçiş — tek temiz
devir. Kontrol kolunun 4 koşusunun 3'ünde yo-yo var.

**NEDENSEL ZİNCİR:** istisna yalnız son 3 m'de çalışır, ama etkisi tüm
koşuya yayılıyor. Çünkü kontrol kolunda araç 3 m'ye gelince körleşiyor,
ıskalıyor, dönüp yeniden yaklaşıyor — süre 31 s, kesinti 5.2 s. Deney
kolunda ilk geçişte bitiyor — 10.8 s, kesinti 0.4 s.

---

## 3 · KARAR

İlan edilen kural: *"imha deney ≥ kontrol VE çakılma yok → girer"*.
Sonuç: 4/4 = 4/4, çakılma yok. **Ö-A GİRER.**

⚠ **DÜRÜST ÇEKİNCE — birincil ölçüt AYIRMADI.** `imha` iki kolda da 4/4;
bu senaryoda tavana dayanmış ve kolları ayırt edemiyor. Kazanım TAMAMEN
ikincil ölçütlerde (süre 3 kat, kesinti 13 kat, kutu yaşı 6 kat, yo-yo
6→0). Bunlar tutarlı ve nedensel zinciri açık, ama sonraki kampanyalar
için **daha zor bir senaryo gerekiyor** ki birincil ölçütün oynayacak yeri
olsun. Aksi halde her özellik "4/4 vs 4/4" diye eşit görünür.

## 4 · AÇIK KALAN
- Ö-B: hedef kadrajda sistematik olarak merkezin ÜSTÜNDE (0-5 m'de
  216 px). Kadraj dışı çıkışların 48'i üstten, 13'ü alttan. Kamera 26.5°
  aşağı eğik, kadraj ufkun 18.5° üstü .. 71.5° altı — yukarı 3.9 kat az yer.
- Ö-C: yerellik kapısı yarıçapı.
- `roll_p90` kontrol kolunda üç kez tam 20.8° çıktı; doyum hipotezi
  ÇÜRÜDÜ (komut medyanı 0.03-0.20, doyumda kare yok). 7. koşuda 25.0
  çıkınca tesadüf olduğu anlaşıldı. Kapandı.
