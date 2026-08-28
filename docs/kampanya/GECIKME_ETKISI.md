# KAMPANYA GECİKME — 145 ms video gecikmesi kapalı çevrimde ne yapıyor?

**Tarih:** 2026-08-27/28 · **n = 4/kol** · 8 uçuş · dönüşümlü (T G T G T G T G)

---

## 0 · NEYİ SINADIK

Gerçek donanımda video zinciri **~166 ms** ölçüldü (1800 örnek, altı ayrı
yöntem, `docs/GERCEK_SISTEM.md` §5.0) ve **yazılımla düşürülemiyor**.
Güdümün ödediği pay ~136-151 ms. Simde gecikme YOK — yani bugüne kadar
ölçtüğümüz her şey iyimser.

**Soru:** bu gecikme kapalı çevrimde gerçekten zarar veriyor mu?

**Tek değişken:** ekran yakalama yoluna gecikme tamponu
(`DOW_SAHTE_GECIKME_MS`). Güdüm koduna DOKUNULMADI.

| kol | ne |
|---|---|
| **T** | taban, gecikme yok (bugünkü sim) |
| **G** | `DOW_SAHTE_GECIKME_MS=145` |

---

## 1 · MEKANİZMA KAPISI (§5.1) — GEÇTİ ✅

| | T | G |
|---|---|---|
| `sahte_gec_ms` (mekanizma sütunu) | **0.0** | **133.5** |
| kutu yaşı medyanı | 0.12 s | **0.27 s** (+0.15) |

İki bağımsız kanal aynı şeyi söylüyor. Gecikme gerçekten uygulandı.

⚠ **Gerçekleşen 133 ms, istenen 145 değil.** Yakalama 15 Hz (66.7 ms/kare)
olduğu için kare seçimi o adımlara yuvarlanıyor. Ölçülen gerçek bandın
(136-151 ms) hemen ALTINDA — yani bu kampanya gerçeği hafife alıyor.

---

## 2 · SONUÇ (n=4/kol, medyan)

| ölçüt | T (taban) | G (gecikme) | fark |
|---|---|---|---|
| **isabet** | **4/4** | **4/4** | — |
| **imha** | **4/4** | **4/4** | — |
| ⭐ **süre (s)** | **14.25** | **33.45** | **+19.2 (2.3 KAT)** |
| tespit % | 84.2 | 71.1 | **−13.1 puan** |
| kutu yaşı med (s) | 0.12 | 0.27 | +0.15 |
| **kutu yaşı p90 (s)** | 0.34 | **1.31** | **+0.97 (3.9 KAT)** |
| **\|roll\| p90 (°)** | 7.1 | **29.8** | **+22.7 (4.2 KAT)** |
| cx işaret değişimi/s | 0.14 | 0.27 | ×1.9 |
| **kesinti sayısı** | 1.5 | **4.5** | ×3 |
| **kesinti süresi (s)** | 0.65 | **3.25** | ×5 |
| en yakın (m) | 0.95 | 0.43 | −0.51 |
| devir menzili (m) | 14.6 | 14.6 | 0.0 |
| kontrol Hz | 41.9 | 43.0 | +1.1 |

**Koşu koşu süre:**
`T = 14.3, 14.2, 49.2, 14.1` · `G = 33.3, 33.9, 33.6, 32.8`

---

## 3 · HÜKÜM

### 3.1 · ⭐ Gecikme İSABETİ ENGELLEMİYOR

