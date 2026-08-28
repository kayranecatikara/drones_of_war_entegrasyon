# -*- coding: utf-8 -*-
"""
================================================================================
DRON KAMERASI — CANLI YOLO TESTİ (GERÇEK dron, oyun DEĞİL)
================================================================================
    .venv/bin/python araclar/model_test_etme_kodlari.py --model yolo26n

Dronun FPV vericisi -> yer alıcısı -> AV çıkışı -> USB yakalama kartı
(/dev/video2, MacroSilicon MS210x "EasierCAP") -> bu araç. Kare ekrana
kutularıyla çizilir; istenirse kaydedilir.

DONANIM (bu bilgisayarda tespit edildi 2026-08-26):
  /dev/video0,1 : dizüstünün kendi web kamerası (test için değil)
  /dev/video2,3 : MacroSilicon MS210x video yakalayıcı  <- DRON BURADA
  Desteklediği kipler:
    YUYV 720x576@25 (PAL) / 720x480@30 (NTSC)   <- ANALOG KAYNAK, ham
    MJPG 1280x720@60 / 1920x1080@30             <- kart içinde ÖLÇEKLENMİŞ
  ⚠ MJPG 1920x1080 bu kartta ÖLÜ kare veriyor (düz gri, std=0.0) — KULLANMA.

VARSAYILAN KİP: YUYV 720x576 @25 — **PAL, HAM ANALOG** (2026-08-26'da değişti).
  ÖNCEDEN MJPG 1280x720'ydi; gecikme şikâyeti üzerine ölçüldü ve değiştirildi.
  MJPG yolunda kare şu fazladan işlerden geçiyordu:
    * kart 720x576'yı 1280x720'ye BÜYÜTÜYOR (yeni bilgi yok)
    * sonra JPEG'e SIKIŞTIRIYOR (kart içinde, kare tamamlanmadan başlayamaz)
    * bu bilgisayarda geri AÇILIYOR: ÖLÇÜLDÜ **10.6 ms/kare**
  10.6 ms, yolo26n'in çıkarım süresinin (ÖLÇÜLDÜ 9.0 ms) üstünde — yani
  görüntüyü sıkıştırıp açmak, tespit etmekten pahalıydı. YUYV'de bu üç adım
  da YOK: sürücü ne aldıysa onu verir.
  BEDEL — dürüstçe: PAL 25 fps ile sınırlı, MJPG 1280x720 60 fps'e çıkabiliyordu
  (kart o kareleri UYDURUYOR, analog kaynak zaten 25). Ve YUYV sıkıştırmasız:
  720·576·2·25 = **20.7 MB/s**, kart USB 2.0'da (ÖLÇÜLDÜ 480 Mbit/s) ve UVC
  eşzamanlı aktarım tavanı ~24 MB/s — yani sığıyor ama DAR. Kare düşmesi
  görürsen --ntsc (720x480 = 17.2 MB/s) ya da --mjpg'ye dön.
  Eski davranış: --mjpg (1280x720).  NTSC kaynak: --ntsc (720x480 @30).

SİNYAL KAPISI: alıcı yayın bulamayınca DÜZ MOR kare + köşede kanal OSD'si
  ("C8 5945") basar. Bu karede gri std ≈ 5-6; gerçek görüntüde 30+.
  Eşik 12 seçildi; altına düşünce ekrana "SİNYAL YOK" yazılır.

TAZE KARE (gecikmenin ASIL sebebi): sürücü, ana döngü çıkarım yaparken
  kare kuyruklar; `read()` sonra sıradaki **BAYAT** kareyi verir. Ekranda
  gördüğün gecikme budur. ÖLÇÜLDÜ (bu bilgisayar, V4L2): BUFFERSIZE=4 iken
  200 ms takılmadan sonra 3 kare beklemeden geliyor = **~100 ms bayat**;
  BUFFERSIZE=1'de 1 kare = ~33 ms. Bu araç ayrı bir iş parçacığında kamerayı
  DURMADAN okur ve ana döngüye her zaman EN SON kareyi verir; arada kalanlar
  atılır (atılan sayısı OSD'de "atilan" olarak görünür — atılması İYİDİR,
  bayat kare göstermemek demektir). OSD'deki "yas XX ms" o karenin
  kameradan alınmasıyla ekrana basılması arasındaki BİLGİSAYAR TARAFI
  gecikmesidir. Kapatıp kıyaslamak için: --tekiplik
  ⚠ Analog zincirin kendi gecikmesi (kamera -> VTX -> VRX -> kart) buraya
  DAHİL DEĞİL ve buradan ölçülemez; onu ancak ekrana kronometre tutup
  kameraya göstererek ölçersin.

KANAL SIRASI: `cv2.VideoCapture.read()` zaten **BGR** döner ve ultralytics
  numpy girdisini BGR varsayar -> DÖNÜŞÜM YAPILMAZ. (Oyun tarafında bu
  2026-08-25'te hataydı, bkz. araclar/kadraj.py başlığı.)

⛔ MENZİL HESABI YOK. `dow/gorus/kamera.py` içindeki C=997 px·m sabiti OYUN
  kamerasının odak uzaklığına aittir. Gerçek dron kamerası başka bir mercek;
  o sabitle menzil yazmak UYDURMA olur. Kutu boyutu piksel olarak gösterilir.

TUŞLAR
  q / ESC  çık                 k  o anki kareyi logs/model_testi/ altına yaz
  +  / -   güven eşiği ±0.05   r  kayıt başlat/durdur (annotasyonlu)
  b        kutuları gizle/göster
  ENTER    o anki kareyi HAM olarak agumantasyon_icin/ altına yaz

AGUMANTASYON KARELERİ — neden `k` ve `r`den AYRI bir yol:
  `k` ve `r` ANNOTASYONLU kareyi (`o`) yazar: üstünde çizilmiş kutular, sınıf
  yazıları ve köşedeki telemetri satırları vardır. Bunlar teşhis içindir.
  ENTER ise kameradan gelen HAM kareyi (`im`) yazar — üstünde tek piksel çizim
  yoktur. Sebep: bu kareler yeniden etiketlenip eğitime/veri artırmaya
  (augmentation) girecek. Üstünde kutu çizili bir kareyi eğitirsen ağ "yeşil
  dikdörtgen" gibi sahte bir ipucu öğrenir ve gerçek uçuşta o ipucu olmadığı
  için tespit çöker. Bu yüzden ham kare yazılır ve JPEG kalitesi 95'e çekilir
  (ekran kaydındaki 88 değil) — kayıp sıkıştırma artefaktı etiketlemeyi ve
  küçük hedefleri bozmasın diye.

  Dosya adı: <model>_<YYYYAAGG_SSDDss>_<sıra>.jpg  — zaman damgası hangi
  oturumda çekildiğini, sıra numarası aynı saniyede birden çok basılırsa
  üzerine yazmamayı garanti eder. Sayaç, dizinde ZATEN olan .jpg sayısından
  başlar; aracı ikinci kez çalıştırınca eski kareler silinmez/üzerine yazılmaz.

  ⚠ SİNYAL YOKKEN de yazar (kasten). Mor/gürültülü kare de bazen "negatif
  örnek" olarak işe yarar; ama OSD'de uyarı görünür, ayıklamak sende.
================================================================================
"""
import argparse, os, sys, threading, time
import cv2, numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

