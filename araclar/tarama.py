# -*- coding: utf-8 -*-
"""
================================================================================
PARAMETRE TARAMASI — bir ya da İKİ ayarı birlikte, dönüşümlü koş
================================================================================
    python3 araclar/tarama.py <ad> <ALAN[,ALAN2]> <d1[/e1],d2[/e2],...> <tekrar> <sure>

ALAN adı `IBVS.` ile başlarsa `dow.gudum.ibvs.IbvsCfg` alanı, yoksa
`dow.ayarlar.Ayar` alanı değiştirilir. Örnek:
    python3 araclar/tarama.py B2 IBVS.KOPRU_S 0,1.0 4 120

Örnek (istasyon geometrisi 3x2 ızgarası):
    python3 araclar/tarama.py GK ISTASYON_MENZIL_M,ISTASYON_ALT_ORAN \
        15/0.45,11/0.45,8/0.45,15/0.75,11/0.75,8/0.75 2 45

DÖNÜŞÜMLÜ (CLAUDE.md §4): her tekrar turunda TÜM değerler sırayla koşulur —
sim kayması bütün kolları eşit etkilesin diye. Bir kolun hepsini arka arkaya
koşmak yasak.

Her koşu için GERÇEK TESPİT oranı da ölçülür (araclar/tespit_olcu.py) —
ham "kutu var mı" oranı yanlış-pozitifi ödüllendirdiği için tek başına
raporlanmaz.
================================================================================
"""
import csv, os, sys, threading, time
import numpy as np, mss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.ayarlar import Ayar
from dow.ana import Beyin
from dow import panel as PANEL
from araclar.kadraj import hazirla
from araclar.kosu import (kosu_yap, _yeni_gorev, _saglikli, _gorus_isi,
                          _gorus_isp, gorus_durdur, _son_kare)
from araclar.tespit_olcu import olc


def _ayarla(alan, v):
    """`IBVS.X` -> IbvsCfg.X, `DET.X` -> DetCfg.X, aksi halde Ayar.X.
    Bool alanlar 0/1 ile verilir."""
    from dow.gudum import ibvs as _I
    from dow.gorus.dedektor import DetCfg as _D
    from dow.gorus.iz import IzCfg as _Z
    if alan.startswith("IBVS."):   hedef, ad = _I.IbvsCfg, alan[5:]
    elif alan.startswith("DET."):  hedef, ad = _D, alan[4:]
    elif alan.startswith("IZ."):   hedef, ad = _Z, alan[3:]
    else:                          hedef, ad = Ayar, alan
    assert hasattr(hedef, ad), f"bilinmeyen alan: {alan}"
    eski = getattr(hedef, ad)
    if isinstance(eski, bool):  setattr(hedef, ad, bool(v))
    elif isinstance(eski, int): setattr(hedef, ad, int(v))
    else:                       setattr(hedef, ad, v)


