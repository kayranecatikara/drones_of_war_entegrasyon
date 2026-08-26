# -*- coding: utf-8 -*-
"""
================================================================================
DESEN TEŞHİSİ — hedef sürekli dönerken güdüm NEREDE kaybediyor?
================================================================================
`kayip_teshis.py` kayıpları üçe ayırır (kadraj dışı / dedektör kör / kapı).
Bu araç aynı ayrımı DESEN senaryolarında yapar ve üstüne SÜREKLİ MANEVRAYA
özgü iki şey ekler:

  1. ASPEKT-TESPİT EĞRİSİ — hedefin bize gösterdiği yüz ile tespit oranı.
     KC1'de bulundu: kuyrukta %56-74, yanda %6-46, kafada %4-19.
     Sürekli dönüşte aspekt SÜREKLİ kayar; eğri burada daha da belirleyici.

  2. AÇISAL HIZ — hedefin kadrajdaki görünür hareket hızı (px/s).
     Dairede LOS dönüş hızı sabit ve sıfırdan büyüktür; güdümün bunu takip
     edip edemediği doğrudan ölçülür.

⛔ HÜKÜM ARACI DEĞİL, TEŞHİS ARACI. Buradan çıkan sayılar İYİLEŞTİRME FİKRİ
   üretir; kabul kararını taze uçuş A/B'si verir (§2).

Kullanım: python3 araclar/desen_teshis.py logs/KD1
================================================================================
"""
import argparse
import csv
import glob
import math
import os
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_W, IMG_H = 1920.0, 1080.0


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def kollar(kok):
    """logs/<kok>/<desen>__t<n>/k01 -> {desen: [dizin, ...]}"""
    out = {}
    for d in sorted(glob.glob(os.path.join(KOK, kok, "*__t*"))):
        ad = os.path.basename(d).split("__")[0]
        out.setdefault(ad, []).append(d)
    return out


