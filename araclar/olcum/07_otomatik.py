# -*- coding: utf-8 -*-
"""⭐ GECIKME OLCUMU — TAM OTOMATIK, TEK KOMUT, ELLE OKUMA YOK.

Kullanim:   python3 araclar/olcum/07_otomatik.py <cihaz> [monitor]
Ornek   :   python3 araclar/olcum/07_otomatik.py /dev/video2 HDMI-0
            python3 araclar/olcum/07_otomatik.py /dev/video2
            (monitor verilmezse bagli ekranlari listeler ve sorar)

Bu betik 02/03/04/05/06'nin YERINE gecer. Tek komut, tek terminal.

================================================================
NASIL CALISIYOR
================================================================
Ekranda insan icin sayi degil, MAKINE ICIN bir isaret gosteriyoruz:
ArUco isareti (siyah-beyaz kare desen). Deseni her 25 ms'de bir
degistiriyoruz ve "hangi deseni saat kacta gosterdik" diye not aliyoruz.

Kamera ekrana bakiyor. Yakalanan her karede OpenCV deseni TANIYOR ve
numarasini soyluyor. O numaranin ne zaman gosterildigini bildigimiz icin:

    gecikme = (karenin bize ulastigi an) - (o desenin gosterildigi an)

Insan hicbir sey okumuyor, hicbir sey yazmiyor.

================================================================
UC KOL (ayni kosuda, sirayla, donusumlu)
================================================================
  A = TABAN         : duz cv2 read()
  B = BUFFERSIZE=1  : surucuye "tek tampon" der (yalniz Linux/V4L2)
  C = BOSALTMA      : kuyruktaki bayat kareleri atar (her platformda)

Sira: A B C A B C  — donusumlu, cunku sinyal/yuk zamanla degisebilir.

================================================================
⚠ KURULUM — BASLAMADAN ONCE
================================================================
  * Drone'u ELINDE TUTMA. Kitap yiginina/sehpaya koy, banta al,
    kamerasi monitore baksin. Olcum ~2 dakika surer.
  * Monitor ile kamera arasi ~40-60 cm.
  * Ekrandaki kare desen, kamera goruntusunde BUYUK ve NET gorunsun.
  * Oda isigini kis; ekran parlamasin.
  * Betik ISINMA sirasinda deseni goruyor mu diye KENDISI kontrol eder
    ve goremezse SANA SOYLER — o zaman duzeltip tekrar baslarsin.
"""
import csv
import os
import statistics as st
import sys
import threading
import time
from collections import deque

import cv2
import numpy as np

CIKTI = os.path.join("logs", "gecikme")

DICT = cv2.aruco.DICT_4X4_100
N_ID = 100
TIK_S = 0.025            # deseni her 25 ms'de bir degistir
ORNEK = 150              # kol basina toplanacak gecerli olcum
# ⛔ B (BUFFERSIZE=1) ve C (bosaltma) 2026-08-27'de OLCULDU: ikisi de
#   taban ile 1 ms icinde AYNI ciktilar (n=300/kol). Kuyruk zaten bostu.
#   Bu yuzden ikinci turda ELENDILER; yerlerine gercek aday kollar geldi.
PLAN = ["A", "D", "E", "F", "A", "D", "E", "F"]

KOL_ADI = {
    "A": "taban (cv2 read, YUYV)",
    "B": "BUFFERSIZE=1",
    "C": "bosaltma (drain)",
    "D": "ffmpeg borusu",
    "E": "gst-launch borusu",
    "F": "natif MJPG",
}
GECMIS = 400             # (t, id) gecmis derinligi

KURULUM = """
============================================================
  ⚠ KURULUM — BASLAMADAN ONCE
============================================================
  [ ] Drone'u ELINDE TUTMA. Kitap yiginina / sehpaya koy,
      gerekirse banta al. Kamerasi monitore baksin.
  [ ] Monitor ile kamera arasi ~40-60 cm.
  [ ] Ekrandaki KARE DESEN, kamera goruntusunde buyuk ve net
      gorunsun (kadrajin en az ucte biri).
  [ ] Oda isigini kis; ekran parlamasin.
  [ ] Baslayinca DRONE'A VE MONITORE DOKUNMA.

  Sure: gorunurluk kontrolu ~10 sn + olcum ~45 sn = ~1 dakika.
  Bitince pencere KENDILIGINDEN kapanir, sonuc ekrana yazilir.
============================================================
"""


