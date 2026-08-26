# KAMPANYA Ö-G — dönüşte yavaşla, kare senaryosunda · **GİRMEDİ**

**Tarih:** 2026-08-26 · **n = 4/kol** · 8/8 geçerli · mekanizma 8/8

## 0 · YAPISAL EKSİK (koddan çıkarıldı)

`hedef_boyut = MENZIL_C/HUCUM_MENZIL = 997/1.0 = 997 px`; gerçek kutu
40-150 px → hata ~900 → `v_istek ≈ 315 m/s` → `V_HUCUM`'a kırpılıyor.
Hız ancak kutu 917 px (**1.1 m menzil**) olunca düşer. Yani **görsel faz
boyunca hız daima tavanda**; güdüm hızı dönüş kabiliyetiyle hiç takas
etmiyor. §5.11: `R = V²/(g·tanθ)` → 21.8 m/s'de 78 m, hedefin dairesi 17.5 m.

§5.13 doğru senaryoyu zaten söylüyordu: *"Doğru senaryo `square`: düz
bacaklar + keskin köşeler"* — "yavaşla/hızlan" çevriminin ikinci yarısı
ancak karede gerçekleşir.

## 1 · SONUÇ — GÖRÜŞ İYİLEŞTİ, VURUŞ BOZULDU

| ölçüt | KONTROL (1.0) | DENEY (0.55) |
|---|---|---|
| imha | 0/4 | 0/4 |
| ⭐ **en yakın** | **5.12 m** | 5.87 m |
| **görsel tespit** | %28.8 | **%50.8** |
| **kutu yaşı p90** | 1.87 s | **1.48 s** |
| \|roll\| p90 | 29.6° | **22.4°** |
| cx dönüş /s | 0.75 | 0.75 |
| kaçırma | **55** | 68 |

En yakın koşu koşu: KONTROL 3.73 / 4.86 / 5.39 / 8.27 · DENEY 5.41 / 6.11 /
5.63 / 9.26 → **dört çiftin dördünde de kontrol önde.**

**Yavaşlamak hedefi kadrajda tutmayı gerçekten kolaylaştırdı** (tespit
+22 puan, kutu yaşı −0.39 s, yatış −7.2°) ama **kapanmayı öldürdü**.
Hedef 18 m/s giderken bizim hızımızı kısmak kapanma hızını doğrudan
azaltıyor.

## 2 · TASARIM KUSURU — ÖLÜ BANT YOK

Kesme dağılımı (n=2723):

| eşik | pay |
|---|---|
| kesme ≤ 0.99 | **%83.7** |
| kesme ≤ 0.90 | %48.1 |
| kesme ≤ 0.70 | %10.9 |

Yasa "keskin köşede yavaşla" değil, **"neredeyse her zaman biraz yavaşla"**
olarak çalıştı (medyan 0.909). Kapanmayı sürekli baltalayan ama dönüşe
anlamlı katkı vermeyen bir ayar.

## 3 · KARAR — GİRMEDİ, KOD KALIYOR (AÇIK BORÇ)

İlan edilen kural birincil ölçüttü; imha 0/4'te aynı, en yakın kötüleşti.
`DOW_YAVASLA` varsayılan **1.0** (kapalı) kalır.

⚠ Bu, Ö-D ve Ö-F'den **farklı bir eleme**: orada mekanizma hiçbir şeye
dokunmamıştı; burada **gerçek ve büyük bir görüş kazancı** var (+22 puan
tespit), bedeli daha ağır.

**AÇIK BORÇ — denenmeye değer varyant:** ölü bant. Nişan hatası eşiğin
(ör. 15°) altındayken kesme **hiç** uygulanmasın, üstünde sert insin.
Böylece düz bacakta tam hız korunur, yalnız köşede yavaşlanır. Bugünkü
tasarımda hata küçükken bile %10 kısma var ve zarar oradan geliyor.
