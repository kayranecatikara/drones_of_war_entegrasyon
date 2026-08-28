# -*- coding: utf-8 -*-
"""ADIM 1 — KARE VARIS DUZENI (on teshis, 5 dakika, kurulum GEREKTIRMEZ).

Kullanim:   python3 01_varis_duzeni.py <cihaz>
Ornek   :   python3 01_varis_duzeni.py /dev/video2        (Linux)
            python3 01_varis_duzeni.py 1                  (Windows)
Cikti   :   logs/gecikme/01_varis.txt

NE OLCER: iki kare arasinda gecen sureyi (ms). 200 kare.

NASIL OKUNUR:
  33 33 33 33 33 ...        -> kuyruk SIG. v4l2 sucLU DEGIL, sorun kartta.
  0 0 0 0 133 0 0 0 0 133   -> kuyruk DOLU. Dort kare tampondan aninda
                               geliyor, sonra bekliyor. v4l2 SUCLU,
                               BEDAVA duzelir (ADIM 3, Kol B/C).
  duzensiz (33 100 12 60)   -> kart kare dusuruyor / sinyal zayif.

⚠ Bu adim kamera-ekran kurulumu istemez. ONCE BUNU KOSUN.
"""
import os
import statistics as st
import sys
import time

import cv2

CIKTI = os.path.join("logs", "gecikme")
os.makedirs(CIKTI, exist_ok=True)

if len(sys.argv) < 2:
    print("kullanim: python3 01_varis_duzeni.py <cihaz>")
    sys.exit(1)

ham = sys.argv[1]
cihaz = int(ham) if ham.isdigit() else ham

cap = cv2.VideoCapture(cihaz)
if not cap.isOpened():
    print("HATA: cihaz acilamadi: %s" % ham)
    sys.exit(1)

cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

print("isiniyor (60 kare)...", flush=True)
for _ in range(60):
    cap.read()

print("olculuyor (200 kare, ~7 saniye)...", flush=True)
t0 = time.perf_counter()
ara = []
for _ in range(200):
    ok, _kare = cap.read()
    t = time.perf_counter()
    if ok:
        ara.append((t - t0) * 1000.0)
    t0 = t
cap.release()

if not ara:
    print("HATA: hic kare alinamadi.")
    sys.exit(1)

anlik = sum(1 for a in ara if a < 5.0)          # tampondan gelen kareler
med = st.median(ara)

satirlar = [
    "KARE VARIS DUZENI",
    "cihaz          : %s" % ham,
    "kare sayisi    : %d" % len(ara),
    "medyan aralik  : %.1f ms   (30 fps -> 33.3 ms beklenir)" % med,
    "en kisa        : %.1f ms" % min(ara),
    "en uzun        : %.1f ms" % max(ara),
    "ANLIK gelen    : %d / %d  (%.0f%%)  <5 ms, yani TAMPONDAN"
    % (anlik, len(ara), 100.0 * anlik / len(ara)),
    "",
    "ilk 40 aralik (ms):",
    " ".join("%.0f" % a for a in ara[:40]),
    "",
]

if anlik > len(ara) * 0.15:
    satirlar.append(">>> HUKUM: KUYRUK DOLU. Karelerin %%%.0f'i tampondan "
                    "aninda geliyor." % (100.0 * anlik / len(ara)))
    satirlar.append(">>> v4l2/surucu tamponu gecikmeye KATKI VERIYOR.")
    satirlar.append(">>> ADIM 3'te Kol B ve Kol C belirgin kazanc vermeli.")
else:
    satirlar.append(">>> HUKUM: kuyruk SIG gorunuyor.")
    satirlar.append(">>> Gecikme buyuk ihtimalle KARTIN kendi tamponunda.")
    satirlar.append(">>> ADIM 3 yine de kosulmali (kesin sayi icin).")

metin = "\n".join(satirlar)
print("\n" + metin)
with open(os.path.join(CIKTI, "01_varis.txt"), "w", encoding="utf-8") as f:
    f.write(metin + "\n")
print("\nyazildi: %s/01_varis.txt" % CIKTI)
