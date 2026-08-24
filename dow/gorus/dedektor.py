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
   BEDEL (fp32): çıkarım 24 -> 60 ms; döngü 17.5 -> 10.8 FPS.
   ⚠ ESKİDEN BURADA "FP16 fayda vermedi" YAZIYORDU — YANLIŞTI, bkz. DetCfg.

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
import os
import time

import numpy as np

# ⭐ MODEL SEÇİMİ (2026-08-24). v5 = OSD hard-negatif + uzak uçak fotoğrafları
# eklenmiş veri setiyle eğitildi (dataset_det_v5, 30 epoch, aynı mimari YOLO11s).
# ÖLÇÜLDÜ — 300 UZAK hedefli kare (<32 px, >31 m), düz argmax, conf 0.40,
# yani KAPI YOKMUŞ GİBİ:
#            hedefte   OSD'de   baska   kutu yok
#     v3      %17.0     %1.0    %19.3    %62.7
#     v5      %22.7     %0.7    %22.3    %54.3
# -> uzak tespit belirgin daha iyi; OSD zaten %1'di, %0.7'ye indi.
# Geri dönüş: DOW_MODEL=talon_v3
MODEL_YOLU = "modeller/%s.pt" % os.environ.get("DOW_MODEL", "talon_v5")
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


def _b(k, v):  return os.environ.get(k, str(int(v))).strip() not in ("0","","false","False")
def _i(k, v):  return int(float(os.environ.get(k, v)))