YESIL, SARI, KIRMIZI, BEYAZ = (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 255, 255)
SINYAL_ESIK = 12.0          # gri std; altı = alıcıda yayın yok


class TazeKare:
    """Kamerayı AYRI İŞ PARÇACIĞINDA durmadan okur; ana döngü hep EN SON kareyi alır.

    NEDEN GEREKLİ: ana döngü bir karede çıkarım + çizim + imshow yaparken
    (~15-40 ms) sürücü arkada kare kuyruklamaya devam eder. Tek iş parçacıklı
    kodda `cap.read()` o kuyruğun BAŞINDAKİNİ verir — yani en yenisini değil,
    en eskisini. Kuyruk bir kez dolunca gecikme KALICI olur ve döngü hızlansa
    bile kendi kendine kapanmaz.

    ÇÖZÜM: okuma hiç durmaz, tutulan tek kare sürekli üzerine yazılır. Ana
    döngü geç kalırsa aradaki kareler ATILIR (kaybedilir) — istenen budur:
    tespit için 200 ms önceki karenin hiçbir değeri yok.

    BEDEL: kare atlanır, yani her kareyi göremezsin. Kayıt/analiz için her
    kare gerekiyorsa --tekiplik ile kapat (o zaman gecikme geri gelir).
    """
    def __init__(self, cap):
        self.cap, self.im, self.t = cap, None, 0.0
        self.n = self.atilan = 0
        self.alindi = True
        self.kilit = threading.Lock()
        self.dur = False
        self.ip = threading.Thread(target=self._don, daemon=True)
        self.ip.start()

    def _don(self):
        while not self.dur:
            ok, im = self.cap.read()
            if not ok or im is None:
                time.sleep(0.005); continue
            with self.kilit:
                if not self.alindi and self.im is not None:
                    self.atilan += 1          # ana dongu bunu hic gormedi
                self.im, self.t, self.alindi, self.n = im, time.time(), False, self.n + 1

    def oku(self):
        """(kare, karenin YAŞI ms) — yaş, kameradan alınmasından bu yana geçen süre."""
        with self.kilit:
            if self.im is None:
                return None, 0.0
            self.alindi = True
            return self.im, (time.time() - self.t) * 1000.0

    def kapat(self):
        self.dur = True
        self.ip.join(timeout=1.0)


