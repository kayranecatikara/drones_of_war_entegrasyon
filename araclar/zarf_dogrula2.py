# -*- coding: utf-8 -*-
"""Talon donus zarfi — DUZELTILMIS. Onceki surumde omega, 1 s pencere suresine
bolunuyordu (30x kucuk cikiyordu). Burada yon 1 s pencereden, TUREV ise
ornekleme araligindan alinir."""
import sys, numpy as np
d = np.genfromtxt(sys.argv[1], delimiter=",", names=True)
t=d["t_s"]; hx=d["hx_m"]; hy=d["hy_m"]; hz=d["hz_m"]
fs = 1/np.median(np.diff(t)); W = int(round(fs))          # 1 s yon penceresi

# hareketsiz bolumleri at: 1 s'lik yer degistirme > 5 m
dx=hx[W:]-hx[:-W]; dy=hy[W:]-hy[:-W]
v = np.hypot(dx,dy)/(t[W:]-t[:-W])
tt = t[W:]
hareket = v > 5.0
print(f"toplam {len(t)} ornek / {t[-1]-t[0]:.0f} s;  HAREKETLI ornek: {hareket.sum()} "
      f"(%{100*hareket.mean():.1f})")
print(f"seyir hizi (yalniz hareketli): medyan={np.median(v[hareket]):.3f} "
      f"std={v[hareket].std():.3f} m/s")

hdg = np.unwrap(np.arctan2(dy,dx))
w = np.degrees(np.gradient(hdg, tt))                        # DOGRU: dt=ornek araligi
w = w[hareket]; aw = np.abs(w)
V = np.median(v[hareket])
print(f"\nDONUS HIZI: medyan={np.median(aw):.2f}  %75={np.percentile(aw,75):.2f} "
      f"%90={np.percentile(aw,90):.2f}  %99={np.percentile(aw,99):.2f} deg/s")
print(f"duz ucus orani (|w|<8 deg/s) = %{100*np.mean(aw<8):.1f}")
don = aw>8
print(f"DONUSTEKI omega medyani = {np.median(aw[don]):.2f} deg/s")
print(f"DONUS YARICAPI R=V/w : medyan={V/np.radians(np.median(aw[don])):.1f} m ; "
      f"en sert (%99) = {V/np.radians(np.percentile(aw,99)):.1f} m")

# tur suresi: toplam yon donusu / 360
tur = np.abs(hdg[hareket][-1]-hdg[hareket][0])/(2*np.pi)
sure = tt[hareket][-1]-tt[hareket][0]
print(f"\nTUR: {tur:.1f} tur / {sure:.0f} s -> tur suresi={sure/max(tur,1e-9):.1f} s ; "
      f"tur uzunlugu={V*sure/max(tur,1e-9):.0f} m")

# manevrada yavaslama
vh = v[hareket]
print(f"\nMANEVRADA YAVASLAMA: duz(|w|<5)={np.median(vh[aw<5]):.3f} (n={np.sum(aw<5)})  "
      f"donus(|w|>15)={np.median(vh[aw>15]):.3f} (n={np.sum(aw>15)})  "
      f"fark=%{100*(np.median(vh[aw<5])-np.median(vh[aw>15]))/np.median(vh[aw<5]):.2f}")
# yatis acisi (koordineli donus varsayimi): tan(phi)=V*w/g
phi = np.degrees(np.arctan(V*np.radians(aw[don])/9.81))
print(f"ESDEGER YATIS (koordineli donus): medyan={np.median(phi):.1f} "
      f"%99={np.percentile(phi,99):.1f} deg")
