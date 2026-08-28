# -*- coding: utf-8 -*-
"""
================================================================================
ZOR ÖRNEK DOĞRULAMA — etiketi GÖZLE sınamadan tek kare eğitime gitmez
================================================================================
⛔ NEDEN ZORUNLU: yanlış etikete eğitmek modeli İYİLEŞTİRMEZ, BOZAR. Bu
   proje bunu bir kez yaşadı: kaydedilmiş kareleri sonradan telemetriyle
   eşleştiren ilk sürümde "7 m" yazan kutu BOMBOŞ göğe düşüyordu ve tablo
   "120 aday kare bulundu" diyordu. Sayı doğruydu, ETİKETLER ÇÖPTÜ.

Bu araç iki şey yapar:
  1. KONTAK SAYFASI — kutuyu kareye çizer; insan bakar ve karar verir.
  2. OTOMATİK AKIL SAĞLIĞI — kutunun içindeki piksellerle dışarısını
     kıyaslar. Talon gökyüzüne karşı KOYU bir siluet; kutu içi ile
     çevresi arasında hiç fark yoksa o kutu muhtemelen BOŞTUR.
     Bu bir kanıt değil, ELEME aracıdır — insan bakışının yerine geçmez.

Kullanım:
    python3 araclar/zor_dogrula.py veri/zor
    python3 araclar/zor_dogrula.py veri/zor --n 24
================================================================================
"""
import argparse
import csv
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--temizle", type=float, default=None,
                    help="bu kontrastın altındaki kareleri ELE (öneri: 25)")
    a = ap.parse_args()
    import cv2
    import numpy as np

    kd = os.path.join(KOK, a.dizin)
    imd, lbd = os.path.join(kd, "images"), os.path.join(kd, "labels")
    if not os.path.isdir(imd):
        print("⛔ dizin yok: %s" % a.dizin); return
    adlar = sorted(x[:-4] for x in os.listdir(imd) if x.endswith(".jpg"))
    if not adlar:
        print("⛔ kare yok."); return

    man = {}
    mp = os.path.join(kd, "manifest.csv")
    if os.path.exists(mp):
        for r in csv.DictReader(open(mp)):
            man[r["ad"]] = r

    print("\n" + "=" * 68)
    print("  ZOR ÖRNEK DOĞRULAMA — %s" % a.dizin)
    print("=" * 68)
    print("  kare: %d" % len(adlar))

    # --- otomatik akıl sağlığı: kutu içi ile çevresi farklı mı ---
    skor = []
    for ad in adlar:
        im = cv2.imread(os.path.join(imd, ad + ".jpg"))
        lp = os.path.join(lbd, ad + ".txt")
        if im is None or not os.path.exists(lp):
            continue
        H, W = im.shape[:2]
        p = open(lp).read().split()
        if len(p) < 5:
            continue
        cx, cy, w, h = (float(p[1]) * W, float(p[2]) * H,
                        float(p[3]) * W, float(p[4]) * H)
        x1, y1 = max(0, int(cx - w / 2)), max(0, int(cy - h / 2))
        x2, y2 = min(W, int(cx + w / 2)), min(H, int(cy + h / 2))
        if x2 - x1 < 4 or y2 - y1 < 4:
            continue
        ic = im[y1:y2, x1:x2].astype(float)
        m = 2
        X1, Y1 = max(0, int(cx - m * w / 2)), max(0, int(cy - m * h / 2))
        X2, Y2 = min(W, int(cx + m * w / 2)), min(H, int(cy + m * h / 2))
        dis = im[Y1:Y2, X1:X2].astype(float)
        # kutu içi en KOYU piksel, çevrenin ortalamasından ne kadar koyu
        kontrast = float(dis.mean() - ic.min())
        skor.append((kontrast, ad, man.get(ad, {})))

    if skor:
        import statistics as st
        v = sorted(x[0] for x in skor)
        zayif = [x for x in skor if x[0] < 30.0]
        print("\n  OTOMATİK AKIL SAĞLIĞI (kutu içi koyuluk farkı)")
        print("     medyan %.0f | p10 %.0f | p90 %.0f"
              % (st.median(v), v[int(.1 * (len(v) - 1))], v[int(.9 * (len(v) - 1))]))
        print("     ⚠ kontrast < 30 olan (kutu BOŞ olabilir): %d/%d  (%%%.0f)"
              % (len(zayif), len(skor), 100.0 * len(zayif) / len(skor)))
        print("     ⚠ Bu ELEME aracıdır, kanıt değil. Karar kontak sayfasına bakılarak verilir.")
        if zayif:
            print("     en şüpheli 5:")
            for k, ad, mm in sorted(zayif)[:5]:
                print("        %-22s kontrast %5.0f  menzil %s m  kutu %s px"
                      % (ad, k, mm.get("menzil_m", "?"), mm.get("kutu_px", "?")))

    # --- ELEME (--temizle) ---
    #   ⚠ ÖDÜNLEŞİM: zor örnek madenciliği ZOR olanı ister; kontrast
    #     süzgeci en zoru da eler. Ama DOĞRULANAMAYAN bir etiket, eksik
    #     örnekten daha kötüdür — modele "şu boş gökyüzü Talon'dur" diye
    #     öğretir. Eşik bu yüzden GEVŞEK tutulur (gürültü tabanını keser),
    #     ve elenen kareler SİLİNMEZ, `elenen/` altına taşınır ki karar
    #     geri alınabilsin ve sayı raporlanabilsin.
    if a.temizle is not None and skor:
        import shutil
        ed = os.path.join(kd, "elenen")
        os.makedirs(os.path.join(ed, "images"), exist_ok=True)
        os.makedirs(os.path.join(ed, "labels"), exist_ok=True)
        tasindi = 0
        for k, ad, mm in skor:
            if k >= a.temizle:
                continue
            for alt, uz in (("images", ".jpg"), ("labels", ".txt")):
                src = os.path.join(kd, alt, ad + uz)
                if os.path.exists(src):
                    shutil.move(src, os.path.join(ed, alt, ad + uz))
            tasindi += 1
        print("\n  🧹 ELEME (kontrast < %.0f): %d kare -> %s/elenen/"
              % (a.temizle, tasindi, a.dizin))
        print("     kalan: %d kare" % (len(skor) - tasindi))
        print("     ⚠ silinmedi, taşındı — karar geri alınabilir.")

    # --- kontak sayfası ---
    n = min(a.n, len(adlar))
    sec = adlar[:: max(1, len(adlar) // n)][:n]
    kucuk = []
    for ad in sec:
        im = cv2.imread(os.path.join(imd, ad + ".jpg"))
        lp = os.path.join(lbd, ad + ".txt")
        if im is None or not os.path.exists(lp):
            continue
        H, W = im.shape[:2]
        p = open(lp).read().split()
        cx, cy, w, h = (float(p[1]) * W, float(p[2]) * H,
                        float(p[3]) * W, float(p[4]) * H)
        x1, y1 = int(cx - w / 2), int(cy - h / 2)
        x2, y2 = int(cx + w / 2), int(cy + h / 2)
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 3)
        mm = man.get(ad, {})
        cv2.putText(im, "%sm" % (mm.get("menzil_m", "?")),
                    (x1, max(24, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX,
                    1.1, (0, 0, 255), 3)
        kucuk.append(cv2.resize(im, (640, 360)))
    if kucuk:
        while len(kucuk) % 3:
            kucuk.append(np.zeros_like(kucuk[0]))
        sat = [np.hstack(kucuk[i:i + 3]) for i in range(0, len(kucuk), 3)]
        yol = os.path.join(KOK, "logs", "zor_dogrula.jpg")
        cv2.imwrite(yol, np.vstack(sat))
        print("\n  ✔ kontak sayfası: logs/zor_dogrula.jpg (%d kare)" % len(kucuk))
        print("    KIRMIZI kutu hedefin ÜSTÜNDE mi? Değilse veri seti ÇÖPTÜR.\n")


if __name__ == "__main__":
    main()
