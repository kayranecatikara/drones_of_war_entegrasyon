# -*- coding: utf-8 -*-
"""
================================================================================
DRON KAMERASI — CANLI YOLO TESTİ (GERÇEK dron, oyun DEĞİL)
================================================================================
    .venv/bin/python araclar/dron_kamera.py --model yolo26n

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

VARSAYILAN KİP: MJPG 1280x720.
  NEDEN: analog kaynak PAL mi NTSC mi bilinmiyorsa YUYV'de yanlış boyut
  seçmek kareyi kaydırır/yırtar. MJPG'de kart kaynağı kendi çözer ve her
  hâlükârda geçerli kare basar. Ham analog piksel istersen: --ham (720x576)
  ya da --ham --ntsc (720x480).
  BEDEL: kart 720'den 1280'e BÜYÜTÜYOR — yeni bilgi eklenmez, JPEG bozulması
  eklenir. YOLO zaten girdiyi `imgsz`ye ölçeklediği için tespit açısından
  ikisi birbirine yakındır; kesin kıyas için --ham ile de koş.

SİNYAL KAPISI: alıcı yayın bulamayınca DÜZ MOR kare + köşede kanal OSD'si
  ("C8 5945") basar. Bu karede gri std ≈ 5-6; gerçek görüntüde 30+.
  Eşik 12 seçildi; altına düşünce ekrana "SİNYAL YOK" yazılır.

KANAL SIRASI: `cv2.VideoCapture.read()` zaten **BGR** döner ve ultralytics
  numpy girdisini BGR varsayar -> DÖNÜŞÜM YAPILMAZ. (Oyun tarafında bu
  2026-08-25'te hataydı, bkz. araclar/kadraj.py başlığı.)

⛔ MENZİL HESABI YOK. `dow/gorus/kamera.py` içindeki C=997 px·m sabiti OYUN
  kamerasının odak uzaklığına aittir. Gerçek dron kamerası başka bir mercek;
  o sabitle menzil yazmak UYDURMA olur. Kutu boyutu piksel olarak gösterilir.

TUŞLAR
  q / ESC  çık                 k  o anki kareyi logs/dron_kamera/ altına yaz
  +  / -   güven eşiği ±0.05   r  kayıt başlat/durdur (annotasyonlu)
  b        kutuları gizle/göster
================================================================================
"""
import argparse, os, sys, time
import cv2, numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

YESIL, SARI, KIRMIZI, BEYAZ = (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 255, 255)
SINYAL_ESIK = 12.0          # gri std; altı = alıcıda yayın yok


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
    p.add_argument("--model", default="yolo26n", help="modeller/<ad>.pt")
    p.add_argument("--cihaz", type=int, default=2, help="/dev/videoN")
    p.add_argument("--imgsz", type=int, default=960)
    p.add_argument("--conf",  type=float, default=0.40)
    p.add_argument("--ham",   action="store_true", help="YUYV natif analog kip")
    p.add_argument("--ntsc",  action="store_true", help="--ham ile 720x480")
    p.add_argument("--fps",   type=float, default=30.0)
    p.add_argument("--kayit", default="", help="logs/<ad>/ altına kare yaz")
    p.add_argument("--sure",  type=float, default=0.0, help="0 = süresiz")
    a = p.parse_args()

    yol = "modeller/%s.pt" % a.model
    if not os.path.exists(yol):
        sys.exit("HATA: %s yok." % yol)

    if a.ham:
        fourcc, W, H = "YUYV", 720, (480 if a.ntsc else 576)
    else:
        fourcc, W, H = "MJPG", 1280, 720

    print("[1/3] kamera açılıyor: /dev/video%d  %s %dx%d" % (a.cihaz, fourcc, W, H))
    cap, im0 = kamera_ac(a.cihaz, fourcc, W, H, a.fps)
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

    AD = "DRON KAMERASI  -  %s" % a.model
    cv2.namedWindow(AD, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(AD, gw, gh)
    print("[3/3] pencere açık.  q=çık  k=kare kaydet  +/-=eşik  r=kayıt  b=kutu")

    conf = a.conf
    ciz = True
    kayit_acik = bool(kdiz)
    kayit_i = 0
    n = nk = 0
    fps_t, fps_n, fps = time.time(), 0, 0.0
    t_bas = time.time()
    try:
        while True:
            ok, im = cap.read()
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

            satir = ["%s  imgsz=%d  conf>=%.2f" % (a.model, a.imgsz, conf),
                     "cikarim %5.1f ms   dongu %4.1f FPS   %dx%d" % (det_ms, fps, gw, gh),
                     "kutulu kare: %d/%d = %.0f%%" % (nk, n, 100.0 * nk / max(1, n))]
            satir.append("EN IYI conf %.2f   kutu %.0fx%.0f px   (toplam %d)"
                         % en_iyi if en_iyi else "KUTU YOK")
            if not sinyal:
                satir.append("!! SINYAL YOK (gri std %.1f < %.0f) - dronu ac / "
                             "alici kanalini ayarla" % (gri_std, SINYAL_ESIK))
            if kayit_acik:
                satir.append("KAYIT: %d kare" % kayit_i)

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
                    kdiz = os.path.join("logs", "dron_kamera_%d" % int(time.time()))
                    os.makedirs(kdiz, exist_ok=True)
                kayit_acik = not kayit_acik
                print("kayit:", kayit_acik, kdiz)
            if k == ord('k'):
                os.makedirs("logs/dron_kamera", exist_ok=True)
                ad = "logs/dron_kamera/%s_%d.jpg" % (a.model, int(time.time()))
                cv2.imwrite(ad, o); print("yazildi:", ad)

            if a.sure and time.time() - t_bas > a.sure: break
    finally:
        cap.release(); cv2.destroyAllWindows()
        print("bitti — %d kare, kutulu %d (%.0f%%), %.1f s"
              % (n, nk, 100.0 * nk / max(1, n), time.time() - t_bas))


if __name__ == "__main__":
    main()
