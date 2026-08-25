# -*- coding: utf-8 -*-
"""
================================================================================
MOTOR ÖLÇ — dört çıkarım yolunu AYRI SÜREÇLERDE kıyasla
================================================================================
    1. .pt  fp32      (bugünkü varsayılan)
    2. .pt  fp16
    3. .engine fp16   (TensorRT)
    4. .onnx          (onnxruntime, CUDA EP)

⛔ HER YOL AYRI SÜREÇTE ÖLÇÜLÜR. Aynı süreçte arka arkaya ölçmek sonucu
   BOZUYOR: CUDA bağlamı, cuDNN autotune önbelleği ve bellek havuzu ilk
   yükten sonra ısınmış kalıyor, sonrakiler haksız avantaj alıyor.
   (Yer-kontrol deposu da aynı tuzağa düşmüş: dört modeli tek süreçte
   ölçünce 50 ms çıkan model, ayrı süreçte 10.2 ms çıkmış.)

⛔ FP16 SESSİZCE YOK SAYILIR. ultralytics'te predictor bir kez kurulduktan
   sonra `predict(half=True)` ETKİSİZDİR — model fp32 kalır ve ölçüm
   "fp16 fayda vermedi" yalanını üretir. Bu yüzden fp16 yolu, gerçek
   hassasiyeti uygulayan `Dedektor` sınıfı üzerinden ölçülür.

⚠ TensorRT 11 NOTU: `BuilderFlag.FP16` bu sürümde YOK; motorun hassasiyeti
   ONNX'ten gelir (bkz. `motor_uret.py`).

DOĞRULUK: hız kıyası tek başına yetmez — her yol için "kutulu kare sayısı"
ve "medyan en yüksek güven" de basılır. Bunlar ayrışıyorsa hız kazancı
BEDAVA DEĞİLDİR ve ayrıca truth doğrulamalı ölçüm gerekir.

Kullanım:  python3 araclar/motor_olc.py [kare_dizini]
================================================================================
"""
import json
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARSAYILAN_KARE = "logs/TAKIP3_K_1/k01/kareler"

# Alt süreçte koşan ölçüm gövdesi. Tek bir yolu ölçer, JSON basar.
COCUK = r'''
import os,sys,time,json,statistics as st,warnings,logging
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
sys.path.insert(0, sys.argv[1])
os.chdir(sys.argv[1])
yol_turu, kare_d, imgsz = sys.argv[2], sys.argv[3], int(sys.argv[4])
import numpy as np, cv2
kar = [cv2.imread(os.path.join(kare_d,f)) for f in sorted(os.listdir(kare_d))[:40]]
kar = [k for k in kar if k is not None]
sonuc = {"yol": yol_turu, "n_kare": len(kar)}

def bitir(sure, kutulu, confs):
    sonuc["ms"] = st.median(sure); sonuc["p90"] = float(np.percentile(sure,90))
    sonuc["kutulu"] = kutulu
    sonuc["conf"] = st.median(confs) if confs else -1.0
    print("JSON:"+json.dumps(sonuc)); sys.exit(0)

if yol_turu in ("pt_fp32","pt_fp16"):
    import torch
    from dow.gorus import dedektor as D
    D.DetCfg.FP16 = (yol_turu == "pt_fp16")
    D.IMGSZ_UZAK = imgsz
    d = D.Dedektor(uyarlanabilir=False)
    rgb = [cv2.cvtColor(k, cv2.COLOR_BGR2RGB) for k in kar]
    d.isit(rgb[0]); d._hassasiyet_uygula()
    for _ in range(6): d.bul(rgb[0])
    torch.cuda.synchronize()
    s=[]; n=0; c=[]
    for k in rgb:
        t=time.perf_counter(); b=d.bul(k)
        torch.cuda.synchronize(); s.append((time.perf_counter()-t)*1000)
        if b: n+=1; c.append(float(b[4]))
    sonuc["fp16_gercekten"] = bool(d._fp16)
    bitir(s,n,c)

if yol_turu == "engine":
    import torch
    from ultralytics import YOLO
    m = YOLO(sys.argv[5], task="detect")
    for _ in range(6): m.predict(kar[0], imgsz=imgsz, conf=0.4, verbose=False)
    torch.cuda.synchronize()
    s=[]; n=0; c=[]
    for k in kar:
        t=time.perf_counter(); r=m.predict(k,imgsz=imgsz,conf=0.4,verbose=False)[0]
        torch.cuda.synchronize(); s.append((time.perf_counter()-t)*1000)
        b=r.boxes
        if b is not None and len(b): n+=1; c.append(float(b.conf.max()))
    bitir(s,n,c)

if yol_turu == "onnx":
    import onnxruntime as ort
    so = ort.SessionOptions(); so.log_severity_level = 3
    sess = ort.InferenceSession(sys.argv[5], so,
                                providers=["CUDAExecutionProvider","CPUExecutionProvider"])
    sonuc["saglayici"] = sess.get_providers()[0]
    gir = sess.get_inputs()[0]
    _, _, H, W = gir.shape
    tip = np.float16 if "float16" in gir.type else np.float32
    def hazirla(im):
        # ultralytics letterbox'ı ile AYNI: uzun kenarı W'ye ölçekle, ortala
        h0,w0 = im.shape[:2]; r = min(W/w0, H/h0)
        nw,nh = int(round(w0*r)), int(round(h0*r))
        rs = cv2.resize(im,(nw,nh))
        tuval = np.full((H,W,3),114,np.uint8)
        y0,x0 = (H-nh)//2,(W-nw)//2
        tuval[y0:y0+nh, x0:x0+nw] = rs
        x = cv2.cvtColor(tuval,cv2.COLOR_BGR2RGB).transpose(2,0,1)[None]
        return np.ascontiguousarray(x, dtype=tip)/tip(255.0)
    girdiler=[hazirla(k) for k in kar]
    ad = gir.name
    for _ in range(6): sess.run(None, {ad: girdiler[0]})
    s=[]; n=0; c=[]
    for g in girdiler:
        t=time.perf_counter(); o=sess.run(None,{ad:g})
        s.append((time.perf_counter()-t)*1000)
        y=np.asarray(o[0])                      # (1, 4+nc, N)
        if y.ndim==3 and y.shape[1]>=5:
            sk=y[0,4:,:].max()
            if sk>=0.4: n+=1; c.append(float(sk))
    bitir(s,n,c)
'''


