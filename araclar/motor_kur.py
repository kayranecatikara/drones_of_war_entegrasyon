# -*- coding: utf-8 -*-
"""
================================================================================
MOTOR KUR — TensorRT `.engine` üret ve kazancı ÖLÇ
================================================================================
NEREDEN GELDİ: `avci-drone-yer-kontrol` deposunun `model-fps` branch'i,
`arac/motor_kur.py`. Orada 7 kat kazanç ölçülmüş (113.5 ms -> 13.1 ms).

⚠ O KAZANÇ BİZDE TEKRARLANMAZ — ölçüldü 2026-08-24:
    onların .pt  : 113.5 ms   (fp16 canlıya uygulanmıyordu)
    bizim  .pt   :  18.4 ms   (imgsz 1920, fp16 — hata bizde düzeltilmiş)
    onların .engine: 13.1 ms
  Yani bizim `.pt` onların `.engine`'inden zaten hızlı. Buradaki soru
  "7 kat" değil, "18.4 ms daha da düşer mi".

⭐ BİZE ÖZGÜ PÜRÜZ — UYARLANABİLİR ÇÖZÜNÜRLÜK
  Dedektörümüz kareye göre imgsz seçiyor (uzak 1920 / yakın 960; eşik
  ölçülmüş, `dedektor.py` başlığına bakın). TensorRT motoru ise SABİT girdi
  boyutuna derlenir. Üç yol var:

    A) İKİ MOTOR (960 + 1920) — uyarlanabilirlik korunur, ama iki motor
       GPU belleğinde durur. Oyun aynı 8 GB'ı kullanıyor: risk.
    B) TEK MOTOR @1920 + uyarlanabilirliği BIRAK — motor 1920'de yeterince
       hızlıysa yakın rejime hiç gerek kalmaz. En sade yol.
    C) DİNAMİK ŞEKİL (dynamic=True) — tek motor iki boyut, ama dinamik
       motorlar statiklerden yavaştır.

  Bu araç A ve B için motorları üretir ve ÜÇÜNÜ DE ölçer; karar ölçümle
  verilir, tahminle değil.

⚠ `.engine` TAŞINMAZ. GPU modeline, sürücü ve TensorRT sürümüne bağlıdır.
  Başka makineden kopyalanan motor ya yüklenmez ya sessizce yanlış çalışır.
  Bu yüzden `.gitignore`'a girer, her makinede yeniden üretilir.

Kullanım:
    python3 araclar/motor_kur.py            # 1920 ve 960 motorlarını üret + ölç
    python3 araclar/motor_kur.py --olc      # üretme, yalnız mevcutları ölç
    python3 araclar/motor_kur.py --imgsz 1920
================================================================================
"""
import argparse
import os
import statistics as st
import sys
import time
import warnings

warnings.filterwarnings("ignore")

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

KARE_D = os.path.join(KOK, "logs/BOSLUK/k02/kareler")   # ölçüm için gerçek kareler


def ortam():
    import torch
    print("  --- ORTAM ---")
    print("    torch      : %s" % torch.__version__)
    ok = torch.cuda.is_available()
    print("    CUDA       : %s" % ok)
    if ok:
        print("    GPU        : %s" % torch.cuda.get_device_name(0))
    try:
        import tensorrt
        print("    tensorrt   : %s" % tensorrt.__version__)
    except Exception as e:
        print("    tensorrt   : ⛔ YOK (%r)" % (e,)); return False
    return ok


def uret(pt_yol, imgsz, zorla=False):
    """`<model>_<imgsz>.engine` üret. Zaten varsa atla."""
    from ultralytics import YOLO
    hedef = pt_yol[:-3] + "_%d.engine" % imgsz
    if os.path.exists(hedef) and not zorla:
        print("    ✔ zaten var: %s" % os.path.basename(hedef)); return hedef
    print("    ⏳ derleniyor imgsz=%d  (2-4 dk, GPU'yu meşgul eder)..." % imgsz)
    t0 = time.time()
    m = YOLO(pt_yol)
    cikti = m.export(format="engine", imgsz=imgsz, half=True, device=0, verbose=False)
    if os.path.abspath(cikti) != os.path.abspath(hedef):
        os.replace(cikti, hedef)
    print("    ✔ HAZIR  %.1f MB  %.0f sn"
          % (os.path.getsize(hedef) / 1e6, time.time() - t0))
    return hedef


