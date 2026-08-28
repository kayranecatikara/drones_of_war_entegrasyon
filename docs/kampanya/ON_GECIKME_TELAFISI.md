# KAMPANYA Ö-N — GECİKME TELAFİSİ

**Tarih:** 2026-08-28 · **n = 8/kol** · 16 uçuş · dönüşümlü · her iki kolda gecikme 133 ms

---

## 0 · NE SINANDI

Gecikme, kapalı çevrimde zarar veriyor (kampanya GECIKME_ETKISI: süre
3.1 kat, isabet 4/4 → 3/4). Bu kampanya **tedaviyi** sınadı.

| kol | ne |
|---|---|
| **G** | gecikme 133 ms, telafi KAPALI |
| **GT** | gecikme 133 ms, telafi AÇIK |

**Telafi ne yapıyor:** köprü, kutunun atalet yönünü hesaplarken ŞU ANKİ
duruşu kullanıyordu; oysa kare 133 ms önce çekilmişti. Telafi, KARENİN
ÇEKİLDİĞİ anın duruşunu kullanır (duruş halka tamponundan).

**İLAN EDİLEN KARAR KURALI (koşmadan önce yazıldı):**
> GT, G'ye göre süreyi belirgin kısaltıp **isabeti düşürmüyor** ve
> salınımı artırmıyorsa GİRER. Nötrse karar kullanıcıya. Kötüyse §5.12.

---

## 1 · MEKANİZMA KAPISI (§5.1) — GEÇTİ ✅

| kol | `telafi_px` örnek | sıfır-olmayan | medyan |
|---|---|---|---|
| G | 145 | **0** | 0.0 px |
| GT | 30 | 25 | **15.6 px** |

Telafi kapalıyken tam sıfır, açıkken nişan noktasını gerçekten kaydırıyor.

---

## 2 · SONUÇ (n=8/kol)

```
G  süreler : 13.6, 29.7, 31.1, 37.3, 60.7, 75.0, 75.6, 118.6     isabet 8/8
GT süreler : 13.4, 14.5, 15.5, 28.4, 30.2, 45.1, 78.0, 149.1     isabet 6/8
```

| ölçüt | G | GT | fark |
|---|---|---|---|
| ⭐ süre (s) | 49.00 | **29.30** | 0.60 kat |
| ⭐ **isabet** | **8/8** | **6/8** | ⛔ DÜŞTÜ |
| tespit % | 61.8 | 65.4 | 1.06 |
| \|roll\| p90 (°) | 29.4 | 23.7 | 0.81 |
| kesinti süresi (s) | 9.75 | 5.50 | 0.56 |
| kesinti sayısı | 14.0 | 6.0 | 0.43 |
| kutu yaşı p90 (s) | 1.47 | 1.45 | 0.98 |
| en yakın (m) | 0.78 | 0.97 | 1.24 |

**Sıralama testi:** rastgele bir GT koşusu, rastgele bir G koşusundan
daha hızlı olma olasılığı **%62** (şans = %50). Zayıf ayrım.

---

## 3 · ⛔ n=4'TEKİ RAPORUM FAZLA İYİMSERDİ

Bu kampanya n=4'te durdurulup raporlanmıştı. n=8'e çıkınca etkinin
büyük kısmı **eridi**:

| ölçüt | n=4'te | n=8'de |
|---|---|---|
| süre | 0.34 kat | **0.60 kat** |
| isabet | 3/4 vs 4/4 | **6/8 vs 8/8** |
| tespit % | 1.31 kat | **1.06 kat** |
| kesinti süresi | 0.16 kat | **0.56 kat** |
| kutu yaşı p90 | 0.64 kat | **0.98 kat** (yok oldu) |

§5.4 tam olarak bunu söylüyor ve bu sefer **bana oldu**. n=4 asgari sınır,
rahat değil; ara sonuç "karar" gibi sunulmamalıydı.

---

## 4 · KARAR — İLAN EDİLEN KURALA GÖRE **GİRMEZ**

Kural üç şart koyuyordu:

