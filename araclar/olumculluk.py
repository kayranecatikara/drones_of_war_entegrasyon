# -*- coding: utf-8 -*-
"""
================================================================================
ÖLÜMCÜLLÜK — geçiş başına vuruş olasılığı ve Rmin dağılımı
================================================================================
ÖLÇÜLDÜ (182 geçiş, 58 koşu, yedi kampanya havuzu, 2026-08-27):

    Rmin bandı    geçiş  vuruş   oran
    0.5-1.0 m        13      6    %46
    1.0-1.5 m        63     32    %51
    1.5-2.0 m        19     11    %58
    2.0-3.0 m        10      0     %0
    3.0+ m           76      0     %0

İKİ SONUÇ:
  1. ÖLÜMCÜL YARIÇAP 2.0 m ve KESKİN — üstünde 86 geçişte SIFIR vuruş.
  2. İÇERİDE vuruş oranı ~%50 ve YAKINLIKLA ARTMIYOR.

⭐ (2)'nin anlamı: 2 m'nin içine girmek GEREKLİ ama YETERLİ değil. 2 m
   içindeki geçişlerde vuranı ıskalayandan ayıran ölçebildiğim hiçbir
   büyüklük yok (Rmin 1.30 vs 1.20 — ıskalar daha YAKIN; aspekt 25.5 vs
   28.8; kapanma 4.45 vs 4.19; hedef yatışı 26.0 vs 31.5). Tek fark son
   0.7 s tespit %80 vs %67. Yani içerideki yazı-tura simülatörün gövde
   çarpışma geometrisinde. Kesin vuruş için gövdenin İÇİNE (~0.5 m altı)
   girmek gerekir.

HASSASİYET TABANI (58 koşu): en yakın menzil p25 1.00 · p50 1.10 ·
p75 1.30 m. Yalnız 1 koşu 0.8 m altına inebilmiş.

TABANIN KAYNAĞI (hesaplandı, ölçümle tuttu):
    τ = 1/CevCfg.K_V = 0.67 s ; kapanma ~4 m/s
    -> son etkili düzeltme 0.67×4 ≈ 2.7 m menzilde DONAR
    -> o menzildeki yanal hata ≈ 3 × 150/540 ≈ 0.83 m

Bu araç bir kampanyada bu tabloyu kol kol üretir. Bir özelliğin
TERMİNAL HASSASİYETİ iyileştirip iyileştirmediği burada görünür;
KARARI yine `araclar/kacirma.py` (birincil ölçüt) verir.

Kullanım: python3 araclar/olumculluk.py logs/KL1
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def gecisler(d, sicrama=10.0, acilma=6.0, esik=8.0):
    """(Rmin, vuruş mu, fren_aktif) listesi. Vuruş = menzil SIÇRAMASI."""
    y = os.path.join(d, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return []
    R = []
    for r in csv.DictReader(open(y)):
        t, m = _f(r, "t"), _f(r, "menzil3_m") or _f(r, "menzil_m")
        if None in (t, m):
            continue
        R.append((t, m, _f(r, "fren")))
    if len(R) < 20:
        return []
    vur_i = None
    for i in range(len(R) - 1):
        if R[i + 1][1] - R[i][1] >= sicrama:
            vur_i = i
            break
    dip, gec = None, []
    for i, x in enumerate(R):
        if dip is None or x[1] < R[dip][1]:
            dip = i
        if R[dip][1] < esik and x[1] - R[dip][1] >= acilma:
            gec.append(dip)
            dip = None
    if dip is not None and R[dip][1] < esik:
        gec.append(dip)
    out = []
    for i in gec:
        pen = R[max(0, i - 14):i + 1]
        fr = max((x[2] or 0) for x in pen)
        out.append((R[i][1], vur_i is not None and abs(i - vur_i) <= 10, fr))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KL1")
    a = ap.parse_args()
    kollar = {}
    for d in sorted(glob.glob(os.path.join(KOK, a.kok, "*__t*"))):
        kollar.setdefault(os.path.basename(d).split("__")[0], []).append(d)
    if not kollar:
        print("⛔ koşu yok: %s" % a.kok)
        return

    print("\n" + "=" * 70)
    print("  ÖLÜMCÜLLÜK — %s   (ölçülen ölümcül yarıçap: 2.0 m)" % a.kok)
    print("=" * 70)
    print("\n  %-12s %8s %9s %10s %11s %10s"
          % ("kol", "geçiş", "<2 m", "<2m payı", "vuruş", "Rmin p50"))
    print("  " + "-" * 62)
    OZ = {}
    for kol in sorted(kollar):
        G = [g for d in kollar[kol] for g in gecisler(d)]
        if not G:
            continue
        ic = [g for g in G if g[0] < 2.0]
        vur = [g for g in G if g[1]]
        OZ[kol] = G
        print("  %-12s %8d %9d %9.0f%% %10d %9.2f m"
              % (kol, len(G), len(ic), 100.0 * len(ic) / len(G), len(vur),
                 st.median([g[0] for g in G])))
    print("\n  Rmin BANDINA GÖRE (kol kol)")
    print("  %-12s %10s %10s %10s %10s"
          % ("kol", "<1.0 m", "1.0-2.0", "2.0-3.0", "3.0+"))
    print("  " + "-" * 56)
    for kol in sorted(OZ):
        G = OZ[kol]
        b = [sum(1 for g in G if g[0] < 1.0),
             sum(1 for g in G if 1.0 <= g[0] < 2.0),
             sum(1 for g in G if 2.0 <= g[0] < 3.0),
             sum(1 for g in G if g[0] >= 3.0)]
        print("  %-12s %10d %10d %10d %10d" % (kol, *b))
    # §5.1 mekanizma
    for kol in sorted(OZ):
        if kol != "acik":
            continue
        fr = sum(1 for g in OZ[kol] if g[2])
        print("\n  §5.1 MEKANİZMA: fren, %d/%d geçişte aktifti  ->  %s"
              % (fr, len(OZ[kol]),
                 "GEÇTİ" if fr > 0 else "⛔ HİÇ ATEŞLEMEDİ, koşular GEÇERSİZ"))
    print("""
  ⛔ Bu tablo KARAR VERDİRMEZ (§5.2): 2 m'ye girmek gerekli ama yeterli
     değil; içeride vuruş oranı ~%50 ve yakınlıkla artmıyor.
     Kararı `araclar/kacirma.py` (birincil ölçüt) verir.
""")


if __name__ == "__main__":
    main()
