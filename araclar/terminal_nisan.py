# -*- coding: utf-8 -*-
"""
================================================================================
TERMİNAL NİŞAN HATASI — ıskanın DOĞRUDAN ölçütü, metre cinsinden
================================================================================
NEDEN BU ÖLÇÜT (§5.5 — ölçüt kullanıcının hedefinden türetilir):
KULLANICI: *"asıl amacımız hiç kaçırma olmadan ilk denemede hedef talonu
vurmak"*. Kaçırma sayısı doğru ama KABA bir ölçüttür — koşu başına 0-4
arası zıplar ve n=6'da bile gürültüde boğulur. Iskanın FİZİKSEL sebebi
ise sürekli bir büyüklüktür: temas anındaki nişan hatası.

ÖLÇÜLDÜ (KM2, n=4/kol): ıskalar 0.9-1.5 m'de, bazı vuruşlar 1.8 m'de.
Yani ölümcül yarıçap metre altı ve isabeti belirleyen şey son saniyedeki
nişan hatasıdır:
    kol         yanal    dikey
    yok        0.26 m   0.60 m
    kademeli   1.37 m   1.45 m

NASIL HESAPLANIR — piksel hatası METREYE çevrilir:
    yanal_m = R · (cx − CX) / F_PX
Benzer üçgenler: kadrajdaki (cx−CX) piksellik sapma, F_PX odak
uzaklığında (px) bir açıya karşılık gelir; R menzilinde o açı
R·(cx−CX)/F_PX metreye denk düşer (F_PX = kameranın odak uzaklığı,
piksel cinsinden; bu depoda 540.4 px).

⭐ SEVİYE ÇERÇEVESİ ZORUNLU: ham (cx−CX) kendi YATIŞIMIZI de içerir.
   Görüntüyü kendi yatışımız kadar geri döndürürüz:
       e_sev = e_x·cos(φ) + e_y·sin(φ)
   ÖLÇÜLDÜ: bu düzeltme manevralı kolda 156 px'i 114 px'e indiriyor,
   yani kendi yatışımız hatanın ~%25'i. Düzeltmeden bakan bir ölçüt
   güdüm kusuru ile kendi yatışımızı karıştırır.

⚠ ÖLÇÜM-ONLY: menzil `menzil3_m` truth kanalından okunur (GPS). Güdüme
   GİRMEZ (§10); yalnız pikseli metreye çevirmek için kullanılır.

Kullanım: python3 araclar/terminal_nisan.py logs/KJ1 --pencere 1.0
================================================================================
"""
import argparse
import csv
import glob
import math
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)
from dow.gorus import kamera as KAM
from araclar.arka import ArkaBekci


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def kosu_olc(d, pencere_s):
    """Bir koşunun EN YAKIN anına giden `pencere_s` saniyesini ölç."""
    y = os.path.join(d, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return None
    ab = ArkaBekci(d)
    S = []
    for r in csv.DictReader(open(y)):
        t = _f(r, "t")
        m = _f(r, "menzil3_m") or _f(r, "menzil_m")
        if None in (t, m):
            continue
        if ab.var and ab.arkada(t):        # geçtikten SONRASI ölçüme girmez
            continue
        S.append((t, m, _f(r, "vis_cx"), _f(r, "vis_cy"),
                  _f(r, "drone_roll"), r.get("basarili") == "1",
                  _f(r, "i_akt"), _f(r, "yaw_I")))
    if len(S) < 8:
        return None
    i = min(range(len(S)), key=lambda k: S[k][1])
    t0 = S[i][0]
    pen = [x for x in S if t0 - pencere_s <= x[0] <= t0]
    kutulu = [x for x in pen if x[5] and x[2] is not None]
    if len(kutulu) < 3:
        return None
    ya, di = [], []
    for x in kutulu:
        ph = math.radians(x[4] or 0.0)
        ex, ey = x[2] - KAM.CX, x[3] - KAM.CY
        ya.append(abs(x[1] * (ex * math.cos(ph) + ey * math.sin(ph)) / KAM.F_PX))
        di.append(abs(x[1] * (-ex * math.sin(ph) + ey * math.cos(ph)) / KAM.F_PX))
    return {
        "ad": os.path.basename(d),
        "Rmin": S[i][1],
        "yanal": st.median(ya),
        "dikey": st.median(di),
        "tespit": 100.0 * len(kutulu) / max(1, len(pen)),
        "i_akt": max((x[6] or 0) for x in pen),
        "yaw_I": max((abs(x[7]) if x[7] is not None else 0.0) for x in pen),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KJ1")
    ap.add_argument("--pencere", type=float, default=1.0,
                    help="en yakın andan geriye kaç saniye")
    a = ap.parse_args()

    kollar = {}
    for d in sorted(glob.glob(os.path.join(KOK, a.kok, "*__t*"))):
        kollar.setdefault(os.path.basename(d).split("__")[0], []).append(d)
    if not kollar:
        print("⛔ koşu yok: %s" % a.kok)
        return

    print("\n" + "=" * 74)
    print("  TERMİNAL NİŞAN HATASI — %s (son %.1f s, seviye çerçevesi)"
          % (a.kok, a.pencere))
    print("=" * 74)
    print("\n  %-14s %7s %10s %10s %9s %8s %9s"
          % ("koşu", "Rmin", "yanal_m", "dikey_m", "tespit%", "i_akt", "|yaw_I|"))
    print("  " + "-" * 70)
    OZ = {}
    for kol in sorted(kollar):
        R = [x for x in (kosu_olc(d, a.pencere) for d in kollar[kol]) if x]
        for x in R:
            print("  %-14s %6.2fm %9.2f %10.2f %8.0f%% %8d %9.1f°"
                  % (x["ad"], x["Rmin"], x["yanal"], x["dikey"], x["tespit"],
                     int(x["i_akt"]), x["yaw_I"]))
        OZ[kol] = R
    print("\n  ÖZET (medyan)")
    print("  %-14s %4s %10s %10s %9s %10s"
          % ("kol", "n", "yanal_m", "dikey_m", "tespit%", "MEKANİZMA"))
    print("  " + "-" * 62)
    for kol in sorted(OZ):
        R = OZ[kol]
        if not R:
            continue
        sifir = sum(1 for x in R if not x["i_akt"])
        print("  %-14s %4d %9.2f %10.2f %8.0f%% %7s"
              % (kol, len(R), st.median([x["yanal"] for x in R]),
                 st.median([x["dikey"] for x in R]),
                 st.median([x["tespit"] for x in R]),
                 "%d/%d sıfır" % (sifir, len(R))))
    print("""
  KARAR (KJ1 için koşmadan ÖNCE ilan edildi):
    yanal_m >=%30 düşer VE kaçırma kötüleşmez VE KJ2'de (manevrasız)
    hiçbir ölçüt bozulmazsa -> GİRER. Aksi halde ELENİR.
  ⚠ MEKANİZMA sütunu sıfır olan deney koşusu VERİ NOKTASI DEĞİLDİR (§5.1).
""")


if __name__ == "__main__":
    main()
