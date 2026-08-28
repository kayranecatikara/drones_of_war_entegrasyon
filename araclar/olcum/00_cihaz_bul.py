# -*- coding: utf-8 -*-
"""ADIM 0 — yakalama kartini bul ve dogrula.

Kullanim:   python3 00_cihaz_bul.py
Cikti   :   logs/gecikme/00_cihaz.txt  + ekrana ozet

NE YAPAR: 0..9 arasi tum video cihazlarini acmayi dener, acilan her birinden
bir kare alir ve boyutunu yazar. Boylece "hangi indeks yakalama karti,
hangisi dizustunun kendi web kamerasi" sorusu KESIN cevaplanir.

⚠ NEDEN GEREKLI: cv2.VideoCapture(0) genellikle DIZUSTUNUN KENDI KAMERASIDIR.
  Yanlis cihazi olcerseniz butun sayilar anlamsiz olur.
"""
import os
import sys

import cv2

CIKTI = os.path.join("logs", "gecikme")
os.makedirs(CIKTI, exist_ok=True)

satirlar = []


def yaz(s):
    print(s, flush=True)
    satirlar.append(s)


yaz("OpenCV surumu: %s" % cv2.__version__)
yaz("Platform      : %s" % sys.platform)
yaz("")

# Linux'ta yol ile, Windows'ta indeks ile denenir.
adaylar = []
if sys.platform.startswith("linux"):
    adaylar = ["/dev/video%d" % i for i in range(10)]
else:
    adaylar = list(range(10))

for a in adaylar:
    cap = cv2.VideoCapture(a)
    if not cap.isOpened():
        cap.release()
        continue
    ok, kare = cap.read()
    if ok and kare is not None:
        h, w = kare.shape[:2]
        yaz("ACILDI  %-14s ->  %d x %d" % (str(a), w, h))
        ad = os.path.join(CIKTI, "00_cihaz_%s.png" % str(a).replace("/", "_"))
        cv2.imwrite(ad, kare)
        yaz("        ornek kare: %s" % ad)
    else:
        yaz("ACILDI  %-14s ->  kare ALINAMADI" % str(a))
    cap.release()

yaz("")
yaz("=> Kaydedilen PNG'lere BAKIN. Icinde FPV goruntusu (OSD, ufuk) olan")
yaz("   hangisiyse YAKALAMA KARTI odur. Bir sonraki adimda onu kullanin.")

with open(os.path.join(CIKTI, "00_cihaz.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(satirlar) + "\n")
print("\nyazildi: %s/00_cihaz.txt" % CIKTI)
