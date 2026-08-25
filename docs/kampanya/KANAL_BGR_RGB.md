# KAMPANYA KANAL — dedektöre BGR mi RGB mi?

**Tarih:** 2026-08-25 · **n = 4/kol** · 8 uçuş · dönüşümlü

---

## 0 · HATA NEYDİ

`ultralytics`, kendisine verilen **numpy dizisini BGR varsayar** (PIL Image
verilirse RGB kabul eder). Bizim boru hattı RGB veriyordu:

```python
img = grab_rgb(sct)            # araclar/kadraj.py -> RGB
beyin.gorsel_tik(img, ...)     # -> det.bul(img_rgb)
self.m.predict(im, ...)        # <- ultralytics bunu BGR sanıyor
```

Model, `talon_v3.pt`, DOĞRU renklerle eğitildi; uçuşta ona **kırmızı ve mavi
kanalları takas edilmiş** bir dünya gösterdik. Gökyüzü mavi değil turuncu,
gövde başka tonda — model "eğitimde gördüğüme benzemiyor" deyip güvenini
düşürdü.

⚠ Arkadaşın deposunda (`avci-drone-yer-kontrol`) bu açıkça notlanmış:
*"ultralytics numpy diziyi BGR varsayar; grab_frame_bgr() BGR döndürdüğünden
doğrudan geçmek DOĞRU renktir"* — **onlar BGR veriyor, biz RGB veriyorduk.**

### Çevrimdışı ölçüm (156 kare, truth doğrulamalı)

| kanal sırası | GERÇEK tespit | yanlış-poz | boş kare |
|---|---|---|---|
| **BGR** (doğrusu) | **%68.6** | %7.1 | %24.4 |
| RGB (eski hâl) | %32.1 | %2.6 | **%65.4** |

Dedektör kapasitesinin **yarısından azı** kullanılıyordu.

---

## 1 · DÜZELTME

| dosya | ne değişti |
|---|---|
| `araclar/kadraj.py` | `grab_rgb` → **`grab_bgr`**, `BGRA2RGB` → `BGRA2BGR` |
| `dow/panel.py` | `RGB2BGR` çevrimi **kaldırıldı** (kaynak zaten BGR) |
| `araclar/kayit.py` | `imwrite`'taki `[:, :, ::-1]` **kaldırıldı** |
| `araclar/esik_tarama.py` | `imread` sonrası `BGR2RGB` **kaldırıldı** |
| `araclar/izleyici.py` | `ucusta_mi(img[::-1])` → `ucusta_mi(img)` |

Fonksiyon **adı da** değişti: `grab_rgb` diye adlandırılmış ama BGR döndüren
bir fonksiyon bir sonraki değişikliği yapanı yanıltırdı (§5.12).

`hud_parlak`, `ucusta_mi`, `gorev_bitti_mi` kanal sırasından **bağımsızdır**
(hepsi kanal ortalaması/std kullanır) — dokunulmadı.

Aynı anda **fp16 açıldı** (ölçüldü: 28.6 → 18.6 ms, 1.54 kat, kutular aynı).

⚠ İki değişiklik BİRLİKTE ölçüldü (kanal + fp16). Ayrıştırılmadılar çünkü
fp16'nın doğruluk etkisi ayrıca ölçülmüştü (kutulu kare ve güven eşit) ve
kanal etkisi çevrimdışı olarak tek başına doğrulanmıştı.

---

## 2 · SONUÇ (n=4/kol)

| | **DÜZELTİLMİŞ** (BGR+fp16) | **ESKİ** (RGB+fp32) |
|---|---|---|
| ⭐ **imha** | **4/4** | **1/4** |
| temas | 4/4 | 2/4 |
| koşular | **12✓ 20✓ 17✓ 20✓** | 150✗ 150✗ 150✗ 107✓ |
| süre medyanı | **18.2 s** | 150 s |
| **kutu yaşı p90** | **0.37 s** | 1.73 s |
| görsel tespit | **%82.4** | %50.9 |
| en yakın | **0.70 m** | 1.02 m |
| çıkarım süresi | **17.1 ms** | 22.3 ms |
| kontrol döngüsü | **44.0 Hz** | 40.5 Hz |
| \|roll\| p90 | **3.15°** | 9.35° |

**Regresyon YOK:** istasyonda en iyi hata 4.90 vs 4.71 m, görsel devir
menzili aynı.

**Salınım üçte bire indi** (9.35° → 3.15°): araç artık hayalete nişan
almadığı için sakin uçuyor.

---

## 3 · ⛔ BU BULGU BUGÜNKÜ TÜM KAMPANYALARI ŞÜPHELİ KILIYOR

Aşağıdaki kampanyaların **hepsi ters kanalda**, yani yarı kör bir
dedektörle ölçüldü. Sayıları arşivde kalsın ama **karar dayanağı olarak
kullanılmamalı**:

| kampanya | ne ölçtü | durum |
|---|---|---|
| `HZ4_GORUS_HIZI` | çıkarım tavanı | ⚠ ters kanalda |
| `ISP_GORUS_IS_PARCACIGI` | ayrı iş parçacığı | ⚠ ters kanalda |
| `TAKIP_HYBRIDSORT` | takipçi (v5 ile) | ⚠ ters kanal + yanlış model |
| `MODEL20_V3_V5` | v3 vs v5 | ⚠ ters kanalda |
| `TAKIP3` | takipçi (v3 ile) | ⚠ ters kanalda |

**Özellikle model kararı (v3 > v5) şüpheli** — v5 ters kanalda daha çok
kaybediyor olabilirdi. Kullanıcı kararı (2026-08-25): *"v5 kötü onu boşver,
arkadaş yeni model eğitiyor"* — yeni model geldiğinde DÜZELTİLMİŞ kanalla
kıyaslanacak.

Takipçi kararı `TAKIP4` ile düzeltilmiş kanalda yeniden ölçülüyor.

---

## 4 · DERS

Bugün sırasıyla şunlar suçlandı: **model** (v5→v3 geri alındı), **takipçi**
(yok diye), **tavan** (semptom çıktı), **mimari** (kazanç vermedi),
**TensorRT/ONNX** (ikisi de elendi). Hepsinin altında **tek satırlık bir
kanal hatası** vardı.

**Bekçi B50** eklendi: kaynağın BGR ürettiğini, yanıltıcı `grab_rgb` adının
kalmadığını, panel ve kayıt yollarının tutarlı olduğunu sınar. Eski kanal
yalnız `DOW_KANAL_ESKI=1` kill-switch'i içinde üretilebilir (A/B için).
**Bekçi B51**: fp16 açık ve `_hassasiyet_uygula` ile GERÇEKTEN uygulanıyor.
