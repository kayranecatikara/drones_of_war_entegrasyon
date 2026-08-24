# -*- coding: utf-8 -*-
"""
================================================================================
DEDEKTÖR HIZ + KALİTE TEZGÂHI — çevrimdışı, EŞLEŞTİRİLMİŞ
================================================================================
NEDEN: "ONNX/FP16 hızlandırır" bir HİPOTEZDİR. Hızı ölçmek kolay, ama hız
kaliteyi bozarsa değersizdir. Bu tezgâh AYNI karelerde hem süreyi hem
GERÇEK TESPİT oranını (truth-eşleşmeli, tespit_olcu.py tanımı) ölçer.

⚠ Bu ÇEVRİMDIŞI ölçümdür -> HİPOTEZ üretir, KARAR vermez (CLAUDE.md §2).
   Karar taze uçuş + video ile verilir.

ZAMANLAMA DİSİPLİNİ:
  * her kol için 10 kare ısınma (CUDA çekirdek derlemesi, cuDNN autotune)
  * her ölçümden önce/sonra torch.cuda.synchronize() -> asenkron GPU
    çağrısını "bitmiş" sanmayı engeller
  * medyan ve p90 raporlanır (ortalama tek bir takılmayla kayar)
================================================================================
"""
import argparse, csv, os, statistics as st, sys, time
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gorus import kamera as KAM


def _f(r, k):
    try:
        v = float(r[k]);  return v if v == v else None
    except (KeyError, TypeError, ValueError):
        return None


def kareleri_yukle(dizinler, n_max):
    """(img_bgr, bek_cx, bek_cy, bek_w) listesi — yalnız hedefin KADRAJDA
    olduğu kareler (payda tespit_olcu.py ile aynı olsun)."""
    veri = []
    for d in dizinler:
        mp = os.path.join(d, "meta.csv")
        if not os.path.exists(mp): continue
        with open(mp) as fh:
            for r in csv.DictReader(fh):
                bx, by, bw = _f(r,"bek_cx"), _f(r,"bek_cy"), _f(r,"bek_w")
                if bx is None or bw is None or bw <= 0: continue
                if not (0 <= bx < KAM.IMG_W and 0 <= by < KAM.IMG_H): continue
                p = os.path.join(d, "kareler", "f%04d.jpg" % int(r["kare"]))
                if not os.path.exists(p): continue
                veri.append((p, bx, by, bw))
                if len(veri) >= n_max: break
        if len(veri) >= n_max: break
    out = []
    for p, bx, by, bw in veri:
        im = cv2.imread(p)
        if im is not None: out.append((im, bx, by, bw))
    return out


def gercek_mi(kutu, bx, by, bw):
    """tespit_olcu.py ile AYNI tanım: merkez tol içinde + boyut 0.5-2.0x."""
    if kutu is None: return False
    cx, cy, w = kutu[0], kutu[1], kutu[2]
    tol = max(60.0, 1.5 * bw)
    if (cx-bx)**2 + (cy-by)**2 > tol*tol: return False
    return 0.5*bw <= w <= 2.0*bw


