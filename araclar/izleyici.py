# -*- coding: utf-8 -*-
"""
================================================================================
GÖRÜŞ İZLEYİCİSİ — kamera ve dedektör TAM HIZDA, panele bas
================================================================================
Kullanıcı isteği: "drone kamerası kaç FPS görüyorsa UI'da da öyle olsun,
detection modelinin çıktısını kaç FPS ile geliyorsa öyle bas, tam
performansını görmek istiyorum."

MİMARİ — üç bağımsız iş parçacığı (biri diğerini BEKLEMEZ):
  1) YAKALAMA : ekranı azami hızda grab eder, son kareyi paylaşır
  2) ÇIKARIM  : son kareyi alır, YOLO + HybridSORT koşar, sonucu paylaşır
  3) ÇİZİM    : son kare + son sonucu birleştirip panele basar
Böylece kamera FPS'i dedektör FPS'ine BAĞLI DEĞİL; panel ikisini de
kendi hızında gösterir ve üç ayrı sayaçla hangisinin darboğaz olduğu görünür.

⛔ Bu süreç SDK'ya BAĞLANMAZ (oyun tek istemci kabul ediyor). Yalnız ekranı
   okur. Kampanya süreci güdüm telemetrisini /telem'e POST eder.

    python3 araclar/izleyici.py
    -> http://127.0.0.1:8801
================================================================================
"""
import os, sys, threading, time
import numpy as np, mss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow import panel as PANEL
from dow.gorus import kamera as KAM
from dow.gorus.dedektor import Dedektor
from dow.gorus.tracker import TalonTracker
from araclar.kadraj import BOLGE, ucusta_mi

_dur = threading.Event()
_kare = {"img": None, "n": 0}
_sonuc = {"tespit": None, "iz": None, "n": -1, "imgsz": 0}
_kl = threading.Lock()


def _yakala():
    sct = mss.mss()
    while not _dur.is_set():
        img = np.array(sct.grab(BOLGE))[:, :, :3][:, :, ::-1]   # RGB
        with _kl:
            _kare["img"] = img; _kare["n"] += 1
        PANEL.fps_isaretle("yakala")


def _cikarim():
    det = Dedektor()
    trk = TalonTracker()
    ilk = True
    son_n = -1
    while not _dur.is_set():
        with _kl:
            img, n = _kare["img"], _kare["n"]
        if img is None or n == son_n:
            time.sleep(0.002); continue
        son_n = n
        if ilk:
            det.isit(img); ilk = False
        d = det.bul(img)
        dets = (np.array([[d[0]-d[2]/2, d[1]-d[3]/2, d[0]+d[2]/2, d[1]+d[3]/2,
                           d[4], 0]], np.float32)
                if d else np.empty((0, 6), np.float32))
        trk.update(dets, img[:, :, ::-1])
        akt = trk.active_boxes(max_coast=20)
        iz = None
        if akt:
            a = min(akt, key=lambda x: x["coast"])
            x1, y1, x2, y2 = a["bbox"]
            iz = ((x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1, a["id"], a["coast"])
        with _kl:
            _sonuc.update({"tespit": d, "iz": iz, "n": n, "imgsz": det.son_imgsz})
        PANEL.fps_isaretle("dedektor")


def _cizim():
    son_n = -1
    while not _dur.is_set():
        with _kl:
            img, n = _kare["img"], _kare["n"]
            s = dict(_sonuc)
        if img is None or n == son_n:
            time.sleep(0.002); continue
        son_n = n
        d, iz = s["tespit"], s["iz"]
        tel = {"durum": "UÇUŞTA" if ucusta_mi(img[:, :, ::-1]) else "drone yok",
               "imgsz": s["imgsz"]}
        if d:
            tel["vis_conf"] = round(d[4], 2)
            tel["vis_kutu_px"] = round(max(d[2], d[3]), 1)
            r = KAM.menzil(max(d[2], d[3]))
            if r: tel["vis_menzil"] = round(r, 1)
        if iz:
            tel["iz_id"] = int(iz[4]); tel["iz_coast"] = int(iz[5])
        PANEL.kare_koy(img, d, iz, tel)


def main():
    PANEL.baslat(8801)
    isl = [threading.Thread(target=f, daemon=True)
           for f in (_yakala, _cikarim, _cizim)]
    for t in isl: t.start()
    print("izleyici çalışıyor — http://127.0.0.1:8801", flush=True)
    try:
        while True:
            time.sleep(5)
            print(f"  FPS  yakalama {PANEL._hz(PANEL._fps['yakala']):.1f} | "
                  f"dedektör {PANEL._hz(PANEL._fps['dedektor']):.1f} | "
                  f"ekran {PANEL._hz(PANEL._fps['ekran']):.1f}", flush=True)
    except KeyboardInterrupt:
        _dur.set()


if __name__ == "__main__":
    main()