def kamera_ac(cihaz, fourcc, w, h, fps):
    c = cv2.VideoCapture(cihaz, cv2.CAP_V4L2)
    if not c.isOpened():
        sys.exit("HATA: /dev/video%d açılamadı. Başka bir program tutuyor "
                 "olabilir:  fuser -v /dev/video%d" % (cihaz, cihaz))
    c.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    c.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    c.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    c.set(cv2.CAP_PROP_FPS, fps)
    c.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # gecikme birikmesin
    for _ in range(8):                      # kart oturana kadar birkaç kare at
        c.read()
    ok, im = c.read()
    if not ok or im is None:
        sys.exit("HATA: kare okunamadı (%s %dx%d)." % (fourcc, w, h))
    return c, im


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="yolo26n",
                   help="modeller/<ad>.pt kısaltması VEYA doğrudan .pt yolu")
    p.add_argument("--cihaz", type=int, default=2, help="/dev/videoN")
    p.add_argument("--imgsz", type=int, default=960)
    p.add_argument("--conf",  type=float, default=0.40)
    p.add_argument("--mjpg", action="store_true",
                   help="ESKİ kip: kartın büyüttüğü MJPG 1280x720 (daha yavaş)")
    p.add_argument("--ntsc", action="store_true", help="PAL yerine NTSC 720x480@30")
    p.add_argument("--tekiplik", action="store_true",
                   help="taze-kare iş parçacığını KAPAT (kıyas için; gecikme artar)")
    p.add_argument("--fps",   type=float, default=30.0)
    p.add_argument("--kayit", default="", help="logs/<ad>/ altına kare yaz")
    p.add_argument("--sure",  type=float, default=0.0, help="0 = süresiz")
    p.add_argument("--agu",   default="agumantasyon_icin",
                   help="ENTER ile HAM karelerin yazılacağı dizin")
    a = p.parse_args()

    # MODEL YOLU: iki yazım da kabul edilir.
    #   --model yolo26l              -> modeller/yolo26l.pt  (kısaltma)
    #   --model /yol/bir/yere/x.pt   -> aynen o dosya        (kopyalamaya gerek yok)
    # AYIRT ETME: içinde "/" varsa ya da ".pt" ile bitiyorsa YOL sayılır.
    yol = a.model if ("/" in a.model or a.model.endswith(".pt")) \
          else "modeller/%s.pt" % a.model
    yol = os.path.expanduser(yol)
    if not os.path.exists(yol):
        sys.exit("HATA: %s yok.\n  Kısaltma kullandıysan dosya modeller/ "
                 "altında mı bak; değilse tam yolu ver." % yol)

    # ⚠ ultralytics uzantıyı DAYATIYOR: `check_suffix` .pt dışını reddeder
    #   (AssertionError: acceptable suffix is {'.pt'}, not .zip).
    #   Ama bir .pt ZATEN bir zip arşividir; tarayıcıdan `.pt.zip` diye inen
    #   dosya çoğu zaman ağırlığın TA KENDİSİDİR. O yüzden dosyayı açmıyoruz,
    #   sadece modeller/ altına .pt adıyla bir SEMBOLİK BAĞ kurup onu veriyoruz.
    #   (Kopya değil bağ: 53 MB'ı ikinci kez yazmanın anlamı yok.)
    if not yol.endswith(".pt"):
        os.makedirs("modeller", exist_ok=True)
        ad = os.path.basename(yol)
        for uz in (".zip", ".bin", ".dat"):
            if ad.endswith(uz): ad = ad[:-len(uz)]
        if not ad.endswith(".pt"): ad += ".pt"
        bag = os.path.join("modeller", ad)
        if not os.path.exists(bag):
            os.symlink(os.path.abspath(yol), bag)
            print("      uzantı .pt değil -> bağ kuruldu: %s" % bag)
        yol = bag

    # KİP SEÇİMİ: varsayılan HAM ANALOG (PAL). --mjpg eski davranışa döner.
    if a.mjpg:
        fourcc, W, H, FPS = "MJPG", 1280, 720, a.fps
    else:
        fourcc, W, H, FPS = ("YUYV", 720, 480, 30.0) if a.ntsc else ("YUYV", 720, 576, 25.0)

    print("[1/3] kamera açılıyor: /dev/video%d  %s %dx%d @%.0f%s"
          % (a.cihaz, fourcc, W, H, FPS, "" if a.mjpg else "  (HAM ANALOG)"))
    cap, im0 = kamera_ac(a.cihaz, fourcc, W, H, FPS)
    gw, gh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print("      gerçekleşen: %dx%d @ %.0f fps" % (gw, gh, cap.get(cv2.CAP_PROP_FPS)))

    from ultralytics import YOLO
    print("[2/3] model: %s  (imgsz=%d conf=%.2f)" % (yol, a.imgsz, a.conf))
    m = YOLO(yol)
    print("      sınıflar:", m.names)
    for _ in range(3):
        m.predict(im0, imgsz=a.imgsz, conf=a.conf, verbose=False)   # ısıtma

    kdiz = None
    if a.kayit:
        kdiz = os.path.join("logs", a.kayit)
        os.makedirs(kdiz, exist_ok=True)
        print("      kayıt:", kdiz)

    # AGUMANTASYON DİZİNİ: araç açılırken kurulur (ENTER'a basınca değil) ki
    # yazma izni/disk sorunu varsa daha ilk saniyede görülsün, kare çekmeye
    # çalışırken değil. Sayaç dizindeki mevcut .jpg sayısından başlatılır.
    agu_diz = os.path.abspath(os.path.expanduser(a.agu))
    os.makedirs(agu_diz, exist_ok=True)
    agu_i = len([f for f in os.listdir(agu_diz) if f.lower().endswith(".jpg")])
    print("      agumantasyon: %s  (dizinde %d kare var)" % (agu_diz, agu_i))

    AD = "DRON KAMERASI  -  %s" % os.path.basename(yol)
    cv2.namedWindow(AD, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(AD, gw, gh)
    print("[3/3] pencere açık.  ENTER=agumantasyon karesi  q=çık  "
          "k=kare kaydet  +/-=eşik  r=kayıt  b=kutu")

    # TAZE KARE KAYNAĞI: varsayılan açık. --tekiplik ile eski (bayat) yol.
    taze = None if a.tekiplik else TazeKare(cap)
    print("      taze-kare iş parçacığı:", "KAPALI (--tekiplik)" if a.tekiplik else "AÇIK")

    conf = a.conf
    ciz = True
    kayit_acik = bool(kdiz)
    kayit_i = 0
    n = nk = 0
    agu_son = ""          # OSD'de gösterilecek son yazılan dosyanın adı
    agu_son_t = 0.0       # ne zaman yazıldı (2 s sonra OSD'den silinir)
    fps_t, fps_n, fps = time.time(), 0, 0.0
    t_bas = time.time()
    try:
        while True:
            if taze is not None:
                im, yas_ms = taze.oku()
                if im is None:
                    time.sleep(0.005); continue      # ilk kare henüz gelmedi
            else:
                ok, im = cap.read()
                yas_ms = 0.0                          # tek iplikte ölçülemez
                if not ok or im is None:
                    print("kare okunamadı, yeniden deneniyor..."); time.sleep(0.1); continue
            n += 1

            gri_std = float(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).std())
            sinyal = gri_std >= SINYAL_ESIK

            td = time.perf_counter()
            r = m.predict(im, imgsz=a.imgsz, conf=conf, verbose=False)[0]
            det_ms = (time.perf_counter() - td) * 1000.0

            o = im.copy()
            en_iyi = None
            b = r.boxes
            if b is not None and len(b):
                xy = b.xyxy.cpu().numpy(); cf = b.conf.cpu().numpy()
                cl = b.cls.cpu().numpy().astype(int)
                i_iyi = int(cf.argmax())
                nk += 1
                if ciz:
                    for i in range(len(xy)):
                        x1, y1, x2, y2 = [int(v) for v in xy[i]]
                        renk = YESIL if i == i_iyi else SARI
                        cv2.rectangle(o, (x1, y1), (x2, y2), renk, 2)
                        cv2.putText(o, "%s %.2f" % (m.names.get(cl[i], cl[i]), cf[i]),
                                    (x1, max(18, y1 - 6)), 0, 0.6, renk, 2)
                x1, y1, x2, y2 = xy[i_iyi]
                en_iyi = (float(cf[i_iyi]), float(x2 - x1), float(y2 - y1), len(xy))

            fps_n += 1
            if time.time() - fps_t >= 1.0:
                fps = fps_n / (time.time() - fps_t); fps_t = time.time(); fps_n = 0

            satir = ["%s  imgsz=%d  conf>=%.2f  %s" % (a.model, a.imgsz, conf, fourcc),
                     "cikarim %5.1f ms   dongu %4.1f FPS   %dx%d" % (det_ms, fps, gw, gh),
                     ("kare yasi %4.1f ms   atilan %d/%d  (bilgisayar tarafi gecikme)"
                      % (yas_ms, taze.atilan, taze.n)) if taze is not None
                     else "TEK IPLIK - kare bayat olabilir (--tekiplik acik)",
                     "kutulu kare: %d/%d = %.0f%%" % (nk, n, 100.0 * nk / max(1, n))]
            satir.append("EN IYI conf %.2f   kutu %.0fx%.0f px   (toplam %d)"
                         % en_iyi if en_iyi else "KUTU YOK")
            if not sinyal:
                satir.append("!! SINYAL YOK (gri std %.1f < %.0f) - dronu ac / "
                             "alici kanalini ayarla" % (gri_std, SINYAL_ESIK))
            if kayit_acik:
                satir.append("KAYIT: %d kare" % kayit_i)
            satir.append("ENTER = agumantasyon karesi   (bu oturuma kadar: %d)" % agu_i)
            if time.time() - agu_son_t < 2.0:
                satir.append(">> YAZILDI: %s" % agu_son)

            for j, s in enumerate(satir):
                y = 24 + j * 26
                cv2.putText(o, s, (12, y), 0, 0.62, (0, 0, 0), 4)
                cv2.putText(o, s, (12, y), 0, 0.62,
                            KIRMIZI if s.startswith("!!") else (SARI if j == 0 else BEYAZ), 1)

            cv2.imshow(AD, o)

            if kayit_acik and kdiz:
                cv2.imwrite(os.path.join(kdiz, "f%05d.jpg" % kayit_i), o,
                            [cv2.IMWRITE_JPEG_QUALITY, 88])
                kayit_i += 1

            k = cv2.waitKey(1) & 0xFF
            if k in (ord('q'), 27): break
            if k == ord('b'): ciz = not ciz
            if k == ord('+') or k == ord('='): conf = min(0.95, conf + 0.05)
            if k == ord('-'): conf = max(0.05, conf - 0.05)
            if k == ord('r'):
                if not kdiz:
                    kdiz = os.path.join("logs", "model_testi_%d" % int(time.time()))
                    os.makedirs(kdiz, exist_ok=True)
                kayit_acik = not kayit_acik
                print("kayit:", kayit_acik, kdiz)
            # ENTER: GTK/Qt yapılarına göre 13 (CR) ya da 10 (LF) gelebiliyor;
            # ikisi de kabul edilir. Yazılan kare `o` DEĞİL `im` — yani ham.
            if k in (13, 10):
                agu_ad = "%s_%s_%04d.jpg" % (
                    os.path.splitext(os.path.basename(yol))[0],
                    time.strftime("%Y%m%d_%H%M%S"), agu_i)
                agu_yol = os.path.join(agu_diz, agu_ad)
                if cv2.imwrite(agu_yol, im, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    agu_i += 1
                    agu_son, agu_son_t = agu_ad, time.time()
                    print("agumantasyon:", agu_yol)
                else:
                    print("HATA: yazılamadı ->", agu_yol)

            if k == ord('k'):
                os.makedirs("logs/model_testi", exist_ok=True)
                ad = "logs/model_testi/%s_%d.jpg" % (
                    os.path.splitext(os.path.basename(yol))[0], int(time.time()))
                cv2.imwrite(ad, o); print("yazildi:", ad)

            if a.sure and time.time() - t_bas > a.sure: break
    finally:
        if taze is not None: taze.kapat()
        cap.release(); cv2.destroyAllWindows()
        print("bitti — %d kare, kutulu %d (%.0f%%), %.1f s"
              % (n, nk, 100.0 * nk / max(1, n), time.time() - t_bas))
        if taze is not None:
            print("taze-kare: kameradan %d kare geldi, %d tanesi bayat kalmadan atildi"
                  % (taze.n, taze.atilan))
        print("agumantasyon dizini: %s  (toplam %d kare)" % (agu_diz, agu_i))


if __name__ == "__main__":
    main()