| şart | sonuç |
|---|---|
| süreyi belirgin kısaltsın | ⚠ kısaltıyor ama zayıf (%62 sıralama) |
| **isabeti düşürmesin** | ⛔ **DÜŞÜRDÜ: 8/8 → 6/8** |
| salınımı artırmasın | ✅ artırmadı (0.81 kat) |

> **GT GİRMEZ.** Varsayılan KAPALI kalır (`DOW_GECIKME_TELAFI=0`).

§5.6: sonuç bölünmüş çıktı diye ölçüt DEĞİŞTİRİLMEDİ.

⚠ Kod ELENMEDİ, çünkü aşağıdaki kusur hipotezi sınanmadan silmek erken
olur. Bir sonraki oturumda ya düzeltilip yeniden ölçülür ya §5.12 ile
tamamen çıkarılır. **Ölü kod tutmak borçtur — bu borç kayıtlıdır.**

---

## 5 · ⭐ KUSUR HİPOTEZİ (sınanmadı, sonucu YENİDEN YORUMLAMAK İÇİN DEĞİL)

`telafi_px` bazı karelerde **saçma** değerlere çıkıyor:

| koşu | telafi_px max |
|---|---|
| N14_GT | **2391 px** |
| N16_GT | 637 px |
| N12_GT | 544 px |
| N10_GT | 368 px |

1920 piksel genişlikte **2391 pikselllik** bir düzeltme fiziksel olarak
anlamsızdır. Yani telafi bazen tamamen yanlış bir yere nişan aldırıyor.

**Muhtemel sebep:** telafi `piksel_kerteriz` / `kerteriz_piksel` çiftini
kullanıyor; bunlar roll'u **birinci derece küçük-açı** yaklaşımıyla
çeviriyor. `kamera.py`'nin kendi notu diyor ki:

> *"Gazebo'da ölçülmüş: 30-40° yatışta bu yaklaşım 11-14° sapma veriyor.
> Bu zincir (`los_seviye`) TAM dönüşüm yapar."*

Gecikmeli kolda `roll_p90` 24-49° — yani **tam da yaklaşımın bozulduğu
banda** giriyoruz. `tan()` büyük açıda patlıyor.

**Sınanacak çare (ayrı iş):**
1. Telafiyi `los_seviye` / `seviye_piksel` TAM zincirine taşı
2. Düzeltmeye makullük kapısı koy (ör. > 300 px ise uygulama)
3. Yeniden ölç, n≥8

⚠ Bu hipotez, yukarıdaki KARARI değiştirmez. Kural ilan edilmişti ve
sonuç kuralı geçmedi. Hipotez ancak yeni bir ölçümle karara dönüşür.

---

## 6 · RAPORDAN ÖNCE ÜÇ SORU (§5.8)

1. **Özellik çalıştı mı?** ✅ `telafi_px` G'de 0, GT'de medyan 15.6 px.
2. **Ölçütüm kötü bir sebeple mi iyileşti?** ⚠ `en_yakin` G lehine (0.78 vs
   0.97) ama bu KAZANIM DEĞİL: G defalarca tur atıyor, çok deneme yapan
   kol şans eseri daha yakın geçiyor. Ölçüt burada deneme sayısını ölçüyor.
3. **n kaç, hüküm kurulur mu?** n=8/kol. Süre farkı için sıralama testi
   %62 — zayıf. İsabet farkı (8/8 vs 6/8) tek yönlü ve kararı belirledi.

---

## 7 · SINIRLAR

- Uygulanan gecikme **133 ms**, gerçek 136-151 ms → gerçeği hafife alıyor.
- Tek senaryo: hedef kaçmıyor, GNSS temiz.
- §5.10 regresyon uçuşu KOŞULMADI — gerek yok, yapısal garanti var:
  gecikme yokken `kare_t == t` olur ve telafi hiç çalışmaz (bekçi B64).
- Koşu değişkenliği yüksek: aynı G kolu üç kampanyada 3/4, 4/4, 8/8.