def monitorler():
    """xrandr --listmonitors ciktisini ayristir.
    Donus: [(ad, genislik, yukseklik, x, y, mm_genislik), ...]"""
    import re
    import subprocess
    try:
        c = subprocess.check_output(["xrandr", "--listmonitors"],
                                    text=True, timeout=5)
    except Exception:
        return []
    out = []
    for satir in c.splitlines()[1:]:
        m = re.search(r"\+\*?(\S+)\s+(\d+)/(\d+)x(\d+)/(\d+)\+(\d+)\+(\d+)",
                      satir)
        if m:
            ad, w, mmw, h, _mmh, x, y = m.groups()
            out.append((ad, int(w), int(h), int(x), int(y), int(mmw)))
    return out


def ekran_sec(istek=None):
    """Hangi monitorde gosterecegiz? Donus: (ad, x, y, w, h)."""
    mons = monitorler()
    if not mons:
        print("⚠ xrandr okunamadi - varsayilan konum kullanilacak.")
        return ("?", 0, 0, 1280, 960)

    if istek:
        if "," in istek:                       # "1920,0" bicimi
            x, y = [int(v) for v in istek.split(",")[:2]]
            for ad, w, h, mx, my, _ in mons:
                if mx == x and my == y:
                    return (ad, mx, my, w, h)
            return ("elle", x, y, 1600, 900)
        for ad, w, h, mx, my, _ in mons:
            if ad.lower() == istek.lower():
                return (ad, mx, my, w, h)
        print("⚠ '%s' diye bir monitor yok." % istek)

    print("\nBAGLI MONITORLER")
    for i, (ad, w, h, mx, my, mmw) in enumerate(mons):
        inc = ((mmw ** 2 + (mmw * h / float(w)) ** 2) ** 0.5) / 25.4
        print("  [%d] %-10s %dx%d  konum +%d+%d   ~%.0f inc"
              % (i, ad, w, h, mx, my, inc))
    if len(mons) == 1:
        ad, w, h, mx, my, _ = mons[0]
        return (ad, mx, my, w, h)
    while True:
        try:
            c = input("Hangi monitorde gosterelim? (numara) > ").strip()
        except (EOFError, KeyboardInterrupt):
            raise SystemExit("\niptal.")
        if c.isdigit() and int(c) < len(mons):
            ad, w, h, mx, my, _ = mons[int(c)]
            return (ad, mx, my, w, h)
        print("  gecersiz - listedeki numaralardan birini yaz.")


