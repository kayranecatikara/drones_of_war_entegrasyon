# -*- coding: utf-8 -*-
"""
================================================================================
BOŞLUK ÖLÇÜMÜ — tespit kesintileri ve KISA ufukta öngörü mü dondurma mı?
================================================================================
NEDEN GEREKTİ: meta.csv 2 Hz. 9 Hz çıkarımda %54 başarıyla ortalama boşluk
1.85 çıkarım ≈ 0.2 s — yani ASIL OLAY meta.csv'nin örnekleme aralığının
ALTINDA (§5.3: ölçüt, ölçtüğü şeyin en az 5 katı hızda örneklenmeli).
0.5 s ve üstünde "dondurma kazanır" diye ölçmüştüm; gerçek boşluklar oradan
KISA ve o bandı hiç ölçmemiştim. `cikarim.csv` bunu kapatır.

ÇIKTILAR
  1) boşluk uzunluğu dağılımı (kaç çıkarım / kaç saniye)
  2) boşluk sebebi: model bulamadı / kapı eledi / hedef kadraj dışı
  3) ⭐ boşluk süresince KONUM kestirimi: DONDUR vs İLERİ TAŞI, ufka göre
  4) aynısı BOYUT için
  5) hepsi hedefin ASPEKTİNE göre kırılmış (kuyruk/yan/kafa)
================================================================================
"""
import argparse, csv, glob, os, statistics as st, sys
import numpy as np


def oku(kok):
    K = []
    for d in sorted(glob.glob(os.path.join(kok, "*"))):
        p = os.path.join(d, "cikarim.csv")
        if not os.path.exists(p): continue
        S = []
        for r in csv.DictReader(open(p)):
            def f(k):
                try:
                    v = float(r[k]); return v if v == v else None
                except Exception: return None
            S.append(dict(t=f("t"), ok=int(float(r.get("basarili") or 0)),
                          durum=r.get("durum", ""),
                          cx=f("vis_cx"), cy=f("vis_cy"), w=f("vis_w"),
                          bx=f("bek_cx"), by=f("bek_cy"), bw=f("bek_w"),
                          aday=f("yerel_aday"), uygun=f("yerel_uygun"),
                          asp=f("aspekt_deg"), R=f("menzil_m")))
        if len(S) > 10: K.append((os.path.basename(d), S))
    return K


