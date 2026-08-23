# -*- coding: utf-8 -*-
"""
================================================================================
KOŞU VİDEOSU — kayıtlı kareleri telemetri yakısıyla birleştir
================================================================================
CLAUDE.md §2 adım 3-4'ün DoW karşılığı. Kullanıcı kuralı: kareler tek tek
İNCELENİR; "iki üç kareye bakıp geçmek yeterli DEĞİLDİR".

Her kareye o anın telemetrisi yakılır (meta.csv'den, kare numarasıyla EŞLİ):
  faz | istasyon hatası | hedefe menzil | hedefin yükselişi | kutu px | güven
Ayrıca çizilir:
  YEŞİL kutu = dedektörün verdiği kutu
  TURUNCU artı = truth geometriden ÖNGÖRÜLEN hedef konumu (tespit anının
                 duruşuyla; `bek_cx/bek_cy` sütunu varsa ondan)
  MAVİ çizgi  = ufuk (hedef bunun ÜSTÜNDEyse arka plan gökyüzü)

    python3 araclar/video.py <kosu_dizini> [cikti.mp4] [fps]
================================================================================
"""
import csv, math, os, subprocess, sys, tempfile
import cv2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gorus import kamera as KAM


def _f(r, k):
    try:
        v = float(r[k]); return v if v == v else None
    except (KeyError, TypeError, ValueError): return None


def yap(dizin, cikti=None, fps=6, olcek=0.6):
    meta = os.path.join(dizin, "meta.csv")
    kdir = os.path.join(dizin, "kareler")
    R = {int(r["kare"]): r for r in csv.DictReader(open(meta))}
    cikti = cikti or os.path.join("logs", os.path.basename(dizin.rstrip("/")) + ".mp4")
    tmp = tempfile.mkdtemp(prefix="dowvid_")
    n = 0
    for k in sorted(R):
        yol = os.path.join(kdir, f"f{k:04d}.jpg")
        if not os.path.exists(yol): continue
        im = cv2.imread(yol)
        if im is None: continue
        r = R[k]
        # --- öngörülen konum + ufuk ---
        bcx, bcy, bw = _f(r, "bek_cx"), _f(r, "bek_cy"), _f(r, "bek_w")
        uf = _f(r, "bek_ufuk_cy")
        if bcx is None:
            hx, hy, hz = _f(r,"hedef_x"), _f(r,"hedef_y"), _f(r,"hedef_z")
            dx, dy, dz = _f(r,"drone_x"), _f(r,"drone_y"), _f(r,"drone_z")
            p, ro, yw = _f(r,"drone_pitch"), _f(r,"drone_roll"), _f(r,"drone_yaw")
            if None not in (hx,hy,hz,dx,dy,dz,p,ro,yw):
                yat = math.hypot(hx-dx, hy-dy); mz = math.hypot(yat, hz-dz)
                el = math.degrees(math.atan2(hz-dz, max(yat,1e-6)))
                az = ((math.degrees(math.atan2(hy-dy,hx-dx)) - yw + 180) % 360) - 180
                bcx, bcy, bw = KAM.beklenen_kadraj(mz, el, az, p, ro)
                _, uf, _ = KAM.beklenen_kadraj(mz, 0.0, az, p, ro)
        if uf is not None and 0 <= uf < KAM.IMG_H:
            cv2.line(im, (0, int(uf)), (KAM.IMG_W, int(uf)), (255, 150, 0), 1)
            cv2.putText(im, "ufuk", (12, int(uf)-8), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255,150,0), 2)
        if bcx is not None and 0 <= bcx < KAM.IMG_W and 0 <= bcy < KAM.IMG_H:
            cv2.drawMarker(im, (int(bcx), int(bcy)), (0,170,255),
                           cv2.MARKER_CROSS, 34, 2)
        vcx, vcy, vw, vh = (_f(r,"vis_cx"), _f(r,"vis_cy"), _f(r,"vis_w"), _f(r,"vis_h"))
        if None not in (vcx, vcy, vw, vh):
            cv2.rectangle(im, (int(vcx-vw/2), int(vcy-vh/2)),
                              (int(vcx+vw/2), int(vcy+vh/2)), (60,255,60), 2)
        # --- yakı ---
        sat = [f"t={_f(r,'t') or 0:6.1f}s  kare {k}  {r.get('durum','')}",
               f"ist_hata {_f(r,'ist_hata_m') or float('nan'):5.1f} m   "
               f"hedefe {_f(r,'gercek_menzil') or float('nan'):5.1f} m   "
               f"yukselis {_f(r,'gercek_elev') or float('nan'):5.1f}",
               (f"KUTU {vw:5.1f} px  conf {_f(r,'vis_conf') or 0:.2f}  "
                f"yas {_f(r,'vis_yas') or -1:.2f}s" if vw else "KUTU YOK"),
               (f"hedef yonelim r/p/y  {_f(r,'hedef_roll') or 0:6.1f} "
                f"{_f(r,'hedef_pitch') or 0:6.1f} {_f(r,'hedef_yaw') or 0:6.1f}"
                if r.get("hedef_yaw") else "hedef yonelim: KAYITTA YOK")]
        y = 40
        for t in sat:
            cv2.putText(im, t, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0,0,0), 5)
            cv2.putText(im, t, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255,255,255), 2)
            y += 36
        im = cv2.resize(im, None, fx=olcek, fy=olcek, interpolation=cv2.INTER_AREA)
        n += 1
        cv2.imwrite(os.path.join(tmp, f"v{n:05d}.jpg"), im,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not n:
        print("kare yok"); return None
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(fps),
                    "-i", os.path.join(tmp,"v%05d.jpg"),
                    "-c:v","libx264","-pix_fmt","yuv420p", cikti], check=True)
    print(f"{cikti}  ({n} kare, {fps} fps = {n/fps:.0f} s video, "
          f"gercek sure {n*0.5:.0f} s -> {0.5*fps:.0f}x hizli)")
    return cikti


if __name__ == "__main__":
    d = sys.argv[1]
    yap(d, sys.argv[2] if len(sys.argv) > 2 else None,
        int(sys.argv[3]) if len(sys.argv) > 3 else 6)
