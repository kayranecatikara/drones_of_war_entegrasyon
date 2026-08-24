# KAMPANYA MODEL20 — talon_v3 vs talon_v5

**Tarih:** 2026-08-24 · **Kol başına n = 10** · 20 uçuş · dönüşümlü

---

## 0 · NEREDEN ÇIKTI

Kullanıcı gözlemi (birebir alıntı — §5.5, ölçüt bundan türetildi):

> *"şu an sanırım detection iyileşmiş gibi, daha sürekli. ama önceden
> detection bu kadar iyi değilken hedef aracı çok daha iyi vurduğumuz zaman
> vardı — direkt GPS güdümüyle istasyona oturup sonrasında görsel güdüme
> geçiyorduk ve aracı vuruyorduk, direkt 20 saniyede falan. ama şu an full
> kaçıyor hedef araç."*

Kulağa ters geliyordu ("daha iyi tespit, daha kötü vuruş"). Ölçüm
kullanıcıyı DOĞRULADI.

### Tarihsel kanıt

| dönem | model | n | imha | süre medyanı |
|---|---|---|---|---|
| HZ (08-23 23:24) | v3 | 4 | 4/4 | — |
| **HZ2** (08-24 00:00) | **v3** | 16 | **16/16** | **13.8 s** |
| **HZ3** (08-24 00:22) | **v3** | 8 | **8/8** | |
| KAPI2 (01:19) | v3 | 4 | 4/4 | |
| — v5 sisteme girdi (b592a05, 10:36) — | | | | |
| V5 · MDL · IZ · BOSLUK (09:57-12:34) | v5 | 24 | 15/24 | **107.8 s** |
| TAKIP (17:00) | v5 | 11 | 6/11 | 94.2 s |

**Gece 32/32 (%100), sonrası 21/35 (%60).** Kırılma bir kod değişikliğinde
değil, 8.5 saatlik boşlukta — ve o boşlukta olan tek şey v5'in girmesi.

### İlk doğrulama (MAB, n=4/kol)

| | talon_v3 | talon_v5 |
|---|---|---|
| imha | **4/4** | 3/4 |
| süre | 27, 34, 34, 14 s | 65, 65, 18, 100 s |
| en yakın | **0.43 m** | 0.94 m |

Kullanıcı bunun üzerine 10'ar koşuluk kesin kampanya istedi.

---

## 1 · ÇÜRÜTÜLEN HİPOTEZLER (hepsi ölçüldü)

| hipotez | ölçüm | sonuç |
|---|---|---|
| "eskiden hiç temas yoktu, ölçüt yanıltıyor" | eski `ozet.csv`'de `temas/imha` **sütunu yok** — script eksik sütunu 0 saydı | ⛔ benim okuma hatam |
| "v5 yanlış yere kutu atıyor" | GERÇEK tespit v3 %76 / **v5 %95** | ⛔ v5 DAHA doğru |
| "v5'in kutu ölçeği kaymış, menzil bozuluyor" | kutu/beklenen v3 0.976 / v5 0.957 | ⛔ %2, ihmal |
| "hedef farklı davranıyor" | hız 17.8-17.9, manevra %47-51, irtifa 86-91 — **tüm oturumlarda aynı** | ⛔ hedef aynı |
| "güdüm değişti" | istasyon hatası 6.5-8.4 m, devir menzili 14.2-14.8 m — iki dönemde de aynı | ⛔ güdüm aynı |

---

## 2 · MEKANİZMA — MENZİL BANDINA GÖRE TESPİT

Görsel fazda, kutu yaşı < 0.3 s olan karelerin oranı:

| kaynak | 0-4 m | **4-8 m** | **8-15 m** |
|---|---|---|---|
| v3 (HZ2+HZ3, n=222) | %43 | **%87** | **%88** |
| v3 (MAB, n=52) | %62 | **%91** | **%93** |
| v5 (BOSLUK+IZ, n=403) | %32 | %60 | %73 |
| v5 (MAB, n=89) | %18 | %74 | %85 |
| v5 (TAKIP, n=318) | %49 | %55 | %75 |

**Angajman bandında (4-15 m) v3 açık ara önde.** v5 UZAK menzil için
eğitildi (hard negatif + uzak uçak fotoğrafı) ve orada daha iyi — ama
bizim vuruşumuz 4-15 m'de oluyor.

**Zincir:** v5 terminalde temas kaybeder → GÖRSEL'den ISTASYON'a **2 kat
sık** düşer (medyan 2 vs 1) → devirden vuruşa 20 s yerine 51 s → koşuların
üçte biri hiç vuramaz.

---

## 3 · ÖLÇÜTLER — KOŞMADAN ÖNCE İLAN EDİLDİ

| rol | ölçüt |
|---|---|
| **BİRİNCİL** | `imha` oranı (x/10) **ve** imha süresi medyanı |
| **MEKANİZMA (§5.1)** | 4-15 m bandı tespit oranı; iki kolda fark YOKSA modeller aynı davranmış demektir → kampanya GEÇERSİZ |
| **GEÇERLİLİK EŞİ (§5.2)** | en yakın menzil — `imha`, koşu tam en yakınlaşma anında bittiğinde 1 sayılır; iyi imha + kötü en yakın = ŞÜPHELİ |
| **⛔ REGRESYON (§5.10)** | istasyon hatası, görsel devir menzili/zamanı |
| **SALINIM (§4)** | roll işaret değişimi/s, \|roll\| p90 |

