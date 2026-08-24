# -*- coding: utf-8 -*-
"""
================================================================================
MODEL KIYASI — talon_v3 vs talon_v5, İMHA ODAKLI
================================================================================
Ölçütler `KAMPANYA MODEL20` planında KOŞMADAN ÖNCE ilan edildi; bu araç
yalnız onları hesaplar (§5.6 — sonuca bakıp ölçüt seçmek yasak).

BİRİNCİL   : imha oranı (x/n) VE imha süresi medyanı
             Kullanıcının cümlesinden türetildi (§5.5): *"hedef aracı çok daha
             iyi vurduğumuz zaman vardı... direkt 20 saniyede falan"*
MEKANİZMA  : angajman bandı (4-15 m) tespit oranı — iki kol arasında fark YOKSA
             modeller fiilen aynı davranmış demektir, kampanya GEÇERSİZ (§5.1)
GEÇERLİLİK : en yakın menzil (§5.2 — `imha`, koşu tam en yakınlaşma anında
             bittiğinde 1 sayılır; iyi imha + kötü en yakın = ŞÜPHELİ)
REGRESYON  : istasyon hatası, görsel devir menzili (§5.10)
SALINIM    : roll işaret değişimi/s, |roll| p90 (§4)

⛔ GEÇERSİZ KOŞU = `ihlal` sütunu dolu olan (§4). SÜREYE GÖRE ELEME YOKTUR:
   bu kampanyada KISA KOŞU = HIZLI İMHA, yani ölçülen şeyin ta kendisi.
   (İlk yazımda "süre < 20 s ise at" filtresi vardı ve v3'ün 13.7 s'de imha
   eden koşusunu ATIYORDU — v3'ün EN İYİ koşularını eleyip sonucu v5 lehine
   çevirecekti. Kampanya sürerken yakalandı.)

Kullanım:  python3 araclar/model_kiyas20.py
================================================================================
"""
import csv
import glob
import os
import statistics as st
import sys

import numpy as np

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(v, d=float("nan")):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def kol(desen):
    """Bir kolun GEÇERLİ koşularını topla."""
    out = []
    for d in sorted(glob.glob(os.path.join(KOK, desen))):
        p = os.path.join(d, "ozet.csv")
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p)):
            if (r.get("ihlal") or "-").strip() not in ("-", ""):
                continue
            # ⛔ SÜREYE GÖRE ELEME YOK — bu kampanyada KISA KOŞU = HIZLI İMHA,
            #   yani ölçmek istediğimiz şeyin ta kendisi. Önceki araçtan
            #   "süre < 20 s ise geçersiz" filtresini kopyalamıştım; ilk v3
            #   koşusu 13.7 s'de imha etmişti ve filtre onu ATIYORDU —
            #   v3'ün EN İYİ koşularını eleyip sonucu v5 lehine çevirecekti.
            #   Geçersizliğin tek ölçütü `ihlal` sütunudur (§4).
            #   ⚠ İstisna: imha OLMADAN çok kısa biten koşu gerçekten
            #     bozuktur (drone doğmamış vb.); onu da `ihlal` yakalıyor.
            r["_dizin"] = d
            out.append(r)
    return out


def bant_tespit(kayitlar):
    """MEKANİZMA (§5.1): görsel fazda menzil bandına göre TAZE kutu oranı.
    `vis_yas < 0.3 s` = güdümün o an elinde taze kutu var."""
    B = {}
    for r in kayitlar:
        m = os.path.join(r["_dizin"], "k01", "meta.csv")
        if not os.path.exists(m):
            continue
        for x in csv.DictReader(open(m)):
            if not str(x.get("durum", "")).startswith("GORSEL"):
                continue
            R = _f(x.get("gercek_menzil"))
            y = _f(x.get("vis_yas"))
            if not np.isfinite(R):
                continue
            k = (0, 4) if R < 4 else ((4, 8) if R < 8 else
                                      ((8, 15) if R < 15 else (15, 999)))
            B.setdefault(k, []).append(1 if (np.isfinite(y) and 0 <= y < 0.3) else 0)
    return B


def sat(ad, a, b, anah, birim="", buyuk_iyi=False):
    va = [_f(x.get(anah)) for x in a]
    vb = [_f(x.get(anah)) for x in b]
    va = [v for v in va if np.isfinite(v) and v != -1]
    vb = [v for v in vb if np.isfinite(v) and v != -1]
    if not va or not vb:
        print("  %-26s   veri yok" % ad); return
    ma, mb = st.median(va), st.median(vb)
    kaz = (ma > mb) if buyuk_iyi else (ma < mb)
    print("  %-26s %9.2f%-3s %9.2f%-3s   %s"
          % (ad, ma, birim, mb, birim,
             "v3 ↑" if kaz else ("=" if abs(ma - mb) < 1e-9 else "v5 ↑")))


