# -*- coding: utf-8 -*-
"""
================================================================================
Ö-K · YEDEK DEDEKTÖR — YOLO kesintisinde RENK/KONTRAST maskesiyle taze konum
================================================================================
KAYNAK: takım arkadaşı Kayra'nın önerisi (2026-08-28). Üç parçalı:
  1. "kesinti öncesi son kutu büyüklüğü kesinti sırasında da kullanılsın"
  2. "HSV aralıklarından gelen tespit, model kesildiğinde nerede olduğuna
     dair çıkarım versin"
  3. "çıkan tüm bbox'ların ağırlıklı ortalaması merkez olarak kullanılsın"

⚠ 1. MADDE ZATEN VARDI. Köprü (`ana.py::_kopru_kutu`) son kutunun `w`/`h`
  değerini KOPRU_S boyunca değiştirmeden taşıyor. Bu modül onu bozmaz:
  köprünün YALNIZ YÖNÜNÜ tazeler, boyutuna/ömrüne DOKUNMAZ (aşağıda).

--------------------------------------------------------------------------------
NEDEN GEREKLİ — ölçüldü
--------------------------------------------------------------------------------
Görsel fazın %34.3'ünde taze YOLO kutusu YOK ve köprü donmuş konumu taşıyor
(N kampanyası, 16 uçuş, 791 tik). Köprü KENDİ dönüşümüzü telafi eder ama
hedefin KENDİ hareketini bilmez: 1 s boyunca 20 m/s yanal kaçan hedefi eski
yerinde sanar. Bu modül o boşluğa TAZE BİR KONUM ÖLÇÜMÜ koyar.

--------------------------------------------------------------------------------
GERÇEK ANALOG KAYITTA ÖLÇÜLDÜ (2026-08-28) — `~/Masaüstü/ucak_veri_seti`
713 kare, 720x480 NTSC, C8/5945 MHz, MacroSilicon VRX, turuncu boyalı Talon
--------------------------------------------------------------------------------
HSV imzası (464 bin piksel):  H 173-180 ∪ 0-14 | S p5 115 | V p5 81
  Üç oturumda da kararlı (H medyan 5-7, S p5 114-115).
  ⚠ Üçü de AYNI GÜN, 5 dakika arayla. Farklı güneş açısı / otomatik pozlama
    bandı kaydırır. Bu yüzden band SABİT DEĞİL, env ile ayarlanabilir.

⛔ DÜZELTME (2026-08-29, kullanıcı itirazı üzerine yeniden ölçüldü)
Bu dosyanın ilk hâlinde "maske uçağı %99.3 buluyor, sorun maskede değil"
yazıyordu. **O CÜMLE YANLIŞTI.** Ölçtüğüm şey "kadrajda en az bir leke
var mı" idi — lekenin UÇAKTA olup olmadığına bakmıyordu. Uçağın ne kadarını
kapladığına da bakmıyordu. Gerçek sayılar (713 HAM kare, tam kadraj):

    hiç leke bulunamayan kare     : 3/713 = %0.4   <- "%99.3" YALNIZ BUYDU
    ALAN_MIN geçen leke / kare    : medyan 7, p90 13
    en büyük leke alanı           : medyan 5099 px², p90 13315 px²
    2. leke / 1. leke oranı       : medyan %28, p90 %85
    2. leke en büyüğün >%50'si    : karelerin %28.1'inde
                                    -> en büyük leke UÇAK OLMAYABİLİR

Gözle doğrulandı (6 ham kare, `logs/HSV_GERCEK/ham_kontrol.jpg`):
  · maske uçağın GÖVDESİNİ tutuyor, ince/koyu KANAT ve KUYRUĞU sık kaçırıyor
  · arka plandaki KIRMIZI-ÇİZGİLİ BİNA uçaktan büyük leke üretebiliyor
Yani maske uçağın tamamını bulmuyor ve tek başına ayırt edici değil.
Ö-K'nin işe yaraması KONUM KAPISINA (köprü çıpası) bağlıdır — kapı olmadan
bu maske hedefi bulamaz.

Bandı sıkılaştırmak bunu ÇÖZMÜYOR (kaçırılan kanat zaten koyu, daha da
kaçırılır):
    S>110 (taban)        leke 6   S>150  leke 3   S>110+şekil kapısı leke 6

⚠ ESKİ "doğruluk" SAYILARI GEÇERSİZ SAYILMALI — hepsi DAİRESELDİ, yani
maskenin en büyük lekesini yine maskenin kendisiyle kıyaslıyordu:
    (R=120 px -> %83.9, R=200 px -> %87.4, ve aşağıdaki %88.9/%91.4/%81.2)
Bunlar bir ÜST SINIR bile değil, ölçüm değil. Ö-K'nin gerçek isabet oranı
ETİKETLİ veriyle ölçülmeden bilinmiyor. Karar bu ölçümden sonra verilecek.

Küme kutusu / beklenen boyut:  medyan 1.08  p95 3.16
    kapı [0.4, 2.5] -> kabul %90.2   <- BOYUT_ALT/BOYUT_UST buradan

--------------------------------------------------------------------------------
SEVKEDİLEN KODUN UÇTAN UCA ÖLÇÜMÜ (bu dosya, gerçek kayıt, 404 kare çifti)
--------------------------------------------------------------------------------
    yedek konum verdi        : %88.9   (kalan %11.1'i boyut kapısı REDDETTİ)
    verdiğinde HEDEFTE       : %91.4
    tüm karelere göre        : %81.2
⭐ RED GÜVENLİDİR, yanlış cevap değildir: `bul` None dönünce köprü donmuş
   konumunda kalır — yani BUGÜNKÜ davranış. Boyut kapısı kapsamayı düşürüp
   isabeti yükseltir (%87.4 -> %91.4) ve bu takas bilinçlidir.
⚠ Bu sayıların "doğruluğu" aynı maskenin en büyük lekesidir (DAİRESEL) —
  ÜST SINIR sayılmalı. Bağımsız etiketli ölçüm gerçek uçuşta yapılacak.

--------------------------------------------------------------------------------
⛔ KAYRA'NIN 3. MADDESİ OLDUĞU GİBİ UYGULANAMAZ — ölçüldü
--------------------------------------------------------------------------------
"Tüm bbox'ların ağırlıklı ortalaması" KAPISIZ alınırsa nişan noktası
lekelerin ARASINDAKİ BOŞLUĞA düşer — orada hiçbir şey yoktur:
    ham "tüm lekelerin ortalaması" : hata medyan 57.6 px (720 px kadrajda %8)
    konum kapılı ağırlıklı merkez  : hata medyan  1.0 px
Ortalama AYNI NESNENİN PARÇALARI için doğru (uçak maskede gövde+kanat diye
bölünüyor), AYRI NESNELER için felakettir. O yüzden: önce KAPI, sonra ORTALAMA.

⛔ VE KAPI KENDİ ÇIKTISINA DAYANAMAZ. İlk denemede kapıyı bir önceki kendi
  merkezine dayadım; 410 karenin 91'inde (%22) çatıya kilitlenip sürüklendi
  (en uzun olay 2.3 s, sapma 510 px). Kapı KÖPRÜYE dayanır: köprü kendi
  dönüşümüzü IMU ile telafi eder ve YOLO'dan gelen beklenen boyutu taşır.

--------------------------------------------------------------------------------
⛔ BOYUT KAPISI TEK TEK LEKEYE UYGULANAMAZ — ölçüldü (sim, bağımsız etiket)
--------------------------------------------------------------------------------
    kapı                    çöp leke   hedef kümede KALDI
    yok                        778           %78.8
    konum                       18           %72.0
    konum + TEK TEK boyut        1           %48.2   <- hedefin kendisini kesiyor
Maske uçağı parçalara böldüğü için her parça beklenen boyutun altında kalıyor.
=> Boyut kapısı ancak BİRLEŞTİRMEDEN SONRA, KÜME kutusuna uygulanır.

--------------------------------------------------------------------------------
⛔ SİMÜLATÖRDE ÖLÇÜLEMEZ — bu modülün KAZANIMI sim'de aranmaz (§5.13)
--------------------------------------------------------------------------------
Sim uçağının RENK İMZASI YOK (250 kare, 2515 etiketli kareden örneklendi):
    kanal   kutu içi (uçak)   çevre (arka plan)
    H            101                101
    S             83                 80
    V p10         79                159     <- ayıran TEK kanal: parlaklık
Sim'de uçak renkli nesne değil, gri bir SİLÜET. Vekil "koyu silüet" maskesinin
tavanı ölçüldü: nişan doğruluğu %48.7 (gerçekteki turuncu maske %83.9+).
Küme/beklenen boyut oranı sim'de 5.04, gerçekte 1.08 — sim maskesi KİRLİ.
=> Sim kampanyası "özellik mi kötü, sim maskesi mi kötü" sorusunu AYIRAMAZ.
   Sim'de YALNIZ REGRESYON ölçülür (§5.10); KAZANIM gerçek uçuşta ölçülür.

--------------------------------------------------------------------------------
YAPISAL GÜVENLİK — bu modül köprüyü KAÇIRAMAZ
--------------------------------------------------------------------------------
`ana.py::_yedek_dene` yalnız köprünün `az`/`el` alanlarını yazar.
DOKUNMADIKLARI ve neden:
  `t`     : köprünün ömrü SON GERÇEK YOLO tespitinden sayılmaya devam eder.
            Yedek `t`yi tazeleseydi yanlış bir kilit SONSUZA KADAR yaşardı.
  `w`,`h` : Kayra'nın 1. maddesi — boyut kesinti boyunca DONDURULMUŞ kalır.
            Menzil kutu boyutundan çıktığı için yedeğin gürültülü silueti
            menzile ASLA karışmaz.
  `conf`  : yedek bir güven skoru üretmez; uydurulmaz.
Sonuç: yedek en fazla KOPRU_S kadar iş görür, sonra köprü normal şekilde düşer.
================================================================================
"""
import os

