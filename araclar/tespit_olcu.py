# -*- coding: utf-8 -*-
"""
================================================================================
GERÇEK TESPİT ÖLÇÜMÜ — meta.csv'den, truth geometriyle eşleştirerek
================================================================================
NEDEN HAM ORAN YETMEZ (kullanıcı 2026-08-22):
  "detection modeli bazen çok yanlış yerleri algılıyor, OSD'yi falan tespit
   edip 0.50 conf atıyor."
  Dedektör her karede EN YÜKSEK GÜVENLİ kutuyu döner (argmax). O kutu OSD
  yazısı da olabilir. "Kutu var mı" diye saymak yanlış-pozitifi ÖDÜLLENDİRİR.

⚠ HANGİ ANIN GEOMETRİSİ (2026-08-22'de yakalanan yanlılık):
  Kutu, kontrol döngüsüne 0.075-0.28 s GECİKMEYLE ulaşıyor (ekran kopyalama
  15 ms + YOLO 60 ms, dedektör 5 Hz). Bu sürede araç yaw/roll yapıyor.
  Karşılaştırmayı KAYIT anının duruşuyla kurmak, kutuyu hedefin gerisinde
  gösteriyor ve YANLIŞ-POZİTİF saydırıyordu. Bedeli kollara eşit değildi:
  dik bakan (oran 0.75) kollarda sapma medyanı 93 px, 0.45'te 51 px.
  ÇÖZÜM: kayıt artık `bek_cx/bek_cy/bek_w/bek_ufuk_cy` sütunlarını TESPİT
  ANININ duruşundan hesaplayıp yazıyor. Bu sütunlar VARSA onlar kullanılır;
  yoksa (eski koşular) kayıt anının duruşuna düşülür ve sonuç bu yanlılığı
  taşır — eski ve yeni kampanyalar bu yüzden BİRBİRİYLE KIYASLANMAZ.

TANIM — bir kare "GERÇEK TESPİT" sayılır ancak ve ancak:
  1) o karede dedektör bir kutu verdiyse (vis_cx/vis_cy/vis_w dolu), VE
  2) kutu merkezi, KALİBRE kamera modelinin truth geometriden öngördüğü
     yere `tol` piksel içinde düşüyorsa, VE
  3) kutu genişliği öngörülenin 0.5-2.0 katı arasındaysa.
  tol = max(60 px, 1.5 x öngörülen kutu genişliği)
       -> 15 m'de 92 px, 8 m'de 171 px. Hedef büyüdükçe merkez daha çok
          kayabilir ve hâlâ "hedefin üstünde" sayılır.

⚠ Bu ölçüm YALNIZ ANALİZDİR. truth kanalı güdüme ASLA girmez; yarışmada bu
  kanal zaten yoktur. Kamera modeli (TILT 26.5°, f 540.4 px) 2.6 px artıkla
  kalibre edildi, yani öngörü bizim ölçütümüzü bozacak kadar gürültülü değil.

ÇIKTI SÖZLÜĞÜ
  n_istasyon        : ISTASYON fazındaki kare sayısı (payda)
  kadraj_yuzde      : hedefin GEOMETRİK olarak kadrajda olduğu kare oranı
                      ⭐ GEÇERLİLİK EŞİ — %90 altındaysa tespit oranı anlamsız
  ufuk_ustu_yuzde   : hedefin ufuk çizgisinin üstünde olduğu oran (= gökyüzü)
  ham_yuzde         : kutu VAR olan kare oranı (yanlış-pozitif dahil)
  gercek_yuzde      : ⭐ BİRİNCİL ÖLÇÜT
  yanlis_yuzde      : kutu var ama hedefte DEĞİL (ham - gerçek)
  kutu_beklenen_px  : truth'tan öngörülen kutu genişliği medyanı
  gok_payi_px       : hedefin ufuk çizgisinin kaç px üstünde durduğu (medyan)
================================================================================
"""
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gorus import kamera as KAM


def _f(r, k):
    try:
        v = float(r[k])
        return v if v == v else None
    except (KeyError, TypeError, ValueError):
        return None


