# -*- coding: utf-8 -*-
"""
================================================================================
TERMİNAL TEŞHİS — 2 m'nin İÇİNE girip vuranı vuramayandan ne ayırıyor?
================================================================================
GEREKÇE (2026-08-27 gecesi, 32 uçuş): sistem hedefi buluyor, yaklaşıyor,
1 metreye giriyor — ve ıskaların HEPSİ öldürücü yarıçapın içinde kalıyor
(1.14 · 0.87 · 1.08 · 1.14 · 0.70 m). Yani darboğaz GÖRME ya da YAKLAŞMA
değil, TEMAS ANI.

Bu araç en yakın anı bulur ve ondan geriye bir pencerede (varsayılan 1.0 s)
vuran koşularla vuramayanları AYNI ölçütlerle karşılaştırır.

⛔ NE YAPMAZ — BU BİR HİPOTEZ ÜRETECİDİR, KARAR ARACI DEĞİL:
   Çevrimdışı log analizidir; CLAUDE.md §2 gereği kabul kararını YALNIZ taze
   uçuş + video verir. Buradan çıkan her fark, kampanyaya çevrilmeden
   "bulgu" sayılmaz.

⛔ GÜÇ UYARISI: ıska sayısı AZ (gecede 5). n<10 iken hiçbir fark "anlamlı"
   diye sunulmaz; araç her satırda n'i basar ve az örneklemi işaretler.

⚠ ÇOKLU KARŞILAŞTIRMA TUZAĞI: burada bir düzine ölçüt yan yana bakılıyor.
   Yeterince ölçüte bakarsan biri şans eseri ayrışır. Bu yüzden çıktı
   "en büyük fark" diye tek bir kazanan İLAN ETMEZ; hepsini birden basar ve
   kararı insana bırakır (§5.6 — sonuca bakıp ölçüt seçmek yasak).

Kullanım:
    python3 araclar/terminal_teshis.py logs/HZ2 logs/ISP1 logs/KARMA10
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

# incelenecek ölçütler: (csv sütunu, etiket, mutlak deger mi)
OLCUTLER = [
    ("vis_cx",      "nişan hatası |cx-960| (px)", "cx"),
    ("vis_w",       "kutu genişliği (px)",        None),
    ("vis_h",       "kutu yüksekliği (px)",       None),
    ("vis_conf",    "dedektör güveni",            None),
    ("iz_yas",      "kutu yaşı (s)",              None),
    ("dz_m",        "dikey ofset |dz| (m)",       "abs"),
    ("aspekt_deg",  "hedef aspekti |° |",         "abs"),
    ("hedef_roll",  "hedef yatışı |° |",          "abs"),
    ("drone_roll",  "drone yatışı |° |",          "abs"),
    ("ibvs_v",      "komut hızı (m/s)",           None),
    ("olcum_hiz",   "gerçekleşen hız (m/s)",      None),
]


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def _isabet(d):
    y = os.path.join(d, "ozet.csv")
    if not os.path.exists(y):
        return None
    try:
        return int(list(csv.DictReader(open(y)))[0].get("isabet") or 0) == 1
    except Exception:
        return None


def kosu_terminali(d, pencere):
    """En yakın anı bul, ondan geriye `pencere` saniyelik ölçütleri topla."""
    y = os.path.join(d, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return None
    rows = [r for r in csv.DictReader(open(y))]
    if len(rows) < 20:
        return None
    # en yakın an: menzil3_m minimumu (yeniden doğuş sıçramasından ÖNCE)
    dizi = []
    for r in rows:
        t, m = _f(r, "t"), _f(r, "menzil3_m")
        if t is None or m is None:
            continue
        if dizi and m - dizi[-1][1] >= 10.0:      # hedef despawn -> kes
            break
        dizi.append((t, m, r))
    if len(dizi) < 10:
        return None
    en = min(dizi, key=lambda x: x[1])
    t_min, R_min = en[0], en[1]
    pen = [r for (t, m, r) in dizi if t_min - pencere <= t <= t_min]
    if len(pen) < 3:
        return None
    out = {"ad": os.path.basename(d), "Rmin": R_min, "n_kare": len(pen)}
    kutulu = [r for r in pen if r.get("basarili") == "1"]
    out["süreklilik"] = len(kutulu) / len(pen)
    for sut, _et, kip in OLCUTLER:
        vals = []
        for r in (kutulu if sut.startswith("vis") or sut == "iz_yas" else pen):
            v = _f(r, sut)
            if v is None:
                continue
            if kip == "cx":
                v = abs(v - 960.0)
            elif kip == "abs":
                v = abs(v)
            vals.append(v)
        out[sut] = st.median(vals) if vals else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizinler", nargs="+")
    ap.add_argument("--pencere", type=float, default=1.0)
    ap.add_argument("--yaricap", type=float, default=2.0,
                    help="yalniz bu menzilin ICINE giren kosular alinir")
    a = ap.parse_args()

    vuran, iskalayan = [], []
    for kok in a.dizinler:
        for oz in sorted(glob.glob(os.path.join(KOK, kok, "*", "ozet.csv"))):
            d = os.path.dirname(oz)
            isb = _isabet(d)
            if isb is None:
                continue
            t = kosu_terminali(d, a.pencere)
            if not t or t["Rmin"] > a.yaricap:
                continue
            t["kampanya"] = kok
            (vuran if isb else iskalayan).append(t)

    print("=" * 78)
    print("  TERMİNAL TEŞHİS — %s" % ", ".join(a.dizinler))
    print("  en yakın andan geriye %.1f s · yalnız Rmin ≤ %.1f m koşular"
          % (a.pencere, a.yaricap))
    print("=" * 78)
    print()
    print("  VURAN: %d koşu      ISKALAYAN: %d koşu" % (len(vuran), len(iskalayan)))
    if len(iskalayan) < 3 or len(vuran) < 3:
        print("  ⛔ karşılaştırma için yeterli örneklem yok.")
        return
    if len(iskalayan) < 10:
        print("  ⚠ ıska sayısı %d < 10 — HİÇBİR FARK 'anlamlı' diye sunulamaz;"
              % len(iskalayan))
        print("    aşağıdakiler yalnız HİPOTEZ adayıdır (§5.4).")

    print()
    print("  %-30s %10s %10s %9s" % ("ölçüt (terminal medyan)", "VURAN", "ISKA", "fark"))
    print("  " + "-" * 62)

    def bas(et, av, ai):
        av = [x for x in av if x is not None]
        ai = [x for x in ai if x is not None]
        if len(av) < 3 or len(ai) < 3:
            print("  %-30s %10s %10s %9s" % (et, "—", "—", "n yetersiz"))
            return
        mv, mi = st.median(av), st.median(ai)
        if abs(mv) > 1e-9:
            f = "%+.0f%%" % (100.0 * (mi - mv) / abs(mv))
        else:
            f = "—"
        print("  %-30s %10.2f %10.2f %9s" % (et, mv, mi, f))

    bas("görsel süreklilik (0-1)",
        [x["süreklilik"] for x in vuran], [x["süreklilik"] for x in iskalayan])
    bas("en yakın menzil (m)",
        [x["Rmin"] for x in vuran], [x["Rmin"] for x in iskalayan])
    for sut, et, _k in OLCUTLER:
        bas(et, [x.get(sut) for x in vuran], [x.get(sut) for x in iskalayan])

    print()
    print("  ISKALAYAN KOŞULAR (tek tek):")
    for x in sorted(iskalayan, key=lambda z: z["Rmin"]):
        print("    %-22s Rmin %.2f m  süreklilik %.0f%%  |cx| %s px  |dz| %s m"
              % (x["ad"], x["Rmin"], 100 * x["süreklilik"],
                 ("%.0f" % x["vis_cx"]) if x.get("vis_cx") is not None else "—",
                 ("%.1f" % x["dz_m"]) if x.get("dz_m") is not None else "—"))

    print()
    print("=" * 78)
    print("  ⛔ BU BİR HİPOTEZ LİSTESİDİR, BULGU DEĞİL. Çevrimdışı log analizi")
    print("     yalnız hipotez üretir; kabul kararını taze uçuş verir (§2).")
    print("=" * 78)


if __name__ == "__main__":
    main()