def main():
    ad = sys.argv[1]
    alanlar = sys.argv[2].split(",")
    def _cev(x):
        try: return float(x)
        except ValueError: return x        # metin alanlar (ör. DIKEY_YASA)
    kombolar = [tuple(_cev(x) for x in p.split("/")) for p in sys.argv[3].split(",")]
    assert all(len(k) == len(alanlar) for k in kombolar), "kombo/alan sayısı uyuşmuyor"
    tekrar = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    sure = float(sys.argv[5]) if len(sys.argv) > 5 else 60.0
    etiket = lambda k: "/".join((f"{v:g}" if isinstance(v, float) else str(v))
                                for v in k)

    kok = os.path.join("logs", ad); os.makedirs(kok, exist_ok=True)
    sct = mss.mss()
    ok, img0 = hazirla(sct)
    print(f"hazırlık: {'UÇUŞTA' if ok else 'BAŞARISIZ'}", flush=True)
    if not ok: sys.exit(1)

    det = None
    if Ayar.GORSEL_AKTIF or Ayar.DEDEKTOR_GOSTER:
        from dow.gorus.dedektor import Dedektor
        det = Dedektor(); det.isit(img0)
        print(f"dedektör: {'GÜDÜMDE' if Ayar.GORSEL_AKTIF else 'yalnız PANELDE'}",
              flush=True)

    PANEL.baslat(8801)
    print(f"panel: http://127.0.0.1:8801  (yakalama tavanı "
          f"{Ayar.PANEL_YAKALA_HZ:.0f} Hz, dedektör tavanı "
          f"{Ayar.PANEL_DET_HZ:.0f} Hz)", flush=True)
    _gorus_isp[0] = threading.Thread(target=_gorus_isi, args=(det,), daemon=True)
    _gorus_isp[0].start()
    for _ in range(100):
        if _son_kare()[0] is not None: break
        time.sleep(0.05)

    beyin = Beyin(dedektor=det if Ayar.GORSEL_AKTIF else None)
    if not beyin.b.baglan(): print("SDK yok"); sys.exit(1)

    top = len(kombolar) * tekrar
    print(f"\nTARAMA {'/'.join(alanlar)}: {[etiket(k) for k in kombolar]} "
          f"x{tekrar} x {sure:.0f}s  = {top} koşu", flush=True)
    bas = f"{'#':>3} {'kombo':>10} {'ihlal':>12} {'EN YAKIN':>9} {'isabet':>7} " \
          f"{'tespit%':>8} {'gorsel_s':>9} {'kesinti':>8} {'rollp90':>8} " \
          f"{'ist_hata':>9} {'devir@':>7} {'tik_hz':>7}"
    print(bas, flush=True)
    ozet = []; i = 0
    for tur in range(tekrar):
        for kombo in kombolar:
            i += 1
            for alan, v in zip(alanlar, kombo):
                _ayarla(alan, v)
            if not _saglikli(beyin) or not _yeni_gorev(beyin) \
                    or not _saglikli(beyin):
                print(f"{i:3d} {etiket(kombo):>10}  sim hazır değil — ATLANDI",
                      flush=True)
                continue
            dz = os.path.join(kok, f"{etiket(kombo).replace('/', '_')}__t{tur+1}")
            o = kosu_yap(beyin, sct, dz, sure, det)
            t = olc(os.path.join(dz, "meta.csv")) or {}
            mz = 0.0
            try:
                rows = [r for r in csv.DictReader(open(os.path.join(dz, "meta.csv")))
                        if r.get("durum") == "ISTASYON" and r.get("hedef_menzil_m")]
                mz = float(np.median([float(r["hedef_menzil_m"]) for r in rows])) if rows else 0.0
            except Exception: pass
            R = (kombo[0] if (alanlar[0] == "ISTASYON_MENZIL_M"
                              and isinstance(kombo[0], float)) else float("nan"))
            ihR = o["ist_hata_medyan"] / R if R == R and R else float("nan")
            o.update({"kosu": i, "kombo": etiket(kombo), "tur": tur + 1,
                      "menzil_med": round(mz, 1), "ih_bolu_R": round(ihR, 2)})
            o.update(t)
            ozet.append(o)
            print(f"{i:3d} {etiket(kombo):>10} {o['ihlal']:>12} "
                  f"{o['en_yakin_m']:9.2f} {'EVET' if o['isabet'] else '-':>7} "
                  f"{o.get('gorsel_tespit_yuzde',0):8.1f} {o.get('gorsel_s',0):9.1f} "
                  f"{o.get('kesinti_s',0):8.1f} {o.get('roll_p90',float('nan')):8.1f} "
                  f"{o['ist_hata_medyan']:9.2f} {o['devir_menzil']:7.1f} "
                  f"{o.get('tik_hz',0):7.1f}", flush=True)
            with open(os.path.join(kok, "ozet.csv"), "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(ozet[0].keys()),
                                   extrasaction="ignore")
                w.writeheader(); w.writerows(ozet)

    gorus_durdur()
    if ozet:
        print(f"\n=== ÖZET ({'/'.join(alanlar)}) — medyanlar ===")
        print(f"{'kombo':>10} {'n':>3} {'ist_hata':>9} {'ih/R':>5} {'kutu':>6} "
              f"{'kadraj%':>8} {'gök%':>6} {'HAM%':>6} {'GERÇEK%':>8} {'yanlış%':>8}")
        for kombo in kombolar:
            e = etiket(kombo)
            g = [o for o in ozet if o["kombo"] == e and o["ihlal"] == "-"]
            if not g:
                print(f"{e:>10}   0   (geçerli koşu yok)"); continue
            m = lambda k: float(np.nanmedian([o.get(k, np.nan) for o in g]))
            print(f"{e:>10} {len(g):3d} {m('ist_hata_medyan'):9.2f} "
                  f"{m('ih_bolu_R'):5.2f} {m('kutu_beklenen_px'):6.1f} "
                  f"{m('kadraj_yuzde'):8.1f} {m('ufuk_ustu_yuzde'):6.1f} "
                  f"{m('ham_yuzde'):6.1f} {m('gercek_yuzde'):8.1f} "
                  f"{m('yanlis_yuzde'):8.1f}")
    beyin.b.kapat()


if __name__ == "__main__":
    main()
