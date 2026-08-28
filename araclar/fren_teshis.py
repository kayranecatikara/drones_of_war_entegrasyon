# -*- coding: utf-8 -*-
"""
================================================================================
FREN TEŞHİSİ — "sert fren -> körlük -> hedef kaçar -> kilit bozulur" döngüsü
================================================================================
KULLANICI GÖZLEMİ (2026-08-28, uçuşu kendi gözüyle izledi):
  "kilit isterini sağlamak için beklerken bir fren yapıyor ama öyle bir fren
   ki aracı çok geriye düşürüyor... sert frenlerde aracın eğimi bir anda
   değişiyor, hem tespit için sıkıntı hem hedef araç uzaklaşıyor hem de
   kilit bozuluyor."

Bu araç o cümledeki ÜÇ İDDİAYI da ayrı ayrı sayıyla ölçer:
  (1) FREN SERTLİĞİ   : komut hızının değişim hızı dv/dt (m/s²)
  (2) GERİ DÜŞÜŞ      : fren anından sonraki 3 s'te gerçek menzil ne kadar açıldı
  (3) KÖRLÜK          : aynı 3 s'te tespit oranı ne oldu
  (4) KİLİT KAYBI     : aynı 3 s'te kümülatif kilit süresi ne kadar eridi

⚠ ÖRNEKLEME (§5.3): `ibvs_v` cikarim.csv'de ÇIKARIM hızındadır (~9 Hz,
  110 ms). 20 ms'lik bir basamağı burada göremeyiz — ama basamağın SONUCU
  (iki çıkarım arasında 28 -> 0) görünür. Basamağın KENDİSİ `ozet.csv`'deki
  `sert_fren` sütununda 50 Hz kontrol tikinde sayılır. İkisi birlikte okunur.

⛔ Bu bir KANIT aracı değil, TEŞHİS aracıdır: neyin neye yol açtığını
   gösterir, hangi kolun kazandığını `araclar/kilit_ozet.py` söyler.

Kullanım:
    python3 araclar/fren_teshis.py logs/KREG24
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st

ESIK = -40.0        # m/s²; ölçülen dağılımda p05 = -40.2
PENCERE_S = 3.0     # fren sonrası bakılan süre


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def kosu_coz(d):
    y = os.path.join(d, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return None
    # ⛔ YALNIZ KİLİT FAZI. `durum=="GORSEL"` yetmez: TERMİNAL alt fazı da
    #   GORSEL'dir ve TEMAS ANINDA kutu 1300 px'e patlayıp terminal PI'yi
    #   bir tikte sıfırlar — bu -1400 m/s²'lik "fren", vuruşun kendisidir,
    #   kusur değil. Ölçüte karıştırmak iki kolu da sahte olarak kötü
    #   gösterir (2026-08-28'de tam bu oldu: dv_min her iki kolda -1395).
    R = [r for r in csv.DictReader(open(y))
         if r.get("durum") == "GORSEL" and (r.get("faz") or "KILIT") == "KILIT"]
    if len(R) < 30:
        return None
    olay = []
    for i in range(1, len(R)):
        t0, t1 = _f(R[i - 1], "t"), _f(R[i], "t")
        v0, v1 = _f(R[i - 1], "ibvs_v"), _f(R[i], "ibvs_v")
        if None in (t0, t1, v0, v1) or t1 <= t0:
            continue
        dv = (v1 - v0) / (t1 - t0)
        if dv >= ESIK:
            continue
        pen = [x for x in R[i:i + 60]
               if _f(x, "t") is not None and _f(x, "t") - t1 <= PENCERE_S]
        if len(pen) < 8:
            continue
        R0 = _f(R[i], "menzil3_m")
        Rs = [_f(x, "menzil3_m") for x in pen if _f(x, "menzil3_m") is not None]
        k0 = _f(R[i], "kilit_s") or 0.0
        ks = [_f(x, "kilit_s") for x in pen if _f(x, "kilit_s") is not None]
        olay.append({
            "dv": dv, "v0": v0, "v1": v1,
            "R0": R0, "Rmax": max(Rs) if Rs else R0,
            "tespit": sum(1 for x in pen if x.get("basarili") == "1") / len(pen),
            "kilit0": k0, "kilit_son": ks[-1] if ks else k0})
    tum = list(R)
    tespit_taban = sum(1 for x in tum if x.get("basarili") == "1") / len(tum)
    ad = os.path.basename(d)
    return {"ad": ad, "kol": ad.split("_")[1] if "_" in ad else "?",
            "sen": ad.split("__")[-1] if "__" in ad else "?",
            "olay": olay, "n": len(R), "tespit_taban": tespit_taban}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    a = ap.parse_args()
    kok = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       a.dizin)
    R = [x for x in (kosu_coz(d) for d in sorted(glob.glob(os.path.join(kok, "*")))
                     if os.path.isdir(d)) if x]
    if not R:
        print("⛔ koşu yok: %s" % a.dizin); return

    print("=" * 82)
    print("  FREN TEŞHİSİ — %s   (eşik %.0f m/s², pencere %.0f s)"
          % (a.dizin, ESIK, PENCERE_S))
    print("=" * 82)

    kollar = {}
    for x in R:
        kollar.setdefault(x["kol"], []).append(x)

    for kol in sorted(kollar):
        g = kollar[kol]
        olay = [o for x in g for o in x["olay"]]
        kare = sum(x["n"] for x in g)
        tb = st.median([x["tespit_taban"] for x in g])
        print("\n  ── %s ──  n=%d koşu, %d görsel çıkarım" % (kol, len(g), kare))
        print("     taban tespit oranı            %%%.1f" % (100 * tb))
        print("     SERT FREN OLAYI               %d   (çıkarım başına %%%.2f)"
              % (len(olay), 100.0 * len(olay) / max(1, kare)))
        if not olay:
            print("     ✅ hiç sert fren yok — regülatör sözleşmesi tutuyor")
            continue
        print("     (1) en sert basamak           %.0f m/s²   (medyan %.0f)"
              % (min(o["dv"] for o in olay), st.median([o["dv"] for o in olay])))
        print("         komut düşüşü              %.1f -> %.1f m/s (medyan)"
              % (st.median([o["v0"] for o in olay]),
                 st.median([o["v1"] for o in olay])))
        d = [o["Rmax"] - o["R0"] for o in olay if o["R0"] is not None]
        if d:
            print("     (2) GERİ DÜŞÜŞ (3 s)          +%.1f m (medyan)   en kötü +%.1f m"
                  % (st.median(d), max(d)))
        print("     (3) KÖRLÜK: fren sonrası tespit %%%.0f   (taban %%%.0f)"
              % (100 * st.median([o["tespit"] for o in olay]), 100 * tb))
        kd = [o["kilit0"] - o["kilit_son"] for o in olay]
        print("     (4) KİLİT KAYBI (3 s)         %.2f s eridi (medyan)"
              % st.median(kd))

    print("\n" + "=" * 82)
    print("  ⚠ Bu araç NEDEN'i gösterir, KAZANANI değil. Kol kararı:")
    print("    python3 araclar/kilit_ozet.py %s" % a.dizin)
    print("=" * 82)


if __name__ == "__main__":
    main()