def bosluklar(S, faz="GORSEL"):
    """[(bas_idx, uzunluk_cikarim, sure_s)]"""
    out = []; i = 0
    G = [k for k in S if k["durum"].startswith(faz)]
    while i < len(G):
        if G[i]["ok"]:
            i += 1; continue
        j = i
        while j < len(G) and not G[j]["ok"]: j += 1
        if i > 0 and j < len(G):
            out.append((i, j - i, G[j]["t"] - G[i-1]["t"]))
        i = j
    return out, G


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kokler", nargs="+")
    a = ap.parse_args()
    K = []
    for kok in a.kokler: K += oku(kok)
    print("koşu: %d" % len(K))

    # --- 1) boşluk dağılımı ---
    hepsi = []; G_hepsi = []
    for ad, S in K:
        b, G = bosluklar(S); hepsi += b; G_hepsi += G
    if not G_hepsi:
        print("GORSEL fazda çıkarım yok"); sys.exit(0)
    basari = 100.0 * sum(k["ok"] for k in G_hepsi) / len(G_hepsi)
    print("\nGÖRSEL fazda çıkarım: %d  |  başarı %.1f%%  |  boşluk sayısı %d"
          % (len(G_hepsi), basari, len(hepsi)))
    if hepsi:
        u = sorted(x[1] for x in hepsi); s = sorted(x[2] for x in hepsi)
        print("boşluk UZUNLUĞU (çıkarım): medyan %.0f  p90 %.0f  maks %.0f"
              % (st.median(u), np.percentile(u, 90), max(u)))
        print("boşluk SÜRESİ  (saniye) : medyan %.2f  p90 %.2f  maks %.2f"
              % (st.median(s), np.percentile(s, 90), max(s)))
        for esik in (0.15, 0.3, 0.5, 1.0):
            pay = 100.0 * sum(1 for x in s if x <= esik) / len(s)
            sure = 100.0 * sum(x for x in s if x <= esik) / max(1e-9, sum(s))
            print("   <= %.2f s olan boşluklar: sayıca %%%.0f, TOPLAM KÖR SÜRENİN %%%.0f'i"
                  % (esik, pay, sure))

    # --- 2) sebep ---
    kd = mb = ke = dg = 0
    for k in G_hepsi:
        if k["ok"]: continue
        if k["bx"] is None or not (0 <= k["bx"] < 1920 and 0 <= (k["by"] or -1) < 1080): kd += 1
        elif (k["aday"] or 0) == 0: mb += 1
        elif (k["uygun"] or 0) == 0: ke += 1
        else: dg += 1
    n = max(1, kd + mb + ke + dg)
    print("\nBAŞARISIZ ÇIKARIMIN SEBEBİ (n=%d): kadraj dışı %%%.1f | MODEL bulamadı %%%.1f"
          " | KAPI eledi %%%.1f | diğer %%%.1f" % (n, 100*kd/n, 100*mb/n, 100*ke/n, 100*dg/n))

    # --- 3/4) ⭐ KISA UFUKTA DONDUR vs İLERİ TAŞI ---
    print("\n⭐ BOŞLUK SÜRESİNCE KESTİRİM (truth ile): DONDUR mu İLERİ TAŞI mı?")
    print("%-12s %6s | %-22s | %-22s" % ("ufuk","n","KONUM hata medyan (px)","BOYUT hata medyan (px)"))
    print("%-12s %6s | %10s %10s | %10s %10s" % ("","","dondur","ileri","dondur","1/w ileri"))
    kova = {}
    for ad, S in K:
        G = [k for k in S if k["durum"].startswith("GORSEL")]
        for i in range(2, len(G)):
            if not (G[i-2]["ok"] and G[i-1]["ok"]): continue
            p2, p1 = G[i-2], G[i-1]
            dt = p1["t"] - p2["t"]
            if not (0.02 < dt < 0.5): continue
            vx = (p1["cx"]-p2["cx"])/dt; vy = (p1["cy"]-p2["cy"])/dt
            s1, s2 = 1.0/max(p1["w"],1), 1.0/max(p2["w"],1)
            vs = (s1-s2)/dt
            for j in range(i, min(i+12, len(G))):
                g = G[j]
                if g["bx"] is None or g["bw"] is None: continue
                D = g["t"] - p1["t"]
                if D <= 0 or D > 1.2: continue
                key = round(min(D, 1.2)/0.1)*0.1
                don_p = np.hypot(g["bx"]-p1["cx"], g["by"]-p1["cy"])
                il_p  = np.hypot(g["bx"]-(p1["cx"]+vx*D), g["by"]-(p1["cy"]+vy*D))
                sp = max(s1 + vs*D, s1/3.0); sp = min(sp, s1*3.0)
                don_w = abs(g["bw"] - p1["w"]); il_w = abs(g["bw"] - 1.0/max(sp,1e-9))
                kova.setdefault(key, []).append((don_p, il_p, don_w, il_w))
    for key in sorted(kova):
        v = kova[key]
        if len(v) < 10: continue
        print("%-12.1f %6d | %10.0f %10.0f | %10.0f %10.0f" % (key, len(v),
              st.median([x[0] for x in v]), st.median([x[1] for x in v]),
              st.median([x[2] for x in v]), st.median([x[3] for x in v])))

    # --- 5) aspekt kırılımı ---
    print("\nBAŞARI — hedefin ASPEKTİNE göre (0°=kuyruk, 180°=kafa kafaya)")
    print("%-14s %7s %10s" % ("aspekt","n","başarı%"))
    for lo, hi in ((0,20),(20,45),(45,90),(90,180)):
        g = [k for k in G_hepsi if k["asp"] is not None and lo <= k["asp"] < hi]
        if len(g) < 10: continue
        print("%-14s %7d %10.1f" % ("%d-%d°"%(lo,hi), len(g),
              100.0*sum(k["ok"] for k in g)/len(g)))
