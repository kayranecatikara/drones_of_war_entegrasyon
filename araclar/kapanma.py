# -*- coding: utf-8 -*-
"""
================================================================================
KAPANMA HIZI — Ö-K'nın mekanizma kapısı ve doğrudan çıktısı
================================================================================
NEDEN BU ÖLÇÜT: 40 koşuluk havuzda, iyi ve kötü koşuyu ayıran EN GÜÇLÜ
değişken kapanma hızıydı:

    ölçüt (menzil 5-20 m)      az kaçırma    çok kaçırma
    kapanma hızı                  2.1 m/s        0.5 m/s
    en uzun körlük (ıska sonrası) 0.2 s          4.9 s
    LOS dönüş hızı                6.2 °/s        5.2 °/s   <- FARK YOK

Son satır önemli: hedefin ne kadar manevra yaptığı ıskayı AYIRMIYOR.

KAPANMANIN BÜTÇESİ ÇOK DAR:
    araç GÖRSEL fazda 22.1 m/s  ·  hedef ~18 m/s  ->  tavan ~4 m/s
Bu yüzden komut ile gerçekleşen arasındaki 5.9 m/s'lik açık kritik.

§5.1 MEKANİZMA KAPISI (Ö-K): deney kolunda `olcum_hiz` medyanı GORSEL
fazda YÜKSELMELİDİR. Yükselmiyorsa özellik devreye girmemiş demektir ve
o koşu veri noktası değildir — kollar kıyaslanmadan ÖNCE bakılır.

⛔ GEÇERLİLİK EŞİ (§5.2): "kapanma hızı" tek başına hüküm kurdurmaz.
   Hızlı kapanmak, düzeltmeye daha AZ süre bırakır; araç hedefin
   üstünden daha hızlı da geçebilir. Kararı `araclar/kacirma.py` verir.

⚠ Arka kareler (hedefin üstünden geçtikten sonrası) payda dışıdır
   (bkz. araclar/arka.py) — yoksa "kapanma" işaret değiştirip ölçümü bozar.

Kullanım: python3 araclar/kapanma.py logs/KK1
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
from araclar.arka import ArkaBekci


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def kosu_olc(d, lo, hi):
    y = os.path.join(d, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return None
    ab = ArkaBekci(d)
    S, KOM, GER = [], [], []
    for r in csv.DictReader(open(y)):
        t = _f(r, "t")
        m = _f(r, "menzil3_m") or _f(r, "menzil_m")
        if None in (t, m):
            continue
        if ab.var and ab.arkada(t):
            continue
        gorsel = str(r.get("durum") or "").startswith("GORSEL")
        if gorsel:
            k, g = _f(r, "ibvs_v"), _f(r, "olcum_hiz")
            if k is not None:
                KOM.append(k)
            if g is not None:
                GER.append(g)
        if lo <= m <= hi:
            S.append((t, m))
    if len(S) < 8 or not GER:
        return None
    dt = S[-1][0] - S[0][0]
    if dt < 0.5:
        return None
    return {"ad": os.path.basename(d),
            "kapanma": (S[0][1] - S[-1][1]) / dt,
            "komut": st.median(KOM) if KOM else None,
            "gercek": st.median(GER),
            "n": len(S)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KK1")
    ap.add_argument("--lo", type=float, default=5.0)
    ap.add_argument("--hi", type=float, default=20.0)
    a = ap.parse_args()

    kollar = {}
    for d in sorted(glob.glob(os.path.join(KOK, a.kok, "*__t*"))):
        kollar.setdefault(os.path.basename(d).split("__")[0], []).append(d)
    if not kollar:
        print("⛔ koşu yok: %s" % a.kok)
        return

    print("\n" + "=" * 72)
    print("  KAPANMA — %s  (menzil %.0f-%.0f m, arka kareler çıkarılmış)"
          % (a.kok, a.lo, a.hi))
    print("=" * 72)
    print("\n  %-14s %6s %11s %11s %11s %10s"
          % ("koşu", "kare", "KOMUT", "GERÇEK", "AÇIK", "kapanma"))
    print("  " + "-" * 66)
    OZ = {}
    for kol in sorted(kollar):
        R = [x for x in (kosu_olc(d, a.lo, a.hi) for d in kollar[kol]) if x]
        for x in R:
            print("  %-14s %6d %9.1f %10.1f %10.1f %9.1f"
                  % (x["ad"], x["n"], x["komut"] if x["komut"] else -1,
                     x["gercek"],
                     (x["komut"] - x["gercek"]) if x["komut"] else -1,
                     x["kapanma"]))
        OZ[kol] = R
    print("\n  ÖZET (medyan)")
    print("  %-14s %4s %11s %11s %11s"
          % ("kol", "n", "KOMUT", "GERÇEK hız", "kapanma"))
    print("  " + "-" * 56)
    taban = None
    for kol in sorted(OZ):
        R = OZ[kol]
        if not R:
            continue
        g = st.median([x["gercek"] for x in R])
        print("  %-14s %4d %9.1f %10.1f %10.1f"
              % (kol, len(R),
                 st.median([x["komut"] for x in R if x["komut"]]),
                 g, st.median([x["kapanma"] for x in R])))
        if kol in ("kapali", "yok"):
            taban = g
    if taban is not None and "acik" in OZ and OZ["acik"]:
        ga = st.median([x["gercek"] for x in OZ["acik"]])
        art = ga - taban
        print("\n  §5.1 MEKANİZMA KAPISI: gerçekleşen hız %+.1f m/s  ->  %s"
              % (art, "GEÇTİ" if art >= 0.5 else
                 "⛔ DÜŞTÜ (özellik devreye girmemiş, koşular GEÇERSİZ)"))
    print("""
  ⛔ Kapanma hızı TEK BAŞINA hüküm kurdurmaz (§5.2): hızlı kapanmak
     düzeltmeye daha AZ süre bırakır. Kararı `araclar/kacirma.py` verir.
""")


if __name__ == "__main__":
    main()
