# -*- coding: utf-8 -*-
"""
================================================================================
GÜVEN EŞİĞİ TARAMASI — düşük eşik ne kurtarır, ne getirir?
================================================================================
SORU (2026-08-24): `model-fps` branch'i predict eşiğini 0.10'da tutup zayıf
kutuları TAKİPÇİYE süzdürüyor; biz 0.40 KAPI kullanıyoruz. Hangisi daha çok
GERÇEK tespit veriyor, ve düşük eşiğin bedeli ne kadar yanlış-pozitif?

YÖNTEM: kayıtlı karelerde dedektörü DÜŞÜK eşikte koştur, her kutuyu
meta.csv'deki `bek_cx/bek_cy/bek_w` (truth geometriden ÖNGÖRÜLEN kadraj)
ile kıyasla. Üç sayı çıkar:

  argmax@0.40   : bugünkü davranış — en güvenli kutu hedefte mi
  argmax@düşük  : eşiği indirip TAKİPÇİSİZ koşsak ne olurdu (FP riski)
  herhangi@düşük: hedefte EN AZ BİR kutu var mı — takipçinin YAKALAYABİLECEĞİ
                  üst sınır. Bu üçüncü sayı TAKİPÇİNİN TAVANIDIR.

⚠ BU ÖLÇÜM KANIT DEĞİL, HİPOTEZDİR (CLAUDE.md §2): çevrimdışı replay yalnız
  hipotez üretir; kabul kararını taze uçuş + video verir. Amaç, uçuşa
  çıkmadan mekanizmanın çalışıp çalışmadığını görmek.

Kullanım:  python3 araclar/esik_tarama.py logs/BOSLUK/k02 [düşük_eşik]
================================================================================
"""
import csv
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gorus.dedektor import Dedektor          # noqa: E402


def _f(v, d=float("nan")):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def hedefte_mi(kutu, bx, by, bw):
    """tespit_olcu.py ile AYNI tanım (kıyas tutarlı olsun diye birebir):
    merkez tol içinde VE genişlik öngörülenin 0.5-2.0 katı."""
    tol = max(60.0, 1.5 * bw)
    return (float(np.hypot(kutu[0] - bx, kutu[1] - by)) <= tol
            and 0.5 <= kutu[2] / max(bw, 1.0) <= 2.0)


def main(kosu, dusuk=0.10):
    meta = list(csv.DictReader(open(os.path.join(kosu, "meta.csv"))))
    kare_d = os.path.join(kosu, "kareler")
    det = Dedektor()
    n = ok40 = okA = okH = fp40 = fpA = 0
    kutu_say = []
    for r in meta:
        bx, by, bw = _f(r.get("bek_cx")), _f(r.get("bek_cy")), _f(r.get("bek_w"))
        if not np.isfinite(bx) or not np.isfinite(bw) or bw <= 0:
            continue                              # öngörü yok (hedef kadraj dışı)
        yol = os.path.join(kare_d, "f%04d.jpg" % int(r["kare"]))
        if not os.path.exists(yol):
            continue
        img = cv2.cvtColor(cv2.imread(yol), cv2.COLOR_BGR2RGB)
        kutular = det.bul_hepsi(img, dusuk, merkez=None)   # TEK çıkarım, düşük eşik
        n += 1
        kutu_say.append(len(kutular))
        y40 = [k for k in kutular if k[4] >= 0.40]
        if y40:
            a = max(y40, key=lambda k: k[4])
            if hedefte_mi(a, bx, by, bw): ok40 += 1
            else: fp40 += 1
        if kutular:
            a = max(kutular, key=lambda k: k[4])
            if hedefte_mi(a, bx, by, bw): okA += 1
            else: fpA += 1
        if any(hedefte_mi(k, bx, by, bw) for k in kutular):
            okH += 1
    if not n:
        print("kullanılabilir kare yok"); return
    def p(x): return "%5.1f%%" % (100.0 * x / n)
    print("\n%s  —  n = %d kare  (düşük eşik = %.2f)" % (kosu, n, dusuk))
    print("  " + "-" * 64)
    print("  argmax @0.40   GERÇEK tespit: %s   yanlış-poz: %s  <- BUGÜNKÜ" % (p(ok40), p(fp40)))
    print("  argmax @%.2f   GERÇEK tespit: %s   yanlış-poz: %s  <- takipçisiz" % (dusuk, p(okA), p(fpA)))
    print("  herhangi@%.2f  hedefte kutu : %s                    <- TAKİPÇİ TAVANI" % (dusuk, p(okH)))
    print("  " + "-" * 64)
    print("  kutu/kare: medyan %.0f  maks %d" % (np.median(kutu_say), max(kutu_say)))
    print("  KAZANÇ TAVANI (tavan - bugünkü): %+.1f puan" % (100.0 * (okH - ok40) / n))
    print("  ⚠ HİPOTEZ — kabul kararı taze uçuşla verilir (§2).\n")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.10)