**Karar kuralı (sonuçtan önce):**
* v3'ün imha oranı ≥ v5 VE süresi belirgin düşük → **v3 onaylanır**
* v5 kazanırsa → **varsayılan geri v5 yapılır** ve bugünkü kararın yanlış
  olduğu açıkça yazılır
* Bölünmüş → ölçüt DEĞİŞTİRİLMEZ, karar kullanıcıya

---

## 4 · KAMPANYA OLAYLARI

**(a) SDK portu geç açılıyor.** Görev-sonu kurtarmasından (PLAY AGAIN → 'E')
sonra oyunun SDK sunucusu 12345'i bazen 24 s, bazen 60 s'de bile açmıyor.
İki v3 koşusu bu yüzden düştü ve kollar dengesizleşti (§5.9).
**Çare:** 60 s'de açılmazsa GÖREV BAŞTAN KURULUR (koşu düşürülmez).

**(b) ⛔ ÇÖZÜMLEYİCİDE ÖLÇÜT HATASI — kampanya sürerken yakalandı.**
`model_kiyas20.py`'yi başka bir kampanyanın aracından kopyalarken
**"süre < 20 s ise koşu geçersiz"** filtresi de geldi. Orada kısa koşu
İPTAL demekti; burada **HIZLI İMHA** demek. İlk v3 koşusu 13.7 s'de imha
etmişti ve filtre onu ATIYORDU — yani filtre, tam da v3'ün üstünlüğünü
oluşturan koşuları eleyip sonucu **v5 lehine** çevirecekti.

**Ders:** bir aracı başka kampanyadan kopyalayınca o kampanyanın
VARSAYIMLARI da geliyor. Geçerlilik filtresi her kampanyada yeniden
gerekçelendirilmeli.

---

## 5 · SONUÇ

*(koşu bitince doldurulacak — sonuca bakıp ölçüt seçmek yasak, §5.6)*

---

## 5 · SONUÇ — v3 ONAYLANDI (n=7 / n=6, kullanıcı yeterli buldu)

| | **talon_v3** | talon_v5 |
|---|---|---|
| ⭐ **imha** | **7/7** | **2/6** |
| temas | 7/7 | 4/6 |
| **süre medyanı** | **17.3 s** | 129.4 s |
| koşular | 14✓ 40✓ 64✓ 14✓ 14✓ 17✓ 35✓ | 150✗ 150✗ 48✓ 109✗ 150✗ 14✓ |
| en yakın | **0.63 m** | 1.01 m |
| görsel devir zamanı | 10.3 s | 16.1 s |

**Mekanizma kapısı ✔** (modeller ayrışıyor):

| menzil | v3 | v5 |
|---|---|---|
| 0-4 m | %36.8 (n=19) | %28.3 (n=46) |
| **4-8 m** | **%67.6** (n=34) | %53.9 (n=76) |
| **8-15 m** | **%87.7** (n=57) | %74.0 (n=154) |

**Regresyon YOK:** istasyonda en iyi hata 4.45 vs 4.43 m, görsel devir
menzili 14.5 vs 14.4 m — GPS zinciri bozulmamış.

**Salınım ölçütü KIYASLANAMADI (§5.2):** v3'ün görsel fazı çoğu koşuda
2.6-3.6 saniye — salınım gözlemek için veri yok. Bu bir eksiklik değil,
sonucun kendisi: salınım UZUN KOVALAMANIN ölçütüdür ve v3 kovalamıyor.

| v3 koşusu | görsel faz | | v5 koşusu | görsel faz |
|---|---|---|---|---|
| V3_1 | 2.6 s ✓ | | V5_1 | 120.3 s ✗ |
| V3_20 | 3.1 s ✓ | | V5_2 | 134.9 s ✗ |
| V3_22 | 3.1 s ✓ | | V5_22 | 32.1 s ✓ |
| V3_23 | 3.6 s ✓ | | V5_3 | 3.6 s ✓ |

### KARAR

`MODEL_YOLU` varsayılanı **`talon_v3`**. Geri dönüş: `DOW_MODEL=talon_v5`.

### ⭐ YENİ MODEL EĞİTECEKLERE NOT

v5 kötü bir model DEĞİL — **yanlış bandı iyileştiren** bir model. Uzak
menzil için eğitildi (hard negatif + uzak uçak fotoğrafı) ve orada daha
iyi olabilir. Ama bu sistemin vuruşu **4-15 m**'de oluyor ve orada v3
açık ara önde. Bir sonraki model bu bandı hedeflemeli:

* **4-15 m arası, hedefin kadrajın büyük kısmını kapladığı kareler**
* hedefin YAN ve ÖN yüzünü gösterdiği kareler (manevra anları)
* hareket bulanıklığı olan kareler (yakın geçişte kaçınılmaz)

Uzak menzil (>30 m) tespiti bu sistemde GPS fazıyla kapanıyor; görsel
devir zaten ≤50 m'de yapılıyor.

### AÇIK BORÇ

`DOW_TAKIP` (HybridSort) kampanyası **v5 ile koşuldu** → sonucu artık
geçerli değil. İki sebeple yeniden koşulmalı: (a) karışmış değişken,
(b) takipçi tespit deliklerini köprülemek için var ve v3'te delik çok
daha az (4-15 m'de %68-88 vs %54-74), yani aynı kazancı vermesi
beklenmez. Şu an varsayılan KAPALI, sistem bu belirsizlikten etkilenmiyor.
