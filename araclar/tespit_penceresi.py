# -*- coding: utf-8 -*-
"""
================================================================================
TESPİT PENCERESİ — dedektörün çıktısını koşu boyunca AYRI pencerede izle
================================================================================
KULLANICI (2026-08-27): *"koşuları yaptırırken yanda detection modelinin
çıktısının nasıl olduğunu gösteren bir pencere görebilir miyim"*

⛔⛔ EN ÖNEMLİ TASARIM KARARI — NEDEN KENDİ YOLO'SUNU KOŞTURMUYOR:
  Bu pencere ekranı KENDİ kopyalayıp KENDİ çıkarımını yapsaydı GPU'da ikinci
  bir YOLO koşardı. Ölçüldü: tek çıkarım uçuşta 30 ms ve GPU zaten oyunla
  paylaşılıyor. İkinci model, ölçtüğümüz koşunun çıkarım hızını düşürür ve
  kampanyayı GEÇERSİZ kılar (§5.1: özelliğin ölçümü, ölçüm aracının kendisi
  tarafından bozulamaz).

  Onun yerine bu araç, `kosu.py`'nin ZATEN yayınladığı MJPEG akışını okur.
  Kutular sunucuda çiziliyor (`dow/panel.py::kare_koy`), yani gördüğün kutu
  güdümün O AN kullandığı kutunun TA KENDİSİDİR — ikinci bir yorum değil.
  Maliyet: JPEG çözme, ~1-2 ms/kare CPU. GPU maliyeti SIFIR.

KUTU RENKLERİ (sunucunun çizdiği):
  YEŞİL DÜZ    = dedektör o karede hedefi GERÇEKTEN buldu
  TURUNCU KESİK = ölçüm YOK; takipçinin öngörüsü (kutu yaşlanıyor)
  kutu yoksa   = o karede hiçbir şey bulunamadı

⚠ EKRANI KAPATMA: yakalama tüm ekrana bakıyor. Bu pencereyi OYUNUN ÜSTÜNE
  koyarsan panelin kaynak kapısı kapanır ve görüntü DONAR (üst şeritte
  "KAYNAK KAPALI" yazar). Pencereyi İKİNCİ EKRANA taşı.

⚠ KAMPANYA ARALARI: her koşu arasında oyun ve `kosu.py` yeniden başlıyor,
  yani panel de iniyor. Bu araç bunu bekler ve kendi kendine yeniden bağlanır;
  kapatıp açman gerekmez.

Kullanım:
    DISPLAY=:1 python3 araclar/tespit_penceresi.py
    DISPLAY=:1 python3 araclar/tespit_penceresi.py --olcek 1.4   # büyüt
  Çıkış: pencere seçiliyken  q  ya da  ESC
================================================================================
"""
import argparse
import json
import threading
import time
import urllib.error
import urllib.request

import cv2
import numpy as np

PENCERE = "DoW — dedektor ciktisi (kosu.py akisi)"

# telemetri, arka planda ve YAVAŞ okunur: panel HTTP'si koşuyla aynı süreçte
# olduğu için sık istek atmak ölçülen koşuya yük bindirir.
TELEM_HZ = 4.0

_telem = {"d": {}, "t": 0.0}
_dur = threading.Event()


def _telem_isi(port):
    yol = "http://127.0.0.1:%d/api/telemetry" % port
    while not _dur.is_set():
        try:
            with urllib.request.urlopen(yol, timeout=1.5) as c:
                _telem["d"] = json.loads(c.read() or b"{}")
                _telem["t"] = time.time()
        except Exception:
            _telem["d"] = {}
        time.sleep(1.0 / TELEM_HZ)


def _mjpeg_kareler(port):
    """MJPEG akışını çözüp kare kare verir. Akış koparsa StopIteration."""
    r = urllib.request.urlopen("http://127.0.0.1:%d/video" % port, timeout=5)
    tampon = b""
    while not _dur.is_set():
        parca = r.read(16384)
        if not parca:
            return
        tampon += parca
        # JPEG sınırları: FFD8 ... FFD9
        bas = tampon.find(b"\xff\xd8")
        son = tampon.find(b"\xff\xd9", bas + 2)
        if bas != -1 and son != -1:
            jpg = tampon[bas:son + 2]
            tampon = tampon[son + 2:]
            img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                yield img
        elif len(tampon) > 4_000_000:      # bozuk akış — tamponu boşalt
            tampon = b""


