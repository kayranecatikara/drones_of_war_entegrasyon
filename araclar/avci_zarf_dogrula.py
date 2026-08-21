# -*- coding: utf-8 -*-
"""AVCI DRONE zarfini ham izden BAGIMSIZ dogrula.
hedef_iz kaydi dx_m/dy_m/dz_m (drone truth konumu) icerir ve zaman araligi
zarf_olcum asamalarini KAPSAR -> raporun avci sayilarini yeniden hesaplayabiliriz."""
import sys, numpy as np
iz, asama = sys.argv[1], sys.argv[2]
d = np.genfromtxt(iz, delimiter=",", names=True)
t = d["t_mutlak"]; x=d["dx_m"]; y=d["dy_m"]; z=d["dz_m"]
A = np.genfromtxt(asama, delimiter=",", names=True, dtype=None, encoding="utf-8")
fs = 1/np.median(np.diff(d["t_s"]))
print(f"iz: {t[0]:.1f}..{t[-1]:.1f}  ({fs:.1f} Hz)\n")

def turev(v, tt, W):
    """W ornekli merkezi fark -> gurultuyu bastir."""
    return (v[W:]-v[:-W])/(tt[W:]-tt[:-W]), tt[W:]

W = max(1, int(round(fs*0.20)))     # 200 ms pencere
for satir in np.atleast_1d(A):
    ad = str(satir["asama"]); t0=float(satir["t_bas"]); t1=float(satir["t_bit"])
    m = (t>=t0)&(t<=t1)
    if m.sum() < 5:
        print(f"{ad:18s} ORNEK YOK (iz bu araligi kapsamiyor)"); continue
    tt=t[m]; xx=x[m]; yy=y[m]; zz=z[m]
    vx,_ = turev(xx,tt,W); vy,_ = turev(yy,tt,W); vz,tv = turev(zz,tt,W)
    vh = np.hypot(vx,vy)
    ax,_ = turev(vx,tv,W); ay,_ = turev(vy,tv,W); az,_ = turev(vz,tv,W)
    ah = np.hypot(ax,ay)
    print(f"{ad:18s} n={m.sum():5d} sure={t1-t0:5.2f}s | "
          f"v_yatay max={vh.max():6.2f} | vz max={vz.max():6.2f} min={vz.min():6.2f} | "
          f"a_yatay max={ah.max():6.2f} %95={np.percentile(ah,95):6.2f} | "
          f"az max={az.max():6.2f} min={az.min():6.2f}  [m/s, m/s2]")
    if ad.startswith("saf_roll") or ad.startswith("roll"):
        # hiz vektoru donus hizi
        hdg=np.unwrap(np.arctan2(vy,vx)); w=np.degrees(np.gradient(hdg,tv))
        gecerli = vh>5
        if gecerli.sum()>5:
            print(f"{'':18s}   hiz-vektoru donusu: medyan={np.median(np.abs(w[gecerli])):.1f} "
                  f"max={np.abs(w[gecerli]).max():.1f} deg/s   (V={np.median(vh[gecerli]):.1f} m/s)")
            print(f"{'':18s}   esdeger yatis atan(a/g) = {np.degrees(np.arctan(ah.max()/9.81)):.1f} deg")
