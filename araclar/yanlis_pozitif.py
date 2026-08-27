# -*- coding: utf-8 -*-
"""
================================================================================
YANLIŞ-POZİTİF ORANI — "tespit arttı" iddiasının GEÇERLİLİK EŞİ (§5.2)
================================================================================
Güven eşiğini düşüren her özellik (Ö-I gibi) tespit oranını KENDİLİĞİNDEN
yükseltir; çünkü daha çok kutuyu kabul eder. Bu sayı TEK BAŞINA kanıt
değildir — kabul edilenlerin GERÇEKTEN hedef olup olmadığı sorulmadan
"tespit %48 -> %70 oldu" demek, §5.2'nin yasakladığı şeydir.

NASIL ÖLÇÜLÜR — `bek_cx/bek_cy/bek_w` sütunları:
  Bunlar hedefin GERÇEK konumunun kadraja izdüşümüdür (GPS gerçeğinden
  hesaplanır). ⚠ ÖLÇÜM-ONLY: güdüm bunları GÖRMEZ (§10 yarışma kısıtı;
  bekçi B5 bunu sınar). Yalnız analizde kullanılır.

  Kabul edilen kutunun merkezi ile beklenen merkez arasındaki uzaklık,
  BEKLENEN KUTU BOYUTUNA bölünür:
        hata = |merkez - beklenen| / max(bek_w, 1)
  hata <= TOL ise kutu GERÇEK, değilse YANLIŞ-POZİTİF sayılır.
  TOL = 1.0 varsayılan: bir kutu genişliği kadar sapmaya izin (izdüşüm
  kendisi de yaklaşıktır — hedefin merkezi ile gövde merkezi çakışmaz).

OKUMA:
  yanlış-pozitif oranı iki kolda AYNI ise, tespit artışı GERÇEK kazanımdır.
  Deney kolunda oran belirgin yükseliyorsa, artış SAHTEDİR — özellik çöp
  kutuyu içeri alıyor demektir ve güdüm yanlış şeye nişan alır.

Kullanım: python3 araclar/yanlis_pozitif.py logs/KI1 --menzil 12
================================================================================
"""
import argparse
import csv
import glob
import math
import os
import statistics as st

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KI1")
    ap.add_argument("--menzil", type=float, default=12.0,
                    help="yalnız bu menzilin altı (Ö-I'nin çalıştığı bant)")
    ap.add_argument("--tol", type=float, default=1.0,
                    help="kaç kutu genişliği sapmaya izin")
    a = ap.parse_args()

    kollar = {}
    for d in sorted(glob.glob(os.path.join(KOK, a.kok, "*__t*"))):
        kollar.setdefault(os.path.basename(d).split("__")[0], []).append(d)
    if not kollar:
        print("⛔ koşu yok: %s" % a.kok)
        return

    print("\n" + "=" * 72)
    print("  YANLIŞ-POZİTİF — %s  (menzil < %.0f m, tolerans %.1f kutu)"
          % (a.kok, a.menzil, a.tol))
    print("=" * 72)
    print("\n  %-10s %8s %9s %11s %10s %11s"
          % ("kol", "kabul", "gerçek%", "yanlış-poz%", "hata med", "güven med"))
    print("  " + "-" * 62)
    for kol in sorted(kollar):
        n = ok = 0
        hata = []
        conf = []
        for d in kollar[kol]:
            y = os.path.join(d, "k01", "cikarim.csv")
            if not os.path.exists(y):
                continue
            for r in csv.DictReader(open(y)):
                m = _f(r, "menzil3_m") or _f(r, "menzil_m")
                if m is None or m >= a.menzil or r.get("basarili") != "1":
                    continue
                X, Y = _f(r, "vis_cx"), _f(r, "vis_cy")
                BX, BY, BW = _f(r, "bek_cx"), _f(r, "bek_cy"), _f(r, "bek_w")
                if None in (X, Y, BX, BY, BW) or BW <= 0:
                    continue
                n += 1
                e = math.hypot(X - BX, Y - BY) / max(BW, 1.0)
                hata.append(e)
                c = _f(r, "vis_conf")
                if c is not None:
                    conf.append(c)
                if e <= a.tol:
                    ok += 1
        if n >= 10:
            print("  %-10s %8d %8.1f%% %10.1f%% %10.2f %11s"
                  % (kol, n, 100.0 * ok / n, 100.0 * (n - ok) / n,
                     st.median(hata),
                     "%.2f" % st.median(conf) if conf else "—"))

    print("""
  KARAR KURALI (§5.2 geçerlilik eşi):
    yanlış-poz% iki kolda benzer  -> tespit artışı GERÇEK, kazanım sayılır
    deney kolunda >5 puan yüksek  -> artış SAHTE, özellik çöp kutu alıyor
""")


if __name__ == "__main__":
    main()
