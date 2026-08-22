# GÖRSEL GÜDÜM SİCİLİ — DoW

Her kampanyanın ölçülmüş sonucu. Kararlar buradan izlenir.
Ölçütler: **tespit%** = görsel fazdaki karelerin kaçında geçerli kutu var ·
**en yakın** = truth'tan ölçülen en küçük menzil (ÖLÇÜM-ONLY) ·
**isabet** = en yakın < 4 m.

---

## ⭐ TABAN — GV09 (n=6): İSABET 3/6, en yakın medyan 5.10 m

Yapılandırma: **yalnız dikey kadraj regülasyonu**. Lead, merkez freni ve
sakin kamera KAPALI.

| koşu | tespit% | en yakın | isabet |
|---|---|---|---|
| 1 | 21.3 | 15.77 | — |
| 2 | 37.8 | 2.95 | ✅ |
| 3 | 33.3 | 6.73 | — |
| 4 | 22.9 | 12.31 | — |
| 5 | 34.7 | 3.46 | ✅ |
| 6 | 37.2 | 2.65 | ✅ |

6/6 geçerli · görsel faza giren 6/6 · devir ~22.6 m (10 kare şartı)

### 🔑 EN GÜÇLÜ BULGU: korelasyon(tespit%, en_yakın) = **−0.982**

| | tespit aralığı |
|---|---|
| **isabet** olanlar | %34.7 – %37.8 |
| **ıska** olanlar | %21.3 – %33.3 |

**Eşik net: tespit %34'ün üstünde isabet, altında ıska.**

→ İsabet oranını yükseltmenin yolu **güdüm yasasından değil, GÖRME'den**
geçiyor. Görsel fazda tespit oranı yükselmeden isabet yükselmez.

---

## Denenen ve GERİ ALINAN eklemeler

Hedefi vuramayınca güdüm yasasına üst üste ekleme yaptım; **her biri işi
kötüleştirdi**. Hepsinin kararı n=3 ile verilmişti — CLAUDE.md §5.4 ihlali.

| kampanya | eklenen | en yakın medyan | isabet |
|---|---|---|---|
| GV02 | dikey kadraj reg. (taban) | 12.05 | 1/4 |
| GV03 | + lead | 13.75 | 0/3 |
| GV04 | + merkez freni | 13.00 | 0/3 |
| GV06 | + sakin kamera | 16.08 | 0/3 |
| GV07 | + tam yaw bandı | 18.12 | 0/4 |

**Sakin kamera** tespiti +5.7 puan artırdı (%26.6 → %32.3, A/B n=3/kol) ama
**%34 eşiğinin altında kaldığı için** isabete dönüşmedi. Bu, yukarıdaki
korelasyonla tutarlı. Kod duruyor, anahtar kapalı; eşiği aşabilirse
yeniden değerlendirilecek.

---

## Kök neden bulguları (ölçülmüş)

**1. Saf takip hedefin irtifasına tırmandırıyor (GV01).** Hız vektörünü
doğrudan hedefe nişanlamak, 24° yükselişte 11.4 m/s tırmanma demek; araç
hedefin hizasına çıkıyor ve kamera 26.5° YUKARI baktığı için hedefi
göremiyor. **Çare:** dikey kanal artık hız nişanlamıyor, hedefi kadrajda
sabit yükseklikte tutuyor (cy → cy_ref).

**2. Tespiti öldüren şey hız değil KONTROL EFORU** (n=416 görsel kare):

| büyüklük | tespit VAR | tespit YOK |
|---|---|---|
| \|roll\| | 0.095 | 0.200 (2.1×) |
| \|throttle\| | 0.300 | 0.669 (2.2×) |
| \|yaw\| | 0.103 | 0.194 (1.9×) |
| \|pitch\| | 0.249 | 0.258 (fark yok) |
| hız | 21.1 | 19.9 (fark yok) |

**3. Çürütülen iki hipotezim.** (a) "Hedef ufka düşüyor, arka plan arazi" —
gerçek geometri kaydedilince çürüdü: hedef üstümüzde, elev +14…+17°.
(b) "İleri uçuş alçalmayı zorlaştırıyor" — tersi çıktı, kolaylaştırıyor.

---

## SIRADAKİ: tespit oranını %34 eşiğinin üstüne çıkarmak

Adaylar — **ayrı ve dönüşümlü A/B, n≥4/kol**:

1. **bbox köprüsü (ölü-hesap):** kayıp karelerde bbox'ı görüntü hızıyla
   ileri taşı. Gazebo'da `VIS_KOPRU_S` ile vardı, DoW'a taşınmadı.
2. **Görsel fazda daima imgsz=1920.** Uyarlanabilir eşik (55 px) yakında
   960'a düşüyor; o ölçüm SABİT istasyonda yapılmıştı, hızlı hareketle
   960 kötü olabilir.
3. **conf eşiği 0.40 → daha düşük.** Yanlış-pozitif riski artar; geçerlilik
   kapısı (menzil 3-50 m) onu bir ölçüde emer.
