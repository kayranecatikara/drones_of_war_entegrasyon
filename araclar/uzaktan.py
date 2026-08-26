# -*- coding: utf-8 -*-
"""
================================================================================
 UZAKTAN KONTROL — panel + ekran yakalama, UÇUŞ TAKIMI YOK
================================================================================
Amaç TEK: oyunu arayüzde görmek ve Talon'u klavye/joystick ile sürmek.

NEDEN AYRI BİR GİRİŞ NOKTASI:
  `araclar/kosu.py` bir ÖLÇÜM koşucusudur — YOLO yükler, SDK'ya bağlanır,
  güdüm döngüsü koşar ve görev-sonu ekranından kurtulmak için MENÜYE TIKLAR.
  Uzaktan kontrol için bunların hepsi gereksiz; üstelik menü otomasyonu
  beklenmedik bir ekranda yanlış yere tıklayabilir. Burada o katmanların
  HİÇBİRİ yok: yalnız panel + kare yakalama.

NE YAPAR:
  * paneli 8801'de açar (arayüz + /video + /api/talon)
  * ekranı yakalayıp panele basar  -> oyun arayüze yansır
  * HUD imzası yoksa kareyi YAYINLAMAZ ve uyarı basar (yanlış pencere kapısı)

NE YAPMAZ:
  * uçurmaz, SDK'ya bağlanmaz, dedektör çalıştırmaz, menüye tıklamaz

KULLANIM:
    DISPLAY=:0 python3 araclar/uzaktan.py
    tarayıcı: http://127.0.0.1:8801

ÖNKOŞUL: oyun TAM EKRAN açık ve görevde olmalı (FLY -> E). Yakalama sabit
  ekran bölgesine bakar (kadraj.BOLGE = 1920x1080); pencere modunda HUD
  beklenen yerde olmaz ve kaynak kapısı sürekli uyarı basar.
================================================================================
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mss

from araclar.kadraj import BOLGE, BOLGE_HUD, grab_bgr, hud_parlak
from dow import panel as PANEL

YAKALA_HZ = float(os.environ.get("DOW_UZAKTAN_HZ", "15"))
OLCEK     = float(os.environ.get("DOW_UZAKTAN_OLCEK", "0.5"))
HUD_ESIK  = 0.05          # kadraj.ucusta_mi_hud ile AYNI eşik


def main():
    port = int(os.environ.get("DOW_PORT", "8801"))
    PANEL.baslat(port=port)
    print("panel      : http://127.0.0.1:%d" % port, flush=True)
    print("yakalama   : %.0f Hz, olcek %.2f" % (YAKALA_HZ, OLCEK), flush=True)
    print("Talon      : arayuzde '🎯 Talon Kontrol'", flush=True)
    print("durdurmak  : Ctrl+C", flush=True)

    dt = 1.0 / max(1.0, YAKALA_HZ)
    son_uyari = 0.0
    with mss.mss() as sct:
        while True:
            t = time.time()
            try:
                img = grab_bgr(sct, BOLGE)
                pk = hud_parlak(grab_bgr(sct, BOLGE_HUD))
                oyun_mu = pk > HUD_ESIK
                PANEL.kaynak_isaretle(oyun_mu, pk)
                if oyun_mu:
                    PANEL.fps_isaretle("yakala")
                    PANEL.kare_koy(img, None, olcek=OLCEK)
                elif t - son_uyari > 5.0:
                    son_uyari = t
                    print("  ⚠ oyun karesi YOK (HUD %.3f) — oyun tam ekran ve "
                          "gorevde mi? uzerini kapatan pencere var mi?" % pk,
                          flush=True)
            except Exception as e:
                if t - son_uyari > 5.0:
                    son_uyari = t
                    print("  yakalama hatasi: %s" % e, flush=True)
            kalan = dt - (time.time() - t)
            if kalan > 0:
                time.sleep(kalan)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nkapatildi", flush=True)
