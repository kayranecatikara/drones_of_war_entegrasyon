# -*- coding: utf-8 -*-
"""
================================================================================
MANEVRA TEŞHİSİ — sert manevra anında güdümde NE kopuyor?
================================================================================
`manevra.py` senaryosu için. Kayıpları üçe ayırmanın (kadraj dışı / dedektör
kör / kapı eledi) üstüne, MANEVRA EVRESİNE göre ayrıştırır:

    boş   : hedef kendi rotasında (devralma yok, kanatlar sağlam)
    hafif : menzil <= 45 m, faz != GORSEL, yatış ~20°
    sert  : faz == GORSEL, yatış ~35°

⭐ NEDEN EVREYE GÖRE: hedefin yatışı tespiti belirliyor (ölçüldü: düz %90,
   25-40° %49). Evreleri karıştıran bir ortalama, "güdüm mü görüş mü"
   sorusunu cevaplayamaz.

⚠ TEPKİ GECİKMESİ: sert evre başladıktan sonra güdümün nişanı ne kadar
   sürede toparladığı ölçülür — manevraya tepki hızının doğrudan ölçütü.

⛔ HÜKÜM ARACI DEĞİL, TEŞHİS ARACI (§2): buradan İYİLEŞTİRME FİKRİ çıkar;
   kabul kararını taze uçuş A/B'si verir.

Kullanım: python3 araclar/manevra_teshis.py logs/KM1
================================================================================
"""
import argparse
import bisect
import csv
import glob
import json
import math
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)          # doğrudan çalıştırıldığında da bulunsun
from araclar.arka import ArkaBekci
IMG_W, IMG_H = 1920.0, 1080.0


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def evre_serisi(kdizin):
    """manevra.json olaylarından (t, evre) sıralı liste."""
    y = os.path.join(kdizin, "manevra.json")
    if not os.path.exists(y):
        return [], []
    d = json.load(open(y))
    ts = [e["t"] for e in d.get("olaylar", [])]
    ev = [e["evre"] for e in d.get("olaylar", [])]
    return ts, ev


def evre_bul(ts, ev, t):
    if not ts:
        return "?"
    i = bisect.bisect_right(ts, t) - 1
    return ev[i] if i >= 0 else "bos"