def pencere_kur(ad_pencere, x, y, w, h):
    """Pencereyi ISTENEN monitore tasi ve buyut.

    ⚠ TAM EKRAN (WND_PROP_FULLSCREEN) KULLANMIYORUZ: cok ekranli
      kurulumda hangi ekrana acilacagi pencere yoneticisine kaliyor ve
      genellikle BIRINCIL ekrani seciyor. Tasinabilir ve ongorulebilir
      olan, pencereyi elle konumlandirmaktir.
    """
    cv2.namedWindow(ad_pencere, cv2.WINDOW_NORMAL)
    kw, kh = int(w * 0.94), int(h * 0.88)
    cv2.moveWindow(ad_pencere, x + (w - kw) // 2, y + 40)
    cv2.resizeWindow(ad_pencere, kw, kh)
    cv2.waitKey(60)
    cv2.moveWindow(ad_pencere, x + (w - kw) // 2, y + 40)   # bazi WM'ler ikinci cagriya ihtiyac duyar
    cv2.waitKey(60)


def isaret_uret(sozluk, boyut=760):
    """Her id icin desen goruntusunu ONCEDEN uret (dongude uretmek yavas)."""
    gen = getattr(cv2.aruco, "generateImageMarker", None) or cv2.aruco.drawMarker
    tuval = []
    for i in range(N_ID):
        m = gen(sozluk, i, boyut)
        img = np.full((boyut + 120, boyut + 120), 255, np.uint8)
        img[60:60 + boyut, 60:60 + boyut] = m
        tuval.append(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
    return tuval


class Boru:
    """Harici bir surecten (ffmpeg / gst-launch) HAM kare okur.

    NEDEN GEREKLI: bu OpenCV derlemesinde `GStreamer: NO`. Yani
    cv2.VideoCapture(..., CAP_GSTREAMER) CALISMIYOR ve OpenCV'yi yeniden
    derlemek numpy/opencv surum kirilganligi yuzunden riskli (CLAUDE.md).
    Cozum: boru hattini KOMUT SATIRINDAN kurup ham baytlari stdout'tan
    okumak. Cekirdek borusu geri basinc uygular, yani biz okumazsak
    surec bekler -> kare BIRIKMEZ.
    """

    def __init__(self, komut, w=640, h=480):
        import subprocess
        self.n = w * h * 3                       # bgr24
        self.p = subprocess.Popen(komut, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, bufsize=0)

    def isOpened(self):
        return self.p.poll() is None

    def _tam_oku(self, n):
        """TAM n bayt oku.

        ⛔ TUZAK (yakalandi 2026-08-27): `bufsize=0` ile stdout bir
        `io.FileIO` olur ve `read(n)` TEK syscall yapar -> boru tamponu
        kadar (genelde 65536 bayt) dondurur, istenen n'i DEGIL. Bir kare
        921600 bayt oldugu icin her okuma eksik geliyordu ve kol sessizce
        SIFIR kare uretiyordu. Dolmadan donmemek gerekiyor.
        """
        parcalar, kalan = [], n
        while kalan > 0:
            b = self.p.stdout.read(kalan)
            if not b:
                return None                      # surec kapandi
            parcalar.append(b)
            kalan -= len(b)
        return b"".join(parcalar)

    def read(self):
        veri = self._tam_oku(self.n)
        if veri is None:
            return False, None
        return True, np.frombuffer(veri, np.uint8).reshape(480, 640, 3).copy()

    def grab(self):
        return self.read()[0]

    def retrieve(self):
        return self.read()

    def set(self, *a):
        return True

    def get(self, *a):
        return 0

    def release(self):
        try:
            self.p.kill()
            self.p.wait(timeout=2)
        except Exception:
            pass


def ffmpeg_komut(cihaz):
    return ["ffmpeg", "-hide_banner", "-loglevel", "error",
            "-fflags", "nobuffer", "-flags", "low_delay",
            "-f", "v4l2", "-input_format", "yuyv422",
            "-video_size", "640x480", "-framerate", "30",
            "-i", str(cihaz), "-pix_fmt", "bgr24", "-f", "rawvideo", "-"]


def gst_komut(cihaz):
    return ["gst-launch-1.0", "-q",
            "v4l2src", "device=%s" % cihaz, "io-mode=2", "!",
            "video/x-raw,format=YUY2,width=640,height=480,framerate=30/1", "!",
            "videoconvert", "!", "video/x-raw,format=BGR", "!",
            "fdsink", "fd=1", "sync=false"]


class Yakalayici(threading.Thread):
    """Kareleri okur, deseni tanir, gecikmeyi hesaplar."""

    def __init__(self, cihaz, kol, gecmis, kilit, dedektor):
        super().__init__(daemon=True)
        self.cihaz, self.kol = cihaz, kol
        self.gecmis, self.kilit = gecmis, kilit
        self.det = dedektor
        self.sonuc = []
        self.gorulmedi = 0
        self.eslesmedi = 0
        self.dur = threading.Event()
        self.hata = None
        self.notlar = []
        self.hazir = threading.Event()

    def _ac(self):
        if self.kol == "D":                      # ffmpeg borusu
            try:
                b = Boru(ffmpeg_komut(self.cihaz))
                self.notlar.append("D: ffmpeg borusu (nobuffer, low_delay)")
                return b
            except Exception as e:
                self.notlar.append("D BASARISIZ: %s" % e)
                return None
        if self.kol == "E":                      # gstreamer borusu
            try:
                b = Boru(gst_komut(self.cihaz))
                self.notlar.append("E: gst-launch borusu (io-mode=2, sync=false)")
                return b
            except Exception as e:
                self.notlar.append("E BASARISIZ: %s" % e)
                return None

        cap = cv2.VideoCapture(self.cihaz)
        if not cap.isOpened():
            return None
        dortlu = "MJPG" if self.kol == "F" else "YUYV"
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*dortlu))
        if self.kol == "F":
            self.notlar.append("F: natif MJPG 640x480 (USB aktarimi ~10 kat az)")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        if self.kol == "B":
            kabul = cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.notlar.append("BUFFERSIZE=1 kabul: %s | geri okunan: %s"
                               % (kabul, cap.get(cv2.CAP_PROP_BUFFERSIZE)))
            if not kabul:
                self.notlar.append("UYARI: surucu desteklemiyor -> kol B = kol A")
        return cap

    def _kare(self, cap):
        if self.kol != "C":
            ok, k = cap.read()
            return ok, k
        for _ in range(12):                    # BOSALTMA
            t0 = time.perf_counter()
            cap.grab()
            if time.perf_counter() - t0 > 0.010:   # bu grab BEKLEDI -> canli
                break
        return cap.retrieve()

    def run(self):
        cap = self._ac()
        if cap is None:
            self.hata = "cihaz acilamadi: %s" % self.cihaz
            self.hazir.set()
            return
        for _ in range(45):                    # isinma
            if not cap.read()[0]:
                break
        self.hazir.set()

        while not self.dur.is_set() and len(self.sonuc) < ORNEK:
            ok, kare = self._kare(cap)
            t_varis = time.time()
            if not ok or kare is None:
                continue
            gri = cv2.cvtColor(kare, cv2.COLOR_BGR2GRAY)
            kose, idler, _ = self.det.detectMarkers(gri)
            if idler is None or len(idler) == 0:
                self.gorulmedi += 1
                continue
            gid = int(idler.flatten()[0])
            t_gost = None
            with self.kilit:
                for t, i in reversed(self.gecmis):
                    if i == gid and t <= t_varis:
                        t_gost = t
                        break
            if t_gost is None:
                self.eslesmedi += 1
                continue
            # ⚠ YARIM TIK DUZELTMESI (oz-testle dogrulandi, +14 ms sapma).
            # Desen TIK_S'de bir degisiyor; eslestirme hep "en son gosterilen"
            # desene dusuyor. Kamera o deseni, gosterilmeye baslamasindan
            # SONRA rastgele bir anda goruyor -> olcum ortalama TIK_S/2 kadar
            # FAZLA cikiyor. Sentetik testte 180 ms -> 194 ms olcuyordu;
            # duzeltmeyle 181 ms.
            g = (t_varis - t_gost) * 1000.0 - (TIK_S * 1000.0 / 2.0)
            if 0.0 < g < 1500.0:
                self.sonuc.append(g)
            else:
                self.eslesmedi += 1
        cap.release()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ham = sys.argv[1]
    istek_ekran = sys.argv[2] if len(sys.argv) > 2 else None
    cihaz = int(ham) if ham.isdigit() else ham
    os.makedirs(CIKTI, exist_ok=True)

    sozluk = cv2.aruco.getPredefinedDictionary(DICT)
    par = cv2.aruco.DetectorParameters()
    dedektor = cv2.aruco.ArucoDetector(sozluk, par)

    print("desenler hazirlaniyor...", flush=True)
    kareler = isaret_uret(sozluk)

    ekran_ad, ex, ey, ew, eh = ekran_sec(istek_ekran)
    print("\n>>> DESEN SU MONITORDE GOSTERILECEK: %s  (+%d+%d, %dx%d)"
          % (ekran_ad, ex, ey, ew, eh))
    print(">>> Kamerayi ISTE O monitore dogrult.")

    print(KURULUM)
    try:
        input("Kurulum hazirsa ENTER > ")
    except (EOFError, KeyboardInterrupt):
        print("\niptal.")
        return

    pencere_kur("isaret", ex, ey, ew, eh)

    gecmis = deque(maxlen=GECMIS)
    kilit = threading.Lock()
    gid = 0
    son_tik = 0.0

    def ekran_tik():
        """Deseni gerekiyorsa degistir. Ana is parcaciginda cagrilir."""
        nonlocal gid, son_tik
        simdi = time.time()
        if simdi - son_tik < TIK_S:
            cv2.waitKey(1)
            return
        cv2.imshow("isaret", kareler[gid])
        cv2.waitKey(1)
        t = time.time()
        with kilit:
            gecmis.append((t, gid))
        gid = (gid + 1) % N_ID
        son_tik = t

    # --- isinma + gorunurluk kontrolu ---
    print("\ndesen gorunuyor mu diye bakiliyor (5 saniye)...", flush=True)
    deneme = Yakalayici(cihaz, "A", gecmis, kilit, dedektor)
    deneme.start()
    t0 = time.time()
    while time.time() - t0 < 5.0 and not deneme.hazir.is_set():
        ekran_tik()
    t0 = time.time()
    while time.time() - t0 < 5.0 and len(deneme.sonuc) < 10:
        ekran_tik()
    deneme.dur.set()
    deneme.join(timeout=3)

    if deneme.hata:
        cv2.destroyAllWindows()
        print("\nHATA: %s" % deneme.hata)
        return
    if len(deneme.sonuc) < 5:
        cv2.destroyAllWindows()
        print("\n" + "!" * 60)
        print("DESEN TANINAMIYOR. Olcum baslatilmadi.")
        print("  gorulmedi: %d kare | eslesmedi: %d"
              % (deneme.gorulmedi, deneme.eslesmedi))
        print("\nYAPILACAK:")
        print("  * Kamerayi monitore daha iyi dogrult, desen kadraji doldursun")
        print("  * Mesafeyi 40-60 cm yap")
        print("  * Oda isigini kis, ekran parlamasin")
        print("  * Odaklanma/netlik sorunu varsa kamerayi biraz uzaklastir")
        print("!" * 60)
        return
    print("✓ desen taniniyor (%d ornek, kaba medyan %.0f ms). Olcum basliyor.\n"
          % (len(deneme.sonuc), st.median(deneme.sonuc)))

    # --- asil olcum: 6 kosu, donusumlu (pencere zaten acik) ---
    kosular, notlar = [], []
    for n, kol in enumerate(PLAN, 1):
        etiket = "%s%d" % (kol, 1 + (n - 1) // len(set(PLAN)))
        print("[%d/%d] %-26s ..." % (n, len(PLAN), KOL_ADI.get(kol, kol)),
              end="", flush=True)
        y = Yakalayici(cihaz, kol, gecmis, kilit, dedektor)
        y.start()
        t0 = time.time()
        while y.is_alive() and time.time() - t0 < 45.0:
            ekran_tik()
        y.dur.set()
        y.join(timeout=3)
        if y.sonuc:
            print("  %d olcum, medyan %.0f ms" % (len(y.sonuc), st.median(y.sonuc)))
            kosular.append((etiket, kol, y.sonuc))
        else:
            print("  BASARISIZ (olcum yok)")
        notlar.extend(y.notlar)

    cv2.destroyAllWindows()

    if not kosular:
        print("\nHic olcum toplanamadi.")
        return

    # --- rapor ---
    sat = []

    def yaz(s):
        print(s, flush=True)
        sat.append(s)

    yaz("")
    yaz("=" * 62)
    yaz("GECIKME OLCUMU — SONUC")
    yaz("=" * 62)
    yaz("cihaz: %s | kol basina hedef ornek: %d | desen tiki: %.0f ms"
        % (ham, ORNEK, TIK_S * 1000))
    yaz("")
    yaz("KOSU KOSU")
    yaz("%-8s %-4s %6s %10s %10s %10s" %
        ("etiket", "kol", "n", "medyan", "%10", "%90"))
    for etiket, kol, v in kosular:
        s = sorted(v)
        yaz("%-8s %-4s %6d %10.0f %10.0f %10.0f"
            % (etiket, kol, len(v), st.median(v),
               s[int(len(s) * 0.10)], s[int(len(s) * 0.90)]))

    kollar = {}
    for _, kol, v in kosular:
        kollar.setdefault(kol, []).extend(v)

    yaz("")
    yaz("KOL KOL (kosular birlestirilmis)")
    yaz("%-4s %-26s %6s %10s %10s"
        % ("kol", "yontem", "n", "medyan", "en iyi"))
    ozet = {}
    for kol in sorted(kollar):
        v = kollar[kol]
        ozet[kol] = st.median(v)
        yaz("%-4s %-26s %6d %10.0f %10.0f"
            % (kol, KOL_ADI.get(kol, "?"), len(v), st.median(v), min(v)))

    yaz("")
    yaz("=" * 62)
    yaz("KARAR")
    yaz("=" * 62)
    A = ozet.get("A")
    if A is None:
        yaz("Taban (kol A) olculemedi.")
    else:
        yaz("Taban (A, duz read)        : %6.0f ms" % A)
        for kol in sorted(k for k in ozet if k != "A"):
            yaz("%-26s : %6.0f ms   (kazanc %+.0f ms)"
                % (KOL_ADI.get(kol, kol), ozet[kol], A - ozet[kol]))
        en_iyi = min(ozet, key=lambda k: ozet[k])
        kazanc = A - ozet[en_iyi]
        yaz("")
        if kazanc < 20:
            yaz(">>> YAZILIM TAMPONU SUCLU DEGIL.")
            yaz(">>> Gecikme cihazin kendi donaniminda.")
            yaz(">>> ⛔ 2026-08-27: ALTI yontem denendi (A/B/C/D/E/F,")
            yaz("    n=300/kol, 1800 olcum). HEPSI 1-2 ms icinde AYNI.")
            yaz("    Yazilim tarafinda alinacak yol KALMADI.")
            yaz(">>> Tek kalan yol: GECIKME TELAFISI (ileri kestirim).")
        else:
            yaz(">>> KOL %s KAZANDI: %.0f ms bedava kazanc." % (en_iyi, kazanc))
            yaz(">>> Bu yontem sisteme KALICI konmali.")

    if notlar:
        yaz("")
        yaz("SURUCU NOTLARI")
        for n_ in dict.fromkeys(notlar):
            yaz("  " + n_)

    yaz("")
    yaz("OLCUMUN SINIRI (durust not)")
    yaz("  * Sayilar MONITORUN kendi gecikmesini de icerir (~16-40 ms).")
    yaz("    Kollar arasi FARK temizdir - monitor payi hepsinde ayni.")
    yaz("  * Desen %.0f ms'de bir degisiyor -> ornek basina ±%.0f ms"
        % (TIK_S * 1000, TIK_S * 1000 / 2))
    yaz("    yuvarlama. Yarim tiklik SISTEMATIK sapma (%.0f ms) COTARILDI;"
        % (TIK_S * 1000 / 2))
    yaz("    sentetik testte 180 ms -> 181 ms olculuyor.")
    yaz("  * Gercek gudum monitor kullanmaz: oradaki gecikme bu")
    yaz("    sayilardan ~20-25 ms DAHA AZDIR.")

    with open(os.path.join(CIKTI, "SONUC.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(sat) + "\n")
    with open(os.path.join(CIKTI, "ham_olcumler.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["etiket", "kol", "gecikme_ms"])
        for etiket, kol, v in kosular:
            for g in v:
                w.writerow([etiket, kol, "%.1f" % g])

    print("\nyazildi: %s/SONUC.txt  ve  ham_olcumler.csv" % CIKTI)


if __name__ == "__main__":
    main()