class DetCfg:
    """CANLI ayarlar — SINIF nitelikleri. Güdüm döngüsü her karede okur,
    panel uçuş sırasında değiştirebilir (CLAUDE.md §6).

    FP16 — 16 bit kayan nokta
    ------------------------
    Ağırlıklar ve ara hesaplar 32 yerine 16 bitle tutulur. Ekran kartının
    "tensor core" birimleri 16 bitte iki kat iş yapar.
    ÖLÇÜLDÜ 2026-08-23, 140 kare, EŞLEŞTİRİLMİŞ (aynı kareler):
        fp32 imgsz1920: 30.6 ms | gerçek tespit %80.0
        fp16 imgsz1920: 19.1 ms | gerçek tespit %79.3     <- 1.6 KAT
    ⛔ Bu dosyanın ESKİ başlığında "FP16 fayda vermedi" yazıyordu — YANLIŞTI.
      O ölçüm oyun çalışırken (GPU paylaşımlıyken) alınmış olmalı.
    ⛔ ONNX Runtime (CUDA sağlayıcı, fp16) AYNI karelerde 38.0 ms — PyTorch
      fp16'nın İKİ KATI. ONNX ELENDİ, modeller/*.onnx üretilmedi bırakıldı.

    PENCERE_PX — natif yerel pencere (ROI)
    --------------------------------------
    Kaynak kadraj 1920x1080; imgsz=1920 dendiğinde ultralytics uzun kenarı
    1920'ye ölçekler -> ölçek katsayısı TAM 1.0. Yani ağa ZATEN natif piksel
    gidiyor, sadece 1088'e dolgu var. O hâlde hedefin etrafından PxP natif
    kare kesmek hedefin PİKSELLERİNİ DEĞİŞTİRMEZ; yalnız taranan alanı
    P²/(1920·1088) kadar küçültür (640 icin 1/5.1).
    ÖLÇÜLDÜ 2026-08-23, eşleştirilmiş, truth-doğrulamalı, 120 kare/bant:
        bant           TAM1920   KIRP640
        <25px (>40m)     %15.0     %12.5
        25-40 (25-40m)   %20.8     %25.0
        40-70 (14-25m)   %81.7     %81.7
        >70px  (<14m)    %50.0     %50.0
      -> kalite AYNI, süre 30.6 -> 5.7 ms.
    ⛔ PENCERE BOYUTU REJİME GÖRE SEÇİLİR — ÖLÇÜLDÜ 2026-08-23 (HZ ilk
      çevrimi, §5.1 mekanizma kapısı): görsel fazda hedef iri olduğu için
      uyarlanabilir kural zaten imgsz=960 seçiyor. 960 letterbox 960x544 =
      522 bin piksel; 640 pencere 410 bin. Yani BUGÜNKÜ tabana karşı kazanç
      yalnız 1.28 kat -> uçuşta det_ms 19.9 -> 19.6, yani HİÇ.
      5.4 katlık kazanç imgsz=1920'ye karşıydı ve o yalnız UZAK menzilde
      devreye giriyor. Bu yüzden pencere, mevcut YAKIN_ESIK_PX kuralına
      oturtuldu:
          kutu >= 55 px (yakın): 960 letterbox -> 448 natif  (2.6 kat)
          kutu <  55 px (uzak) : 1920          -> 640 natif  (5.1 kat)
      Her iki boyut da kendi bandında tam kadrajla EŞİT ölçüldü
      (448: %82.5 vs %81.7 ve %49.2 vs %50.0).

    ⚠ Pencere merkezi `dow/ana.py::_yerel_bul` içindeki `ref`tir: köprüyle
      KENDİ dönüşümümüz telafi edilmiş son kutu. Girdi yalnız kamera + kendi
      IMU'muz — GPS YOK (§10 temiz).

    ISKA_TAM — pencere ıskalarsa AYNI tikte tam kadraja düş
    -------------------------------------------------------
    Bu kapı sayesinde tespit oranı taban koldan KÖTÜ OLAMAZ: pencere bir şey
    bulursa hızlıyız, bulamazsa zaten tam kadraj koşuyoruz. Bedel yalnız
    ıska karelerinde (~3 ms fazla).
    """
    MODEL         = os.environ.get("DOW_MODEL", "talon_v5")
    FP16          = _b("DOW_FP16", False)
    PENCERE_PX    = _i("DOW_PENCERE_PX", 0)        # UZAK rejim; 0 = KAPALI
    PENCERE_YAKIN = _i("DOW_PENCERE_YAKIN", 448)   # YAKIN rejim (kutu>=55px)
    ISKA_TAM      = _b("DOW_PENCERE_ISKA_TAM", True)


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
        self.son_pencere = 0             # §5.1 mekanizma: 0 = tam kadraj
        self.son_ms = 0.0                # §5.1 mekanizma: tarama süresi
        self.pencere_say = 0; self.tam_say = 0; self.iska_tam = 0
        self._fp16 = False               # modelin O ANKİ gerçek hassasiyeti
        self._model_yuklu = os.path.splitext(os.path.basename(yol))[0]

    def isit(self, img):
        for iz in (IMGSZ_YAKIN, IMGSZ_UZAK):
            for _ in range(2):
                self.m.predict(img, imgsz=iz, conf=self.conf,
                               half=DetCfg.FP16, verbose=False)
        self._isindi = True

    def _imgsz_sec(self):
        if not self.uyarlanabilir: return IMGSZ_UZAK
        # kutu yoksa (son_w=0) DAİMA duyarlı kol
        return IMGSZ_YAKIN if self._son_w >= self.yakin_esik else IMGSZ_UZAK

    def _model_uygula(self):
        """DetCfg.MODEL değişmişse ağırlıkları YENİDEN YÜKLE.

        NEDEN GEREKLİ: A/B kampanyasında iki modeli DÖNÜŞÜMLÜ koşmak şart
        (§4) — bir modelin hepsini arka arkaya koşmak sim kaymasını kola
        yazar. Model yalnız başlangıçta okunursa dönüşüm imkânsızdır.
        ⚠ Yeniden yükleme predictor'ı sıfırlar; bu yüzden fp16 durumu da
        sıfırlanır ve `_hassasiyet_uygula` bir sonraki karede yeniden
        uygular.
        """
        istenen = str(DetCfg.MODEL)
        if istenen == self._model_yuklu: return
        from ultralytics import YOLO
        self.m = YOLO("modeller/%s.pt" % istenen)
        self._model_yuklu = istenen
        self._isindi = False; self._fp16 = False; self._son_w = 0.0

    def _hassasiyet_uygula(self):
        """⛔ FP16 BAYRAĞINI GERÇEKTEN UYGULA — yoksa kol SAHTE kalır.

        YAŞANDI 2026-08-23 (ve muhtemelen 2026-08-21'de de): `predict(...,
        half=True)` ultralytics predictor'ı BİR KEZ kurulduktan sonra
        YOK SAYILIYOR. Model `torch.float32` kalıyor, süre değişmiyor.
        Mekanizma kapısı (§5.1) yakaladı: uçuşta det_ms 19.9 -> 20.6, yani
        HİÇ hızlanma yok. Çevrimdışı tezgâhta çalışmasının sebebi orada her
        kol için YENİ bir YOLO nesnesi kurulmasıydı.

        DOĞRU YOL — ikisi BİRDEN gerekir:
          1) ağırlıkları dönüştür (`.half()` / `.float()`)
          2) `AutoBackend.fp16` bayrağını çevir — GİRDİ tensörünün tipi
             `predictor.preprocess` içinde buna bakılarak seçilir; yalnız
             ağırlığı çevirmek tip uyuşmazlığı hatası verir.
        """
        ist = bool(DetCfg.FP16)
        if ist == self._fp16: return
        pr = getattr(self.m, "predictor", None)
        ab = getattr(pr, "model", None) if pr is not None else None
        if ab is None: return                      # predictor henüz kurulmadı
        ab.half() if ist else ab.float()
        ab.fp16 = ist
        if hasattr(pr, "args"): pr.args.half = ist
        self._fp16 = ist

    def _cikar(self, im, imgsz, conf, x0=0, y0=0):
        """Bir görüntüyü tara; kutuları TAM KADRAJ koordinatında döner."""
        r = self.m.predict(im, imgsz=imgsz, conf=conf,
                           half=DetCfg.FP16, verbose=False)[0]
        out = []
        for b in r.boxes:
            a1, b1, a2, b2 = b.xyxy[0].tolist()
            out.append(((a1+a2)/2.0 + x0, (b1+b2)/2.0 + y0,
                        a2-a1, b2-b1, float(b.conf)))
        return out

    def _tara(self, img, conf, merkez):
        """PENCERE varsa oradan, yoksa/ıskalarsa TAM KADRAJDAN tarar.

        Teşhis (§5.1 mekanizma sütunu):
          son_pencere : bu karede kullanılan pencere kenarı (0 = tam kadraj)
          son_ms      : bu karenin toplam tarama süresi (ms)
        """
        self._model_uygula()
        if not self._isindi: self.isit(img)
        self._hassasiyet_uygula()          # §5.1: bayrak GERÇEKTEN uygulansın
        t0 = time.perf_counter()
        # REJİM SEÇİMİ — `_imgsz_sec` ile AYNI eşik (`_son_w` vs YAKIN_ESIK).
        P = int(DetCfg.PENCERE_PX)
        if P > 0 and self._son_w >= self.yakin_esik:
            P = int(DetCfg.PENCERE_YAKIN) or P
        H, W = img.shape[:2]
        if P > 0 and merkez is not None and P <= min(W, H):
            x0 = int(min(max(merkez[0] - P/2.0, 0), W - P))
            y0 = int(min(max(merkez[1] - P/2.0, 0), H - P))
            alt = np.ascontiguousarray(img[y0:y0+P, x0:x0+P])
            kutular = self._cikar(alt, P, conf, x0, y0)
            self.pencere_say += 1
            if kutular or not DetCfg.ISKA_TAM:
                self.son_pencere = P
                self.son_ms = (time.perf_counter() - t0) * 1000.0
                return kutular
            self.iska_tam += 1          # pencere boş -> AYNI tikte tam kadraj
        iz = self._imgsz_sec()
        self.son_imgsz = iz
        kutular = self._cikar(img, iz, conf, 0, 0)
        self.tam_say += 1
        self.son_pencere = 0
        self.son_ms = (time.perf_counter() - t0) * 1000.0
        return kutular

    def bul(self, img, merkez=None):
        """En yüksek güvenli kutu: (cx, cy, w, h, conf) ya da None.
        ⚠ Menzil BİLİNMEZ -> boyut/konum kapısı UYGULANMAZ; argmax'a mecburuz.
          Bu yüzden CONF_MIN yüksek tutulur (ölçümle seçildi)."""
        kutular = self._tara(img, self.conf, merkez)
        if not kutular:
            self._son_w = 0.0            # kayıpta duyarlı kola DÖN
            return None
        b = max(kutular, key=lambda k: k[4])
        self._son_w = b[2]
        return b

    def bul_hepsi(self, img, conf=None, merkez=None):
        """DÜŞÜK eşikte TÜM kutular: [(cx, cy, w, h, conf), ...].

        NEDEN: `bul()` argmax döner ve argmax yanlış-pozitif olabilir
        (OSD yazısı 0.50 güven alabiliyor). Görsel fazda hedefin NEREDE
        olduğunu KENDİ önceki kutumuzdan biliyoruz; o yüzden eşiği
        düşürüp adayları YERELLİK ile eleyebiliriz. Bu kapı tamamen
        KAMERA içidir — GPS yok (§10)."""
        kutular = self._tara(img, conf or self.conf, merkez)
        self._son_w = max((k[2] for k in kutular), default=0.0)
        return kutular

    def sifirla(self):
        self._son_w = 0.0
