# -*- coding: utf-8 -*-
"""
================================================================================
DEDEKTÖR — talon_v3.pt (kullanıcının DoW fotoğraflarıyla eğittiği model)
================================================================================
ÖLÇÜLDÜ 2026-08-21, canlı DoW V5.0.0, n=857 kare, EŞLEŞTİRİLMİŞ A/B
(aynı karede iki çözünürlük). "GERÇEK tespit" = kutu, kalibre kamera
modelinin öngördüğü konumun yakınında VE makul boyutta.

  menzil    imgsz=960   imgsz=1920
  25-40 m      %32         %63
  40-60 m       %6         %55
  60-90 m       %0          %9

⭐ imgsz=1920 ZORUNLU. Sebep: 1920x1080 kadraj 960'a küçültülünce hedef
   YARIYA iner; 50 m'de 20 px olan Talon ağın girdisinde 10 px kalır ve
   YOLO'nun tespit sınırının altına düşer.
   BEDEL: çıkarım 24 -> 60 ms; döngü 17.5 -> 10.8 FPS. (FP16 fayda vermedi.)

KONUM DOĞRULUĞU: tespit edilen kutu, kalibre modelin öngördüğü yere
   1.6-2.5 px içinde düşüyor -> kamera modeli bağımsız DOĞRULANDI.

GÜVEN EŞİĞİ (1920'de tarandı):
  eşik 0.10 -> tespit %49, argmax doğru %43   (yanlış-pozitif argmax'ı çalıyor)
  eşik 0.40 -> tespit %40, argmax doğru %40   (fark KAPANIYOR)
  eşik 0.50 -> tespit %38, argmax doğru %38
  SEÇİM 0.40: ~9 puan tespit karşılığında yanlış-pozitifin en yüksek güveni
  çalmasını tamamen bitirir. Güdüm menzili bilmediği için argmax'a mecburdur.

⚠ GÖRSEL DEVİR MENZİLİ <= 50 m. 60-90 m'de tespit %9 — orada GPS fazı sürer.
⚠ Tespit %55-63; kesintiler VAR. Gazebo'daki bbox köprüsü (ölü-hesap ile
  bbox'ı görüntü hızıyla ileri taşıma) burada da ZORUNLU olacak.
================================================================================
"""
import numpy as np

MODEL_YOLU = "modeller/talon_v3.pt"
IMGSZ      = 1920      # ÖLÇÜLDÜ: 960 kullanmak 40-60 m'de tespiti %55 -> %6 düşürür
CONF_MIN   = 0.40      # ÖLÇÜLDÜ: argmax'ı yanlış-pozitiften korur
DEVIR_MENZIL_M = 50.0  # bu menzilin ötesinde görsel devir YAPILMAZ


class Dedektor:
    def __init__(self, yol=MODEL_YOLU, imgsz=IMGSZ, conf=CONF_MIN):
        from ultralytics import YOLO
        self.m = YOLO(yol); self.imgsz=imgsz; self.conf=conf
        self._isindi = False

    def isit(self, img):
        for _ in range(3):
            self.m.predict(img, imgsz=self.imgsz, conf=self.conf, verbose=False)
        self._isindi = True

    def bul(self, img):
        """En yüksek güvenli kutuyu döner: (cx, cy, w, h, conf) ya da None.
        ⚠ Menzil BİLİNMEZ -> boyut/konum kapısı UYGULANMAZ; argmax'a mecburuz.
          Bu yüzden CONF_MIN yüksek tutulur (ölçümle seçildi)."""
        if not self._isindi: self.isit(img)
        r = self.m.predict(img, imgsz=self.imgsz, conf=self.conf, verbose=False)[0]
        if not len(r.boxes): return None
        b = max(r.boxes, key=lambda x: float(x.conf))
        x1,y1,x2,y2 = b.xyxy[0].tolist()
        return ((x1+x2)/2.0, (y1+y2)/2.0, x2-x1, y2-y1, float(b.conf))
