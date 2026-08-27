# -*- coding: utf-8 -*-
"""
================================================================================
MENZİL KALİBRASYONU — kutu boyutu gerçek menzille tutarlı mı?
================================================================================
Güdüm menzili kutu boyutundan çıkarıyor (benzer üçgenler):

        p = C / R        ->        R = C / p

  p = kutunun piksel boyutu, güdümde `max(w, h)` (ibvs.py satır 406)
  R = hedefe menzil (m)
  C = MENZIL_C = 997 px·m   (kamera odak uzaklığı × hedefin fiziksel boyu)

Yani C SABİT olmalı: her karede `max(w,h) × gerçek_menzil` çarpımı aynı sayıyı
vermeli. Vermiyorsa güdümün gördüğü menzil sistematik olarak yanlıştır.

⛔⛔ BU ÖLÇÜM İKİ KEZ YAPILAMADI — SEBEBİ KAYIT EKSİĞİYDİ:
   `cikarim.csv`'de `vis_h` YOKTU, yalnız `vis_w` vardı. `max(w,h)` yerine
   genişliğe bakınca hedef YATIKKEN sahte bir sapma çıkıyordu. 2026-08-26'da
   bundan "görsel menzil 2 kat sapıyor" diye bir iddia yazıldı ve GERİ ALINDI;
   2026-08-27'de aynı tuzağa ikinci kez girildi ve hüküm kurulmadı.
   `vis_h` 2026-08-27'de eklendi — bu araç ancak ondan SONRAKİ koşularda
   anlamlıdır. Eski koşularda `vis_h` sütunu yoksa araç bunu SÖYLER ve
   o koşuyu ATLAR (sessizce genişliğe düşmez — §5.2).

⚠ GEÇERLİLİK: yalnız GÖRSEL fazdaki, TAZE (kutu yaşı küçük) ve gerçek menzili
   bilinen kareler alınır. Bayat kutu, hedefin ESKİ menzilini anlatır ve
   çarpımı sahte şekilde kaydırır.

ÇIKTI: C'nin dağılımı ve C'nin hedef ASPEKTİNE göre nasıl kaydığı. Aspekt
   (hedefi hangi açıdan görüyoruz) siluetin genişliğini değiştirir; C oradan
   kayıyorsa bu bir MODEL sorunu değil GEOMETRİdir ve tek bir sabitle
   düzeltilemez.

Kullanım:
    python3 araclar/menzil_kalibre.py logs/HZ2
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MENZIL_C_KOD = 997.0          # dow/gudum/ibvs.py'nin kullandığı değer
YAS_ESIK_S = 0.30             # bundan yaşlı kutu ALINMAZ


def _f(r, k):
    try:
        v = r.get(k)
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin", nargs="?", default="logs/HZ2")
    ap.add_argument("--yas", type=float, default=YAS_ESIK_S)
    a = ap.parse_args()

    C, C_aspekt, atlanan, kullanilan = [], [], [], 0
    for yol in sorted(glob.glob(os.path.join(KOK, a.dizin, "*", "k*", "cikarim.csv"))):
        rows = list(csv.DictReader(open(yol)))
        if not rows:
            continue
        if "vis_h" not in rows[0]:
            atlanan.append(os.path.relpath(os.path.dirname(yol), KOK))
            continue
        for r in rows:
            if r.get("basarili") != "1" or r.get("durum") != "GORSEL":
                continue
            w, h = _f(r, "vis_w"), _f(r, "vis_h")
            R = _f(r, "menzil3_m")
            yas = _f(r, "iz_yas")
            if not w or not h or not R or R <= 0:
                continue
            if yas is not None and yas >= 0 and yas > a.yas:
                continue
            p = max(w, h)
            c = p * R
            if not (50 < c < 20000):        # bariz saçmalar (yeniden doğuş vb.)
                continue
            C.append(c)
            kullanilan += 1
            asp = _f(r, "aspekt_deg")
            if asp is not None:
                C_aspekt.append((abs(asp), c, w, h))

    print("=" * 74)
    print("  MENZİL KALİBRASYONU — %s" % a.dizin)
    print("  C = max(w,h) × gerçek_menzil   ·   kodun kullandığı değer: %.0f" % MENZIL_C_KOD)
    print("=" * 74)

    if atlanan:
        print()
        print("  ⚠ vis_h SÜTUNU OLMAYAN %d koşu ATLANDI (sessizce genişliğe" % len(atlanan))
        print("    düşülmedi — o hata iki kez yapıldı):")
        for x in atlanan[:6]:
            print("      %s" % x)
        if len(atlanan) > 6:
            print("      ... +%d tane daha" % (len(atlanan) - 6))

    if len(C) < 30:
        print("\n  ⛔ ÖLÇÜLEMEDİ: yalnız %d geçerli kare var (en az 30 gerek)." % len(C))
        return

    C.sort()
    med = st.median(C)
    print()
    print("  kare sayısı        : %d  (GÖRSEL faz, taze kutu, kutu yaşı ≤ %.2f s)"
          % (kullanilan, a.yas))
    print("  C medyan           : %7.0f px·m" % med)
    print("  C p10 / p90        : %7.0f  /  %.0f" % (C[len(C) // 10], C[len(C) * 9 // 10]))
    print("  yayılım (p90/p10)  : %7.2f kat" % (C[len(C) * 9 // 10] / max(1e-9, C[len(C) // 10])))
    print()
    sapma = 100.0 * (med - MENZIL_C_KOD) / MENZIL_C_KOD
    print("  KODA GÖRE SAPMA    : %+.1f%%" % sapma)
    if abs(sapma) < 8:
        print("    -> sabit YERİNDE; kutu tabanlı menzil sistematik kaymıyor.")
    else:
        yon = "UZAK" if sapma < 0 else "YAKIN"
        print("    -> güdüm hedefi sistematik olarak %s görüyor." % yon)
        print("       R_gercek = R_gudum × %.3f" % (med / MENZIL_C_KOD))

    if C_aspekt:
        print()
        print("  ASPEKTE GÖRE (hedefi hangi açıdan görüyoruz):")
        print("  %-14s %6s %9s %9s %8s" % ("aspekt bandı", "n", "C medyan", "h/w med", "sapma%"))
        bantlar = [(0, 15), (15, 30), (30, 45), (45, 90), (90, 180)]
        for lo, hi in bantlar:
            g = [(c, w, h) for (asp, c, w, h) in C_aspekt if lo <= asp < hi]
            if len(g) < 10:
                continue
            cm = st.median([x[0] for x in g])
            hw = st.median([x[2] / max(1e-9, x[1]) for x in g])
            print("  %3d-%3d°       %6d %9.0f %9.2f %+7.1f"
                  % (lo, hi, len(g), cm, hw, 100.0 * (cm - MENZIL_C_KOD) / MENZIL_C_KOD))
        print()
        print("  ⚠ C aspekte göre BELİRGİN kayıyorsa tek bir sabitle düzeltilemez:")
        print("    hedefin silueti açıya göre daralıyor demektir (geometri, model değil).")

    print()
    print("=" * 74)


if __name__ == "__main__":
    main()
