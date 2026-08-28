# -*- coding: utf-8 -*-
"""
================================================================================
HZ KAMPANYASI ÖZETİ — SENARYO İÇİNDE kol kıyası, PAYDASIZ ölçütlerle
================================================================================
`araclar/hz_kampanya.sh` çıktısını (`<NN>_<kol>__<senaryo>`) senaryoya göre
gruplar ve her senaryo içinde `taban` ile `hizli` kolunu kıyaslar.

⛔⛔ NİYE `tespit%` KULLANILMIYOR — PAYDA DEĞİŞTİ:
   `gorsel_tespit_yuzde` = kutu bulunan çıkarım / TOPLAM çıkarım. Bu
   kampanyanın DEĞİŞKENİ tam da toplam çıkarım sayısı. Yani oranın paydası
   kola göre iki katına çıkıyor ve iki kol AYNI ŞEYİ ölçmüyor.
   ÖLÇÜLDÜ (04_hizli__kademeli): çıkarım 2 katına çıktı, oran %37.5 -> %21.5
   DÜŞTÜ, ama saniyede bulunan kutu 2.7 -> 3.0 ARTTI. Orana bakan "kötüleşti"
   der, mutlak sayıya bakan "değişmedi" der. Doğrusu ikincisi.
   Bu yüzden birincil görüş ölçütü **TESPİT/s** (saniyede bulunan kutu).

⛔ `ozet.csv`'deki `det_hz` DE KULLANILMIYOR: paydası uçuş süresi ama görüş
   iş parçacığı uçuştan önce başlayıp sonra da yazıyor. Kısa koşularda şişer
   (03_taban__kademeli: gerçek 7.3 Hz, ozet 12.8 — tavan 10 iken!). Burada
   çıkarım hızı `cikarim.csv` satır sayısından HAM hesaplanır.

⛔ KIYAS SENARYO İÇİNDE (§5.9): daire'de taban isabet ~0, kademeli'de ~1.
   Kolları senaryodan bağımsız havuzlamak karışım oranını ölçer.

⛔ GEÇERLİLİK EŞİ (§5.2): salınım yalnız kutulu karelerde sayılır. TESPİT/s
   düşük olan hücrelerde salınım ⚠ ile işaretlenir ve hükme girmez.

Kullanım:
    python3 araclar/hz_ozet.py logs/HZ25
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from araclar.kacirma import kosuyu_coz          # noqa: E402

N_HUKUM = 4          # §5.4
TESPIT_S_ESIK = 3.0  # bunun altında salınım ölçütleri güvenilmez sayılır


def _f(r, k):
    try:
        v = r.get(k)
        return float(v) if v not in (None, "", "-", "nan") else None
    except Exception:
        return None


def _med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def _g(v, bic="%6.2f", yok="     —"):
    return yok if v is None else bic % v


def _ham(kdiz):
    """cikarim.csv'den HAM çıkarım/s ve TESPİT/s — paydası kayıt penceresi."""
    yol = os.path.join(kdiz, "cikarim.csv")
    if not os.path.exists(yol):
        return None, None
    rows = list(csv.DictReader(open(yol)))
    t = [float(r["t"]) for r in rows if r.get("t")]
    if len(t) < 2:
        return None, None
    sure = max(t) - min(t)
    if sure <= 0:
        return None, None
    tes = sum(1 for r in rows if r.get("basarili") == "1")
    return len(rows) / sure, tes / sure


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin", nargs="?", default="logs/HZ25")
    a = ap.parse_args()

    hucre = {}
    for oz in sorted(glob.glob(os.path.join(KOK, a.dizin, "*", "ozet.csv"))):
        d = os.path.dirname(oz)
        ad = os.path.basename(d)                 # NN_kol__senaryo
        try:
            govde = ad.split("_", 1)[1]
            kolu, sen = govde.split("__", 1)
        except Exception:
            continue
        try:
            r = list(csv.DictReader(open(oz)))[0]
        except Exception:
            continue
        kdiz = os.path.join(d, "k01")
        cps, tps = _ham(kdiz)
        kc = kosuyu_coz(kdiz) if os.path.isdir(kdiz) else None
        hucre.setdefault(sen, {}).setdefault(kolu, []).append(
            {"ad": ad, "r": r, "kc": kc, "cps": cps, "tps": tps})

    print("=" * 80)
    print("  HZ KAMPANYASI — %s" % a.dizin)
    print("  kol adlari kampanya betiginden gelir (A = 1. env, B = 2. env)")
    print("  birincil görüş ölçütü: TESPİT/s (oran DEĞİL — payda kola göre değişiyor)")
    print("=" * 80)

    for sen in sorted(hucre):
        print()
        print("█" * 80)
        print("  SENARYO: %s" % sen.upper())
        print("█" * 80)
        kollar = hucre[sen]
        # kol adlari kampanyaya gore degisir: eski HZ25'te taban/hizli,
        # gece kampanyalarinda A/B. Bilinen sirayi koru, kalani alfabetik ekle.
        _bilinen = ("taban", "hizli", "A", "B")
        adlar = ([k for k in _bilinen if k in kollar]
                 + sorted(k for k in kollar if k not in _bilinen))
        if not adlar:
            continue

        def satir(baslik, fn, bic="%10s"):
            print("  %-26s" % baslik, end="")
            for k in adlar:
                print(bic % fn(kollar[k]), end="")
            print()

        print("  %-26s" % "", end="")
        for k in adlar:
            print("%10s" % k, end="")
        print()
        print("  " + "-" * (26 + 10 * len(adlar)))

        satir("n", lambda g: len(g))
        satir("⭐ İLK DENEMEDE VURUŞ",
              lambda g: "%d/%d" % (sum(1 for x in g
                                       if (_f(x["r"], "isabet") or 0) >= 1), len(g)))
        satir("⭐ kaçırma (medyan)",
              lambda g: _g(_med([x["kc"]["n_kacirma"] for x in g if x["kc"]]),
                           "%.1f", "—"))
        satir("en yakın (m, medyan)",
              lambda g: _g(_med([_f(x["r"], "en_yakin_m") for x in g]), "%.2f", "—"))
        print("  " + "-" * (26 + 10 * len(adlar)))
        satir("çıkarım/s  [MEKANİZMA]",
              lambda g: _g(_med([x["cps"] for x in g]), "%.1f", "—"))
        satir("⭐ TESPİT/s",
              lambda g: _g(_med([x["tps"] for x in g]), "%.1f", "—"))
        satir("kutu yaşı medyan (s)",
              lambda g: _g(_med([_f(x["r"], "kutu_yasi_med") for x in g]), "%.3f", "—"))
        satir("kutu yaşı p90 (s)",
              lambda g: _g(_med([_f(x["r"], "kutu_yasi_p90") for x in g]), "%.2f", "—"))
        print("  " + "-" * (26 + 10 * len(adlar)))
        satir("çıkarım süresi (ms)  [bedel]",
              lambda g: _g(_med([_f(x["r"], "det_ms") for x in g]), "%.1f", "—"))
        satir("kontrol döngüsü (Hz)",
              lambda g: _g(_med([_f(x["r"], "tik_hz") for x in g]), "%.1f", "—"))
        print("  " + "-" * (26 + 10 * len(adlar)))
        satir("cx dönüş/s",
              lambda g: _g(_med([_f(x["r"], "cx_donus_s") for x in g]), "%.2f", "—"))
        satir("|yatış| p90 (°)",
              lambda g: _g(_med([_f(x["r"], "roll_p90") for x in g]), "%.1f", "—"))

        # geçerlilik eşi
        for k in adlar:
            tps = _med([x["tps"] for x in kollar[k]])
            if tps is not None and tps < TESPIT_S_ESIK:
                print("  ⚠ %s kolunda TESPİT/s %.1f < %.1f — salınım sayıları"
                      " HÜKME GİREMEZ (§5.2)" % (k, tps, TESPIT_S_ESIK))
        n_min = min(len(kollar[k]) for k in adlar)
        if n_min < N_HUKUM:
            print("  ⚠ n=%d < %d — bu senaryo ARA VERİdir, hüküm cümlesi kurulmaz (§5.4)"
                  % (n_min, N_HUKUM))

        print("  koşular:")
        for k in adlar:
            print("    %-6s %s" % (k, ", ".join(
                "%s(%s m,%s)" % (x["ad"].split("_")[0],
                                 _g(_f(x["r"], "en_yakin_m"), "%.2f", "?"),
                                 "İSABET" if (_f(x["r"], "isabet") or 0) >= 1
                                 else "ıska")
                for x in kollar[k])))

    print()
    print("=" * 80)
    print("  ⛔ SENARYOLAR ARASI HAVUZLAMA YOK (§5.9): daire ile kademeli aynı")
    print("     zorlukta değil; havuzlanmış medyan karışım oranını ölçer.")
    print("=" * 80)


if __name__ == "__main__":
    main()