def olc(yol, imgsz, n=40):
    """Gerçek karelerde medyan çıkarım süresi (ms) + bulunan kutu sayısı."""
    import cv2
    import torch
    from ultralytics import YOLO
    if not os.path.isdir(KARE_D):
        print("    ⚠ ölçüm karesi yok: %s" % KARE_D); return None
    kareler = [cv2.imread(os.path.join(KARE_D, f))
               for f in sorted(os.listdir(KARE_D))[:n]]
    kareler = [k for k in kareler if k is not None]
    m = YOLO(yol, task="detect")
    for k in kareler[:5]:
        m.predict(k, imgsz=imgsz, conf=0.10, verbose=False)
    torch.cuda.synchronize()
    sure, kutu = [], 0
    for k in kareler:
        t = time.perf_counter()
        r = m.predict(k, imgsz=imgsz, conf=0.10, verbose=False)[0]
        torch.cuda.synchronize()
        sure.append((time.perf_counter() - t) * 1000.0)
        kutu += len(r.boxes) if r.boxes is not None else 0
    return st.median(sure), kutu, len(kareler)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imgsz", type=int, nargs="*", default=[1920, 960])
    ap.add_argument("--olc", action="store_true", help="üretme, yalnız ölç")
    ap.add_argument("--zorla", action="store_true")
    a = ap.parse_args()

    if not ortam():
        print("\n⛔ TensorRT/CUDA hazır değil — motor üretilemez.\n"); return

    from dow.gorus.dedektor import MODEL_YOLU
    pt = os.path.join(KOK, MODEL_YOLU)
    print("\n  --- MODEL --- %s" % pt)
    if not os.path.exists(pt):
        print("    ⛔ model yok"); return

    sonuc = []
    print("\n  --- TABAN (.pt) ---")
    for iz in a.imgsz:
        r = olc(pt, iz)
        if r:
            print("    .pt      imgsz=%-5d : %6.1f ms   (%d kutu / %d kare)" % (iz, r[0], r[1], r[2]))
            sonuc.append((".pt", iz, r[0], r[1]))

    print("\n  --- MOTOR (.engine) ---")
    for iz in a.imgsz:
        try:
            yol = (pt[:-3] + "_%d.engine" % iz) if a.olc else uret(pt, iz, a.zorla)
            if not os.path.exists(yol):
                print("    ⚠ motor yok: %s" % os.path.basename(yol)); continue
            r = olc(yol, iz)
            if r:
                print("    .engine  imgsz=%-5d : %6.1f ms   (%d kutu / %d kare)" % (iz, r[0], r[1], r[2]))
                sonuc.append((".engine", iz, r[0], r[1]))
        except Exception as e:
            print("    ⛔ imgsz=%d başarısız: %r" % (iz, e))

    print("\n  --- KARAR VERİSİ ---")
    for iz in a.imgsz:
        p = next((x for x in sonuc if x[0] == ".pt" and x[1] == iz), None)
        e = next((x for x in sonuc if x[0] == ".engine" and x[1] == iz), None)
        if p and e:
            print("    imgsz=%-5d  %.1f -> %.1f ms  (%.2f kat)  kutu %d vs %d %s"
                  % (iz, p[2], e[2], p[2] / max(e[2], 1e-9), p[3], e[3],
                     "✔ AYNI" if p[3] == e[3] else "⚠ FARKLI — doğruluk sınanmalı"))
    print("\n  ⚠ Bu ölçüm OYUN KAPALIYKEN yapıldı. Uçuşta GPU oyunla paylaşılır")
    print("     ve süreler ~2 kat artar (ölçüldü: 18.4 ms -> 35-47 ms).")
    print("     Kabul kararı taze uçuşla verilir (§2).\n")


if __name__ == "__main__":
    main()
