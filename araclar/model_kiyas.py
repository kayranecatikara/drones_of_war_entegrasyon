# -*- coding: utf-8 -*-
"""
================================================================================
MODEL KIYASI — v3 vs v5, AYNI karelerde, KAPI YOKMUŞ GİBİ
================================================================================
NİYE BÖYLE ÖLÇÜLÜYOR: yerellik kapısını kaldırmayı düşünüyoruz. Kapı yokken
güdüm dedektörün EN YÜKSEK GÜVENLİ kutusunu (argmax) doğrudan kullanır.
O yüzden burada da argmax alınır, hiçbir eleme yapılmaz — ölçüm, kapısız
sistemin göreceği şeyin ta kendisidir.

ÜÇ SAYI (truth ile eşlenmiş, tespit_olcu.py tanımı):
  gercek%  : argmax kutusu HEDEFİN üstünde            -> yüksek olmalı
  yanlis%  : kutu VAR ama hedefte DEĞİL (= OSD vb.)   -> ⭐ SIFIRA yakın olmalı
  bos%     : hiç kutu yok                             -> düşük olmalı
`yanlis%` kapının varlık sebebidir. Sıfıra inerse kapı gereksizleşir.
================================================================================
"""
import argparse, csv, glob, os, statistics as st, sys, time
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gorus import kamera as KAM

BANTLAR = [(0,25,"<25px   >40 m"), (25,40,"25-40   25-40 m"),
           (40,70,"40-70   14-25 m"), (70,150,"70-150   7-14 m"),
           (150,10000,">150px   <7 m")]

def _f(r,k):
    try:
        v=float(r[k]); return v if v==v else None
    except Exception: return None

def kareler(dizinler, lo, hi, n_max):
    out=[]
    for d in dizinler:
        mp=os.path.join(d,"meta.csv")
        if not os.path.exists(mp): continue
        for r in csv.DictReader(open(mp)):
            bx,by,bw=_f(r,"bek_cx"),_f(r,"bek_cy"),_f(r,"bek_w")
            if bx is None or bw is None or bw<=0: continue
            if not (0<=bx<KAM.IMG_W and 0<=by<KAM.IMG_H): continue
            if not (lo<=bw<hi): continue
            p=os.path.join(d,"kareler","f%04d.jpg"%int(r["kare"]))
            if os.path.exists(p): out.append((p,bx,by,bw))
            if len(out)>=n_max: return out
    return out

def gercek_mi(k,bx,by,bw):
    if k is None: return False
    tol=max(60.0,1.5*bw)
    if (k[0]-bx)**2+(k[1]-by)**2 > tol*tol: return False
    return 0.5*bw <= k[2] <= 2.0*bw

def argmax(m,im,imgsz,conf,half):
    r=m.predict(im,imgsz=imgsz,conf=conf,half=half,verbose=False)[0]
    if not len(r.boxes): return None
    b=max(r.boxes,key=lambda x:float(x.conf))
    x1,y1,x2,y2=b.xyxy[0].tolist()
    return ((x1+x2)/2,(y1+y2)/2,x2-x1,y2-y1,float(b.conf))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--kok",default="logs")
    ap.add_argument("--n",type=int,default=120)
    ap.add_argument("--conf",type=float,default=0.40)
    ap.add_argument("--imgsz",type=int,default=1920)
    ap.add_argument("--modeller",default="talon_v3,talon_v5")
    a=ap.parse_args()

    dz=sorted(glob.glob(a.kok+"/*/*t[0-9]*"))+sorted(glob.glob(a.kok+"/*/k[0-9]*"))
    dz=[d for d in dz if os.path.exists(d+"/meta.csv")]
    from ultralytics import YOLO
    adlar=a.modeller.split(",")
    M={ad:YOLO("modeller/%s.pt"%ad) for ad in adlar}
    bos=np.zeros((1080,1920,3),np.uint8)
    for m in M.values():
        for _ in range(3): m.predict(bos,imgsz=a.imgsz,verbose=False,half=True)

    print("KAPI YOK — düz argmax, conf %.2f, imgsz %d" % (a.conf, a.imgsz))
    print()
    bas = "%-18s %5s" % ("bant","n")
    for ad in adlar: bas += "  | %-8s %-8s %-7s %-7s" % (ad+" gercek%","yanlis%","bos%","ms")
    print(bas); print("-"*len(bas))
    toplam={ad:[0,0,0,[]] for ad in adlar}
    for lo,hi,etiket in BANTLAR:
        ks=kareler(dz,lo,hi,a.n)
        if len(ks)<20:
            print("%-18s %5d  (yetersiz)"%(etiket,len(ks))); continue
        say={ad:[0,0,0,[]] for ad in adlar}
        for p,bx,by,bw in ks:
            im=cv2.imread(p)
            if im is None: continue
            for ad in adlar:
                t0=time.perf_counter()
                k=argmax(M[ad],im,a.imgsz,a.conf,True)
                say[ad][3].append((time.perf_counter()-t0)*1000)
                if k is None: say[ad][2]+=1
                elif gercek_mi(k,bx,by,bw): say[ad][0]+=1
                else: say[ad][1]+=1
        n=len(ks); sat="%-18s %5d" % (etiket,n)
        for ad in adlar:
            g,y,b,ms=say[ad]
            for i in range(3): toplam[ad][i]+=say[ad][i]
            toplam[ad][3]+=ms
            sat += "  | %-8.1f %-8.1f %-7.1f %-7.1f" % (100*g/n,100*y/n,100*b/n,st.median(ms))
        print(sat)
    print("-"*len(bas))
    sat="%-18s %5d" % ("TOPLAM", sum(toplam[adlar[0]][:3]))
    for ad in adlar:
        g,y,b,ms=toplam[ad]; n=g+y+b
        sat += "  | %-8.1f %-8.1f %-7.1f %-7.1f" % (100*g/n,100*y/n,100*b/n,st.median(ms))
    print(sat)
