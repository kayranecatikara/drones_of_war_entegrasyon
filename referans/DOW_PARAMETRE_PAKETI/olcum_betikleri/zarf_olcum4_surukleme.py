# -*- coding: utf-8 -*-
"""ZARF 4 - yercekimi (yatis acisindan) + surukleme (serbest yavaslama)."""
import json,time,math,glob,os,urllib.request
import numpy as np
URL="http://127.0.0.1:8000"; KOK=os.getcwd()
def post(y,v):
    r=urllib.request.Request(URL+y,data=json.dumps(v).encode(),headers={"Content-Type":"application/json"})
    urllib.request.urlopen(r,timeout=3).read()
def cub(**k): post("/api/manuel",{"throttle":k.get("thr",0),"pitch":k.get("pit",0),"roll":k.get("rol",0),"yaw":k.get("yaw",0)})
def tele():
    try:
        with urllib.request.urlopen(URL+"/api/telemetry",timeout=1.0) as f: return json.loads(f.read())
    except Exception: return None
post("/api/command",{"cmd":"manuel_on"})
ciz=[]; att=[]
def adim(ad,sure,att_topla=False,bekle=2.0,**k):
    print("  %-20s %.1f s %s"%(ad,sure,k),flush=True)
    t0=time.perf_counter()
    while time.perf_counter()-t0<sure:
        cub(**k)
        if att_topla:
            d=tele()
            if d and d.get("drone"):
                dd=d["drone"]
                att.append((time.perf_counter(),float(dd.get("roll",0) or 0),float(dd.get("pitch",0) or 0)))
        time.sleep(0.04)
    ciz.append((ad,t0,time.perf_counter()))
    t0=time.perf_counter()
    while time.perf_counter()-t0<bekle: cub(); time.sleep(0.05)
print("  ZARF 4: yercekimi + surukleme")
adim("hizlan",4.0,pit=1.0,bekle=0.0)
adim("serbest_yavasla",7.0)                     # cubuk NOTR -> surukleme profili
adim("orta_yatis",6.0,att_topla=True,rol=0.55)  # sabit yatis -> g
for _ in range(25): cub(); time.sleep(0.05)
print("  bekleniyor..."); time.sleep(8)
F=sorted(glob.glob("veri/hedef_iz/hedef_iz_*.csv"),key=os.path.getmtime)
d=None
for p in reversed(F):
    q=np.genfromtxt(p,delimiter=",",names=True,dtype=None,encoding="utf-8")
    if q.dtype.names and "t_mutlak" in q.dtype.names and q.size>50: d=q; break
t=np.asarray(d["t_mutlak"],float); a=np.argsort(t); t=t[a]
X,Y,Z=[np.asarray(d[k],float)[a] for k in ("dx_m","dy_m","dz_m")]
def pen(t0,t1,kirp=0.2):
    m=(t>=t0+kirp)&(t<=t1)
    if m.sum()<8: return None
    tt=t[m]; W=0.25
    ta,tb=np.clip(tt-W/2,tt[0],tt[-1]),np.clip(tt+W/2,tt[0],tt[-1]); dt=np.maximum(tb-ta,1e-9)
    D=lambda v:(np.interp(tb,tt,v)-np.interp(ta,tt,v))/dt
    vx,vy,vz=D(X[m]),D(Y[m]),D(Z[m])
    return {"t":tt-tt[0],"V":np.hypot(vx,vy),"ah":np.hypot(D(vx),D(vy)),"vz":vz,"n":int(m.sum())}
print(); print("="*70)
for ad,t0,t1 in ciz:
    p=pen(t0,t1)
    if not p: print("  %-20s (ornek yok)"%ad); continue
    if ad=="serbest_yavasla":
        print("  SURUKLEME (cubuk notr, %d ornek)"%p["n"])
        V,A,T=p["V"],p["ah"],p["t"]
        print("    hiz %.1f -> %.1f m/s"%(V[0],V[-1]))
        for i in range(0,len(V),max(1,len(V)//6)):
            print("      t=%4.1f s  V=%5.1f m/s  |a|=%5.2f m/s²"%(T[i],V[i],A[i]))
        g=V>4
        if g.sum()>6:
            # a = k*V^n  -> log-log egim
            k_,n_=np.polyfit(np.log(V[g]),np.log(np.maximum(A[g],1e-3)),1)
            print("    yavaslama modeli: a ~ V^%.2f"%k_)
            print("    -> %s"%("AERODINAMIK SURUKLEME (n~2 beklenir)" if 1.3<k_<2.7
                    else "sabit/aktif frenleme (n~0)" if abs(k_)<0.5 else "belirsiz"))
    elif ad=="orta_yatis":
        print("  YERCEKIMI (sabit yatis, %d ornek)"%p["n"])
        if att:
            ta_=np.array([q[0] for q in att]); ro=np.array([q[1] for q in att])
            m=(ta_>=t0+0.8)&(ta_<=t1)
            if m.sum()>4:
                rr=np.abs(ro[m])
                # roll radyan mi derece mi?
                bir="rad" if rr.max()<3.2 else "derece"
                rd=np.degrees(rr) if bir=="rad" else rr
                print("    yatis acisi: medyan %.1f derece (birim=%s), n=%d"%(np.median(rd),bir,int(m.sum())))
                A=np.median(p["ah"])
                tn=math.tan(math.radians(np.median(rd)))
                if tn>0.05:
                    print("    yanal ivme medyani: %.2f m/s²"%A)
                    print("    g = a/tan(yatis) = %.2f / %.3f = %.2f m/s²"%(A,tn,A/tn))
                    print("    -> standart 9.81 ile fark: %.1f%%"%(100*abs(A/tn-9.81)/9.81))
            else: print("    yeterli attitude ornegi yok")
        else: print("    attitude okunamadi")
print("="*70)
