# -*- coding: utf-8 -*-
"""
================================================================================
KARMA KAMPANYA ÖZETİ — kol kol, GEÇERLİLİK EŞLERİYLE birlikte
================================================================================
`araclar/karma_kampanya.sh` çıktısını hedef davranışına göre gruplar
(taban / kare / daire / kademeli) ve her kol için ölçütleri basar.

⛔ NİYE AYRI BİR ARAÇ — KARIŞIM ORANI TUZAĞI (§5.9):
   Bu kampanyada kollar AYNI ŞEY DEĞİL: `daire`de taban isabet oranı sıfıra
   yakın, `kademeli`de yüksek. Bütün koşuların kaba medyanı, sistemin
   iyiliğini değil KARIŞIM ORANINI ölçer. Bu yüzden burada asla havuzlanmış
   tek bir sayı basılmaz; her ölçüt KOL İÇİNDE verilir.

⛔ GEÇERLİLİK EŞİ ZORUNLU (§5.2): salınım ölçütleri (cx/yatış işaret
   değişimi) YALNIZ kutu olan karelerde sayılıyor. Görsel temas düşükse
   ölçüt "sakin" görünür — çünkü ölçecek kare yoktur. Temas %60'ın altındaki
   kollarda salınım sayıları ⚠ ile işaretlenir ve HÜKME GİRMEZ.

⛔ n<4 iken hüküm cümlesi kurulmaz (§5.4). Araç n'i her satırda basar ve
   n<4 olan kolları "ARA VERİ" diye etiketler.

Kullanım:
    python3 araclar/karma_ozet.py logs/KARMA10
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

TEMAS_ESIK = 60.0        # §5.2 — altındaki kolda salınım GÜVENİLMEZ
N_HUKUM    = 4           # §5.4 — altındaki kolda hüküm cümlesi kurulmaz

# hedef davranışları, kampanya sırasındaki mantıklı sırayla
KOL_SIRA = ["taban", "kademeli", "kare", "daire"]

KOL_ACIKLAMA = {
    "taban":    "hedef kendi rotasında (devralma YOK) — kıyas çizgisi",
    "kademeli": "yakında hafif, GÖRSEL fazda SERT anlık kaçamak",
    "kare":     "40 m kenarlı kare, koşu boyunca — sürekli manevra",
    "daire":    "35 m çaplı daire, koşu boyunca — düz kesim YOK",
}


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin", nargs="?", default="logs/KARMA10")
    a = ap.parse_args()

    kokdiz = os.path.join(KOK, a.dizin)
    kosular = sorted(glob.glob(os.path.join(kokdiz, "*", "ozet.csv")))
    if not kosular:
        print("⛔ ozet.csv bulunamadı: %s" % a.dizin)
        return

    kol = {}
    for oz in kosular:
        d = os.path.dirname(oz)
        ad = os.path.basename(d)
        k = ad.split("_", 1)[1] if "_" in ad else ad
        try:
            r = list(csv.DictReader(open(oz)))[0]
        except Exception:
            continue
        # kaçırma: 20 Hz bbox menzilinden (§5.3 — panel 1 Hz kullanılmaz)
        kdiz = os.path.join(d, "k01")
        kc = kosuyu_coz(kdiz) if os.path.isdir(kdiz) else None
        kol.setdefault(k, []).append({"ad": ad, "r": r, "kc": kc})

    print("=" * 78)
    print("  KARMA KAMPANYA ÖZETİ — %s" % a.dizin)
    print("  her ölçüt KOL İÇİNDE; kollar arası kaba medyan BASILMAZ (§5.9)")
    print("=" * 78)

    for k in KOL_SIRA + [x for x in sorted(kol) if x not in KOL_SIRA]:
        if k not in kol:
            continue
        g = kol[k]
        n = len(g)
        R = [x["r"] for x in g]
        temas = _med([_f(r, "gorsel_tespit_yuzde") for r in R])
        guvenli = temas is not None and temas >= TEMAS_ESIK

        isabet = sum(1 for r in R if (_f(r, "isabet") or 0) >= 1)
        kacirma = [x["kc"]["n_kacirma"] for x in g if x["kc"]]
        # kaçırmaların sebebi: kör mü, gördü de ıskaladı mı
        kor = gordu = 0
        for x in g:
            if not x["kc"]:
                continue
            for ge in x["kc"]["kacirma"]:
                # ⚠ ANAHTAR ADI: `temas_orani` (geçiş anındaki kutulu kare
                #   oranı), `temas` DEĞİL. Eşik 0.5 — `kacirma.py`'nin kendi
                #   raporuyla AYNI olmak zorunda, yoksa iki araç aynı veriden
                #   farklı sayı üretir (2026-08-27'de tam bu oldu: burada
                #   "kör %100" çıkarken kacirma.py 9/14 diyordu).
                if ge.get("temas_orani", 0.0) < 0.5:
                    kor += 1
                else:
                    gordu += 1

        print()
        print("─" * 78)
        print("  %-9s n=%d   %s" % (k.upper(), n, KOL_ACIKLAMA.get(k, "")))
        if n < N_HUKUM:
            print("  ⚠ n<%d — bu kolun sayıları ARA VERİdir, hüküm cümlesi kurulmaz (§5.4)"
                  % N_HUKUM)
        print("─" * 78)

        print("  ⭐ İLK DENEMEDE VURUŞ %d/%d      kaçırma (imha başına ıska geçiş):"
              " medyan %s" % (isabet, n, _g(_med(kacirma), "%.1f", "—")))
        if kor + gordu:
            print("     kaçırma sebebi: KÖR geçti %d (%%%.0f) · GÖRDÜ ıskaladı %d (%%%.0f)"
                  % (kor, 100.0 * kor / (kor + gordu),
                     gordu, 100.0 * gordu / (kor + gordu)))

        print("     en yakın medyan   %s m      görsel faz medyan %s s"
              % (_g(_med([_f(r, "en_yakin_m") for r in R])),
                 _g(_med([_f(r, "gorsel_s") for r in R]), "%5.1f")))
        print("     imha süresi medyan %s s     devir@ medyan %s s"
              % (_g(_med([_f(r, "sure") for r in R]), "%6.1f"),
                 _g(_med([_f(r, "devir_s") for r in R]), "%5.1f")))

        print()
        print("     GÖRÜŞ:  temas %s%%   kutu yaşı p90 %s s   çıkarım %s Hz / %s ms"
              % (_g(temas, "%.1f"),
                 _g(_med([_f(r, "kutu_yasi_p90") for r in R]), "%.2f"),
                 _g(_med([_f(r, "det_hz") for r in R]), "%.1f"),
                 _g(_med([_f(r, "det_ms") for r in R]), "%.1f")))
        print("     KONTROL: döngü %s Hz   görsel kesinti %s s"
              % (_g(_med([_f(r, "tik_hz") for r in R]), "%.1f"),
                 _g(_med([_f(r, "kesinti_s") for r in R]), "%.1f")))

        isaret = "  " if guvenli else "⚠ "
        print("   %sSALINIM: cx dönüş/s %s   yatış dönüş/s %s   |yatış| p90 %s°"
              % (isaret,
                 _g(_med([_f(r, "cx_donus_s") for r in R]), "%.2f"),
                 _g(_med([_f(r, "roll_donus_s") for r in R]), "%.2f"),
                 _g(_med([_f(r, "roll_p90") for r in R]), "%.1f")))
        if not guvenli:
            print("     ⚠ GEÇERLİLİK EŞİ DÜŞTÜ (§5.2): görsel temas %%%.1f < %%%.0f."
                  % (temas or 0.0, TEMAS_ESIK))
            print("       Salınım YALNIZ kutu olan karelerde sayılıyor; ölçecek kare")
            print("       az olduğu için bu sayılar HÜKME GİREMEZ.")

        print()
        print("     koşular: %s" % ", ".join(
            "%s(%s m,%s)" % (x["ad"].split("_")[0],
                             _g(_f(x["r"], "en_yakin_m"), "%.2f", "?"),
                             "İSABET" if (_f(x["r"], "isabet") or 0) >= 1 else "ıska")
            for x in g))

    print()
    print("=" * 78)
    print("  ⛔ KOLLAR ARASI KABA MEDYAN KASTEN BASILMADI: kollar farklı zorlukta,")
    print("     havuzlanmış sayı sistemin iyiliğini değil karışım oranını ölçer (§5.9).")
    print("=" * 78)


if __name__ == "__main__":
    main()
