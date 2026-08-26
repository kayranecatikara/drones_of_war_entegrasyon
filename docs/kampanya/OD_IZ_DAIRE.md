# KAMPANYA Ö-D — tek hedefli iz, daire senaryosunda · **ELENDİ**

**Tarih:** 2026-08-26 · **n = 4/kol** · 8 uçuş · dönüşümlü · 8/8 geçerli

## 0 · NEDEN DENENDİ

KD1'de ölçüldü: dairede yerellik kapısının reddettiklerinin **%98'i konum
filtresi** (759/775). Dedektör kutuyu buluyor, biz atıyoruz. Sebep sabit
yarıçap (`60 + 2w`) ve **dondurulmuş referans**.

`dow/gorus/iz.py` bunun için yazılmış (kapı yaşla 165 px/s genişler) ama
**hiç uçuşta sınanmamıştı** — tek commit'te KAPALI gelmiş, kampanya kaydı
yok. Elenmiş değil, denenmemiş.

## 1 · §5.1 MEKANİZMA KAPISI — 8/8 GEÇTİ

`iz_yas ≥ 0` olan kare sayısı: DENEY 1332/1279/426/1269 · KONTROL 0/0/0/0.
Sızıntı yok, ihlal yok.

## 2 · SONUÇ — HİÇBİR ÖLÇÜTTE FARK YOK

| ölçüt | KONTROL | DENEY |
|---|---|---|
| imha | 0/4 | 0/4 |
| süre | 150 s (tavan) | 150 s (tavan) |
| en yakın | 5.62 m | 5.50 m |
| görsel tespit | %8.7 | %8.2 |
| **kutu yaşı p90** | **2.03 s** | **2.05 s** |
| \|roll\| p90 | 21.5° | 20.6° |
| kaçırma | 30 | 31 |

Kapıyı genişletmek **kutu yaşını bile düşürmedi**.

## 3 · NEDEN — MODÜLÜN KENDİ NOTU DOĞRU ÇIKTI

> *"ÇÖZMEDİĞİ ŞEY: bayat karelerin %67.6'sı 'model hiç kutu bulamadı'dır.
> İz kutu İCAT EDEMEZ."*

Dairede kayıp kovaları: `B` (dedektör hiç kutu üretmedi) **822**,
`C` (kapı eledi) **746**. İz yalnız `C`'ye dokunabilir; o dilim tek başına
sonucu değiştirmiyor.

**ASIL SEBEP BAŞKA — ÖLÇÜLDÜ:** tespit oranı hedefin YATIŞINA bağlı
(kadrajda ve 10-25 m menzilde):

| desen | hedef düz (0-10°) | 25-40° | 40°+ |
|---|---|---|---|
| taban | **%90** | — | %60 |
| kare | %60 | %56 | — |
| daire | — | **%49** | **%52** |

Daire çizmek için hedef sürekli yatmak zorunda; model yatık uçak siluetini
tanımıyor. **Bu bir güdüm sorunu değil, eğitim verisi sorunu.**

## 4 · KARAR

**Ö-D ELENDİ.** `DOW_IZ` KAPALI kalır (zaten varsayılan). §5.12 anlamında
çıkarılacak kod yok: özellik hiç girmedi, kill-switch arkasında duruyor ve
başka bir senaryoda (ör. hedefin düz uçup kadrajda hızlı kaydığı durum)
yeniden sınanabilir.

⭐ **ARKADAŞA NOT (model eğitimi):** veri setine **yatık uçan hedef**
görüntüleri eklenmeli. Ölçülen açık: düz %90 → yatık %49-52.
