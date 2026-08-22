# -*- coding: utf-8 -*-
"""
BAĞIMSIZ İZLEYİCİ — paneli koşudan BAĞIMSIZ, sürekli çalıştırır.

Neden ayrı: panel şimdiye kadar kampanya sürecinin içindeydi ve kampanya
bitince kapanıyordu; kullanıcı "hedefi algıladığını göremedim" dedi.
Bu süreç SDK'ya BAĞLANMAZ (oyun tek istemci kabul ediyor) — yalnız EKRANI
yakalar, dedektörü koşturur ve panele basar. Kampanyayla aynı anda çalışır.

    python3 araclar/izleyici.py [hz]
    -> http://127.0.0.1:8801
"""
import os, sys, time
import numpy as np, mss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.ayarlar import Ayar
from dow import panel as PANEL
from dow.gorus import kamera as KAM
from dow.gorus.dedektor import Dedektor
from araclar.kadraj import BOLGE, ucusta_mi

def main():
    hz = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    PANEL.baslat(8801)
    det = Dedektor()
    sct = mss.mss()
    img = np.array(sct.grab(BOLGE))[:, :, :3][:, :, ::-1]
    det.isit(img)
    print(f"izleyici çalışıyor — http://127.0.0.1:8801  ({hz:.1f} Hz)", flush=True)
    n = 0; bulunan = 0; son = 0.0
    while True:
        t = time.time()
        img = np.array(sct.grab(BOLGE))[:, :, :3][:, :, ::-1]
        ucus = ucusta_mi(img[:, :, ::-1])
        tespit = det.bul(img) if ucus else None
        n += 1
        if tespit: bulunan += 1
        tel = {
            "durum": "UÇUŞTA" if ucus else "drone yok",
            "tespit_orani": round(100.0 * bulunan / max(1, n), 1),
            "kare": n,
            "imgsz": det.son_imgsz,
        }
        if tespit:
            tel["vis_menzil"] = round(KAM.menzil(max(tespit[2], tespit[3])) or -1, 1)
        PANEL.kare_koy(img, tespit, tel)
        if t - son > 5.0:
            son = t
            print(f"  kare {n} | tespit %{100*bulunan/max(1,n):.0f} | "
                  f"{'kutu ' + str(round(max(tespit[2],tespit[3]))) + 'px' if tespit else 'kutu yok'}",
                  flush=True)
        kalan = 1.0/hz - (time.time() - t)
        if kalan > 0: time.sleep(kalan)

if __name__ == "__main__":
    main()
