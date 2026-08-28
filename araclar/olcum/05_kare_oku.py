# -*- coding: utf-8 -*-
"""ADIM 4 — kareleri tek tek gosterir, sayiyi sen yazarsin.

Kullanim:
    python3 araclar/olcum/05_kare_oku.py            <- HEPSINI sirayla
    python3 araclar/olcum/05_kare_oku.py A1         <- yalniz A1

NE YAPAR:
  logs/gecikme/<etiket>/ icindeki her PNG'yi bir pencerede acar.
  Sen terminalden karede YAZAN sayiyi girersin (ornek: 742.318).
  Betik gecikmeyi ANINDA hesaplar ve makul degilse UYARIR.
  olcum.csv her girdiden sonra kendiliginden kaydedilir.

TUSLAR (terminalde):
  sayi + Enter -> kaydet, sonrakine gec
  bos + Enter  -> bu kareyi ATLA (rakam okunmuyorsa)
  a + Enter    -> bu ETIKETI birak, sonraki etikete gec
  q + Enter    -> tamamen cik (girdiler kayitli kalir)

💡 Kosu basina 8 kare YETERLI. Hepsini okumak zorunda degilsin.

⚠ Pencere donmus gorunuyorsa sorun degil - goruntu cizilmistir.
"""
import csv
import os
import sys

import cv2

KOK = os.path.join("logs", "gecikme")
SIRA = ["A1", "B1", "C1", "A2", "B2", "C2"]
YETER = 8


def gecikme_ms(varis, karede):
    g = (varis - karede) * 1000.0
    if g < -500000.0:            # sss.mmm bicimi 1000 s'de bir basa sarar
        g += 1000000.0
    return g


def bir_etiket(etiket):
    """Bir kosu dizinini isle. Donus: 'bitti' | 'atla' | 'cik'."""
    dizin = os.path.join(KOK, etiket)
    yol_csv = os.path.join(dizin, "olcum.csv")
    if not os.path.exists(yol_csv):
        print("\n[%s] olcum.csv yok - atlandi." % etiket)
        return "atla"

    with open(yol_csv, encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))
    alanlar = ["dosya", "varis", "atilan", "karede_yazan"]

    def kaydet():
        with open(yol_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=alanlar)
            w.writeheader()
            for r in satirlar:
                w.writerow({k: r.get(k, "") for k in alanlar})

    def dolu_say():
        return sum(1 for r in satirlar
                   if (r.get("karede_yazan") or "").strip())

    print("\n" + "=" * 58)
    print("ETIKET: %s   |   %d kare, %d tanesi zaten dolu"
          % (etiket, len(satirlar), dolu_say()))
    print("=" * 58)

    for i, r in enumerate(satirlar):
        if (r.get("karede_yazan") or "").strip():
            continue
        if dolu_say() >= YETER:
            print("\n%d kare doldu - bu kosu icin YETERLI." % YETER)
            break

        img = cv2.imread(os.path.join(dizin, r["dosya"]))
        if img is None:
            print("[%d/%d] okunamadi: %s" % (i + 1, len(satirlar), r["dosya"]))
            continue

        cv2.imshow("kare", cv2.resize(img, None, fx=2.0, fy=2.0,
                                      interpolation=cv2.INTER_NEAREST))
        cv2.waitKey(300)                      # pencerenin cizilmesi icin

        varis = float(r["varis"])
        print("\n[%s %d/%d] %s   (varis: %.3f)"
              % (etiket, i + 1, len(satirlar), r["dosya"], varis))

        while True:
            try:
                ham = input("  karede yazan sayi > ").strip().replace(",", ".")
            except EOFError:
                ham = "q"
            d = ham.lower()
            if d == "q":
                kaydet()
                return "cik"
            if d == "a":
                kaydet()
                print("  -> bu etiket birakildi")
                return "atla"
            if ham == "":
                print("  -> atlandi")
                break

            zorla = ham.startswith("!")
            try:
                karede = float(ham[1:] if zorla else ham)
            except ValueError:
                print("  ⚠ sayi degil, tekrar dene (ornek: 742.318)")
                continue

            g = gecikme_ms(varis, karede)
            if not zorla and not (0.0 < g < 2000.0):
                print("  ⚠ hesaplanan gecikme %.0f ms - MAKUL DEGIL." % g)
                print("    Yanlis okumus olabilirsin, tekrar bak.")
                print("    Yine de kaydetmek icin basina ! koy (!%s)" % ham)
                continue

            r["karede_yazan"] = "%.3f" % karede
            kaydet()
            print("  ✓ gecikme = %.0f ms%s" % (g, "  (ZORLANDI)" if zorla else ""))
            break

    kaydet()
    n = dolu_say()
    print("\n[%s] %d / %d kare dolduruldu." % (etiket, n, len(satirlar)))
    if n < YETER:
        print("⚠ %d'den az doldu - sonuc zayif olabilir." % YETER)
    return "bitti"


def main():
    if len(sys.argv) > 1:
        etiketler = sys.argv[1:]
    else:
        etiketler = [e for e in SIRA
                     if os.path.exists(os.path.join(KOK, e, "olcum.csv"))]
        if not etiketler:
            print("HATA: logs/gecikme/ altinda hic kosu bulunamadi.")
            print("Once ADIM 3'u kosun:")
            print("   python3 araclar/olcum/06_hepsini_kos.py <cihaz>")
            sys.exit(1)
        print("Bulunan kosular: %s" % ", ".join(etiketler))

    cv2.namedWindow("kare", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("kare", 1280, 960)

    for e in etiketler:
        if bir_etiket(e) == "cik":
            print("\ncikildi. girdiler kaydedildi.")
            break

    cv2.destroyAllWindows()
    print("\n" + "=" * 58)
    print("SIRADAKI ADIM — sonucu al:")
    print("   python3 araclar/olcum/04_gecikme_oku.py")
    print("=" * 58)


if __name__ == "__main__":
    main()
