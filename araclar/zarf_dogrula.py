# -*- coding: utf-8 -*-
"""DOW ham hedef-izinden Talon zarfini BAGIMSIZ yeniden hesaplar.
Raporun sayilarini dogrulamak/curutmek icin; rapora guvenmez."""
import sys, numpy as np

yol = sys.argv[1]
d = np.genfromtxt(yol, delimiter=",", names=True)
t  = d["t_s"]; hx = d["hx_m"]; hy = d["hy_m"]; hz = d["hz_m"]; hv = d["h_hiz_ms"]
n = len(t)
print(f"ornek={n}  sure={t[-1]-t[0]:.1f} s  ort dt={np.median(np.diff(t))*1000:.1f} ms "
      f"({1/np.median(np.diff(t)):.1f} Hz)")

# --- SDK'nin verdigi hedef hizi gercekten 0 mi? ---
print(f"\nSDK h_hiz_ms alani: min={hv.min():.3f} max={hv.max():.3f} "
      f"sifir-olmayan oran=%{100*np.mean(hv>1e-6):.2f}")

# --- konumdan turetilmis hiz (30 Hz gurultusunu 1 s pencereyle bastir) ---
W = int(round(1.0/np.median(np.diff(t))))          # 1 s'lik pencere
dx = hx[W:]-hx[:-W]; dy = hy[W:]-hy[:-W]; dz = hz[W:]-hz[:-W]; dt = t[W:]-t[:-W]
vxy = np.hypot(dx,dy)/dt
gec = dt > 0
vxy = vxy[gec]
print(f"\nTALON SEYIR HIZI (1 s pencere, yatay): medyan={np.median(vxy):.3f} "
      f"ort={vxy.mean():.3f} std={vxy.std():.3f} m/s")
print(f"  %5={np.percentile(vxy,5):.2f}  %95={np.percentile(vxy,95):.2f} "
      f" min={vxy.min():.2f} max={vxy.max():.2f}")
# bagimsiz kontrol: toplam yol / toplam sure
yol_top = np.sum(np.hypot(np.diff(hx), np.diff(hy)))
print(f"  BAGIMSIZ (toplam yol/sure) = {yol_top/(t[-1]-t[0]):.3f} m/s")

# --- yon ve donus hizi ---
hdg = np.unwrap(np.arctan2(dy, dx))
w = np.degrees(np.diff(hdg)/dt[1:])                # deg/s
w = w[np.isfinite(w)]
aw = np.abs(w)
print(f"\nTALON DONUS HIZI: medyan={np.median(aw):.2f}  %90={np.percentile(aw,90):.2f} "
      f" %99={np.percentile(aw,99):.2f}  max={aw.max():.2f} deg/s")
# donus yaricapi R = V/omega  (yalniz gercekten donerken)
don = aw > 5.0
V = np.median(vxy)
R = V/np.radians(aw[don])
print(f"  DONUS YARICAPI (|w|>5 deg/s, n={don.sum()}): medyan={np.median(R):.1f} m "
      f" %10={np.percentile(R,10):.1f}  %90={np.percentile(R,90):.1f}")
print(f"  duz ucus orani (|w|<8 deg/s) = %{100*np.mean(aw<8):.1f}")
# teorik min yaricap (rapor 51 m diyor): en sert donusten
print(f"  EN SERT donusten R_min = {V/np.radians(np.percentile(aw,99)):.1f} m")

# --- irtifa ---
print(f"\nTALON IRTIFA: medyan={np.median(hz):.1f}  %5={np.percentile(hz,5):.1f} "
      f" %95={np.percentile(hz,95):.1f}  min={hz.min():.1f} max={hz.max():.1f} m")
vz = np.diff(hz)/np.diff(t)
vz = vz[np.isfinite(vz)]
print(f"  dikey hiz: %1={np.percentile(vz,1):.2f}  %99={np.percentile(vz,99):.2f} m/s")

# --- manevrada yavasliyor mu? ---
aw_h = aw[:len(vxy)-1] if len(aw) >= len(vxy)-1 else aw
v_h  = vxy[1:1+len(aw_h)]
duz = aw_h < 5.0; dnn = aw_h > 15.0
print(f"\nMANEVRADA YAVASLAMA: duz={np.median(v_h[duz]):.3f} m/s (n={duz.sum()})  "
      f"donuste={np.median(v_h[dnn]):.3f} m/s (n={dnn.sum()})  "
      f"fark=%{100*(np.median(v_h[duz])-np.median(v_h[dnn]))/np.median(v_h[duz]):.2f}")

# --- saha boyutu ---
print(f"\nSAHA: x {hx.min():.1f}..{hx.max():.1f} ({hx.max()-hx.min():.1f} m)  "
      f"y {hy.min():.1f}..{hy.max():.1f} ({hy.max()-hy.min():.1f} m)")

# --- en yakin gecis (carpisma yaricapi ust siniri) ---
dd = np.sqrt((hx-d["dx_m"])**2 + (hy-d["dy_m"])**2 + (hz-d["dz_m"])**2)
print(f"\nEN YAKIN GECIS: {dd.min():.2f} m   (<10 m olan ornek: {np.sum(dd<10)})")