import cv2
import numpy as np


def _b(ad, v):
    return os.environ.get(ad, str(int(v))).strip() not in ("0", "", "false", "False")


def _f(ad, v):
    return float(os.environ.get(ad, v))


def _i(ad, v):
    return int(float(os.environ.get(ad, v)))


class YedekCfg:
    """CANLI ayarlar — SINIF nitelikleri (CLAUDE.md §6: panel uçuşta değiştirir).

    MASKE
      "turuncu" : gerçek dünya. Turuncu boyalı Talon'un HSV bandı.
      "silue"   : simülatör. Renk imzası olmadığı için gökyüzüne karşı KOYU
                  silüet. ⚠ Yalnız REGRESYON koşuları için; kazanım ölçmez.
    """
    AKTIF     = _b("DOW_YEDEK", False)          # kill-switch, varsayılan KAPALI
    MASKE     = os.environ.get("DOW_YEDEK_MASKE", "turuncu").strip().lower()

    # --- turuncu maske (ÖLÇÜLDÜ: gerçek analog kayıt, 464 bin piksel) ---
    H_UST     = _i("DOW_YEDEK_H_UST", 14)       # 0..H_UST
    H_ALT     = _i("DOW_YEDEK_H_ALT", 170)      # H_ALT..180 (kırmızı sarması)
    S_MIN     = _i("DOW_YEDEK_S_MIN", 110)      # ölçülen p5 = 115
    V_MIN     = _i("DOW_YEDEK_V_MIN", 70)       # ölçülen p5 = 81

    # --- silüet maskesi (YALNIZ sim regresyonu) ---
    SIL_ESIK  = _i("DOW_YEDEK_SIL_ESIK", 18)    # taranmış en iyi (%48.7)
    SIL_BLUR  = _i("DOW_YEDEK_SIL_BLUR", 61)

    ALAN_MIN  = _i("DOW_YEDEK_ALAN", 30)        # px²; altındaki leke gürültü
    KAPI_PX   = _f("DOW_YEDEK_KAPI", 200.0)     # ÖLÇÜLDÜ: R=200 -> %87.4
    BOYUT_ALT = _f("DOW_YEDEK_BOYUT_ALT", 0.4)  # ÖLÇÜLDÜ: kapı [0.4,2.5]
    BOYUT_UST = _f("DOW_YEDEK_BOYUT_UST", 2.5)  #   -> kabul %90.2
    LEKE_MAX  = _i("DOW_YEDEK_LEKE_MAX", 40)    # kapı sonrası bu kadar çok
                                                # leke varsa kadraj karmaşık;
                                                # ortalama anlamsızlaşır -> bırak

    # ⭐ ROI — GECİKME KISITI (kullanıcı kuralı: "gecikmeyi artıracak hiçbir
    #   şey yapmamalıyız"). ÖLÇÜLDÜ (1920x1080, aynı kare, 30 tekrar):
    #       tam kadraj  12.71 ms      <- kabul edilemez, YOLO'nun 2/3'ü
    #       ROI 400x400  0.57 ms      <- 22 KAT ucuz
    #   Sonucu DEĞİŞTİRMEZ: konum kapısı zaten KAPI_PX dışını atıyor.
    #   PAY, kapının kenarına oturan bir lekenin KIRPILMAMASI içindir —
    #   pay olmasaydı kenardaki leke yarım kalır, merkezi ve alanı kayardı.
    PAY_PX    = _f("DOW_YEDEK_PAY", 120.0)


