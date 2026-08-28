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