def _bilgi_seridi(img, bagli):
    """Üstte tek satırlık durum şeridi — hepsi panelin telemetrisinden."""
    d = _telem["d"]
    H, W = img.shape[:2]
    yuk = 62
    serit = np.zeros((yuk, W, 3), np.uint8)
    serit[:] = (24, 30, 38)

    def yaz(x, y, s, renk=(210, 220, 230), olcek=0.42, kalin=1):
        cv2.putText(serit, s, (x, y), cv2.FONT_HERSHEY_SIMPLEX, olcek,
                    renk, kalin, cv2.LINE_AA)

    if not bagli or not d:
        yaz(14, 38, "KOSU ARASI — panel bekleniyor (oyun yeniden basliyor)",
            (90, 170, 255), 0.55, 2)
        return np.vstack([serit, img])

    g = d.get("gorsel", {}) or {}
    perf = g.get("perf", {}) or {}
    tes = g.get("tespit")
    kk = d.get("kaynak_kare", {}) or {}
    faz = (d.get("gudum", {}) or {}).get("faz", "-")
    men = d.get("gercek_mesafe_m") or d.get("distance_m")

    # --- 1. satir: faz, menzil, kutu durumu ---
    yaz(14, 24, "FAZ", (130, 145, 160), 0.36)
    yaz(52, 24, str(faz), (255, 255, 255), 0.46, 2)

    yaz(190, 24, "MENZIL", (130, 145, 160), 0.36)
    yaz(255, 24, ("%.1f m" % men) if isinstance(men, (int, float)) else "—",
        (255, 255, 255), 0.46, 2)

    if tes:
        gercek = bool(tes.get("tespit_mi", True))
        renk = (120, 222, 74) if gercek else (60, 170, 255)
        etiket = "TESPIT" if gercek else "ONGORU (olcum yok)"
        yaz(360, 24, etiket, renk, 0.46, 2)
        yaz(560, 24, "guven %.2f" % float(tes.get("conf", 0.0) or 0.0),
            renk, 0.42)
        yaz(690, 24, "kutu %d px" % int(float(tes.get("w", 0) or 0) * 1920),
            (200, 210, 220), 0.42)
    else:
        yaz(360, 24, "KUTU YOK", (90, 100, 115), 0.46, 2)

    # --- 2. satir: hizlar ve kaynak kapisi ---
    yaz(14, 50, "cikarim %4.1f Hz  /  %5.1f ms" %
        (float(perf.get("fps", 0) or 0), float(perf.get("det_ms", 0) or 0)),
        (160, 175, 190), 0.40)
    yaz(250, 50, "yakalama %4.1f Hz" % float(perf.get("yakala_fps", 0) or 0),
        (160, 175, 190), 0.40)
    oran = g.get("ham_tespit_oran")
    yaz(400, 50, ("ham tespit %%%.0f (son 20 s)" % (float(oran) * 100.0))
        if isinstance(oran, (int, float)) else "ham tespit —",
        (160, 175, 190), 0.40)

    if not kk.get("ok", True):
        yaz(640, 50, "KAYNAK KAPALI — oyunun ustunde pencere var, GORUNTU DONDU",
            (60, 100, 255), 0.42, 2)

    return np.vstack([serit, img])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--olcek", type=float, default=1.0,
                    help="pencere buyutme carpani")
    a = ap.parse_args()

    print("=" * 70)
    print(" TESPIT PENCERESI — http://127.0.0.1:%d/video akisindan" % a.port)
    print(" kutulari SUNUCU cizer: yesil duz = gercek tespit,")
    print("                        turuncu kesik = takipci ongorusu")
    print(" ⚠ pencereyi OYUNUN USTUNE koyma — kaynak kapisi kapanir")
    print(" cikis: pencere seciliyken q ya da ESC")
    print("=" * 70, flush=True)

    threading.Thread(target=_telem_isi, args=(a.port,), daemon=True).start()
    cv2.namedWindow(PENCERE, cv2.WINDOW_NORMAL)

    bos = np.zeros((540, 960, 3), np.uint8)
    bos[:] = (18, 23, 30)
    cv2.putText(bos, "panel bekleniyor...", (300, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (110, 125, 140), 2, cv2.LINE_AA)

    try:
        while not _dur.is_set():
            bagli = False
            try:
                for kare in _mjpeg_kareler(a.port):
                    bagli = True
                    g = _bilgi_seridi(kare, True)
                    if a.olcek != 1.0:
                        g = cv2.resize(g, None, fx=a.olcek, fy=a.olcek,
                                       interpolation=cv2.INTER_LINEAR)
                    cv2.imshow(PENCERE, g)
                    k = cv2.waitKey(1) & 0xFF
                    if k in (ord("q"), 27):
                        _dur.set(); break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            except Exception as e:
                print("akis hatasi: %s" % e, flush=True)
            if _dur.is_set():
                break
            # panel indi (koşu arası) — bekle ve yeniden bağlan
            g = _bilgi_seridi(bos, False)
            if a.olcek != 1.0:
                g = cv2.resize(g, None, fx=a.olcek, fy=a.olcek)
            cv2.imshow(PENCERE, g)
            if (cv2.waitKey(500) & 0xFF) in (ord("q"), 27):
                break
            if bagli:
                print("[%s] akis koptu — yeniden baglaniyor"
                      % time.strftime("%H:%M:%S"), flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        _dur.set()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
