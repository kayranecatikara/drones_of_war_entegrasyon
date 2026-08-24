# -*- coding: utf-8 -*-
"""
================================================================================
Q1 — KIRPMA TESPİTİ BOZUYOR MU? (eşleştirilmiş, menzil bantlı)
================================================================================
Tasarım: AYNI karede iki kol koşulur.
  A) TAM   : imgsz=1920 tam kadraj (mevcut sistem)
  B) KIRP-P: hedefin TRUTH konumu merkezli PxP NATİF kare, imgsz=P

Pencere truth ile merkezlenir — çünkü bu soru "pencere hedefi buluyor mu"
DEĞİL, "hedef pencerenin İÇİNDEYKEN ağ onu tam kadrajdaki kadar iyi
görüyor mu" sorusudur. İzleme sorusu (Q2) ayrı ölçülür.

Ölçüt: tespit_olcu.py'nin GERÇEK TESPİT tanımı (merkez tol içinde +
boyut 0.5-2.0x). Bantlar beklenen kutu genişliğine göre (= menzil).
  R = 997 / w_px  ->  w=20px:50m, 30px:33m, 45px:22m, 70px:14m
================================================================================
"""
import argparse, csv, glob, os, statistics as st, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gorus import kamera as KAM

BANTLAR = [(0,25,"<25px  >40m"), (25,40,"25-40  25-40m"),
           (40,70,"40-70  14-25m"), (70,1e9,">70px  <14m")]

def _f(r,k):
    try:
        v=float(r[k]); return v if v==v else None
    except Exception: return None

def kareler(dizinler, bant_hedef):
    out=[]
    for d in dizinler:
        mp=os.path.join(d,"meta.csv")
        if not os.path.exists(mp): continue
        with open(mp) as fh:
            for r in csv.DictReader(fh):
                bx,by,bw=_f(r,"bek_cx"),_f(r,"bek_cy"),_f(r,"bek_w")
                if bx is None or bw is None or bw<=0: continue
                if not (0<=bx<KAM.IMG_W and 0<=by<KAM.IMG_H): continue
                lo,hi,_=bant_hedef
                if not (lo<=bw<hi): continue
                p=os.path.join(d,"kareler","f%04d.jpg"%int(r["kare"]))
                if os.path.exists(p): out.append((p,bx,by,bw))
    return out

def gercek_mi(k,bx,by,bw):
    if k is None: return False
    tol=max(60.0,1.5*bw)
    if (k[0]-bx)**2+(k[1]-by)**2 > tol*tol: return False
    return 0.5*bw <= k[2] <= 2.0*bw

def en_iyi(m,im,imgsz,conf,half):
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
    ap.add_argument("--pencereler",default="960,640,448")
    a=ap.parse_args()

    dizinler=sorted(glob.glob(a.kok+"/*/*t[0-9]*"))+sorted(glob.glob(a.kok+"/*/k[0-9]*"))
    dizinler=[d for d in dizinler if os.path.exists(d+"/meta.csv")]
    from ultralytics import YOLO
    m=YOLO("modeller/talon_v3.pt")
    Ps=[int(x) for x in a.pencereler.split(",")]
    for _ in range(3): m.predict(np.zeros((1080,1920,3),np.uint8),imgsz=1920,verbose=False,half=True)

    print("%-16s %5s %8s %s" % ("bant","n","TAM%", "  ".join("KIRP%d%%"%p for p in Ps)))
    print("-"*62)
    for bant in BANTLAR:
        ks=kareler(dizinler,bant)[:a.n]
        if len(ks)<20:
            print("%-16s %5d   (yetersiz)"%(bant[2],len(ks))); continue
        tam=0; kirp={p:0 for p in Ps}
        for p_,bx,by,bw in ks:
            im=cv2.imread(p_)
            if im is None: continue
            if gercek_mi(en_iyi(m,im,1920,a.conf,True),bx,by,bw): tam+=1
            H,W=im.shape[:2]
            for P in Ps:
                x0=int(min(max(bx-P/2,0),W-P)); y0=int(min(max(by-P/2,0),H-P))
                alt=np.ascontiguousarray(im[y0:y0+P,x0:x0+P])
                k=en_iyi(m,alt,P,a.conf,True)
                if k is not None: k=(k[0]+x0,k[1]+y0,k[2],k[3],k[4])
                if gercek_mi(k,bx,by,bw): kirp[P]+=1
        n=len(ks)
        print("%-16s %5d %8.1f %s"%(bant[2],n,100.0*tam/n,
              "  ".join("%7.1f"%(100.0*kirp[p]/n) for p in Ps)))
