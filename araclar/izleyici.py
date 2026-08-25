# -*- coding: utf-8 -*-
"""
================================================================================
GÖRÜŞ İZLEYİCİSİ — kampanya KOŞMUYORKEN paneli beslemek için
================================================================================
    python3 araclar/izleyici.py      ->  http://127.0.0.1:8801

⛔⛔ KAMPANYA (araclar/kosu.py veya tarama.py) İLE AYNI ANDA ÇALIŞTIRILMAZ.
   Kampanya paneli ve görüş iş parçacığını KENDİSİ koşturuyor. İkisini
   birlikte açmak ekranı iki kez kopyalar ve YOLO'yu iki kez koşturur.
   ÖLÇÜLDÜ (2026-08-22, GA04 vs GV11): tam bu hata yüzünden istasyon tutma
   5.3 m -> 25.3 m'ye bozuldu ve istenen hız 120 s boyunca tavanda doyumda
   kaldı. Arayüz uçuşu yalnız yavaşlatmıyordu, BOZUYORDU.

HIZ TAVANLARI (Ayar): yakalama PANEL_YAKALA_HZ, dedektör PANEL_DET_HZ.
Oyun ~60-120 FPS basıyor; bunun üstünde kopyalamak AYNI kareyi tekrar okumak.

⛔ HybridSORT çıkarıldı (2026-08-22) — bkz. dow/gorus/dedektor.py başlığı.
⛔ Bu süreç SDK'ya BAĞLANMAZ (oyun tek istemci kabul ediyor); yalnız ekranı okur.
================================================================================
"""
import os, sys, threading, time
import numpy as np, mss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow import panel as PANEL
from dow.ayarlar import Ayar
from dow.gorus import kamera as KAM
from dow.gorus.dedektor import Dedektor
from araclar.kadraj import BOLGE, grab_bgr, ucusta_mi

_dur = threading.Event()
_kare = {"img": None, "n": 0}
_sonuc = {"tespit": None, "n": -1, "imgsz": 0}
_kl = threading.Lock()


def _yakala():
    """Ekranı SABİT hızda kopyala (tavan: Ayar.PANEL_YAKALA_HZ)."""
    sct = mss.mss()
    dt = 1.0 / max(1.0, Ayar.PANEL_YAKALA_HZ)
    while not _dur.is_set():
        t = time.time()
        img = grab_bgr(sct)                                     # sürekli BGR
        with _kl:
            _kare["img"] = img; _kare["n"] += 1
        PANEL.fps_isaretle("yakala")
        kalan = dt - (time.time() - t)
        if kalan > 0:
            time.sleep(kalan)


def _cikarim():
    """YOLO'yu SABİT hızda koştur (tavan: Ayar.PANEL_DET_HZ)."""
    det = Dedektor()
    ilk = True
    son_n = -1
    dt = 1.0 / max(0.1, Ayar.PANEL_DET_HZ)
    while not _dur.is_set():
        t = time.time()
        with _kl:
            img, n = _kare["img"], _kare["n"]
        if img is None or n == son_n:
            time.sleep(0.005); continue
        son_n = n
        if ilk:
            det.isit(img); ilk = False
        d = det.bul(img)
        with _kl:
            _sonuc.update({"tespit": d, "n": n, "imgsz": det.son_imgsz})
        PANEL.fps_isaretle("dedektor")
        kalan = dt - (time.time() - t)
        if kalan > 0:
            time.sleep(kalan)


def _cizim():
    son_n = -1
    while not _dur.is_set():
        with _kl:
            img, n = _kare["img"], _kare["n"]
            s = dict(_sonuc)
        if img is None or n == son_n:
            time.sleep(0.005); continue
        son_n = n
        d = s["tespit"]
        tel = {"durum": "UÇUŞTA" if ucusta_mi(img) else "drone yok",
               "imgsz": s["imgsz"]}
        if d:
            tel["vis_conf"] = round(d[4], 2)
            tel["vis_kutu_px"] = round(max(d[2], d[3]), 1)
            r = KAM.menzil(max(d[2], d[3]))
            if r: tel["vis_menzil"] = round(r, 1)
        PANEL.kare_koy(img, d, tel, olcek=Ayar.PANEL_OLCEK)


def main():
    PANEL.baslat(8801)
    for f in (_yakala, _cikarim, _cizim):
        threading.Thread(target=f, daemon=True).start()
    print(f"izleyici — http://127.0.0.1:8801  "
          f"(yakalama tavanı {Ayar.PANEL_YAKALA_HZ:.0f} Hz, "
          f"dedektör tavanı {Ayar.PANEL_DET_HZ:.0f} Hz)", flush=True)
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
