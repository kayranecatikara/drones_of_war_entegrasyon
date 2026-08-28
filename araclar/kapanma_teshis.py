# -*- coding: utf-8 -*-
"""
================================================================================
KAPANMA TEŞHİSİ — "kilit bandına girebiliyor muyuz?"
================================================================================
KILIT fazının tek işi var: hedefi, ekranda >= %5 göründüğü menzile getirip
ORADA TUTMAK. Bu araç o işin nerede tıkandığını menzil bandına göre gösterir.

ÖLÇÜLDÜ (KREG24) ve bu aracı doğuran bulgu:
  R > 18 m bandında kutu 36 px -> hata 106 px olmasına rağmen komut yalnız
  25.2 m/s, çünkü regülatörün integrali (kilit_I) 22 tavanına çıkamamış,
  14.4'te kalmış. Gerçekleşen 18.6 m/s, hedef 18 m/s -> kapanma +0.6 m/s,
  yani FİİLEN KAPATMIYOR. İntegralin sıfırdan 22'ye çıkması 5.2 s sürüyor
  ve görsel faza her (yeniden) girişte bu süre baştan yaşanıyor.

⛔ BU BİR MEKANİZMA SÜTUNUDUR (§5.1): kazancı yükselten bir kol, R>18 m
   bandında kapanmayı belirgin negatife çekmiyorsa özellik ÇALIŞMAMIŞTIR
   ve o kol veri noktası değildir.

Kullanım: python3 araclar/kapanma_teshis.py logs/KAZ24
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st

BANT = [(0, 8, "< 8 m"), (8, 12, "8-12 m"), (12, 18, "12-18 m"),
        (18, 999, "> 18 m")]
HEDEF_HIZ = 18.0        # ölçüldü: Talon düz uçuşta ~18 m/s


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    a = ap.parse_args()
    kok = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       a.dizin)

    kollar = {}
    for d in sorted(glob.glob(os.path.join(kok, "*"))):
        y = os.path.join(d, "k01", "cikarim.csv")
        if not os.path.isdir(d) or not os.path.exists(y):
            continue
        ad = os.path.basename(d)
        kol = ad.split("_")[1] if "_" in ad else "?"
        sen = ad.split("__")[-1] if "__" in ad else "?"
        R = [r for r in csv.DictReader(open(y))
             if r.get("durum") == "GORSEL" and (r.get("faz") or "KILIT") == "KILIT"]
        # kapanma: gerçek menzilin türevi (ÖLÇÜM-ONLY truth)
        prev = None
        for r in R:
            t, m = _f(r, "t"), _f(r, "menzil3_m")
            if t is None or m is None:
                prev = None if t is None else (t, m)
                continue
            if prev and 0.05 < t - prev[0] < 0.5:
                r["_dR"] = (m - prev[1]) / (t - prev[0])
            prev = (t, m)
        kollar.setdefault((sen, kol), []).extend(R)

    print("=" * 88)
    print("  KAPANMA TEŞHİSİ — %s   (KILIT fazı, gerçek menzil bandına göre)" % a.dizin)
    print("  ⭐ MEKANİZMA SÜTUNU: R>18 m bandında kapanma belirgin NEGATİF olmalı")
    print("=" * 88)

    for sen in sorted(set(k[0] for k in kollar)):
        print("\n ── SENARYO: %s ──" % sen.upper())
        print("  %-4s %-9s %6s %6s %8s %8s %9s %8s %7s"
              % ("kol", "menzil", "n", "kutu", "komut", "gerçek", "KAPANMA",
                 "kilit_I", "tespit"))
        print("  " + "-" * 80)
        for kol in sorted(set(k[1] for k in kollar if k[0] == sen)):
            R = kollar[(sen, kol)]
            for lo, hi, ad in BANT:
                g = [r for r in R if _f(r, "menzil3_m") is not None
                     and lo <= _f(r, "menzil3_m") < hi]
                if len(g) < 20:
                    continue
                tes = [r for r in g if r.get("basarili") == "1"]
                kt = [max(_f(r, "vis_w") or 0, _f(r, "vis_h") or 0) for r in tes]
                vk = [_f(r, "ibvs_v") for r in g if _f(r, "ibvs_v") is not None]
                og = [_f(r, "olcum_hiz") for r in g if _f(r, "olcum_hiz") is not None]
                kI = [_f(r, "kilit_I") for r in g if _f(r, "kilit_I") is not None]
                dR = [r["_dR"] for r in g if "_dR" in r]
                print("  %-4s %-9s %6d %6s %8s %8s %9s %8s %6.0f%%"
                      % (kol, ad, len(g),
                         ("%.0f" % st.median(kt)) if kt else "—",
                         ("%.1f" % st.median(vk)) if vk else "—",
                         ("%.1f" % st.median(og)) if og else "—",
                         ("%+.2f" % st.median(dR)) if dR else "—",
                         ("%.1f" % st.median(kI)) if kI else "—",
                         100.0 * len(tes) / len(g)))
        # kolun TAMAMI
        print("  " + "-" * 80)
        for kol in sorted(set(k[1] for k in kollar if k[0] == sen)):
            R = kollar[(sen, kol)]
            dR = [r["_dR"] for r in R if "_dR" in r]
            m = [_f(r, "menzil3_m") for r in R if _f(r, "menzil3_m") is not None]
            if not dR or not m:
                continue
            iyi = sum(1 for x in m if x <= 9.9) / len(m)
            print("  %-4s TOPLAM     n=%d   menzil medyan %.1f m   "
                  "kilit bandında (<=9.9 m) %%%.0f   kapanma medyan %+.2f m/s"
                  % (kol, len(R), st.median(m), 100 * iyi, st.median(dR)))
    print("\n" + "=" * 88)


if __name__ == "__main__":
    main()
