# -*- coding: utf-8 -*-
"""DİKEY YETKİ x İLERİ HIZ — eksik zarf parçası.
Soru: alçalma yetkisi (thr=-1) ileri uçuşta korunuyor mu?
Hover'da -6.95 m/s ölçmüştük; uçtan uca koşuda araç thr=-1 iken +6.4 m/s
TIRMANDI ve 762 m'ye çıktı. Yani yetki hıza bağlı."""
import sys, time, numpy as np
sys.path.insert(0,".")
from dow.sdk import drone_sdk as d
from araclar import ucus
from araclar.kadraj import hazirla, oyunu_one_al
import mss
sct=mss.MSS(); ok,_=hazirla(sct)
print("hazırlık:", "UÇUŞTA" if ok else "BAŞARISIZ", flush=True); assert ok
assert d.connect(); time.sleep(1)

def olc(pitch, thr, sure=6.0):
    t0=time.time(); k=[]
    while time.time()-t0<sure:
        d.set_control_surfaces(thr, pitch, 0.0, 0.0, True)
        k.append((time.time()-t0, d.get_drone_altitude()/100.0, d.get_drone_speed()/100.0))
        time.sleep(0.03)
    s=[x for x in k if x[0]>sure*0.5]
    t=np.array([x[0] for x in s]); z=np.array([x[1] for x in s]); v=np.array([x[2] for x in s])
    vz=np.linalg.lstsq(np.vstack([t,np.ones_like(t)]).T,z,rcond=None)[0][0]
    return vz, v.mean(), z.mean()

try:
    # güvenli irtifaya çık (önce thr=0 ile 2 s "uyandır" — bayat bağlantıya karşı)
    t0=time.time()
    while time.time()-t0<2: d.set_control_surfaces(0.0,0,0,0,True); time.sleep(0.03)
    t0=time.time()
    while d.get_drone_altitude()/100 < 250 and time.time()-t0<60:
        d.set_control_surfaces(0.8,0,0,0,True); time.sleep(0.03)
    print(f"irtifa {d.get_drone_altitude()/100:.0f} m\n", flush=True)
    print(f"{'pitch':>6} {'thr':>6} {'ileri hız':>10} {'vz':>8}  YORUM", flush=True)
    for pitch in (0.0, 0.25, 0.5, 0.75, 1.0):
        # önce o pitch'te hız kazan
        t0=time.time()
        while time.time()-t0 < 6.0:
            d.set_control_surfaces(ucus.HOVER_THR, pitch, 0,0, True); time.sleep(0.03)
        vz, v, z = olc(pitch, -1.0)
        yorum = "ALÇALIYOR" if vz < -1 else ("TIRMANIYOR ⚠" if vz > 1 else "asılı")
        print(f"{pitch:6.2f} {-1.0:6.2f} {v:9.1f}  {vz:+8.2f}  {yorum}", flush=True)
        # irtifayı topla
        if z > 600 or z < 120:
            hedefz = 250
            t0=time.time()
            while abs(d.get_drone_altitude()/100 - hedefz) > 25 and time.time()-t0 < 60:
                e = hedefz - d.get_drone_altitude()/100
                d.set_control_surfaces(0.8 if e>0 else -1.0, 0,0,0, True); time.sleep(0.03)
finally:
    ucus.guvenli_komut(); d.disconnect()
