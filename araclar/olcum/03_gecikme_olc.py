# -*- coding: utf-8 -*-
"""ADIM 3 — GECIKME OLCUMU (uc kol).

Kullanim:
    python3 03_gecikme_olc.py <cihaz> <kol> <etiket>

    <cihaz>  : /dev/video2   ya da   1
    <kol>    : A | B | C
    <etiket> : A1, B1, A2, B2 ... (ayni kolun kacinci kosusu)

Ornek:
    python3 03_gecikme_olc.py /dev/video2 A A1

KOLLAR:
  A = TABAN. Duz cv2 read(). Hicbir sey degistirilmez.
  B = CAP_PROP_BUFFERSIZE = 1. ⚠ Yalniz Linux/V4L2'de calisir; Windows
      DirectShow'da sessizce yok sayilir (betik bunu SOYLER).
  C = BOSALTMA (drain). Her olcumden once kuyruktaki bayat kareler
      atilir, yalniz CANLI kenardaki kare alinir. HER PLATFORMDA calisir.
      ⭐ Sistemde kalici cozum buyuk ihtimalle bu olacak.

CIKTI: logs/gecikme/<etiket>/  icine 15 PNG + olcum.csv
       PNG'nin ADINDA karenin VARIS zamani yazili.
       PNG'nin ICINDE o an ekranda yazan saat gorunur.
       gecikme = (addaki varis) - (karede yazan)

⚠ ONCE 02_saat.py'yi AYRI TERMINALDE calistirin ve kamerayi ekrana dogrultun.
"""
import csv
import os
import sys
import time

import cv2

N_KARE = 15
ISINMA = 60


def taze_kare(cap, en_fazla=12):
    """Kuyruktaki BAYAT kareleri at, CANLI kenardaki kareyi dondur.

    NASIL CALISIR: grab() kuyrukta kare varken ANINDA doner (<5 ms).
    Kuyruk bosaldiginda bir sonraki kareyi BEKLER (~33 ms). O bekleme
    gorulunce canli kenardayiz demektir; retrieve() ile o kareyi aliriz.
    """
    atilan = 0
    for _ in range(en_fazla):
        t0 = time.perf_counter()
        cap.grab()
        dt = time.perf_counter() - t0
        if dt > 0.010:               # bu grab BEKLEDI -> canli kenar
            break
        atilan += 1
    ok, kare = cap.retrieve()
    return ok, kare, atilan


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    ham, kol, etiket = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    if kol not in ("A", "B", "C"):
        print("HATA: kol A, B ya da C olmali.")
        sys.exit(1)

    cihaz = int(ham) if ham.isdigit() else ham
    cikti = os.path.join("logs", "gecikme", etiket)
    os.makedirs(cikti, exist_ok=True)

    cap = cv2.VideoCapture(cihaz)
    if not cap.isOpened():
        print("HATA: cihaz acilamadi: %s" % ham)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    notlar = []
    if kol == "B":
        kabul = cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        okunan = cap.get(cv2.CAP_PROP_BUFFERSIZE)
        notlar.append("BUFFERSIZE=1 kabul edildi mi: %s | geri okunan: %s"
                      % (kabul, okunan))
        print(notlar[-1])
        if not kabul:
            print("⚠ SURUCU BUFFERSIZE'I DESTEKLEMIYOR. Kol B bu makinede")
            print("  KOL A ile AYNI seydir. Kol C'yi kullanin.")
            notlar.append("UYARI: Kol B gecersiz - surucu desteklemiyor.")

    print("isiniyor...", flush=True)
    for _ in range(ISINMA):
        cap.read()

    print("olculuyor: kol %s, %d kare..." % (kol, N_KARE), flush=True)
    kayit = []
    for i in range(N_KARE):
        if kol == "C":
            ok, kare, atilan = taze_kare(cap)
        else:
            ok, kare = cap.read()
            atilan = 0
        t = time.time()
        if not ok or kare is None:
            continue
        varis = t % 1000.0
        ad = "k%02d_varis_%.3f.png" % (i, varis)
        cv2.imwrite(os.path.join(cikti, ad), kare)
        kayit.append((ad, "%.3f" % varis, str(atilan), ""))
        print("  %s   (atilan bayat kare: %d)" % (ad, atilan), flush=True)

    cap.release()

    yol_csv = os.path.join(cikti, "olcum.csv")
    with open(yol_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dosya", "varis", "atilan", "karede_yazan"])
        for r in kayit:
            w.writerow(r)

    with open(os.path.join(cikti, "not.txt"), "w", encoding="utf-8") as f:
        f.write("kol: %s\ncihaz: %s\n" % (kol, ham))
        f.write("\n".join(notlar) + "\n")

    print("\n" + "=" * 62)
    print("KAYIT TAMAM -> %s" % cikti)
    print("=" * 62)
    print("SIRADAKI IS (ELLE):")
    print("  1. Su dosyayi bir tablo programinda ya da metin")
    print("     duzenleyicide acin: %s" % yol_csv)
    print("  2. Her PNG'yi acin, ICINDE yazan saat sayisini okuyun")
    print("     (ornek: 742.318).")
    print("  3. O sayiyi CSV'nin 'karede_yazan' sutununa yazin.")
    print("  4. Hepsi doldurulunca:  python3 04_gecikme_oku.py")


if __name__ == "__main__":
    main()