def olc(meta_yolu, yalniz_faz="ISTASYON"):
    try:
        R = list(csv.DictReader(open(meta_yolu)))
    except OSError:
        return None
    if yalniz_faz:
        R = [r for r in R if r.get("durum") == yalniz_faz]
    if not R:
        return None

    n = 0; kadraj = 0; ufukustu = 0; ham = 0; gercek = 0
    kutular = []; gokpaylari = []
    for r in R:
        # --- ÖNGÖRÜLEN KADRAJ KONUMU ---
        # 1. tercih: `bek_*` (tespit ANININ duruşuyla, kayıt sırasında
        #    hesaplandı). ⭐ GÖRSEL FAZDA TEK SEÇENEK BUDUR: orada hedefin
        #    GPS'i kasıtlı olarak OKUNMUYOR (§10), dolayısıyla `hedef_x/y/z`
        #    kayda yazılmıyor. `bek_*` truth halkasından geldiği için
        #    ÖLÇÜM-ONLY'dir ve güdüme girmez.
        # 2. tercih (eski koşular): kayıt anının duruşundan yeniden hesapla.
        gcx, gcy, gw = _f(r, "bek_cx"), _f(r, "bek_cy"), _f(r, "bek_w")
        guf = _f(r, "bek_ufuk_cy")
        if None not in (gcx, gcy, gw) and gw > 0:
            tcx, tcy, tw, tuf = gcx, gcy, gw, (guf if guf is not None else 1e9)
        else:
            hx, hy, hz = _f(r, "hedef_x"), _f(r, "hedef_y"), _f(r, "hedef_z")
            dx, dy, dz = _f(r, "drone_x"), _f(r, "drone_y"), _f(r, "drone_z")
            pit, rol, yaw = (_f(r, "drone_pitch"), _f(r, "drone_roll"),
                             _f(r, "drone_yaw"))
            if None in (hx, hy, hz, dx, dy, dz, pit, rol, yaw):
                continue
            yat = math.hypot(hx - dx, hy - dy)
            menzil = math.hypot(yat, hz - dz)
            if menzil < 0.5:
                continue
            elev = math.degrees(math.atan2(hz - dz, max(yat, 1e-6)))
            ker = math.degrees(math.atan2(hy - dy, hx - dx))
            az = (ker - yaw + 180.0) % 360.0 - 180.0
            tcx, tcy, tw = KAM.beklenen_kadraj(menzil, elev, az, pit, rol)
            _, tuf, _ = KAM.beklenen_kadraj(menzil, 0.0, az, pit, rol)
        n += 1
        bw = tw
        icerde = (0 <= tcx < KAM.IMG_W) and (0 <= tcy < KAM.IMG_H)
        if icerde:
            kadraj += 1
            kutular.append(tw)
            if tuf < 1e8:
                gokpaylari.append(tuf - tcy)
                if tcy < tuf:
                    ufukustu += 1
        vcx, vcy, vw = _f(r, "vis_cx"), _f(r, "vis_cy"), _f(r, "vis_w")
        if vcx is None or vw is None or vw <= 0:
            continue
        ham += 1
        tol = max(60.0, 1.5 * tw)
        if (icerde and math.hypot(vcx - tcx, vcy - tcy) <= tol
                and 0.5 <= vw / tw <= 2.0):
            gercek += 1

    if n == 0:
        return None
    med = lambda a: (sorted(a)[len(a) // 2] if a else float("nan"))
    return {
        "n_istasyon": n,
        "kadraj_yuzde": round(100.0 * kadraj / n, 1),
        "ufuk_ustu_yuzde": round(100.0 * ufukustu / max(1, kadraj), 1),
        "ham_yuzde": round(100.0 * ham / n, 1),
        "gercek_yuzde": round(100.0 * gercek / n, 1),
        "yanlis_yuzde": round(100.0 * (ham - gercek) / n, 1),
        "kutu_beklenen_px": round(med(kutular), 1),
        "gok_payi_px": round(med(gokpaylari), 0),
    }


if __name__ == "__main__":
    for y in sys.argv[1:]:
        if os.path.isdir(y):
            y = os.path.join(y, "meta.csv")
        o = olc(y)
        print(f"{y}: {o}")
