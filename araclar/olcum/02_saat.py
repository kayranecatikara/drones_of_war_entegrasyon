# -*- coding: utf-8 -*-
"""ADIM 2 — EKRANDA SAAT GOSTER.

Kullanim:   python3 02_saat.py
Kapatmak:   pencereye tiklayip ESC

NE YAPAR: ekrani kaplayan bir pencerede, bu bilgisayarin KENDI saatini
buyuk rakamlarla gosterir. Bicim: sss.mmm  (saniyenin son uc hanesi +
milisaniye). Ornek: 742.318

⚠ NEDEN KENDI SAATIMIZ: tarayici kronometresi AYRI bir saat olurdu ve iki
  saat arasindaki kaymayi bilemezdik. Ayni saati kullanarak bu hata sifirlanir.

Bu pencere AYRI BIR TERMINALDE calisir ve olcum boyunca ACIK KALIR.
"""
import time

import cv2
import numpy as np

cv2.namedWindow("saat", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("saat", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("Saat penceresi acildi. Kamerayi bu ekrana dogrultun.")
print("Kapatmak icin pencereye tiklayip ESC'ye basin.")

while True:
    s = "%.3f" % (time.time() % 1000.0)
    img = np.zeros((520, 1500, 3), np.uint8)
    cv2.putText(img, s, (30, 360), cv2.FONT_HERSHEY_SIMPLEX,
                9.0, (255, 255, 255), 22, cv2.LINE_AA)
    cv2.imshow("saat", img)
    if cv2.waitKey(1) == 27:
        break

cv2.destroyAllWindows()
