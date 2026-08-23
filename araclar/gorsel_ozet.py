# -*- coding: utf-8 -*-
"""
================================================================================
GÖRSEL KAMPANYA ÖZETİ — karar kuralı ve geçerlilik eşleriyle
================================================================================
    python3 araclar/gorsel_ozet.py logs/B1_TABAN [logs/B2_... ...]
    python3 araclar/gorsel_ozet.py --kol logs/B2_SAKIN     (kombo sütununa göre)

⛔ CLAUDE.md §4: "SALINIM ÖLÇÜLMEDEN 'İYİLEŞTİ' DENMEZ." Bu araç, isabet ve
en yakın menzilin YANINDA salınımı ve görsel temas sürekliliğini de basar;
biri olmadan diğeri raporlanmaz.

GECE İÇİN İLAN EDİLEN KARAR KURALI (koşmadan önce, §4):
  BİRİNCİL   : en_yakin_m MEDYANI (sürekli; n=4-6'da isabet sayımından
               çok daha ayırt edici)
  İKİNCİL    : isabet sayısı
  GEÇERLİLİK EŞLERİ (§5.2):
    en_yakin    <- savrulup ŞANS eseri yaklaşmayla iyileşebilir
                   => cx_donus_s, roll_p90 ve gorsel_tespit_yuzde zorunlu eş
    tespit%     <- hedefi kaybedince ölçülemez, sahte "sakin" görünür
                   => gorsel_s ve kesinti_s zorunlu eş
  MEKANİZMA KAPISI (§5.1): deney kolunun kendi sütunu sıfırsa koşu GEÇERSİZ
  KARAR      : en_yakin medyanı %20+ iyileşir VE salınım ölçütleri
               kötüleşmezse GİRER; kötüleşirse ya da belirsizse ELENİR /
               kullanıcıya bırakılır (§5.6 — ölçüt sonradan değiştirilmez)
  n<4 ise hüküm YOK, "ARA VERİ" (§5.4)
================================================================================
"""
import csv, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUT = [("n", None), ("temas", "sum"), ("sekme", "sum"), ("imha", "sum"),
       ("en_yakin_m", "med"),
       ("tespit%", "med"), ("dogru%", "med"), ("yanlis%", "med"),
       ("kadraj%", "med"), ("manevra%", "med"), ("hedef_w", "med"),
       ("gorsel_s", "med"), ("cx_donus_s", "med"), ("roll_p90", "med"),
       ("kesinti_s", "med"), ("devir_menzil", "med"),
       ("ist_hata_medyan", "med"), ("tik_hz", "med")]

# ÖLÇÜT AYRIMI (2026-08-22 gecesi, koşmadan önce ilan edildi)
#   tespit%  = `gorsel_tespit_yuzde`: ÇIKARIM başına dedektörün geçerli kutu
#              verme oranı. TABAN %31.25 -> bol yer var. T1/T2/T4/T6'nın
#              BİRİNCİL ölçütü (hepsi dedektörü kurtarmayı hedefliyor).
#   dogru%   = güdümün O AN kullandığı kutunun GERÇEKTEN hedefte olma oranı
#              (truth eşleşmeli, 0.5 s kayıt). TABAN %80.9. T5 köprüsünün
#              BİRİNCİL ölçütü (köprü çıkarımı değil, KULLANILAN kutuyu düzeltir).
#   yanlis%  = güdümün YANLIŞ yere nişan aldığı kare oranı. TABAN %19.1.
#   ⚠ GEÇERLİLİK EŞİ (§5.2): tespit% JUNK kutu kabul ederek de yükselebilir
#     (özellikle T4 yerellik kapısı). O yüzden dogru% DÜŞMEMELİ ve yanlis%
#     ARTMAMALI; üçü BİRLİKTE raporlanmadan hüküm kurulmaz.


def _oku(yol):
    kok = yol if os.path.isdir(yol) else os.path.dirname(yol)
    y = os.path.join(yol, "ozet.csv") if os.path.isdir(yol) else yol
    try:
        R = [r for r in csv.DictReader(open(y))]
    except OSError:
        return []
    # koşu dizinini bul: tarama.py "<kombo>__t<n>", kosu.py "k01"
    alt = sorted(d for d in os.listdir(kok)
                 if os.path.isdir(os.path.join(kok, d)))
    for i, r in enumerate(R):
        ad = None
        if "kombo" in r and "tur" in r:
            ad = f"{r['kombo'].replace('/', '_')}__t{r['tur']}"
        elif r.get("kosu"):
            ad = f"k{int(float(r['kosu'])):02d}"
        if ad and ad in alt:
            r["_dizin"] = os.path.join(kok, ad)
        elif i < len(alt):
            r["_dizin"] = os.path.join(kok, alt[i])
    _zenginlestir(R, kok)
    R2 = []
    for r in R:
        r = dict(r); r["tespit%"] = r.get("gorsel_tespit_yuzde")
        R2.append(r)
    return R2


def _sayi(g, k):
    out = []
    for r in g:
        try:
            v = float(r.get(k, "nan"))
            if v == v: out.append(v)
        except (TypeError, ValueError): pass
    return out


