# -*- coding: utf-8 -*-
"""SAĞLAM kamera kalibrasyonu: fx=fy kısıtlı + aykırı değer atma.
Neden kısıt: kare piksellerde fx=fy FİZİKSEL zorunluluktur. Serbest bırakınca
yatay yönde sinyal az (yaw hatası dar bantta) ve fx gürültüye oturuyor."""
import numpy as np, math, sys
sys.path.insert(0,".")
from araclar.kamera_kalib import _don_x, _don_y

def coz_saglam(d, tilt_tara=(15.0,40.0,0.25), tur=4, boyut=(0.5,2.5), conf_min=0.25):
    # kare kare tek aday: boyut kapısı + conf
    key=lambda r:(round(r['menzil'],2),round(r['yaw_hata'],2))
    g={}
    for r in d:
        if r['sira']<0: continue
        if not (boyut[0]*r['bek_px'] <= r['bw'] <= boyut[1]*r['bek_px']): continue
        if r['conf'] < conf_min: continue
        k=key(r)
        if k not in g or r['conf']>g[k]['conf']: g[k]=r
    K=list(g.values())
    if len(K)<20: return None, len(K)
    while True:
        V=[];U=[];Vp=[]
        for r in K:
            e=math.radians(r['elev']); h=math.radians(r['yaw_hata'])
            v=np.array([math.cos(e)*math.cos(h), math.cos(e)*math.sin(h), math.sin(e)])
            # ÖLÇÜLDÜ: pitch işareti -1 (burun aşağı = negatif derece)
            v=_don_x(math.radians(r['own_roll'])) @ _don_y(math.radians(r['own_pitch'])) @ v
            V.append(v); U.append(r['bcx']); Vp.append(r['bcy'])
        V=np.array(V);U=np.array(U);Vp=np.array(Vp)
        en=None
        for tilt in np.arange(*tilt_tara):
            Vt=(_don_y(math.radians(tilt))@V.T).T
            x,y,z=Vt[:,0],Vt[:,1],Vt[:,2]
            ok=x>0.2
            if ok.sum()<15: continue
            # fx=fy=f kısıtlı tek bilinmeyen
            a=np.concatenate([(y/x)[ok],(z/x)[ok]])
            b=np.concatenate([(U-960)[ok],(540-Vp)[ok]])
            f=float(a@b/max(a@a,1e-9))
            art=b-f*a
            rms=float(np.sqrt((art**2).mean()))
            if en is None or rms<en[2]: en=(tilt,f,rms,ok,art)
        if en is None: return None,len(K)
        tilt,f,rms,ok,art=en
        tur-=1
        if tur<=0: break
        # aykırı at: kare başına iki artık (u,v) -> ikisinin normu
        m=ok.sum()
        rn=np.hypot(art[:m],art[m:])
        esik=max(25.0, 2.0*np.median(rn))
        idx=np.where(ok)[0]
        tut=set(idx[rn<=esik].tolist())
        yeni=[K[i] for i in range(len(K)) if i in tut]
        if len(yeni)<20 or len(yeni)==len(K): break
        K=yeni
    return (tilt,f,rms,len(K)), len(K)