def main():
    A, B = kol("logs/M20_V3_*"), kol("logs/M20_V5_*")
    if not A or not B:
        print("veri yok"); return
    ia = sum(1 for x in A if x.get("imha") == "1")
    ib = sum(1 for x in B if x.get("imha") == "1")
    ta = sum(1 for x in A if x.get("temas") == "1")
    tb = sum(1 for x in B if x.get("temas") == "1")

    print("\n" + "=" * 72)
    print("  KAMPANYA MODEL20 — talon_v3 vs talon_v5      n(v3)=%d  n(v5)=%d"
          % (len(A), len(B)))
    print("=" * 72)
    print("  %-26s %12s %12s   kazanan" % ("", "talon_v3", "talon_v5"))
    print("  " + "-" * 68)

    print("\n  ⭐ BİRİNCİL")
    print("  %-26s %9d/%-2d %9d/%-2d   %s"
          % ("İMHA", ia, len(A), ib, len(B),
             "v3 ↑" if ia / len(A) > ib / len(B) else
             ("=" if abs(ia / len(A) - ib / len(B)) < 1e-9 else "v5 ↑")))
    print("  %-26s %9d/%-2d %9d/%-2d" % ("temas", ta, len(A), tb, len(B)))
    sat("İMHA SÜRESİ", A, B, "sure", "s")

    print("\n  ⚙ MEKANİZMA KAPISI (§5.1)")
    ba, bb = bant_tespit(A), bant_tespit(B)
    fark = False
    for k in sorted(set(ba) | set(bb)):
        va, vb = ba.get(k, []), bb.get(k, [])
        if len(va) < 5 or len(vb) < 5:
            continue
        pa, pb = 100 * np.mean(va), 100 * np.mean(vb)
        if k[0] in (4, 8) and abs(pa - pb) > 8:
            fark = True
        print("    %2d-%3d m tespit%%      %8.1f%% (n=%3d) %6.1f%% (n=%3d)"
              % (k[0], k[1], pa, len(va), pb, len(vb)))
    print("     -> angajman bandında fark: %s"
          % ("✔ VAR — modeller ayrışıyor" if fark else
             "⛔ YOK — modeller aynı davranmış, kampanya GEÇERSİZ"))

    print("\n  🔒 GEÇERLİLİK EŞİ (§5.2)")
    sat("en yakın menzil", A, B, "en_yakin_m", "m")

    print("\n  ⛔ REGRESYON (§5.10)")
    # ⛔ `ist_hata_medyan` BU KAMPANYADA GEÇERSİZ — SÜREYLE karışıyor (§5.9).
    #   Ölçüldü (v3, koşu bazında): 6 s koşu 26.6 m | 13 s 63.5 m | 14 s 31.6 m
    #   | 40 s 35.9 m | 64 s 8.3 m. Koşu UZADIKÇA hata düşüyor, çünkü araç
    #   istasyona OTURMAYA vakit buluyor. v3 hedefi erken vurduğu için
    #   oturamıyor ve "hata" aslında YAKLAŞMA fazının kendisi oluyor.
    #   Yani ölçüt, tedavinin etkisiyle (hızlı imha) karışıyor.
    #   SÜREDEN BAĞIMSIZ ölçüt: koşuda ULAŞILAN EN İYİ istasyon hatası.
    sat("ISTASYON en iyi hata", A, B, "ist_hata_min", "m")
    print("     ⚠ `ist_hata_medyan` raporlanmıyor: süreyle karışıyor (§5.9);"
          "\n       v3 hedefi erken vurduğu için istasyona oturamıyor.")
    sat("görsel devir menzili", A, B, "devir_menzil", "m", buyuk_iyi=True)
    sat("görsel devir zamanı", A, B, "devir_s", "s")

    print("\n  〰 SALINIM (§4)")
    sat("roll işaret değişimi", A, B, "roll_donus_s", "/s")
    sat("|roll| p90", A, B, "roll_p90", "°")

    print("\n  --- koşu koşu süreler ---")
    print("    v3: %s" % " ".join("%.0f%s" % (_f(x["sure"]),
                                              "✓" if x.get("imha") == "1" else "✗")
                                  for x in A))
    print("    v5: %s" % " ".join("%.0f%s" % (_f(x["sure"]),
                                              "✓" if x.get("imha") == "1" else "✗")
                                  for x in B))
    print("=" * 72)
    if len(A) < 4 or len(B) < 4:
        print("  ⚠ n < 4/kol — ARA VERİ, KARAR DEĞİL (§5.4)")
    print()


if __name__ == "__main__":
    main()
