# -*- coding: utf-8 -*-
"""
================================================================================
KİLİT FAZI KAMPANYA ÖZETİ — kol kol, GEÇERLİLİK EŞLERİYLE
================================================================================
`araclar/kilit_kampanya.sh` çıktısını okur. Etiket düzeni: `NN_<KOL>__<senaryo>`
(KOL: K = kilit fazı KAPALI, A = AÇIK).

⛔ KIYAS SENARYO İÇİNDE YAPILIR (§5.9). Kolların senaryo karışımı eşit
   olmazsa kaba medyan kolları değil KARIŞIM ORANINI ölçer — 2026-08-12'de
   tam bu yaşandı ("%47 iyileşme" iddiası eşlenince −9%/+2%'ye indi).

⛔ MEKANİZMA KAPISI (§5.1): A kolunda `kilit_faz_s == 0` olan koşu VERİ
   NOKTASI DEĞİL, GEÇERSİZ koşudur — özellik hiç devreye girmemiştir.
   Araç böyle koşuları AYRI sayar ve hükümden ÇIKARIR.

⛔ GEÇERLİLİK EŞİ (§5.2): "kilit sağlandı" tek başına okunamaz. Kilit,
   hedefe YAKLAŞARAK sağlanır; ama asıl amaç VURUŞTUR. Bu yüzden yanında
   daima `isabet` ve `erken_temas` (kilit ALINMADAN çarpma) raporlanır —
   yarışmada kilitsiz vuruş PUAN GETİRMEZ.

Kullanım:
    python3 araclar/kilit_ozet.py logs/KILIT16
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

KOL_ADI = {"K": "KAPALI — bugünkü hal (görsel temas -> doğrudan vuruş)",
           "A": "AÇIK   — kilit fazı: mesafe tut, 5 s kilit biriktir, sonra vuruş",
           "V1": "SERT regülatör — KFWD .35 · IMAX 8 · VMIN 0 · VMAX 28 · SLEW yok",
           "V2": "YUMUŞAK regülatör — KFWD .10 · IMAX 22 · VMIN 12 · VMAX 33 · SLEW 20"}


def _f(r, k, v=None):
    try:
        x = r.get(k)
        return float(x) if x not in (None, "", "-", "nan") else v
    except Exception:
        return v


def _med(v, bic="%6.2f", yok="     —"):
    v = [x for x in v if x is not None]
    return yok if not v else bic % st.median(v)


def kosu_oku(d):
    oz = os.path.join(d, "ozet.csv")
    if not os.path.exists(oz):
        return None
    try:
        r = list(csv.DictReader(open(oz)))[0]
    except Exception:
        return None
    ad = os.path.basename(d)
    parca = ad.split("_")
    kol = parca[1] if len(parca) > 1 else "?"
    sen = ad.split("__")[-1] if "__" in ad else "?"
    x = {"ad": ad, "kol": kol, "sen": sen, "r": r,
         "isabet": int(_f(r, "isabet", 0) or 0),
         "kilit": int(_f(r, "kilit_saglandi", 0) or 0),
         "kilit_t": _f(r, "kilit_t"),
         "kilit_en_iyi": _f(r, "kilit_en_iyi_s", 0.0),
         "kilit_R": _f(r, "kilit_R"),
         "kilit_faz_s": _f(r, "kilit_faz_s", 0.0),
         "terminal_t": _f(r, "terminal_t"),
         "en_yakin": _f(r, "en_yakin_m"),
         "tespit": _f(r, "gorsel_tespit_yuzde"),
         "gorsel_s": _f(r, "gorsel_s"),
         "cx_don": _f(r, "cx_donus_s"),
         "roll_p90": _f(r, "roll_p90"),
         "sert_fren": _f(r, "sert_fren"),
         "dv_min": _f(r, "dv_min"),
         "reg_slew": _f(r, "kilit_reg_slew"),
         "reg_doyum": _f(r, "kilit_reg_doyum"),
         "ihlal": r.get("ihlal", "-")}
    # ⭐ ERKEN TEMAS: vurduk ama kilidi HİÇ alamadık -> yarışmada PUAN YOK.
    x["erken_temas"] = int(x["isabet"] == 1 and x["kilit"] == 0)
    # ⭐ KİLİTLİ VURUŞ: istenen sonuç.
    x["kilitli_vurus"] = int(x["isabet"] == 1 and x["kilit"] == 1)
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    a = ap.parse_args()
    kok = os.path.join(KOK, a.dizin)
    R = [x for x in (kosu_oku(d) for d in sorted(glob.glob(os.path.join(kok, "*")))
                     if os.path.isdir(d)) if x]
    if not R:
        print("⛔ koşu yok: %s" % a.dizin); return

    print("=" * 84)
    print("  KİLİT FAZI KAMPANYASI — %s   (n=%d)" % (a.dizin, len(R)))
    print("=" * 84)

    # ---- MEKANİZMA KAPISI (§5.1) ----
    deney = [y for y in R if y["kol"] in ("A", "V2")]
    gecersiz = [x for x in deney if (x["kilit_faz_s"] or 0) <= 0.0]
    print("\n  §5.1 MEKANİZMA KAPISI — deney kolunda özellik devreye girdi mi")
    print("     (V2 için ayrıca: SERT FREN sayacı 0 OLMALI — regülatörün sözleşmesi)")
    for x in deney:
        _sf = x["sert_fren"]
        _not = "✓"
        if (x["kilit_faz_s"] or 0) <= 0:
            _not = "⛔ GEÇERSİZ (kilit fazı hiç çalışmadı)"
        elif x["kol"] == "V2" and _sf is not None and _sf > 0:
            _not = "⛔ SERT FREN VAR (%d) — regülatör sözleşmesi ihlali" % _sf
        print("     %-18s kilit_faz_s=%5.1f s  sert_fren=%4s  dv_min=%8s  %s"
              % (x["ad"], x["kilit_faz_s"] or 0.0,
                 "—" if _sf is None else int(_sf),
                 "—" if x["dv_min"] is None else ("%.0f" % x["dv_min"]), _not))
    if gecersiz:
        print("     ⛔ %d koşu HÜKÜMDEN ÇIKARILDI." % len(gecersiz))

    # ---- KOŞU KOŞU ----
    print("\n  KOŞULAR")
    print("  %-18s %4s %-9s %6s %8s %9s %8s %7s %7s"
          % ("koşu", "kol", "senaryo", "KİLİT", "en_iyi_s", "kilit@", "R@kilit",
             "isabet", "enyakın"))
    print("  " + "-" * 82)
    for x in R:
        print("  %-18s %4s %-9s %6s %7.2fs %8s %8s %7s %6.2fm"
              % (x["ad"], x["kol"], x["sen"],
                 "✓" if x["kilit"] else "✗", x["kilit_en_iyi"] or 0.0,
                 ("%.1fs" % x["kilit_t"]) if x["kilit_t"] and x["kilit_t"] > 0 else "—",
                 ("%.1fm" % x["kilit_R"]) if x["kilit_R"] and x["kilit_R"] > 0 else "—",
                 "✓" if x["isabet"] else "·",
                 x["en_yakin"] if x["en_yakin"] is not None else -1))

    # ---- SENARYO İÇİNDE KOL KIYASI (§5.9) ----
    senler = sorted(set(x["sen"] for x in R))
    for sen in senler:
        print("\n" + "─" * 84)
        print("  SENARYO: %s" % sen.upper())
        print("─" * 84)
        for kol in ("K", "A", "V1", "V2"):
            g = [x for x in R if x["sen"] == sen and x["kol"] == kol
                 and not (kol in ("A", "V2") and (x["kilit_faz_s"] or 0) <= 0)]
            if not g:
                continue
            n = len(g)
            print("\n   %s  n=%d   %s" % (kol, n, KOL_ADI.get(kol, "")))
            if n < 4:
                print("     ⚠ n<4 — ARA VERİ, hüküm cümlesi kurulmaz (§5.4)")
            kl = sum(x["kilit"] for x in g)
            isb = sum(x["isabet"] for x in g)
            erk = sum(x["erken_temas"] for x in g)
            kv = sum(x["kilitli_vurus"] for x in g)
            print("     ⭐ KİLİT İSTERİ SAĞLANDI   %d/%d" % (kl, n))
            print("        en iyi 10 s kümülatif   %s s   (isteri 5.00)"
                  % _med([x["kilit_en_iyi"] for x in g]))
            print("        kilit süresi (an)       %s s   R@kilit %s m"
                  % (_med([x["kilit_t"] for x in g if x["kilit_t"] and x["kilit_t"] > 0], "%5.1f"),
                     _med([x["kilit_R"] for x in g if x["kilit_R"] and x["kilit_R"] > 0], "%5.1f")))
            print("        KILIT fazında geçen     %s s"
                  % _med([x["kilit_faz_s"] for x in g], "%5.1f"))
            print("        SERT FREN (50 Hz)       %s adet   en sert %s m/s²"
                  % (_med([x["sert_fren"] for x in g], "%5.0f"),
                     _med([x["dv_min"] for x in g], "%6.0f")))
            print("     ── geçerlilik eşleri (§5.2) ──")
            print("        isabet %d/%d   ⭐KİLİTLİ VURUŞ %d/%d   ⚠erken temas %d"
                  % (isb, n, kv, n, erk))
            print("        en yakın %s m   görsel tespit %s%%   görsel faz %s s"
                  % (_med([x["en_yakin"] for x in g]),
                     _med([x["tespit"] for x in g], "%5.1f"),
                     _med([x["gorsel_s"] for x in g], "%5.1f")))
            print("        salınım: cx dönüş/s %s   |yatış| p90 %s°"
                  % (_med([x["cx_don"] for x in g], "%5.2f"),
                     _med([x["roll_p90"] for x in g], "%5.1f")))

    print("\n" + "=" * 84)
    print("  ⚠ 'kilit sağlandı' TEK BAŞINA yeterli değil: yarışmada KİLİTSİZ")
    print("    VURUŞ puan getirmez, KİLİTLİ ama vurulmamış hedef de imha")
    print("    değildir. Karar ölçütü ⭐KİLİTLİ VURUŞ sayısıdır.")
    print("=" * 84)


if __name__ == "__main__":
    main()
