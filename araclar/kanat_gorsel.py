# -*- coding: utf-8 -*-
"""KANAT GORSEL TESTI — isDead ACIK/KAPALI ayni sahnede iki kare.

Sayisal test MENZILLE KARISTI (7.5 m vs 29.6 m); bu yuzden gozle bakiyoruz.
Kontrol acilir, kare alinir; birakilir, 2 s beklenir, kare alinir. Menzil
bu surede cok az degisir, yani iki kare KIYASLANABILIR.
"""
import json
import os
import sys
import time
import urllib.request

import cv2
import mss

KOK = "/home/kayra/projects/drones_of_war_entegrasyon"
sys.path.insert(0, KOK)
os.chdir(KOK)
from araclar.kadraj import grab_bgr

CIK = "/tmp/claude-1000/-home-kayra-projects-avci-sim/218652dc-e1fb-4089-9632-3b9dde62ddbd/scratchpad"
KOPRU = "/tmp/talon_kopru.txt"
sayac = [0]


def yaz(aktif, thr=0.405):
    sayac[0] += 1
    with open(KOPRU + ".tmp", "w") as f:
        f.write("%d %.3f 0.000 0.000 0.000 %d 0\n" % (aktif, thr, sayac[0]))
    os.replace(KOPRU + ".tmp", KOPRU)


def menzil():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8801/telem", timeout=1) as c:
            return json.loads(c.read() or b"{}").get("gercek_mesafe_m")
    except Exception:
        return None


def kare(ad, sct):
    img = grab_bgr(sct)
    yol = os.path.join(CIK, "kanat_%s.jpg" % ad)
    cv2.imwrite(yol, img)
    return yol


with mss.mss() as sct:
    print("menzil bekleniyor (<40 m)...", flush=True)
    t0 = time.time()
    while time.time() - t0 < 120:
        R = menzil()
        if isinstance(R, (int, float)) and R < 40:
            break
        time.sleep(0.3)
    print("menzil %s m" % R, flush=True)

    # --- 1) KONTROL ACIK (isDead) ---
    t1 = time.time()
    while time.time() - t1 < 3.0:
        yaz(1)
        time.sleep(0.1)
    Ra = menzil()
    ya = kare("acik", sct)
    print("ACIK   menzil %s m -> %s" % (Ra, ya), flush=True)

    # --- 2) BIRAK, 2.5 s bekle ---
    t2 = time.time()
    while time.time() - t2 < 2.5:
        yaz(0)
        time.sleep(0.1)
    Rk = menzil()
    yk = kare("kapali", sct)
    print("KAPALI menzil %s m -> %s" % (Rk, yk), flush=True)
    yaz(0)