def _manevra(meta, esik=15.0):
    """GÖRSEL fazın yüzde kaçı hedef >esik °/s dönerken geçti + medyan dönüş."""
    import math
    try:
        R = [r for r in csv.reader(open(meta))]
    except OSError:
        return None, None
    if len(R) < 3: return None, None
    bas = R[0]
    try:
        iy, it, idu = bas.index("hedef_yaw"), bas.index("t"), bas.index("durum")
    except ValueError:
        return None, None
    G = [r for r in R[1:] if len(r) > max(iy, it, idu) and r[idu] == "GORSEL"]
    w = []
    for a, b in zip(G[:-1], G[1:]):
        try:
            ya, yb, ta, tb = float(a[iy]), float(b[iy]), float(a[it]), float(b[it])
        except ValueError:
            continue
        if tb <= ta: continue
        d = abs((yb - ya + 180) % 360 - 180) / (tb - ta)
        if d < 200: w.append(d)
    if not w: return None, None
    return (round(100.0 * sum(1 for x in w if x > esik) / len(w), 1),
            round(float(np.median(w)), 1))


def _zenginlestir(g, kok):
    """Her koşuya truth-eşleşmeli GÖRSEL FAZ ölçütlerini ekle."""
    from araclar.tespit_olcu import olc, temas_sinifla
    for r in g:
        d = r.get("_dizin")
        if not d: continue
        o = olc(os.path.join(d, "meta.csv"), "GORSEL")
        if o:
            r["dogru%"] = o["gercek_yuzde"]; r["yanlis%"] = o["yanlis_yuzde"]
            r["kadraj%"] = o["kadraj_yuzde"]
        # ⭐ C'NİN BİRİNCİL ÖLÇÜTÜ: görsel fazın yüzde kaçı hedef MANEVRA
        #   yaparken geçti. ÖLÇÜLDÜ: hedef zamanının %42.7'sinde >15 °/s
        #   dönüyor ama görsel fazın yalnız %15.4'ü öyle — yani manevrada
        #   VURAMIYOR değiliz, manevrada hiç DEVRETMİYORUZ.
        t, sekme, imha_ani = temas_sinifla(d, r)
        r["temas"] = t; r["isabet"] = t
        r["sekme"] = sekme; r["imha"] = imha_ani
        mv, w = _manevra(os.path.join(d, "meta.csv"))
        if mv is not None:
            r["manevra%"] = mv; r["hedef_w"] = w
    return g


def _satir(ad, g):
    gec = [r for r in g if r.get("ihlal", "-") == "-"]
    p = [f"{ad:>22} {len(gec):3d}"]
    for k, f in SUT[1:]:
        c = _sayi(gec, k)
        if not c: p.append(f"{'-':>8}"); continue
        p.append(f"{(sum(c) if f=='sum' else float(np.median(c))):8.2f}")
    return " ".join(p), gec


def rapor(yollar, kola_gore=False, birlestir=False):
    """birlestir=True: AYNI yapılandırmayla koşulmuş birden çok kampanyayı
    kombo'ya göre havuzla. ⚠ Yalnız yapılandırma BİREBİR aynıysa meşrudur;
    her kampanya kendi içinde dönüşümlü olduğu için sim kayması iki kolu
    eşit etkiler (§4). Havuzlandığı raporda AÇIKÇA yazılır."""
    if birlestir:
        havuz = {}
        for y in yollar:
            for r in _oku(y):
                havuz.setdefault(r.get("kombo", "?"), []).append(r)
        print(f"{'kol (havuzlanmış)':>22} {'n':>3} " +
              " ".join(f"{k:>8}" for k, _ in SUT[1:]))
        print("-" * (26 + 9 * (len(SUT) - 1)))
        for k, g in havuz.items():
            print(_satir(k, g)[0])
        print("\nkoşu koşu en_yakin_m:")
        for k, g in havuz.items():
            gec = [r for r in g if r.get("ihlal", "-") == "-"]
            c = _sayi(gec, "en_yakin_m"); isb = int(sum(_sayi(gec, "isabet")))
            print(f"  {k:>22}: {[round(x,2) for x in c]}  isabet {isb}/{len(gec)}"
                  + ("" if len(gec) >= 4 else "   ⚠ n<4 -> ARA VERİ"))
        return havuz
    return _rapor_ayri(yollar, kola_gore)


def _rapor_ayri(yollar, kola_gore=False):
    print(f"{'kol':>22} {'n':>3} " +
          " ".join(f"{k:>8}" for k, _ in SUT[1:]))
    print("-" * (26 + 9 * (len(SUT) - 1)))
    kayit = {}
    for y in yollar:
        R = _oku(y)
        if not R:
            print(f"{os.path.basename(y):>22}  (veri yok)"); continue
        if kola_gore and "kombo" in R[0]:
            for kombo in dict.fromkeys(r["kombo"] for r in R):
                g = [r for r in R if r["kombo"] == kombo]
                sat, gec = _satir(f"{os.path.basename(y)}:{kombo}", g)
                print(sat); kayit[f"{os.path.basename(y)}:{kombo}"] = gec
        else:
            sat, gec = _satir(os.path.basename(y.rstrip("/")), R)
            print(sat); kayit[os.path.basename(y.rstrip("/"))] = gec
    # koşu koşu en yakın (§5.4 saçılım görünsün)
    print("\nkoşu koşu en_yakin_m (saçılımı gör — medyan tek başına aldatır):")
    for ad, g in kayit.items():
        c = _sayi(g, "en_yakin_m")
        isb = int(sum(_sayi(g, "isabet")))
        print(f"  {ad:>22}: {[round(x,2) for x in c]}  isabet {isb}/{len(g)}"
              + ("" if len(g) >= 4 else "   ⚠ n<4 -> ARA VERİ, hüküm YOK"))
    return kayit


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    rapor(a, "--kol" in sys.argv, "--birlestir" in sys.argv)
