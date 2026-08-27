# -*- coding: utf-8 -*-
"""UÇUŞ MODELİ HIZ PROBU — sabit kumanda gönderip GERÇEK yer hızını ölçer.

Amaç: cevirici'nin varsaydığı model (pitch+0.6 -> 22 m/s) DOĞRU mu?
Run7'de drone yalnız ~8 m/s yer hızı yaptı, SDK 30 m/s dedi. Hangisi gerçek?
Bu prob: her pitch için sabit kumanda tutar, konum farkından yer hızını çıkarır
ve SDK'nın bildirdiği hızla karşılaştırır. HOVER_THR ile irtifa ~sabit tutulur.
"""
import time, math, sys
from dow.sdk.baglanti import DowBaglanti
from dow.gudum.cevirici import CevCfg

def olc(b, thr, pitch, roll, yaw, sure=6.0, hz=20.0):
    dt = 1.0/hz
    # baslangic
    p0 = b.konum(); t0 = time.time()
    yol = 0.0; prev = p0
    sdk_hiz = []
    n = int(sure*hz)
    for i in range(n):
        b.komut(thr, pitch, roll, yaw, arm=True)
        time.sleep(dt)
        p = b.konum()
        yol += math.hypot(p[0]-prev[0], p[1]-prev[1])
        prev = p
        v = b.hiz_vektoru()
        sdk_hiz.append(math.hypot(v[0], v[1]))
    p1 = b.konum(); t1 = time.time()
    T = t1 - t0
    net = math.hypot(p1[0]-p0[0], p1[1]-p0[1])
    return {
        "yer_hiz_net": net/T,        # m/s (net yer degistirme / sure)
        "yer_hiz_yol": yol/T,        # m/s (toplam yol / sure)
        "sdk_hiz_med": sorted(sdk_hiz)[len(sdk_hiz)//2],
        "dz": p1[2]-p0[2],
        "sure": T,
    }

def main():
    b = DowBaglanti()
    print("baglan:", b.baglan())
    # yaw'i sabit tut (mevcut yon), roll=0
    yon = b.yonelim(); yaw_deg = math.degrees(yon[2])
    print("baslangic yaw=%.0f z=%.1f" % (yaw_deg, b.konum()[2]))
    hov = CevCfg.HOVER_THR
    print("HOVER_THR=%.3f" % hov)
    print("\n%-8s %-8s | yer_hiz_net  yer_hiz_yol  sdk_hiz  dz" % ("pitch", "thr"))
    for pitch in [0.3, 0.6, 1.0]:
        r = olc(b, hov, pitch, 0.0, 0.0, sure=6.0)
        print("%-8.2f %-8.2f | %8.1f  %10.1f  %7.1f  %6.1f"
              % (pitch, hov, r["yer_hiz_net"], r["yer_hiz_yol"], r["sdk_hiz_med"], r["dz"]))
        # araya dur (2 sn notr) ki bir sonrakine temiz baslasin
        for _ in range(20):
            b.komut(hov, 0.0, 0.0, 0.0, arm=True); time.sleep(0.05)
    # tam gaz ileri + tam gaz yukari kombinasyonu (max ileri denemesi)
    print("\n-- ekstra: pitch=0.6 + thr degisimleri --")
    for thr in [hov, 0.0, 1.0, -1.0]:
        r = olc(b, thr, 0.6, 0.0, 0.0, sure=5.0)
        print("thr=%-6.2f pitch=0.60 | yer_net=%.1f yer_yol=%.1f sdk=%.1f dz=%.1f"
              % (thr, r["yer_hiz_net"], r["yer_hiz_yol"], r["sdk_hiz_med"], r["dz"]))
    b.komut(0.0, 0.0, 0.0, 0.0, arm=True)
    b.kapat()

if __name__ == "__main__":
    main()
