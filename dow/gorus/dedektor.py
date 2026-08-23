# -*- coding: utf-8 -*-
"""
================================================================================
DEDEKTÖR — talon_v3.pt (kullanıcının DoW fotoğraflarıyla eğittiği model)
================================================================================
ÖLÇÜLDÜ 2026-08-21, canlı DoW V5.0.0, n=857 kare, EŞLEŞTİRİLMİŞ A/B
(aynı karede iki çözünürlük). "GERÇEK tespit" = kutu, kalibre kamera
modelinin öngördüğü konumun yakınında VE makul boyutta.

  menzil    imgsz=960   imgsz=1920
  25-40 m      %32         %63
  40-60 m       %6         %55
  60-90 m       %0          %9

⭐ imgsz=1920 ZORUNLU. Sebep: 1920x1080 kadraj 960'a küçültülünce hedef
   YARIYA iner; 50 m'de 20 px olan Talon ağın girdisinde 10 px kalır ve
   YOLO'nun tespit sınırının altına düşer.
   BEDEL: çıkarım 24 -> 60 ms; döngü 17.5 -> 10.8 FPS. (FP16 fayda vermedi.)

KONUM DOĞRULUĞU: tespit edilen kutu, kalibre modelin öngördüğü yere
   1.6-2.5 px içinde düşüyor -> kamera modeli bağımsız DOĞRULANDI.

GÜVEN EŞİĞİ (1920'de tarandı):
  eşik 0.10 -> tespit %49, argmax doğru %43   (yanlış-pozitif argmax'ı çalıyor)
  eşik 0.40 -> tespit %40, argmax doğru %40   (fark KAPANIYOR)
  eşik 0.50 -> tespit %38, argmax doğru %38
  SEÇİM 0.40: ~9 puan tespit karşılığında yanlış-pozitifin en yüksek güveni
  çalmasını tamamen bitirir. Güdüm menzili bilmediği için argmax'a mecburdur.

⚠ GÖRSEL DEVİR MENZİLİ <= 50 m. 60-90 m'de tespit %9 — orada GPS fazı sürer.
⚠ Tespit %55-63; kesintiler VAR.

⛔ HybridSORT TAKİPÇİSİ ÇIKARILDI (2026-08-22, kullanıcı kararı):
  "şu an detection kötü olduğu için tracking bir işe yaramıyor ve rastgele
   yerlere track atabiliyor, o yüzden gerek yok şu anda hybridsort'a.
   düzgün detection modeli gelince tekrardan entegre edebiliriz."
  Takipçi, dedektörün YANLIŞ-POZİTİFİNİ de bir iz olarak benimseyip Kalman
  ile 20 kare boyunca İLERİ TAŞIYORDU; yani hatayı silmiyor, uzatıyordu.
  Kod `dow/gorus/tracker.py` olarak depo tarihçesinde duruyor (commit b435f08).
================================================================================
"""
import numpy as np

MODEL_YOLU = "modeller/talon_v3.pt"
IMGSZ_UZAK = 1920      # ÖLÇÜLDÜ: 960 kullanmak 40-60 m'de tespiti %56 -> %7 düşürür
IMGSZ_YAKIN = 960      # yakında hız kazanmak için (24 ms vs 60 ms)
CONF_MIN   = 0.40      # ÖLÇÜLDÜ: argmax'ı yanlış-pozitiften korur
DEVIR_MENZIL_M = 50.0  # bu menzilin ötesinde görsel devir YAPILMAZ

# UYARLANABİLİR ÇÖZÜNÜRLÜK EŞİĞİ — bir ÖNCEKİ karenin kutu genişliğine bakar.
# Kutu bu değerden BÜYÜKSE hedef zaten iri demektir; 960 yeterli olur ve
# döngü 10.8 -> 17.5 FPS'e çıkar.
#
# EŞİK ÖLÇÜLDÜ — tahmin DEĞİL. Yakın menzil koşusu, n=788 kare, EŞLEŞTİRİLMİŞ
# (aynı karede iki çözünürlük de koşuldu):
#
#     kutu px   menzil    n     960    1920   kazanan
#     15- 22     54 m    227     %6     %87    1920
#     22- 30     38 m    284    %39     %69    1920
#     30- 40     28 m    107    %67     %89    1920
#     40- 55     21 m    126    %59     %78    1920
#     55- 75     15 m     39    %92     %90    960   <- GEÇİŞ NOKTASI
#     75-110     11 m      5    %40     %40    (n yetersiz)
#
# 55 px'in ALTINDA 1920 açık ara kazanıyor (54 m'de %6 -> %87, 14 kat).
# 55 px'in ÜSTÜNDE ikisi eşitleniyor (%92 vs %90) ama 960 1.6 KAT HIZLI
# -> terminal fazda (menzil <18 m, kapanma hızlı) tepki süresi kazanılır.
YAKIN_ESIK_PX = 55.0   # ÖLÇÜLDÜ (≈18 m menzil)


