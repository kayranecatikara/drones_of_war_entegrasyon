# -*- coding: utf-8 -*-
"""
================================================================================
KOŞU ARACI — bekçili, kayıtlı, OTOMATİK YENİDEN BAŞLATAN test koşumu
================================================================================
DoW'un Gazebo'ya göre ASIL AVANTAJI: bir koşu bitince (çarpma/ıska) `E` ile
saniyeler içinde yenisi başlar. Gazebo'da bir koşu ~5 dk kurulum istiyordu.
Bu araç o avantajı kullanır: N koşuyu arka arkaya, insan müdahalesi olmadan.

Kullanım:
    python3 araclar/kosu.py <ad> [koşu_sayısı] [koşu_süresi_s]

Her koşu için:
    logs/<ad>/k01/meta.csv + kareler/     (0.5 s'de bir kare + telemetri)
    logs/<ad>/ozet.csv                    (koşu başına özet satırı)

BEKÇİ: irtifa tavanı / hedeften uzaklaşma / spawn'dan uzaklaşma / donmuş
telemetri / kopuk bağlantı -> koşu ANINDA iptal, sebebiyle kaydedilir ve
yenisi başlar. "Sapıtmış uçuştan analiz yapmaya çalışmak" biter.
================================================================================
"""
import csv
import math
import os
import subprocess
import sys
import time

import numpy as np
import mss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json as _json
import urllib.request as _url

from dow.ayarlar import Ayar
from dow.ana import Beyin
from dow import panel as PANEL


def _telem_gonder(tel, port=8801):
    """Güdüm telemetrisini bağımsız izleyici paneline gönder (best-effort)."""
    try:
        _url.urlopen(_url.Request(f"http://127.0.0.1:{port}/telem",
                                  data=_json.dumps(tel).encode(),
                                  headers={"Content-Type": "application/json"}),
                     timeout=0.25)
    except Exception:
        pass
from araclar.bekci import Bekci
from araclar.kayit import Kayit
from araclar.kadraj import BOLGE, ucusta_mi, oyunu_one_al, yeniden_dogur, hazirla


def _yeni_gorev():
    """Drone'u yeniden doğur (çarptıysa) ve kadrajın uçuşta olmasını bekle."""
    for _ in range(4):
        yeniden_dogur()
        with mss.mss() as sct:
            img = np.array(sct.grab(BOLGE))[:, :, :3]
        if ucusta_mi(img):
            return True
        oyunu_one_al(); time.sleep(1.0)
    return False


def kosu_yap(beyin, sct, dizin, sure, det=None, panel_ac=True):
    """Tek koşu. Döner: özet sözlüğü."""
    os.makedirs(dizin, exist_ok=True)
    kayit = Kayit(dizin, Ayar.KAYIT_ARALIK) if Ayar.KAYIT_AKTIF else None
    bekci = Bekci(); bekci.sifirla()
    beyin.spawn_sifirla()
    if not beyin.b.canli():
        beyin.b.yeniden_bagla()

    t0 = time.time(); son = t0; n = 0
    son_det = 0.0
    ist_hatalar = []; oturma_t = None
    ihlal = None; tespit = None
    dt_hedef = 1.0 / Ayar.LOOP_HZ

    while time.time() - t0 < sure:
        t = time.time(); dt = max(1e-3, t - son); son = t

        img = None
        gerek_kare = (kayit and kayit.gerek(t - t0)) or panel_ac
        if gerek_kare or Ayar.GORSEL_AKTIF:
            img = np.array(sct.grab(BOLGE))[:, :, :3][:, :, ::-1]   # RGB
            if not ucusta_mi(img[:, :, ::-1]):
                ihlal = "drone_yok"; break
            if Ayar.GORSEL_AKTIF:
                tespit = beyin.gorsel_tik(img, t)
            elif Ayar.DEDEKTOR_GOSTER and det is not None:
                # ⚠ YALNIZ PANEL İÇİN. Çıktı Beyin'e VERİLMEZ; güdüm GPS'te
                #   kalır. Kullanıcı hedefin nasıl algılandığını görsün diye.
                if (t - son_det) >= 1.0 / max(0.1, Ayar.DEDEKTOR_HZ):
                    son_det = t
                    tespit = det.bul(img)

        sonuc = beyin.adim(t, dt)
        if sonuc is None:
            ihlal = "baglanti_yok"; break
        thr, pitch, roll, yaw = sonuc
        ti = beyin.tani

        # ---- BEKÇİ ----
        dp = beyin.b.konum()
        hp = None
        if ti.get("hedef_var"):
            hp = beyin.hedef_konumu(t)
        s = bekci.kontrol(t - t0, dp, beyin._zemin_z, hp, beyin.b.canli())
        if s:
            ihlal = s; break

        # ---- ölçüt: istasyon hatası ----
        ih = ti.get("ist_hata_m")
        if ih is not None and beyin.durum == "ISTASYON":
            ist_hatalar.append(ih)
            if oturma_t is None and ih <= 15.0:
                oturma_t = t - t0

        # ---- panel ----
        # İzleyici (8801) kamerayı+tespiti zaten basıyor; buradan yalnız
        # GÜDÜM sayılarını gönderiyoruz -> tek panelde birleşiyor.
        if panel_ac and (n % 5 == 0):
            tel = {k: (round(v, 2) if isinstance(v, float) else v)
                   for k, v in ti.items() if isinstance(v, (int, float, str))}
            tel["drone_hiz"] = round(beyin.b.hiz(), 2)
            tel["bekci"] = bekci.rapor()
            _telem_gonder(tel)

        # ---- kayıt (0.5 s) ----
        if kayit and kayit.gerek(t - t0):
            yon = beyin.b.yonelim()
            sat = {
                "durum": beyin.durum,
                "drone_x": round(dp[0], 2), "drone_y": round(dp[1], 2),
                "drone_z": round(dp[2], 2),
                "drone_roll": round(math.degrees(yon[0]), 2),
                "drone_pitch": round(math.degrees(yon[1]), 2),
                "drone_yaw": round(math.degrees(yon[2]), 2),
                "drone_hiz": round(beyin.b.hiz(), 2),
                "yukseklik": round(ti.get("yukseklik", 0), 2),
                "thr": round(thr, 3), "pitch": round(pitch, 3),
                "roll": round(roll, 3), "yaw": round(yaw, 3),
            }
            if hp:
                sat.update({"hedef_x": round(hp[0], 2), "hedef_y": round(hp[1], 2),
                            "hedef_z": round(hp[2], 2)})
            for k in ("hedef_hiz", "hedef_yon", "ist_x", "ist_y", "ist_z",
                      "ist_hata_m", "ist_hata_yatay", "ist_hata_dikey",
                      "hedef_menzil_m", "yaw_hata", "v_istek"):
                if k in ti: sat[k] = round(ti[k], 2) if isinstance(ti[k], float) else ti[k]
            if tespit:
                sat.update({"vis_cx": round(tespit[0], 1), "vis_cy": round(tespit[1], 1),
                            "vis_w": round(tespit[2], 1), "vis_h": round(tespit[3], 1),
                            "vis_conf": round(tespit[4], 3)})
            kayit.yaz(t - t0, img, sat)

        n += 1
        kalan = dt_hedef - (time.time() - t)
        if kalan > 0: time.sleep(kalan)

    if kayit: kayit.kapat()
    beyin.b.komut(beyin.cev._vz_cubuk(0.0), 0.0, 0.0, 0.0, True)
    a = np.array(ist_hatalar) if ist_hatalar else np.array([np.nan])
    return {
        "sure": round(time.time() - t0, 1), "tik": n,
        "ihlal": ihlal or "-",
        "ist_hata_medyan": round(float(np.nanmedian(a)), 2),
        "ist_hata_min": round(float(np.nanmin(a)), 2),
        "ist_hata_son5s": round(float(np.nanmedian(a[-int(5/max(1e-9,1/Ayar.LOOP_HZ)):])), 2)
                          if len(a) > 10 else float("nan"),
        "oturma_s": round(oturma_t, 1) if oturma_t else -1,
        "ist_orani_15m": round(float(np.mean(a <= 15.0)), 3) if len(a) > 1 else 0.0,
    }


