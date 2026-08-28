# -*- coding: utf-8 -*-
"""ADIM 3 — TEK KOMUTLA HEPSI. Alti kosuyu donusumlu olarak kendisi yapar.

Kullanim:   python3 araclar/olcum/06_hepsini_kos.py <cihaz>
Ornek   :   python3 araclar/olcum/06_hepsini_kos.py /dev/video2
            python3 araclar/olcum/06_hepsini_kos.py 1            (Windows)

NE YAPAR:
  A1 -> B1 -> C1 -> A2 -> B2 -> C2  sirasiyla kosar.
  Her kosu ~10 saniye, aralarda 3 saniye bekler.
  Toplam ~2 dakika.

⛔ DONUSUMLU sira SART: A,A,B,B,C,C degil, A,B,C,A,B,C.
   Sinyal kalitesi ya da bilgisayar yuku zamanla degisirse
   uc kolu da esit etkilesin diye.

⚠ BASLAMADAN ONCE:
   1. 02_saat.py AYRI TERMINALDE acik ve TAM EKRAN olmali
   2. Kamera o ekrana bakmali, rakamlar net gorunmeli
   3. Kosular boyunca drone'u ve ekrani OYNATMA

Bitince:  python3 araclar/olcum/05_kare_oku.py      (argumansiz = hepsi)
"""
import os
import subprocess
import sys
import time

PLAN = [("A", "A1"), ("B", "B1"), ("C", "C1"),
        ("A", "A2"), ("B", "B2"), ("C", "C2")]

BEKLE = 3.0          # kosular arasi saniye

BURASI = os.path.dirname(os.path.abspath(__file__))
OLC = os.path.join(BURASI, "03_gecikme_olc.py")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cihaz = sys.argv[1]

    if not os.path.exists(OLC):
        print("HATA: bulunamadi -> %s" % OLC)
        sys.exit(1)

    print("=" * 60)
    print("ALTI KOSU — DONUSUMLU")
    print("=" * 60)
    print("cihaz : %s" % cihaz)
    print("plan  : %s" % " -> ".join(e for _, e in PLAN))
    print("sure  : ~2 dakika")
    print()
    print("KONTROL ET:")
    print("  [ ] 02_saat.py ayri terminalde ACIK ve TAM EKRAN")
    print("  [ ] kamera o ekrana bakiyor, rakamlar NET")
    print("  [ ] drone ve ekran sabit, kosular boyunca oynatilmayacak")
    print()
    try:
        input("Hazirsan ENTER'a bas (vazgecmek icin Ctrl+C) > ")
    except (EOFError, KeyboardInterrupt):
        print("\niptal edildi.")
        sys.exit(0)

    basarili, basarisiz = [], []
    t_bas = time.time()

    for i, (kol, etiket) in enumerate(PLAN, 1):
        print("\n" + "-" * 60)
        print("[%d/%d]  KOL %s  ->  %s" % (i, len(PLAN), kol, etiket))
        print("-" * 60, flush=True)

        r = subprocess.run([sys.executable, OLC, cihaz, kol, etiket])
        if r.returncode == 0:
            basarili.append(etiket)
        else:
            basarisiz.append(etiket)
            print("⚠ KOSU BASARISIZ: %s (cikis kodu %d)" % (etiket, r.returncode))

        if i < len(PLAN):
            print("\n... %.0f saniye bekleniyor ..." % BEKLE, flush=True)
            time.sleep(BEKLE)

    print("\n" + "=" * 60)
    print("HEPSI BITTI  (%.0f saniye)" % (time.time() - t_bas))
    print("=" * 60)
    print("basarili : %s" % (", ".join(basarili) or "-"))
    if basarisiz:
        print("BASARISIZ: %s" % ", ".join(basarisiz))
    print()
    print("SIRADAKI ADIM — karelerdeki sayilari gir:")
    print("   python3 araclar/olcum/05_kare_oku.py")
    print()
    print("Sonra sonucu al:")
    print("   python3 araclar/olcum/04_gecikme_oku.py")


if __name__ == "__main__":
    main()