def kollar(kok):
    out = {}
    for d in sorted(glob.glob(os.path.join(KOK, kok, "*__t*"))):
        out.setdefault(os.path.basename(d).split("__")[0], []).append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KM1")
    ap.add_argument("--menzil", type=float, default=40.0)
    a = ap.parse_args()
    K = kollar(a.kok)
    if not K:
        print("⛔ koşu yok: %s" % a.kok)
        return

    print("\n" + "=" * 76)
    print("  MANEVRA TEŞHİSİ — %s  (menzil < %.0f m)" % (a.kok, a.menzil))
    print("=" * 76)

    # ---------- 1) EVREYE GÖRE TESPİT + KAYIP SEBEBİ ----------
    print("\n  EVREYE GÖRE — A=kadraj dışı(GÜDÜM) B=dedektör kör(MODEL) "
          "C=kapı(BİZİM KOD)")
    print("  ⭐ ARK = hedef ARKAMIZDA (üstünden geçtik) — KAYIP DEĞİL.")
    print("     Bu kova ayrılmazsa geçiş geometrisi güdüm kusuru sanılır;")
    print("     ölçüldü: manevralı kolda kayıpların %47'si, manevrasızda %0.")
    print("  %-10s %-7s %6s %8s | %5s %5s %5s %6s %5s %8s"
          % ("kol", "evre", "kare*", "tespit%", "A", "B", "C", "gec_red",
             "ARK", "hedef|roll|"))
    print("  " + "-" * 78)
    for kol in sorted(K):
        for evre in ("bos", "hafif", "sert"):
            n = ok = A = B = C = GR = ARK = 0
            rl = []
            for d in K[kol]:
                y = os.path.join(d, "k01", "cikarim.csv")
                if not os.path.exists(y):
                    continue
                ts, ev = evre_serisi(d)
                ab = ArkaBekci(d)
                R0 = list(csv.DictReader(open(y)))
                if not R0:
                    continue
                t0 = _f(R0[0], "t") or 0.0
                for r in R0:
                    m = _f(r, "menzil3_m") or _f(r, "menzil_m")
                    t = _f(r, "t")
                    if m is None or t is None or m > a.menzil:
                        continue
                    if evre_bul(ts, ev, t - t0) != evre:
                        continue
                    # ⭐ ARKA KOVA: hedefin üstünden geçtiğimiz kareler
                    #   payda dışı bırakılır — "kayıp" değiller.
                    if ab.var and ab.arkada(t):
                        ARK += 1
                        continue
                    n += 1
                    hr = _f(r, "hedef_roll")
                    if hr is not None:
                        rl.append(abs(hr))
                    if r.get("basarili") == "1":
                        ok += 1
                        continue
                    bx, by = _f(r, "bek_cx"), _f(r, "bek_cy")
                    ad = _f(r, "yerel_aday") or 0
                    uy = _f(r, "yerel_uygun") or 0
                    if bx is not None and by is not None and \
                       not (0 <= bx < IMG_W and 0 <= by < IMG_H):
                        A += 1
                    elif ad == 0:
                        B += 1
                    elif uy == 0:
                        C += 1
                    else:
                        GR += 1
            if n >= 10:
                print("  %-10s %-7s %6d %7.1f%% | %5d %5d %5d %6d %5d %7s"
                      % (kol, evre, n, 100.0 * ok / n, A, B, C, GR, ARK,
                         "%.0f°" % st.median(rl) if rl else "—"))

    # ---------- 2) SERT EVREYE TEPKİ ----------
    print("\n  SERT EVREYE TEPKİ — manevra başlayınca güdüm ne yapıyor?")
    print("  %-10s %10s %12s %12s %12s"
          % ("kol", "sert olay", "|cx| önce", "|cx| sonra 1s", "kutu yaşı+1s"))
    print("  " + "-" * 60)
    for kol in sorted(K):
        onc, son, yas = [], [], []
        olay = 0
        for d in K[kol]:
            y = os.path.join(d, "k01", "cikarim.csv")
            if not os.path.exists(y):
                continue
            ts, ev = evre_serisi(d)
            R0 = list(csv.DictReader(open(y)))
            if not R0 or not ts:
                continue
            t0 = _f(R0[0], "t") or 0.0
            for i, (tt, ee) in enumerate(zip(ts, ev)):
                if ee != "sert":
                    continue
                olay += 1
                for r in R0:
                    t = _f(r, "t")
                    if t is None:
                        continue
                    dt = (t - t0) - tt
                    cx = _f(r, "vis_cx")
                    if r.get("basarili") != "1" or cx is None:
                        continue
                    if -0.8 <= dt < 0.0:
                        onc.append(abs(cx - 960.0))
                    elif 0.5 <= dt <= 1.5:
                        son.append(abs(cx - 960.0))
                        vy = _f(r, "vis_yas")
                        if vy is not None:
                            yas.append(vy)
        if olay:
            print("  %-10s %10d %12s %12s %12s"
                  % (kol, olay,
                     "%.0f px" % st.median(onc) if onc else "—",
                     "%.0f px" % st.median(son) if son else "—",
                     "%.2f s" % st.median(yas) if yas else "—"))
    print("""
  OKUMA:
    |cx| sonra >> önce  -> güdüm manevraya YETİŞEMİYOR (nişan kaçtı)
    kutu yaşı büyük     -> güdüm ESKİ kutuya nişan alıyor (kör tepki)
    C/gec_red büyük     -> dedektör buluyor ama BİZ atıyoruz
""")


if __name__ == "__main__":
    main()