class Dedektor:
    """Uyarlanabilir çözünürlüklü dedektör.
    Önceki karenin kutu boyutuna bakarak bu karenin imgsz'sini seçer:
    büyük kutu (yakın hedef) -> 960 (hızlı), küçük kutu (uzak) -> 1920 (duyarlı).
    Kutu yoksa DAİMA 1920 (hedefi kaybetmişken duyarlılık şart)."""

    def __init__(self, yol=MODEL_YOLU, conf=CONF_MIN, uyarlanabilir=True,
                 yakin_esik_px=YAKIN_ESIK_PX):
        from ultralytics import YOLO
        self.m = YOLO(yol); self.conf=conf
        self.uyarlanabilir = uyarlanabilir
        self.yakin_esik = yakin_esik_px
        self._son_w = 0.0
        self._isindi = False
        self.son_imgsz = IMGSZ_UZAK      # teşhis: hangi kolda çalıştık

    def isit(self, img):
        for iz in (IMGSZ_YAKIN, IMGSZ_UZAK):
            for _ in range(2):
                self.m.predict(img, imgsz=iz, conf=self.conf, verbose=False)
        self._isindi = True

    def _imgsz_sec(self):
        if not self.uyarlanabilir: return IMGSZ_UZAK
        # kutu yoksa (son_w=0) DAİMA duyarlı kol
        return IMGSZ_YAKIN if self._son_w >= self.yakin_esik else IMGSZ_UZAK

    def bul(self, img):
        """En yüksek güvenli kutuyu döner: (cx, cy, w, h, conf) ya da None.
        ⚠ Menzil BİLİNMEZ -> boyut/konum kapısı UYGULANMAZ; argmax'a mecburuz.
          Bu yüzden CONF_MIN yüksek tutulur (ölçümle seçildi)."""
        if not self._isindi: self.isit(img)
        iz = self._imgsz_sec(); self.son_imgsz = iz
        r = self.m.predict(img, imgsz=iz, conf=self.conf, verbose=False)[0]
        if not len(r.boxes):
            self._son_w = 0.0            # kayıpta duyarlı kola DÖN
            return None
        b = max(r.boxes, key=lambda x: float(x.conf))
        x1,y1,x2,y2 = b.xyxy[0].tolist()
        w = x2-x1
        self._son_w = w
        return ((x1+x2)/2.0, (y1+y2)/2.0, w, y2-y1, float(b.conf))

    def bul_hepsi(self, img, conf=None):
        """DÜŞÜK eşikte TÜM kutular: [(cx, cy, w, h, conf), ...].

        NEDEN: `bul()` argmax döner ve argmax yanlış-pozitif olabilir
        (OSD yazısı 0.50 güven alabiliyor). Görsel fazda hedefin NEREDE
        olduğunu KENDİ önceki kutumuzdan biliyoruz; o yüzden eşiği
        düşürüp adayları YERELLİK ile eleyebiliriz. Bu kapı tamamen
        KAMERA içidir — GPS yok (§10)."""
        if not self._isindi: self.isit(img)
        iz = self._imgsz_sec(); self.son_imgsz = iz
        r = self.m.predict(img, imgsz=iz, conf=conf or self.conf,
                           verbose=False)[0]
        out = []
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            out.append(((x1+x2)/2.0, (y1+y2)/2.0, x2-x1, y2-y1, float(b.conf)))
        self._son_w = max((o[2] for o in out), default=0.0)
        return out

    def sifirla(self):
        self._son_w = 0.0
