# -*- coding: utf-8 -*-
"""
================================================================================
MOTOR ÜRET — ONNX'ten TensorRT `.engine` (ultralytics'i BYPASS ederek)
================================================================================
⛔ NEDEN ULTRALYTICS'İN `export(format="engine")` KULLANILMIYOR:

  ultralytics 8.4.103 TensorRT dışa aktarımında `nvidia-modelopt[onnx]>=0.44`
  istiyor ve BULAMAYINCA KENDİ KENDİNE KURMAYA ÇALIŞIYOR (AutoUpdate).
  O paketin bağımlılık ağacı ÖLÇÜLDÜ (`pip install --dry-run`, 2026-08-24):

      numpy 2.2.6      <- opencv 4.9 ile ÇÖKER (cv2 import edilemez)
      torch 2.13.0     <- 2.5.1+cu121'in YERİNE, CUDA 13 ile
      cuda-toolkit 13.0.3, nvidia-cudnn-cu13, nvidia-nccl-cu13, cupy-cuda12x...

  Yani tek bir dışa aktarım komutu TÜM ORTAMI deviriyor. Bu, README'de
  uyardığımız numpy<2 tuzağının ta kendisi ve SESSİZCE oluyor.

  Bu araç ONNX dosyasını doğrudan TensorRT `Builder` + `OnnxParser` ile
  derler; ultralytics'e hiç dokunmaz, hiçbir paket kurmaz.

⚠ `.engine` TAŞINMAZ: GPU mimarisine, sürücü ve TensorRT sürümüne özeldir.
  `.gitignore`'da; her makinede yeniden üretilir.

⚠ SABİT GİRDİ ŞEKLİ: motor tek bir imgsz'e derlenir. Dedektörümüz
  uyarlanabilir (960/1920), o yüzden İKİ motor üretilir ve dedektör hangisini
  seçerse onu yükler.

Kullanım:
    python3 araclar/motor_uret.py                 # 1920 ve 960
    python3 araclar/motor_uret.py --imgsz 1920
    python3 araclar/motor_uret.py --fp32          # fp16 kapalı (kıyas için)
================================================================================
"""
import argparse
import os
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


def onnx_uret(pt_yol, imgsz, fp16=True):
    """ultralytics ile YALNIZ ONNX (bu adım modelopt istemiyor).

    ⚠ HASSASİYET BURADA BELİRLENİR. TensorRT 11 "strongly typed" ağlara
    geçti: `BuilderFlag.FP16` ARTIK YOK (ölçüldü — mevcut bayraklar:
    TF32, SPARSE_WEIGHTS, REFIT... FP16/INT8 listede değil). Motorun
    hassasiyeti ONNX modelinin kendi tiplerinden geliyor, o yüzden fp16
    motoru için ONNX de fp16 dışa aktarılmalı."""
    hedef = pt_yol[:-3] + "_%d%s.onnx" % (imgsz, "_fp16" if fp16 else "")
    if os.path.exists(hedef):
        print("    ✔ ONNX zaten var: %s" % os.path.basename(hedef))
        return hedef
    from ultralytics import YOLO
    print("    ⏳ ONNX dışa aktarılıyor (imgsz=%d)..." % imgsz)
    m = YOLO(pt_yol)
    cikti = m.export(format="onnx", imgsz=imgsz, opset=17, simplify=False,
                     dynamic=False, half=fp16, device=0, verbose=False)
    if os.path.abspath(cikti) != os.path.abspath(hedef):
        os.replace(cikti, hedef)
    print("    ✔ %s  (%.1f MB)" % (os.path.basename(hedef),
                                   os.path.getsize(hedef) / 1e6))
    return hedef


def engine_uret(onnx_yol, imgsz, fp16=True, workspace_gb=4):
    """ONNX -> TensorRT engine. SAF TensorRT API; paket kurmaz."""
    import tensorrt as trt
    hedef = onnx_yol[:-5] + ".engine"
    if os.path.exists(hedef):
        print("    ✔ motor zaten var: %s" % os.path.basename(hedef))
        return hedef

    kayit = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(kayit)
    # ⚠ TensorRT 11: `EXPLICIT_BATCH` KALDIRILDI (artık varsayılan).
    #   create_network() argümansız çağrılır; eski sürümlerdeki bayrak
    #   burada AttributeError verir.
    ag = builder.create_network()
    ayrist = trt.OnnxParser(ag, kayit)
    with open(onnx_yol, "rb") as f:
        if not ayrist.parse(f.read()):
            for i in range(ayrist.num_errors):
                print("    ⛔ ONNX ayrıştırma: %s" % ayrist.get_error(i))
            return None

    cfg = builder.create_builder_config()
    try:
        cfg.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE,
                                  workspace_gb * (1 << 30))
    except Exception:
        pass
    # ⚠ TensorRT 11'de `BuilderFlag.FP16` YOK — hassasiyet ONNX'ten gelir
    #   (bkz. onnx_uret notu). Burada yalnız TF32'yi açık bırakıyoruz.

    print("    ⏳ TensorRT derliyor (imgsz=%d, fp16=%s) — 2-5 dk..."
          % (imgsz, fp16))
    t0 = time.time()
    try:
        plan = builder.build_serialized_network(ag, cfg)
    except Exception as e:
        print("    ⛔ derleme hatası: %r" % (e,)); return None
    if plan is None:
        print("    ⛔ derleme None döndü"); return None
    with open(hedef, "wb") as f:
        f.write(plan)
    print("    ✔ %s  (%.1f MB, %.0f sn)"
          % (os.path.basename(hedef), os.path.getsize(hedef) / 1e6,
             time.time() - t0))
    return hedef


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imgsz", type=int, nargs="*", default=[1920, 960])
    ap.add_argument("--fp32", action="store_true")
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    from dow.gorus.dedektor import MODEL_YOLU
    pt = os.path.join(KOK, a.model or MODEL_YOLU)
    if not os.path.exists(pt):
        print("⛔ model yok: %s" % pt); return
    print("\n  MODEL: %s" % pt)
    try:
        import tensorrt as trt
        print("  TensorRT: %s" % trt.__version__)
    except Exception as e:
        print("  ⛔ tensorrt yok (%r)" % (e,)); return

    for iz in a.imgsz:
        print("\n  --- imgsz = %d ---" % iz)
        onnx = onnx_uret(pt, iz, fp16=not a.fp32)
        if onnx:
            engine_uret(onnx, iz, fp16=not a.fp32)

    print("\n  ⚠ Motorlar bu makineye ÖZELDİR; başka bilgisayara kopyalanmaz.")
    print("  Ölçmek için: python3 araclar/motor_olc.py\n")


if __name__ == "__main__":
    main()