# --------------------------------------------------------------- kollar
class KolPT:
    """ultralytics .pt — fp32 ya da fp16 (half)."""
    def __init__(self, yol, imgsz, half, conf):
        from ultralytics import YOLO
        self.m = YOLO(yol); self.imgsz=imgsz; self.half=half; self.conf=conf
        self.ad = "pt%d%s" % (imgsz, "_fp16" if half else "_fp32")
    def cikar(self, img):
        r = self.m.predict(img, imgsz=self.imgsz, conf=self.conf,
                           half=self.half, verbose=False)[0]
        self.sp = r.speed
        if not len(r.boxes): return None
        b = max(r.boxes, key=lambda x: float(x.conf))
        x1,y1,x2,y2 = b.xyxy[0].tolist()
        return ((x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1, float(b.conf))


class KolKirp:
    """⭐ YEREL PENCERE (ROI) — hedefin etrafından NATIF çözünürlükte kare kes.

    NEDEN BU EŞDEĞER: kaynak kadraj 1920x1080; ultralytics imgsz=1920
    dediğimizde uzun kenarı 1920'ye ölçekler -> ölçek katsayısı TAM 1.0.
    Yani hâlihazırda NATİF piksel besliyoruz, sadece 1920x1088'e dolgu var.
    Hedefin etrafından PxP natif kare kesmek, hedefin piksellerini
    DEĞİŞTİRMEZ; yalnız ağın taradığı alanı P²/(1920·1088) kadar küçültür.
    P=640 icin bu 1/5.3 -> çıkarım aynı oranda ucuzlar.

    ⚠ VARSAYIM: hedefin NEREDE olduğunu önceki karedeki KENDİ kutumuzdan
      biliyoruz (GPS yok — §10 uyumlu, tıpkı YEREL_KAPI gibi).
      Kutu yoksa ya da pencere ıskalarsa TAM KADRAJA düşülür.
    """
    def __init__(self, yol, pencere, imgsz_tam, half, conf):
        from ultralytics import YOLO
        self.m = YOLO(yol); self.P=pencere; self.tam=imgsz_tam
        self.half=half; self.conf=conf; self.son=None
        self.kirp_say = 0; self.tam_say = 0
        self.ad = "kirp%d%s" % (pencere, "_fp16" if half else "_fp32")

    def _tahmin(self, im, imgsz):
        r = self.m.predict(im, imgsz=imgsz, conf=self.conf,
                           half=self.half, verbose=False)[0]
        self.sp = r.speed
        if not len(r.boxes): return None
        b = max(r.boxes, key=lambda x: float(x.conf))
        x1,y1,x2,y2 = b.xyxy[0].tolist()
        return ((x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1, float(b.conf))

    def cikar(self, img):
        H, W = img.shape[:2]; P = self.P
        if self.son is not None:
            x0 = int(min(max(self.son[0]-P/2, 0), W-P))
            y0 = int(min(max(self.son[1]-P/2, 0), H-P))
            alt = np.ascontiguousarray(img[y0:y0+P, x0:x0+P])
            k = self._tahmin(alt, P)
            self.kirp_say += 1
            if k is not None:
                k = (k[0]+x0, k[1]+y0, k[2], k[3], k[4])
                self.son = k
                return k
            self.son = None          # pencere ıskaladı -> gelecek kare TAM
            return None
        k = self._tahmin(img, self.tam)
        self.tam_say += 1
        self.son = k
        return k

    def sifirla(self): self.son=None; self.kirp_say=0; self.tam_say=0


def olc(kol, kareler, isinma=10):
    import torch
    for im,_,_,_ in kareler[:isinma]: kol.cikar(im)
    torch.cuda.synchronize()
    sure, dogru, ham = [], 0, 0
    pre, inf, post = [], [], []
    for im, bx, by, bw in kareler:
        t0 = time.perf_counter()
        k = kol.cikar(im)
        torch.cuda.synchronize()
        sure.append((time.perf_counter()-t0)*1000.0)
        sp = getattr(kol, "sp", None)
        if sp: pre.append(sp["preprocess"]); inf.append(sp["inference"]); post.append(sp["postprocess"])
        if k is not None:
            ham += 1
            if gercek_mi(k, bx, by, bw): dogru += 1
    n = len(kareler)
    return dict(ad=kol.ad, n=n,
                ms=st.median(sure), p90=sorted(sure)[int(0.9*n)-1],
                pre=st.median(pre) if pre else 0.0,
                inf=st.median(inf) if inf else 0.0,
                post=st.median(post) if post else 0.0,
                ham=100.0*ham/n, gercek=100.0*dogru/n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dizinler", nargs="+")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--conf", type=float, default=0.40)
    ap.add_argument("--imgsz", type=int, default=1920)
    a = ap.parse_args()

    kareler = kareleri_yukle(a.dizinler, a.n)
    print("yuklenen kare: %d (hedef kadrajda, truth eslesmeli)" % len(kareler))
    print("kutu_beklenen_px medyan: %.1f" % st.median([k[3] for k in kareler]))

    M = "modeller/talon_v3.pt"
    kollar = [KolPT(M, a.imgsz, False, a.conf),
              KolPT(M, a.imgsz, True,  a.conf),
              KolKirp(M, 960, a.imgsz, True, a.conf),
              KolKirp(M, 640, a.imgsz, True, a.conf),
              KolKirp(M, 448, a.imgsz, True, a.conf)]
    satirlar = []
    for k in kollar:
        if hasattr(k, "sifirla"): k.sifirla()
        s = olc(k, kareler)
        if hasattr(k, "kirp_say"):
            s["kirp%"] = 100.0*k.kirp_say/max(1, k.kirp_say+k.tam_say)
        satirlar.append(s)

    print("\n%-14s %4s %8s %8s %7s %7s %8s %9s %7s" %
          ("kol","n","ms_med","ms_p90","on_ms","cik_ms","ham%","gercek%","kirp%"))
    print("-"*86)
    for s in satirlar:
        print("%-14s %4d %8.1f %8.1f %7.1f %7.1f %8.1f %9.1f %7s" %
              (s["ad"], s["n"], s["ms"], s["p90"], s["pre"], s["inf"],
               s["ham"], s["gercek"],
               ("%.0f" % s["kirp%"]) if "kirp%" in s else "-"))
