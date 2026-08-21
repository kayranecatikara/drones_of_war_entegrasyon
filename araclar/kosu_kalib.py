# -*- coding: utf-8 -*-
"""KALİBRASYON KOŞUSU: yaklaş, sonra 15-80 m bandında zengin veri topla."""
import sys, time, math, csv, numpy as np, mss
sys.path.insert(0,"dow/sdk"); sys.path.insert(0,".")
import drone_sdk as d
from ultralytics import YOLO
from dow.gudum.cevirici import HizCubukCevirici
from araclar.kadraj import hazirla, BOLGE, ucusta_mi, oyunu_one_al
from araclar import ucus

cev=HizCubukCevirici(); m=YOLO("modeller/talon_v3.pt")
sct=mss.MSS()
ok,img0 = hazirla(sct)
print("hazırlık:", "UÇUŞTA" if ok else "BAŞARISIZ", flush=True)
assert ok and d.connect(), "bağlanamadı"
time.sleep(1)
for _ in range(3): m.predict(img0,imgsz=1920,conf=0.10,verbose=False)

try:
    print("[1/3] askıda kalmış komut temizleniyor...", flush=True)
    ucus.dur(5.0)
    _,_,_,_,R0 = ucus.geo(); print(f"    başlangıç menzili: {R0:.0f} m", flush=True)
    print("[2/3] yaklaşma...", flush=True)
    ok2,R = ucus.yaklas(cev, hedef_menzil=70.0, azami_sure=200.0,
                        log=lambda s: print(s, flush=True))
    print(f"    {'ULAŞILDI' if ok2 else 'SÜRE DOLDU'} R={R:.0f} m", flush=True)
    if R > 120: raise SystemExit("hedefe yaklaşılamadı — koşu geçersiz")

    print("[3/3] veri toplanıyor (15-80 m)...", flush=True)
    f=open("logs/kamera_kalib.csv","w",newline=""); w=csv.writer(f)
    w.writerow(["menzil","elev","yaw_hata","own_roll","own_pitch","bek_px",
                "sira","conf","bw","bh","bcx","bcy"])
    n=0; t0=time.time(); S=1.718
    while time.time()-t0 < 200:
        R,ez,hy,dz = ucus.istasyon(cev, 0.35 if R>45 else (0.12 if R>22 else -0.05))
        if R < 14: break
        img=np.array(sct.grab(BOLGE))[:,:,:3]
        if not ucusta_mi(img): oyunu_one_al(); time.sleep(0.4); continue
        rr,pp,yy = d.get_drone_rotation()
        r=m.predict(img[:,:,::-1],imgsz=1920,conf=0.10,verbose=False)[0]
        elev=math.degrees(math.asin(max(-1,min(1,dz/R)))); bp=531.4*S/R
        ort=[f"{R:.2f}",f"{elev:.2f}",f"{hy:.2f}",f"{rr:.2f}",f"{pp:.2f}",f"{bp:.2f}"]
        bl=sorted(r.boxes,key=lambda x:-float(x.conf))[:5]
        if not bl: w.writerow(ort+[-1,0,0,0,0,0])
        for i,b in enumerate(bl):
            x1,y1,x2,y2=b.xyxy[0].tolist()
            w.writerow(ort+[i,f"{float(b.conf):.3f}",f"{x2-x1:.1f}",f"{y2-y1:.1f}",
                            f"{(x1+x2)/2:.1f}",f"{(y1+y2)/2:.1f}"])
        n+=1
        if n%40==0: print(f"    n={n} R={R:.0f} m", flush=True)
        time.sleep(0.003)
    f.close(); print(f"BİTTİ: {n} kare", flush=True)
finally:
    ucus.guvenli_komut()
    try: d.disconnect()
    except Exception: pass