def main():
    ad = sys.argv[1] if len(sys.argv) > 1 else "kosu"
    adet = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    sure = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
    kok = os.path.join("logs", ad)
    os.makedirs(kok, exist_ok=True)

    det = None
    if Ayar.GORSEL_AKTIF or Ayar.DEDEKTOR_GOSTER:
        from dow.gorus.dedektor import Dedektor
        det = Dedektor()
        print(f"dedektör: {'GÜDÜMDE' if Ayar.GORSEL_AKTIF else 'yalnız PANELDE'}",
              flush=True)

    sct = mss.mss()
    ok, img0 = hazirla(sct)
    print(f"hazırlık: {'UÇUŞTA' if ok else 'BAŞARISIZ'}", flush=True)
    if not ok: sys.exit(1)
    if det: det.isit(img0)

    beyin = Beyin(dedektor=det)
    if not beyin.b.baglan():
        print("SDK bağlanamadı"); sys.exit(1)

    print(f"\n{adet} koşu x {sure:.0f} s | GPS={Ayar.GPS_KAYNAK} | "
          f"görsel={'AÇIK' if Ayar.GORSEL_AKTIF else 'KAPALI'}", flush=True)
    print(f"{'#':>3} {'süre':>6} {'tik':>5} {'ihlal':>16} {'ist_hata med':>13} "
          f"{'min':>7} {'oturma':>7} {'≤15m %':>7}", flush=True)
    ozetler = []
    for i in range(1, adet + 1):
        if not _yeni_gorev():
            print(f"{i:3d}  görev başlatılamadı"); continue
        if not beyin.b.canli(): beyin.b.yeniden_bagla()
        o = kosu_yap(beyin, sct, os.path.join(kok, f"k{i:02d}"), sure, det)
        o["kosu"] = i; ozetler.append(o)
        print(f"{i:3d} {o['sure']:6.1f} {o['tik']:5d} {o['ihlal']:>16} "
              f"{o['ist_hata_medyan']:13.2f} {o['ist_hata_min']:7.2f} "
              f"{o['oturma_s']:7.1f} {100*o['ist_orani_15m']:7.1f}", flush=True)

    if ozetler:
        with open(os.path.join(kok, "ozet.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ozetler[0].keys()))
            w.writeheader(); w.writerows(ozetler)
        gec = [o for o in ozetler if o["ihlal"] == "-"]
        print(f"\nGEÇERLİ {len(gec)}/{len(ozetler)} koşu")
        if gec:
            m = np.array([o["ist_hata_medyan"] for o in gec])
            print(f"istasyon hatası medyanı: {np.nanmedian(m):.1f} m "
                  f"(Gazebo hedefi ≤10 m)")
    beyin.b.kapat()


if __name__ == "__main__":
    main()
