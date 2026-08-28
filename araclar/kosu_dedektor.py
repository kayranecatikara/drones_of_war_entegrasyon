# -*- coding: utf-8 -*-
"""DEDEKTÖR KAPISI — kalibre kamera modeliyle (artık 2.6 px).
Bir tespit ancak hedefin ÖNGÖRÜLEN kadraj konumuna yakınsa GERÇEK sayılır.
Ayrıca en-yüksek-güvenli kutunun gerçekten hedef olup olmadığı ölçülür
(güdüm menzili bilmediği için pratikte argmax'a mecburdur)."""
import sys, time, math, csv, numpy as np, mss
sys.path.insert(0,"dow/sdk"); sys.path.insert(0,".")
import drone_sdk as d
from ultralytics import YOLO
from dow.gudum.cevirici import HizCubukCevirici
from dow.gorus import kamera as KAM
from araclar.kadraj import hazirla, BOLGE, ucusta_mi, oyunu_one_al
from araclar import ucus

cev=HizCubukCevirici(); m=YOLO("modeller/talon_v3.pt")
sct=mss.MSS(); ok,img0=hazirla(sct)
print("hazırlık:", "UÇUŞTA" if ok else "BAŞARISIZ", flush=True)
assert ok and d.connect(); time.sleep(1)
for iz in (960,1920): m.predict(img0,imgsz=iz,conf=0.10,verbose=False)

try:
    ucus.dur(5.0)
    _,_,_,_,R0=ucus.geo(); print(f"başlangıç R={R0:.0f} m", flush=True)
    ok2,R=ucus.yaklas(cev, 80.0, 200.0, log=lambda s: print(s,flush=True))
    print(f"yaklaşma {'OK' if ok2 else 'SÜRE'} R={R:.0f}", flush=True)
    if R>140: raise SystemExit("yaklaşılamadı")
    f=open("logs/dedektor_kapi.csv","w",newline=""); w=csv.writer(f)
    w.writerow(["menzil","bek_cx","bek_cy","bek_px","imgsz","kutu_sayisi",
                "hedef_bulundu","argmax_hedef","conf_hedef","conf_argmax","hata_px"])
    n=0; t0=time.time()
    while time.time()-t0<230:
        R,ez,hy,dz = ucus.istasyon(cev, 0.40 if R>55 else (0.15 if R>25 else -0.05))
        if R<13: break
        img=np.array(sct.grab(BOLGE))[:,:,:3]
        if not ucusta_mi(img): oyunu_one_al(); time.sleep(0.4); continue
        rr,pp,yy=d.get_drone_rotation()
        elev=math.degrees(math.asin(max(-1,min(1,dz/R))))
        _bk = KAM.beklenen_kadraj(R, elev, hy, pp, rr)
        if _bk is None: continue          # hedef ARKADA — izdüşüm anlamsız
        bcx,bcy,bp = _bk
        rgb=img[:,:,::-1]
        for iz in (960,1920):
            r=m.predict(rgb,imgsz=iz,conf=0.10,verbose=False)[0]
            bl=sorted(r.boxes,key=lambda x:-float(x.conf))
            bul=0; amx=0; cf=0.0; ca=float(bl[0].conf) if bl else 0.0; hp=-1
            for i,b in enumerate(bl):
                x1,y1,x2,y2=b.xyxy[0].tolist(); cx,cy=(x1+x2)/2,(y1+y2)/2
                dpx=math.hypot(cx-bcx,cy-bcy)
                if dpx <= max(45, 2.5*bp) and 0.4*bp <= (x2-x1) <= 3.0*bp:
                    bul=1; cf=float(b.conf); hp=dpx
                    if i==0: amx=1
                    break
            w.writerow([f"{R:.2f}",f"{bcx:.0f}",f"{bcy:.0f}",f"{bp:.1f}",iz,
                        len(bl),bul,amx,f"{cf:.3f}",f"{ca:.3f}",f"{hp:.1f}"])
        n+=1
        if n%40==0: print(f"  n={n} R={R:.0f}", flush=True)
        time.sleep(0.003)
    f.close(); print(f"BİTTİ {n} kare", flush=True)
finally:
    ucus.guvenli_komut()
    try: d.disconnect()
    except Exception: pass
