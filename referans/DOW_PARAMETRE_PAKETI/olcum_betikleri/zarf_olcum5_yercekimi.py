# -*- coding: utf-8 -*-
"""ZARF 5 - g'yi UC farkli yatis acisinda dogrula (tutarli mi?)."""
import json,time,math,glob,os,urllib.request
import numpy as np
URL="http://127.0.0.1:8000"
def post(y,v):
    r=urllib.request.Request(URL+y,data=json.dumps(v).encode(),headers={"Content-Type":"application/json"})
    urllib.request.urlopen(r,timeout=3).read()
def cub(**k): post("/api/manuel",{"throttle":k.get("thr",0),"pitch":k.get("pit",0),"roll":k.get("rol",0),"yaw":k.get("yaw",0)})
def tele():
    try:
        with urllib.request.urlopen(URL+"/api/telemetry",timeout=1.0) as f: return json.loads(f.read())
    except Exception: return None
post("/api/command",{"cmd":"manuel_on"})
ciz=[];att=[]
def adim(ad,sure,rol,bekle=3.0):
    print("  %-14s roll=%.2f  %.0f s"%(ad,rol,sure),flush=True)
    t0=time.perf_counter()
    while time.perf_counter()-t0<sure:
        cub(rol=rol)
        d=tele()
        if d and d.get("drone"):
            dd=d["drone"]
            att.append((time.perf_counter(),abs(float(dd.get("roll",0) or 0)),float(dd.get("z",0) or 0)))
        time.sleep(0.04)
    ciz.append((ad,t0,time.perf_counter()))
    t0=time.perf_counter()
    while time.perf_counter()-t0<bekle: cub(); time.sleep(0.05)
for ad,r in (("yatis_030",0.30),("yatis_055",0.55),("yatis_085",0.85)):
    adim(ad,5.0,r)
for _ in range(25): cub(); time.sleep(0.05)
print("  bekleniyor..."); time.sleep(8)
F=sorted(glob.glob("veri/hedef_iz/hedef_iz_*.csv"),key=os.path.getmtime)
d=None
for p in reversed(F):
    q=np.genfromtxt(p,delimiter=",",names=True,dtype=None,encoding="utf-8")
    if q.dtype.names and "t_mutlak" in q.dtype.names and q.size>50: d=q; break
t=np.asarray(d["t_mutlak"],float); a=np.argsort(t); t=t[a]
X,Y,Z=[np.asarray(d[k],float)[a] for k in ("dx_m","dy_m","dz_m")]
print(); print("="*72)
print("  %-12s%9s%11s%12s%11s%10s"%("asama","yatis","a_yatay","dikey hiz","g=a/tan","sapma"))
gs=[]
for ad,t0,t1 in ciz:
    m=(t>=t0+0.8)&(t<=t1)
    if m.sum()<8: print("  %-12s (ornek yok)"%ad); continue
    tt=t[m]; W=0.25
    ta,tb=np.clip(tt-W/2,tt[0],tt[-1]),np.clip(tt+W/2,tt[0],tt[-1]); dt=np.maximum(tb-ta,1e-9)
    D=lambda v:(np.interp(tb,tt,v)-np.interp(ta,tt,v))/dt
    vx,vy,vz=D(X[m]),D(Y[m]),D(Z[m])
    A=float(np.median(np.hypot(D(vx),D(vy)))); VZ=float(np.median(vz))
    ma=np.array([q[0] for q in att]); ro=np.array([q[1] for q in att])
    k=(ma>=t0+0.8)&(ma<=t1)
    if k.sum()<3: print("  %-12s (attitude yok)"%ad); continue
    R=float(np.median(ro[k])); tn=math.tan(math.radians(R))
    if tn<0.05: print("  %-12s yatis cok kucuk (%.1f)"%(ad,R)); continue
    g=A/tn; gs.append(g)
    print("  %-12s%8.1f°%10.2f%11.2f%12.2f%9.1f%%"%(ad,R,A,VZ,g,100*abs(g-9.81)/9.81))
if len(gs)>=2:
    gs=np.array(gs)
    print()
    print("  g tahminleri: %s"%np.round(gs,2))
    print("  ortalama %.2f  yayilim %.2f m/s²"%(gs.mean(),gs.max()-gs.min()))
    print("  -> %s"%("TUTARLI, g = %.1f m/s² kabul edilebilir"%gs.mean() if gs.max()-gs.min()<1.5
            else "TUTARSIZ (yayilim %.1f) -> basit yatis modeli GECERLI DEGIL, g olculemez"%(gs.max()-gs.min())))
print("="*72)