def _maske_turuncu(img_bgr, c=YedekCfg):
    """Turuncu-kırmızı boyalı hedef. H sarmalı yüzden İKİ band birleşir."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, c.S_MIN, c.V_MIN), (c.H_UST, 255, 255))
    m2 = cv2.inRange(hsv, (c.H_ALT, c.S_MIN, c.V_MIN), (180, 255, 255))
    return cv2.bitwise_or(m1, m2)


def _maske_silue(img_bgr, c=YedekCfg):
    """Yerel medyandan KOYU pikseller. Renk imzası olmayan (sim) hedef için.
    ⚠ Ölçülen tavanı %48.7 — kazanım ölçümünde KULLANILMAZ (§5.13)."""
    g = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = c.SIL_BLUR | 1                      # medianBlur TEK sayı ister
    fark = cv2.subtract(cv2.medianBlur(g, blur), g)
    _, m = cv2.threshold(fark, c.SIL_ESIK, 255, cv2.THRESH_BINARY)
    return m


_MASKELER = {"turuncu": _maske_turuncu, "silue": _maske_silue}


def maske(img_bgr, cfg=YedekCfg):
    f = _MASKELER.get(cfg.MASKE, _maske_turuncu)
    m = f(img_bgr, cfg)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def bul(img_bgr, ref, cfg=YedekCfg):
    """Köprünün öngördüğü yerin çevresinde taze bir KONUM ölç.

    GİRDİ
      img_bgr : kamera karesi
      ref     : (cx, cy, w) — köprünün öngördüğü konum ve BEKLENEN kutu
                genişliği. Kendi IMU'muzla telafi edilmiş; GPS YOK (§10).
    ÇIKTI
      (cx, cy, leke_sayisi) ya da None.
      ⚠ BOYUT DÖNMEZ — boyut köprüde dondurulmuş kalır (Kayra madde 1).

    SIRA ÖNEMLİ (her adımı ölçümle gerekçelendirildi, dosya başlığına bak):
      1. maske
      2. bağlı bileşenler, ALAN_MIN altı atılır
      3. KONUM KAPISI (köprüye göre)        <- kapısız ortalama 57.6 px sapar
      4. küme-içi ALAN-AĞIRLIKLI merkez     <- Kayra madde 3
      5. KÜME kutusuna boyut kapısı         <- tek tek uygulanamaz (%72->%48)
    """
    if img_bgr is None or ref is None:
        return None
    rx, ry, rw = float(ref[0]), float(ref[1]), max(float(ref[2]), 1.0)

    # 0: ROI — yalnız kapının çevresini tara (12.71 ms -> 0.57 ms).
    #    Ofset sona geri eklenir; çıktı DAİMA tam kadraj koordinatındadır.
    H, W = img_bgr.shape[:2]
    P = cfg.KAPI_PX + cfg.PAY_PX
    ax0 = int(max(rx - P, 0)); ay0 = int(max(ry - P, 0))
    ax1 = int(min(rx + P, W)); ay1 = int(min(ry + P, H))
    if ax1 - ax0 < 4 or ay1 - ay0 < 4:
        return None
    alt = np.ascontiguousarray(img_bgr[ay0:ay1, ax0:ax1])
    rx -= ax0; ry -= ay0                       # ref'i ROI koordinatına al

    m = maske(alt, cfg)
    n, _lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return None

    alan = st[1:, cv2.CC_STAT_AREA].astype(np.float64)
    cx = ce[1:, 0]
    cy = ce[1:, 1]
    x0 = st[1:, cv2.CC_STAT_LEFT].astype(np.float64)
    y0 = st[1:, cv2.CC_STAT_TOP].astype(np.float64)
    bw = st[1:, cv2.CC_STAT_WIDTH].astype(np.float64)
    bh = st[1:, cv2.CC_STAT_HEIGHT].astype(np.float64)

    # 2 + 3: alan eşiği VE konum kapısı
    sec = (alan >= cfg.ALAN_MIN) & (np.hypot(cx - rx, cy - ry) <= cfg.KAPI_PX)
    k = int(sec.sum())
    if k == 0 or k > cfg.LEKE_MAX:
        return None

    a = alan[sec]
    # 4: alan-ağırlıklı merkez (Kayra madde 3, KAPININ İÇİNDE)
    ncx = float((cx[sec] * a).sum() / a.sum())
    ncy = float((cy[sec] * a).sum() / a.sum())

    # 5: KÜME kutusu beklenen boyutla uyumlu mu
    kw = float((x0[sec] + bw[sec]).max() - x0[sec].min())
    kh = float((y0[sec] + bh[sec]).max() - y0[sec].min())
    oran = max(kw, kh) / rw
    if not (cfg.BOYUT_ALT <= oran <= cfg.BOYUT_UST):
        return None

    return ncx + ax0, ncy + ay0, k          # ROI ofseti geri eklenir
