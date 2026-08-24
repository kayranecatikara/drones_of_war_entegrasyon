# KAMPANYA TAKİP — HybridSort geri geliyor mu?

**Kol başına n = 4** · 8 uçuş · dönüşümlü T,K,T,K…

---

## 0 · NEREDEN ÇIKTI

Kullanıcının şikâyeti (2026-08-24, birebir alıntı — §5.5):

> *"DETECTİON MODELİ ÇOK KESİK KESİK ÇALIŞIYOR TAKİP SÜREKLİLİĞİ YOK
> BANA HYBRİDSORT KOYMA DİYORSUN AMA ŞU AN DETECTİON MODELİ HEP KESİLİYOR
> BİR TRACKING ALGORİTMASI OLMASI GEREK MİYOR MU"*

Takipçi 22 Ağustos'ta şu **koşullu** gerekçeyle çıkarılmıştı:

> *"şu an detection kötü olduğu için tracking bir işe yaramıyor ve rastgele
> yerlere track atabiliyor... **düzgün detection modeli gelince tekrardan
> entegre edebiliriz**."*

Koşul gerçekleşti: `talon_v5` (OSD hard-negatif + uzak uçak fotoğrafları).

---

## 1 · TEK DEĞİŞKEN

`DOW_TAKIP` 0 / 1. **Diğer her şey bugünkü varsayılan**:
`GORUS_ISP=0`, tavan 15/10. Böylece takipçinin etkisi mimariden yalıtılır.

| kol | takipçi | predict eşiği | seçim |
|---|---|---|---|
| **K** (kontrol) | yok | 0.40 | yerellik kapısı + argmax |
| **T** (deney) | HybridSort | **0.10** | kilitli kimlik (TargetLock) |

⚠ Eşik farkı takipçinin **ayrılmaz parçası**, ikinci değişken değil: zayıf
kutuyu kapıyla atmak yerine zamansal tutarlılıkla süzmek fikrin kendisi.
Ayrı ayrı denemek, özelliği tasarım zarfının dışında sınamak olur (§5.13).

---

## 2 · ÖLÇÜTLER — KOŞMADAN ÖNCE İLAN EDİLDİ

### Birincil
**KÖR SÜRE ORANI** = kutu yaşı > 0.3 s olan zamanın payı.

### ⭐ ZORUNLU GEÇERLİLİK EŞİ (§5.2) — bu kampanyada KRİTİK

**"Kör süre KÖTÜ bir sebeple de düşer mi?"** → **EVET, hem de tam olarak
bu özellikte.** Takipçi, çıkarım ıskaladığında Kalman **öngörüsüyle** kutu
üretir (`takip_kaynak = "tahmin"`). Kutu var diye saymak, YANLIŞ YERE
öngörülmüş kutuyu ÖDÜLLENDİRİR ve kör süreyi **sahte** düşürür.

Zorunlu eş: **GERÇEK TESPİT %** — truth geometriden öngörülen kadraja göre
doğrulanmış kutu oranı (`tespit_olcu.py` ile birebir aynı tanım: merkez
max(60, 1.5·bek_w) px içinde VE genişlik 0.5-2.0 katı).

> **Kör süre düşer ama GERÇEK tespit de düşerse → kazanç SAYILMAZ.**
> Bu tam olarak 22 Ağustos'ta yaşanan şeydir: takipçi hatayı silmiyor,
> `max_age` kadar UZATIYORDU.

İkinci eş: görsel temas oranı.

### Mekanizma kapısı (§5.1)
`takip_n` (aktif iz sayısı) ve `takip_kaynak` dağılımı. Deney kolunda
`takip_n = 0` olan koşu **GEÇERSİZDİR** — özellik hiç çalışmamış demektir.
Ayrıca `takip_kaynak` dağılımı raporlanır: kaç kare `eslesme`, kaç kare
`tahmin`. Tahmin oranı %0 ise takipçi köprüleme YAPMIYOR demektir ve
kazanç başka bir şeyden geliyordur.

### ⛔ Regresyon (§5.10) — etki alanı tablosu

| etkilenebilecek davranış | neden | nerede sınanır |
|---|---|---|
| yanlış-pozitife kilitlenme | takipçi FP'yi iz sanıp `max_age` kadar sürdürebilir | GERÇEK tespit % + `takip_id` değişim sayısı |
| terminal faz (çok yakın) | kutu büyürken IoU eşleşmesi bozulabilir | `en_yakin_m`, isabet |
| hedef kaybı sonrası yeniden yakalama | eski kimlik yeni hedefi eleyebilir | görsel temas kesinti sayısı/süresi |
| GPS istasyon tutma | conf 0.10'da daha çok kutu → çıkarım yavaşlar | `ist_hata_m` |

### Salınım (§4)
cx işaret değişimi/s, roll işaret değişimi/s, |roll| p90.

---

## 3 · KARAR KURALI (sonuçtan ÖNCE)

