# -*- coding: utf-8 -*-
"""DÖNÜŞÜMLÜ A/B kampanyası (CLAUDE.md §4): tek değişken, kollar dönüşümlü.
Kullanım: python3 araclar/ab.py <ad> <AYAR_ADI> <cift_sayisi> <sure_s>"""
import csv, os, sys, time
import numpy as np, mss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.ayarlar import Ayar
from dow.ana import Beyin
from dow import panel as PANEL
from araclar.kadraj import hazirla
from araclar.kosu import kosu_yap, _yeni_gorev

def main():
    ad   = sys.argv[1]
    alan = sys.argv[2]
    cift = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    sure = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0
    kok = os.path.join("logs", ad); os.makedirs(kok, exist_ok=True)
    sct = mss.mss()
    ok, _ = hazirla(sct)
    print(f"hazırlık: {'UÇUŞTA' if ok else 'BAŞARISIZ'}", flush=True)
    if not ok: sys.exit(1)
    det = None
    if Ayar.GORSEL_AKTIF or Ayar.DEDEKTOR_GOSTER:
        from dow.gorus.dedektor import Dedektor
        det = Dedektor(); det.isit(_)
        print(f"dedektör: {'GÜDÜMDE' if Ayar.GORSEL_AKTIF else 'yalnız PANELDE'}", flush=True)
    beyin = Beyin(dedektor=det if Ayar.GORSEL_AKTIF else None)
    if not beyin.b.baglan(): print("SDK yok"); sys.exit(1)

    print(f"\nA/B: {alan} | {cift} çift x {sure:.0f} s | DÖNÜŞÜMLÜ", flush=True)
    print(f"{'#':>3} {'kol':>4} {'ihlal':>15} {'ist_hata med':>13} {'min':>7} "
          f"{'oturma':>7} {'≤15m %':>7}", flush=True)
    ozet=[]; i=0
    for c in range(cift):
        for kol, deger in (("K", False), ("D", True)):
            i += 1
            setattr(Ayar, alan, deger)
            if not _yeni_gorev(): print(f"{i:3d} görev yok"); continue
            if not beyin.b.canli(): beyin.b.yeniden_bagla()
            o = kosu_yap(beyin, sct, os.path.join(kok, f"{kol}{i:02d}"), sure, det)
            o["kosu"]=i; o["kol"]=kol; o[alan]=int(deger); ozet.append(o)
            print(f"{i:3d} {kol:>4} {o['ihlal']:>15} {o['ist_hata_medyan']:13.2f} "
                  f"{o['ist_hata_min']:7.2f} {o['oturma_s']:7.1f} "
                  f"{100*o['ist_orani_15m']:7.1f}", flush=True)
    if ozet:
        with open(os.path.join(kok,"ozet.csv"),"w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(ozet[0].keys())); w.writeheader(); w.writerows(ozet)
        print("\n=== KARAR ===")
        for kol,et in (("K","KAPALI"),("D","AÇIK  ")):
            g=[o for o in ozet if o["kol"]==kol and o["ihlal"]=="-"]
            if not g: print(f"{et}: geçerli koşu YOK"); continue
            m=np.array([o["ist_hata_medyan"] for o in g])
            p=np.array([o["ist_orani_15m"] for o in g])
            ot=np.array([o["oturma_s"] for o in g])
            print(f"{et}: n={len(g)} | ist_hata {np.median(m):.2f} m "
                  f"(min {m.min():.2f}, max {m.max():.2f}) | ≤15m %{100*np.median(p):.0f} "
                  f"| oturma {np.median(ot):.1f} s")
        gk=[o["ist_hata_medyan"] for o in ozet if o["kol"]=="K" and o["ihlal"]=="-"]
        gd=[o["ist_hata_medyan"] for o in ozet if o["kol"]=="D" and o["ihlal"]=="-"]
        if gk and gd:
            print(f"\nfark: {np.median(gd)-np.median(gk):+.2f} m "
                  f"({100*(np.median(gd)-np.median(gk))/np.median(gk):+.0f}%)")
            print(f"⚠ n={min(len(gk),len(gd))}/kol — §5.4: n<4 ise ARA VERİ, hüküm değil")
    beyin.b.kapat()

if __name__ == "__main__":
    main()