def kos(yol_turu, kare_d, imgsz, dosya=None):
    argv = [sys.executable, "-W", "ignore", "-c", COCUK, KOK, yol_turu,
            kare_d, str(imgsz)]
    if dosya:
        argv.append(dosya)
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        return {"yol": yol_turu, "hata": "zaman aşımı"}
    for satir in r.stdout.splitlines():
        if satir.startswith("JSON:"):
            return json.loads(satir[5:])
    son = (r.stderr or r.stdout).strip().splitlines()
    return {"yol": yol_turu, "hata": son[-1][:120] if son else "çıktı yok"}


def main():
    kare_d = sys.argv[1] if len(sys.argv) > 1 else VARSAYILAN_KARE
    if not os.path.isdir(os.path.join(KOK, kare_d)):
        print("⛔ kare dizini yok: %s" % kare_d); return
    eng = "modeller/talon_v3_1920_fp16.engine"
    onx = "modeller/talon_v3_1920_fp16.onnx"
    isler = [("pt_fp32", ".pt fp32  (BUGÜNKÜ)", None),
             ("pt_fp16", ".pt fp16", None),
             ("engine", ".engine fp16 (TensorRT)", eng),
             ("onnx", ".onnx (onnxruntime CUDA)", onx)]

    print("\n" + "=" * 76)
    print("  ÇIKARIM YOLU KIYASI — imgsz 1920, AYRI SÜREÇLER, oyun KAPALI")
    print("=" * 76)
    print("  %-26s %9s %9s %11s %8s" % ("", "medyan ms", "FPS", "kutulu kare",
                                        "conf"))
    print("  " + "-" * 72)
    taban = None
    for tur, ad, dosya in isler:
        if dosya and not os.path.exists(os.path.join(KOK, dosya)):
            print("  %-26s   (dosya yok — üretilmedi)" % ad); continue
        s = kos(tur, kare_d, 1920, dosya)
        if "hata" in s:
            print("  %-26s   ⛔ %s" % (ad, s["hata"])); continue
        if taban is None:
            taban = s["ms"]
        kat = taban / s["ms"]
        ek = ""
        if tur == "pt_fp16" and not s.get("fp16_gercekten", True):
            ek = "  ⚠ fp16 UYGULANMADI"
        if tur == "onnx":
            ek = "  [%s]" % s.get("saglayici", "?")
        print("  %-26s %9.1f %9.1f %7d/%-3d %8.3f  %.2fx%s"
              % (ad, s["ms"], 1000 / s["ms"], s["kutulu"], s["n_kare"],
                 s["conf"], kat, ek))
    print("=" * 76)
    print("  ⚠ Bu ölçüm OYUN KAPALIYKEN. Uçuşta GPU oyunla paylaşılır ve")
    print("    süreler ~1.5-3 kat artar. Kabul kararı taze uçuşla verilir (§2).\n")


if __name__ == "__main__":
    main()