1. `takip_n = 0` olan deney koşusu → **GEÇERSİZ**, veri noktası değil.
2. Kapı geçilirse:
   * kör süre **düştü** VE **GERÇEK tespit düşmedi** VE regresyon yok
     → **TAKİP GİRER**.
   * kör süre düştü ama GERÇEK tespit de düştü → **öngörülen kutular
     yanlış yerde**; takipçi ELENİR (22 Ağustos'un tekrarı).
   * ikisi de nötr → karar kullanıcıya.
3. n = 4/kol; altı **"ARA VERİ, karar değil"** (§5.4).

---

## 4 · SONUÇ

*(koşu bitince doldurulacak)*

---

## 5 · KOŞMADAN ÖNCE YAKALANAN TUZAK — §5.13

Takipçiyi olduğu gibi koşsaydım **özelliği kendi tasarım zarfının DIŞINDA**
sınamış olurdum.

`ibvs.gecerli()` ilk satırında `conf < CONF_MIN (0.40)` diye eliyordu.
Takipçinin TÜM FİKRİ ise zayıf kutuyu tek karede eşikle atmak yerine
kareler arası tutarlılıkla süzmektir — dedektör bu yüzden 0.10'da koşuyor.
Aynı eşiği alt akışta TEKRAR uygulamak, takipçinin yaşattığı her zayıf
kutuyu öldürür.

**ÖLÇÜLDÜ (duman testi, 30 kare):** takipçi 19 kutu döndürdü (3 eşleşme +
16 öngörü); `gecerli()` bunların **14'ünü eledi**, güdüme yalnız 5'i ulaştı.
Yani kutuların **%74'ü** ölçüme hiç girmeyecekti ve ben "HybridSort işe
yaramıyor" diye rapor edecektim — ölçtüğüm şey takipçi değil, eşik olurdu.

**Çözüm:** takipçi AÇIKKEN güven eşiği `TakipCfg.CONF_MIN`'e (0.10) iner.
Kimlik kararını takipçi verir: `TargetLock` kilitlenmek için zaten
conf ≥ 0.40 arıyor; kilit kurulduktan SONRA izi düşük güvenli kutuyla
sürdürmek BYTE mantığının kendisidir.

**Geometrik kontroller AYNEN kalır** (boyut ≥ 8 px, menzil 3-50 m, kadraj
içi) — onlar güven değil FİZİK kontrolü.

**Yapısal garanti (§5.10):**
* **B48** — takipçi KAPALIYKEN 480 girdi kombinasyonunda davranış bit bit aynı
* **B49** — takipçi AÇIKKEN geometri kontrolleri korunuyor

---

## 6 · ARA SONUÇ (n=3 açık / n=2 kapalı — KARAR DEĞİL, §5.4)

| | KAPALI | **AÇIK** |
|---|---|---|
| ⭐ kör süre | %38.5 | **%30.6** |
| kutu yaşı medyan | 0.20 s | **0.07 s** |
| 🔒 **GERÇEK tespit** | %51.0 | **%68.4** |
| çıkarım başarı | %51.4 | **%71.3** |
| ⛔ ISTASYON hata | 6.90 m | 6.73 m |
| isabet | 0.5 | **1.0** |

### Üç kapı da geçildi

**1. MEKANİZMA (§5.1)** — takipçi gerçekten çalıştı:
* çıkarımların **%34.4**'ünde aktif iz vardı
* dönen kutuların **%49.3**'ü `takip_kaynak = "tahmin"`
* `coast` dağılımı (1124 öngörü kutusu): **%47 coast=0**, %53 coast≥1,
  tavan coast=5'te 16 kare

  → İKİ mekanizma da ayrı ayrı iş görüyor:
  **coast=0** = iz zayıf tespitle yaşadı (BYTE ikinci turu → DÜŞÜK EŞİĞİN
  kazancı); **coast≥1** = gerçek Kalman ileri taşıma (KÖPRÜLEMENİN kazancı).

**2. GEÇERLİLİK EŞİ (§5.2)** — kurulan tuzak gerçekleşmedi.
Beklenen risk: "takipçi kör süreyi YANLIŞ YERE öngörülmüş kutularla sahte
düşürür". Ölçüm tersini söyledi: **GERÇEK tespit %51.0 → %68.4 İYİLEŞTİ.**
Takipçi kutu uydurmuyor.

**3. GÖRSEL ÇAPRAZ (§2 adım 4-6)** — öngörü kutularına gözle bakıldı:

| kare | menzil | truth'tan sapma | tolerans | hedef kutuda mı |
|---|---|---|---|---|
| 74 | 16.3 m | **8 px** | 92 px | ✔ evet |
| 214 | 17.4 m | **13 px** | 86 px | ✔ evet |

### Gürültü olan iki "uyarı"

Kaba medyanda görsel temas %19.6 → %11.2 ve |roll| p90 13.6° → 22.3°
görünüyordu. Koşu bazında bakınca ikisi de **tek aykırı koşudan** geliyor
ve aralıklar iç içe:

| ölçüt | KAPALI koşuları | AÇIK koşuları |
|---|---|---|
| kör süre | 38.9, 38.1 | **32.9, 30.6, 28.5** ← hiç örtüşme yok |
| görsel temas | 11.9, 27.4 | 6.7, 11.2, 37.1 ← iç içe |
| \|roll\| p90 | 4.4, 22.8 | 46.6, 22.3, 7.1 ← iç içe |

Kör süredeki ayrım temiz; diğer ikisi güvenilir sinyal değil.

### 22 Ağustos'la fark

O gün eleme gerekçesi: *"takipçi hatayı silmiyor, `max_age` kadar
UZATIYOR"*. Bu kampanyada tersi ölçüldü — GERÇEK tespit ARTTI. Kullanıcının
koyduğu şart (*"düzgün detection modeli gelince"*) belirleyiciymiş.

⚠ **AÇIK NOT:** `GORUS_ISP` ile `TAKIP` **birlikte sınanmadı**. İkisi de
girerse §5.10 gereği bileşik regresyon koşusu gerekir.
