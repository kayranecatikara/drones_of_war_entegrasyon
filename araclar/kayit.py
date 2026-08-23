# -*- coding: utf-8 -*-
"""
================================================================================
UÇUŞ KAYDI — her 0.5 s'de KARE + TELEMETRİ (eşli)
================================================================================
CLAUDE.md §2 adım 2'nin DoW karşılığı; kullanıcı 2026-08-22'de bu mekanizmanın
DoW'da da kurulmasını istedi ("şu an bu test mekaniğini hiç kullanmıyorsun").

NEDEN EŞLİ: kare ile o anın telemetrisi AYNI satırda saklanır. Görüntü ile log
çeliştiğinde yakalanır (Gazebo'da panelin "4.8 m" dediği karede hedef 20 px'ti
— video olmasaydı bozuk ölçütle karar verilecekti). CLAUDE.md §2 adım 6.

ÇIKTI
    <dizin>/kareler/f0001.jpg ...      (0.5 s aralık)
    <dizin>/meta.csv                    (kare ↔ telemetri)
Video:
    ffmpeg -framerate 10 -i <dizin>/kareler/f%04d.jpg -c:v libx264 \
           -pix_fmt yuv420p ucus.mp4        (0.5 s kare -> 10 fps = 5x hızlı)
================================================================================
"""
import csv
import os
import time
import cv2


class Kayit:
    ALANLAR = [
        "kare", "t", "durum",
        "drone_x", "drone_y", "drone_z", "drone_roll", "drone_pitch", "drone_yaw",
        "drone_hiz", "yukseklik",
        "hedef_x", "hedef_y", "hedef_z", "hedef_hiz", "hedef_yon",
        # Hedefin GERÇEK yönelimi (SDK indeks 14-16). `hedef_yon` bundan
        # farklıdır: o, konum farkından türetilmiş EMA'lı ROTA'dır.
        # Kullanıcı isteği (2026-08-22): "hedef aracın ve droneun konumu
        # ROTASYONU ... her yarım saniyede bir kaydet".
        "hedef_roll", "hedef_pitch", "hedef_yaw",
        "ist_x", "ist_y", "ist_z", "ist_hata_m", "ist_hata_yatay", "ist_hata_dikey",
        "hedef_menzil_m", "yaw_hata", "v_istek",
        # §5.1 mekanizma sütunu (C): dönüş ileri beslemesinin ürettiği hız
        # ⚠ ÖLÇÜM-ONLY (truth): gudume ASLA girmez, yalnız analiz için.
        "gercek_menzil", "gercek_dz", "gercek_elev",
        "thr", "pitch", "roll", "yaw",
        "vis_conf", "vis_cx", "vis_cy", "vis_w", "vis_h", "vis_menzil",
        # kutunun YAŞI (s): çıkarım 5 Hz, kayıt 2 Hz -> kutu 0.2 s
        # bayat olabilir. Bayat kutu hedefin gerisinde kalır ve
        # "yanlış-pozitif" gibi görünür; ölçüt bunu ayırt edebilsin.
        "vis_yas",
        # tespit ANINDAKİ duruş+truth'tan öngörülen kadraj konumu. Kutu
        # kontrol döngüsüne ~75-280 ms gecikmeyle ulaşıyor; ölçütü KAYIT
        # anının duruşuyla kurmak, dik bakan kolları haksız cezalandırıyordu.
        "bek_cx", "bek_cy", "bek_w", "bek_ufuk_cy",
        # §5.1 MEKANİZMA SÜTUNLARI — özellik gerçekten devreye girdi mi?
        # Deney kolunda bunlar sıfırsa o koşu veri noktası değil, GEÇERSİZ.
        "kopru_kare", "bayat_birak", "yerel_aday", "yerel_uygun",
        "ibvs_nisan_elev", "ibvs_vz_kirpildi", "ibvs_e_cy", "ibvs_vz_yukari",
    ]

    def __init__(self, dizin, aralik=0.5, jpg_kalite=80):
        self.dizin = dizin
        self.kare_dizin = os.path.join(dizin, "kareler")
        os.makedirs(self.kare_dizin, exist_ok=True)
        self.aralik = aralik
        self.kalite = jpg_kalite
        self._f = open(os.path.join(dizin, "meta.csv"), "w", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=self.ALANLAR, extrasaction="ignore")
        self._w.writeheader()
        self.n = 0
        self._son = 0.0

    def gerek(self, t):
        return (t - self._son) >= self.aralik

    def yaz(self, t, img_rgb, satir):
        """img_rgb: HxWx3 RGB (None ise kare yazılmaz)."""
        self.n += 1
        self._son = t
        if img_rgb is not None:
            yol = os.path.join(self.kare_dizin, f"f{self.n:04d}.jpg")
            cv2.imwrite(yol, img_rgb[:, :, ::-1],
                        [int(cv2.IMWRITE_JPEG_QUALITY), self.kalite])
        satir = dict(satir); satir["kare"] = self.n; satir["t"] = round(t, 3)
        self._w.writerow(satir)
        self._f.flush()

    def kapat(self):
        try: self._f.close()
        except Exception: pass