**4/4 vs 4/4.** Kullanıcının endişesi — *"bayat veriyle yanlış hesaplayıp
kaçırabilir miyiz"* — bu senaryoda **gerçekleşmedi**. Aşama 1'in çevrimdışı
bulgusunu (angajman bandında bayat kutu hedefin genişliğinin yalnız
%11-13'ü kadar kayıyor) uçuş doğruladı.

### 3.2 · ⛔ AMA sistemi 2.3 KAT yavaşlatıyor ve 4 KAT dengesizleştiriyor

- **süre 14 → 33 s**
- **\|roll\| p90 7 → 30°** — gecikmeli geri beslemenin klasik imzası:
  araç geç tepki verip fazla düzeltiyor
- **görsel temas kesintisi ×5** (0.65 → 3.25 s)
- **kutu yaşı p90 ×3.9** — enjekte edilen 0.13 s'ten ÇOK daha fazla:
  gecikme kuyruğu kendi kendini besliyor (savruluyor → hedef kadrajdan
  çıkıyor → tespit kopuyor → kutu daha da bayatlıyor)

### 3.3 · ⛔ "en yakın 0.95 → 0.43 m" bir KAZANIM DEĞİLDİR

Bu, CLAUDE.md §4'ün açıkça uyardığı tuzak: *"yalnız isabet + en yakın
menzile bakan bir ölçüt, dengesizce savrulup şans eseri çarpan aracı
ÖDÜLLENDİRİR."* Geçerlilik eşi bunu doğruluyor — aynı kolda `roll_p90`
**4.2 kat** kötü. G kolu daha yakın geçiyor çünkü daha çok savruluyor.

### 3.4 · MEKANİZMA — birinci geçiş kaybı

Süre dağılımı iki modlu:
- **T:** üç koşu 14 s (ilk geçişte imha), bir koşu 49 s (ıskalayıp dönmüş)
- **G:** dört koşu da 32.8-33.9 s — **hiçbiri ilk geçişte vuramıyor**,
  hepsi ikinci geçişte vuruyor

Devir menzili iki kolda AYNI (14.6 m), yani görsel faz aynı yerde
başlıyor. Fark devirden SONRA doğuyor: gecikmeli araç terminal
yaklaşmayı ilk denemede kapatamıyor.

---

## 4 · RAPORDAN ÖNCE ÜÇ SORU (§5.8)

1. **Özellik çalıştı mı?** ✅ `sahte_gec_ms` 0 vs 133.5, kutu yaşı +0.15 s.
2. **Ölçütüm kötü bir sebeple mi iyileşti?** ✅ Evet — `en_yakin` G lehine
   çıktı ama geçerlilik eşi (`roll_p90` 4.2 kat kötü) bunu çürüttü;
   kazanım sayılmadı (§3.3).
3. **n kaç, hüküm kurulur mu?** n=4/kol, §5.4'ün asgarisi. Süre farkı
   (14 vs 33) büyük ama **dağılımlar örtüşüyor**: T'nin bir koşusu 49.2 s
   ile tüm G koşularının üstünde. Yani "G her zaman daha yavaş" DEĞİL,
   "G ilk geçiş imhasını hiç yakalayamıyor" demek daha doğru.

---

## 5 · KARAR

İlan edilen kural: *"G ≈ T ise telafi yazılmaz; G belirgin kötüyse telafi
gerekçelenir."*

> **G belirgin kötü → GECİKME TELAFİSİ GEREKÇELENDİ.**
> Ama **acil değil**: isabet kaybı yok (4/4). Öncelik, isabeti değil
> **süreyi ve kararlılığı** kurtarmak.

⚠ Yarışma bağlamında bu fark büyüyebilir: burada hedef **kaçmıyor** ve
GNSS **temiz**. Gerçekte hedef manevra yapacak ve GNSS karıştırılacak;
2.3 kat yavaş ve 5 kat daha çok temas kaybeden bir sistem orada
görev süresine sığmayabilir.

---

## 6 · SINIRLAR

- **n=4/kol** — §5.4'ün asgarisi, rahat değil.
- **Uygulanan gecikme 133 ms**, gerçek 136-151 ms → kampanya gerçeği
  HAFİFE ALIYOR.
- **Tek senaryo.** Hedef kaçmıyor, GNSS temiz. §5.10 regresyon listesi
  (sürekli manevra / `circle`) KOŞULMADI.
- Sim yakalama 15 Hz, gerçek kaynak 30 fps — kare hızı eşleşmiyor.

---

## 7 · SIRADAKİ ADIM

Aşama 3 — gecikme telafisi (`DOW_GECIKME_TELAFI`, varsayılan KAPALI):
zaman damgalı duruş halka tamponu + ego-hareket telafisi + ileri kestirim.
Mekanizma sütunu: `kestirim_hata_px`.
Kıyas kolu: bu kampanyanın **G** kolu (aynı 133 ms, telafi açık).

---

# ⭐ EK — MERGE SONRASI TEKRAR (2026-08-28, n=4/kol, 8 uçuş)

## Neden tekrarlandı

Yukarıdaki kampanya `main` birleştirilmeden ÖNCE koşuldu. Main 67 commit
getirdi ve güdüm çekirdeğine dokundu (`ibvs.py` +101, `dedektor.py`,
`ayarlar.py`, "DEVİR KAPISI KAMERAYA BAĞLANDI"). §5.14: eski bağlamda
geçerli bulgu yeni bağlamda sessizce yanlış olabilir.

Merge sonrası devir menzili 14.2-14.7 → **15.9 m** çıktı; taban gerçekten
değişmişti.

## Sonuç — bulgu AYAKTA, üstelik DAHA GÜÇLÜ

| koşu | süre | isabet | tespit% | roll_p90 | kesinti_s | yaş_p90 | gec_ms |
|---|---|---|---|---|---|---|---|
| M01_T | 13.3 | 1 | 92.7 | 22.5 | 0.6 | 0.171 | 0.0 |
| M02_G | 62.9 | 1 | 47.5 | 38.3 | 20.0 | 1.623 | 133.5 |
| M03_T | 15.8 | 1 | 81.8 | 15.8 | 1.2 | 0.312 | 0.0 |
| M04_G | 89.7 | 1 | 61.8 | 37.1 | 21.7 | 1.501 | 133.6 |
| M05_T | 32.8 | 1 | 63.3 | 15.6 | 7.4 | 0.942 | 0.0 |
| M06_G | 88.6 | **0** | 57.4 | 31.8 | 18.7 | 1.560 | 133.6 |
| M07_T | 43.2 | 1 | 73.7 | 20.5 | 6.7 | 1.243 | 0.0 |
| M08_G | 61.7 | 1 | 66.1 | 25.2 | 10.7 | 1.604 | 133.4 |

| ölçüt | T (taban) | G (gecikme) | oran |
|---|---|---|---|
| ⭐ **süre (s)** | 24.3 | **75.8** | **3.12 KAT** |
| ⭐ **isabet** | **4/4** | **3/4** | — |
| tespit % | 77.8 | 59.6 | 0.77 |
| \|roll\| p90 (°) | 18.2 | 34.5 | 1.90 |
| **kesinti süresi (s)** | 4.0 | **19.4** | **4.90 KAT** |
| kesinti sayısı | 6.5 | 23.0 | 3.54 |
| kutu yaşı p90 (s) | 0.63 | 1.58 | 2.52 |
| devir menzili (m) | 15.2 | 14.9 | 0.98 (aynı) |

## İKİ KAMPANYANIN KIYASI

| | merge ÖNCESİ | merge SONRASI |
|---|---|---|
| T süre | 14.2 s | 24.3 s |
| G süre | 33.5 s | **75.8 s** |
| **oran** | 2.35 kat | **3.12 kat** |
| **isabet** | 4/4 vs **4/4** | 4/4 vs **3/4** |
| kesinti (G) | 3.25 s | **19.4 s** |

## ⭐ İKİ YENİ BULGU

### 1 · Dağılımlar artık HİÇ ÖRTÜŞMÜYOR

```
T = 13.3, 15.8, 32.8, 43.2      (en kötü 43.2)
G = 61.7, 62.9, 88.6, 89.7      (en iyi  61.7)
```

**T'nin EN KÖTÜSÜ (43.2 s), G'nin EN İYİSİNDEN (61.7 s) hâlâ hızlı.**
Merge öncesinde örtüşme vardı (T'nin bir koşusu 49.2 s ile tüm G
koşularının üstündeydi). Artık ayrım temiz.

### 2 · ⛔ Gecikme artık İSABETİ DE DÜŞÜRÜYOR

Merge öncesi 4/4 vs 4/4'tü — "gecikme vuruşu engellemiyor" demiştim.
**Yeni tabanda G kolu bir koşuyu kaçırdı (M06_G).** Yani önceki hükmüm
yeni tabanda geçerli değil.

**Mekanizma:** yeni devir kapısı sürekli görsel temasa daha bağımlı.
Gecikmeli kolda temas kesintisi **19.4 s** (koşunun dörtte biri) —
merge öncesinde 3.25 s'ti. Sistem hedefi bulup kaybediyor, bulup
kaybediyor.

## KARAR

> **GECİKME TELAFİSİ GEREKÇELENDİ — ve artık ACİL.**
> Merge öncesi "acil değil, isabet kaybı yok" demiştim. **O hüküm
> çürüdü:** yeni tabanda isabet 4/4 → 3/4 düştü, süre 3.1 kat arttı,
> görsel temas kesintisi 4.9 kat arttı.

⚠ Bu ölçüm hâlâ **133 ms** ile yapıldı; gerçek 136-151 ms. Ve hedef
kaçmıyor, GNSS temiz. Yarışma koşullarında etki daha büyük olacak.
