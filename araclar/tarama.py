# -*- coding: utf-8 -*-
"""PARAMETRE TARAMASI: bir ayarı birkaç değerde koş, karşılaştır.
Kullanım: python3 araclar/tarama.py <ad> <AYAR> <d1,d2,...> <tekrar> <sure_s>
Ayrıca her koşuda TESPİT oranını da ölçer (dedektör panelde açıksa)."""
import csv, os, sys
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
    degerler = [float(x) for x in sys.argv[3].split(",")]
    tekrar = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    sure   = float(sys.argv[5]) if len(sys.argv) > 5 else 60.0
    kok = os.path.join("logs", ad); os.makedirs(kok, exist_ok=True)
    sct = mss.mss()
    ok, img0 = hazirla(sct)
    print(f"hazırlık: {'UÇUŞTA' if ok else 'BAŞARISIZ'}", flush=True)
    if not ok: sys.exit(1)
    det = None
    if Ayar.GORSEL_AKTIF or Ayar.DEDEKTOR_GOSTER:
        from dow.gorus.dedektor import Dedektor
        det = Dedektor(); det.isit(img0)
        print(f"dedektör: {'GÜDÜMDE' if Ayar.GORSEL_AKTIF else 'yalnız PANELDE'}", flush=True)
    beyin = Beyin(dedektor=det if Ayar.GORSEL_AKTIF else None)
    if not beyin.b.baglan(): print("SDK yok"); sys.exit(1)

    print(f"\nTARAMA {alan}: {degerler} x{tekrar} x {sure:.0f}s", flush=True)
    print(f"{'#':>3} {alan:>10} {'ihlal':>12} {'ist_hata':>9} {'min':>7} "
          f"{'oturma':>7} {'≤15m%':>6} {'menzil':>7} {'tespit%':>8} {'kutu px':>8}", flush=True)
    ozet=[]; i=0
    # DÖNÜŞÜMLÜ: her tekrar turunda tüm değerler sırayla (sim kayması eşit dağılsın)
    for tur in range(tekrar):
        for dv in degerler:
            i += 1
            setattr(Ayar, alan, dv)
            if not _yeni_gorev(beyin): print(f"{i:3d} görev yok"); continue
            if not beyin.b.canli(): beyin.b.yeniden_bagla()
            dz = os.path.join(kok, f"d{int(dv):03d}_{tur+1}")
            o = kosu_yap(beyin, sct, dz, sure, det)
            # kayıttan tespit ve menzil istatistiği
            tp, kutu, mz = 0.0, 0.0, 0.0
            try:
                rows=list(csv.DictReader(open(os.path.join(dz,"meta.csv"))))
                rows=[r for r in rows if r.get("durum")=="ISTASYON"]
                if rows:
                    cf=[float(r["vis_conf"]) for r in rows if r.get("vis_conf")]
                    tp=100.0*len(cf)/len(rows)
                    kb=[float(r["vis_w"]) for r in rows if r.get("vis_w")]
                    kutu=float(np.median(kb)) if kb else 0.0
                    m=[float(r["hedef_menzil_m"]) for r in rows if r.get("hedef_menzil_m")]
                    mz=float(np.median(m)) if m else 0.0
            except Exception: pass
            o.update({"kosu":i, alan:dv, "tespit_yuzde":round(tp,1),
                      "kutu_px":round(kutu,1), "menzil_med":round(mz,1)})
            ozet.append(o)
            print(f"{i:3d} {dv:10.1f} {o['ihlal']:>12} {o['ist_hata_medyan']:9.2f} "
                  f"{o['ist_hata_min']:7.2f} {o['oturma_s']:7.1f} "
                  f"{100*o['ist_orani_15m']:6.1f} {mz:7.1f} {tp:8.1f} {kutu:8.1f}", flush=True)
    if ozet:
        with open(os.path.join(kok,"ozet.csv"),"w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(ozet[0].keys())); w.writeheader(); w.writerows(ozet)
        print(f"\n=== ÖZET ({alan}) ===")
        print(f"{alan:>10} {'n':>3} {'ist_hata':>9} {'≤15m%':>6} {'menzil':>7} {'tespit%':>8} {'kutu px':>8}")
        for dv in degerler:
            g=[o for o in ozet if o[alan]==dv and o["ihlal"]=="-"]
            if not g: print(f"{dv:10.1f}  geçerli koşu YOK"); continue
            m=np.array([o["ist_hata_medyan"] for o in g])
            print(f"{dv:10.1f} {len(g):3d} {np.median(m):9.2f} "
                  f"{100*np.median([o['ist_orani_15m'] for o in g]):6.1f} "
                  f"{np.median([o['menzil_med'] for o in g]):7.1f} "
                  f"{np.median([o['tespit_yuzde'] for o in g]):8.1f} "
                  f"{np.median([o['kutu_px'] for o in g]):8.1f}")
        print(f"⚠ n={tekrar}/değer — §5.4: n<4 ise ARA VERİ, hüküm değil")
    beyin.b.kapat()

if __name__ == "__main__":
    main()