def satirlar(dizinler, menzil_ust=40.0):
    for d in dizinler:
        y = os.path.join(d, "k01", "cikarim.csv")
        if not os.path.exists(y):
            continue
        for r in csv.DictReader(open(y)):
            m = _f(r, "menzil3_m") or _f(r, "menzil_m")
            if m is None or m > menzil_ust:
                continue
            yield r, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KD1")
    ap.add_argument("--menzil", type=float, default=40.0)
    a = ap.parse_args()
    K = kollar(a.kok)
    if not K:
        print("⛔ koşu bulunamadı: %s" % a.kok)
        return
    adlar = [x for x in ("taban", "kare", "daire") if x in K] or sorted(K)

    # ---------- 1) KAYIP SEBEBİ ----------
    print("\n" + "=" * 76)
    print("  DESEN TEŞHİSİ — %s   (yalnız menzil < %.0f m)" % (a.kok, a.menzil))
    print("=" * 76)
    print("\n  KAYIP SEBEBİ")
    print("  A=kadraj dışı(GÜDÜM)  B=dedektör kutu ÜRETMEDİ(MODEL)  "
          "C=kapı ELEDİ(BİZİM KOD)")
    print("  %-10s %6s %8s | %6s %6s %6s %10s"
          % ("desen", "kare", "tespit%", "A", "B", "C", "gecerli_red"))
    print("  " + "-" * 62)
    for ad in adlar:
        n = ok = A = B = C = GR = 0
        for r, m in satirlar(K[ad], a.menzil):
            n += 1
            if r.get("basarili") == "1":
                ok += 1
                continue
            bx, by = _f(r, "bek_cx"), _f(r, "bek_cy")
            aday = _f(r, "yerel_aday") or 0
            uyg = _f(r, "yerel_uygun") or 0
            if bx is not None and by is not None and \
               not (0 <= bx < IMG_W and 0 <= by < IMG_H):
                A += 1
            elif aday == 0:
                B += 1
            elif uyg == 0:
                C += 1
            else:
                GR += 1
        if n:
            print("  %-10s %6d %7.1f%% | %6d %6d %6d %10d"
                  % (ad, n, 100.0 * ok / n, A, B, C, GR))

    # ---------- 2) ASPEKT-TESPİT EĞRİSİ ----------
    BANT = [(0, 20), (20, 40), (40, 60), (60, 90), (90, 180)]
    print("\n  ASPEKT-TESPİT EĞRİSİ  (0°=kuyruk · 90°=yan · 180°=kafa kafaya)")
    print("  %-10s %11s %11s %11s %11s %11s"
          % ("desen", "0-20 kuyruk", "20-40", "40-60", "60-90 yan", "90+ kafa"))
    print("  " + "-" * 70)
    for ad in adlar:
        T = {b: [0, 0] for b in BANT}
        for r, m in satirlar(K[ad], a.menzil):
            asp = _f(r, "aspekt_deg")
            if asp is None:
                continue
            b = next((x for x in BANT if x[0] <= abs(asp) < x[1]), None)
            if not b:
                continue
            T[b][1] += 1
            if r.get("basarili") == "1":
                T[b][0] += 1
        hu = []
        for b in BANT:
            o, nn = T[b]
            hu.append("%.0f%% (%d)" % (100.0 * o / nn, nn) if nn >= 5 else "—")
        print("  %-10s %11s %11s %11s %11s %11s" % (ad, *hu))

    print("\n  ASPEKT DAĞILIMI — desen hedefi hangi açıya sokuyor")
    print("  %-10s %11s %11s %11s %11s %11s"
          % ("desen", "0-20", "20-40", "40-60", "60-90", "90+"))
    print("  " + "-" * 70)
    for ad in adlar:
        T = {b: 0 for b in BANT}
        top = 0
        for r, m in satirlar(K[ad], a.menzil):
            asp = _f(r, "aspekt_deg")
            if asp is None:
                continue
            b = next((x for x in BANT if x[0] <= abs(asp) < x[1]), None)
            if b:
                T[b] += 1
                top += 1
        if top:
            print("  %-10s %11s %11s %11s %11s %11s"
                  % (ad, *["%.0f%%" % (100.0 * T[b] / top) for b in BANT]))

    # ---------- 3) AÇISAL HIZ + KADRAJ ----------
    print("\n  KADRAJ DAVRANIŞI  (yalnız KABUL EDİLEN kutular)")
    print("  %-10s %12s %12s %12s %12s"
          % ("desen", "|cx-960| med", "cy med", "kutu px med", "px/s med"))
    print("  " + "-" * 62)
    for ad in adlar:
        cx = []
        cy = []
        w = []
        hiz = []
        for d in K[ad]:
            y = os.path.join(d, "k01", "cikarim.csv")
            if not os.path.exists(y):
                continue
            onc = None
            for r in csv.DictReader(open(y)):
                m = _f(r, "menzil3_m") or _f(r, "menzil_m")
                if m is None or m > a.menzil or r.get("basarili") != "1":
                    onc = None
                    continue
                X, Y, W, t = (_f(r, "vis_cx"), _f(r, "vis_cy"),
                              _f(r, "vis_w"), _f(r, "t"))
                if None in (X, Y, W, t):
                    onc = None
                    continue
                cx.append(abs(X - 960.0))
                cy.append(Y)
                w.append(W)
                if onc and t > onc[2]:
                    dt = t - onc[2]
                    if 0 < dt < 0.5:
                        hiz.append(math.hypot(X - onc[0], Y - onc[1]) / dt)
                onc = (X, Y, t)
        if cx:
            print("  %-10s %12.0f %12.0f %12.0f %12s"
                  % (ad, st.median(cx), st.median(cy), st.median(w),
                     "%.0f" % st.median(hiz) if hiz else "—"))
    print("""
  OKUMA:
    |cx-960| büyük -> hedef kadrajda YANDA, güdüm merkeze alamıyor
    cy < 540       -> hedef merkezin ÜSTÜNDE (kamera 26.5° aşağı eğik)
    px/s büyük     -> hedef kadrajda HIZLI kayıyor; dedektör+güdüm yetişemez
""")


if __name__ == "__main__":
    main()
