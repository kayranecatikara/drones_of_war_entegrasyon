# -*- coding: utf-8 -*-
"""
================================================================================
ARKA YARIKÜRE — "kaybettik" mi, yoksa "ÜSTÜNDEN GEÇTİK" mi?
================================================================================
YAŞANMIŞ HATA (2026-08-27, §2 gözle inceleme yakaladı): kadraj izdüşümü
ışının kamera ekseni bileşenine BÖLER. Hedef arkadayken o bileşen NEGATİF
olur, bölme işareti çevirir ve KADRAJIN İÇİNDE bir piksel üretir.
`tan()` de aynısını yapar: tan(170°) = -0.176 -> cx ≈ kadrajın ortası.

Sonuç: hedefin üstünden geçtikten sonraki kareler, kayıp sınıflandırmasında
"kadraj içinde ama dedektör kör" (B kovası) sayılıyordu. ÖLÇÜLDÜ:

    menzil < 12 m kayıpları     toplam   aslında ARKADA
      KM2/yok  (manevrasız)         42        0   (%0)
      KM2/kademeli (manevralı)     139       65   (%47)
      KI1/kapali                   222       88   (%40)

Manevrasız kolda %0 — çünkü orada hedefi ıskalayıp geçmiyoruz. Manevralı
kolda yarısı. Bu kovayı ayırmadan yapılan her "manevra tespiti bozuyor"
kıyası, geçiş geometrisini güdüm kusuru sanır.

⚠ ÖLÇÜM-ONLY: truth (GPS) kanalı kullanılır, güdüme GİRMEZ (§10).
   Girdi `meta.csv`; `cikarim.csv` satırları zamanla eşlenir.

Kullanım:
    from araclar.arka import ArkaBekci
    ab = ArkaBekci("logs/KM2/kademeli__t2")
    if ab.arkada(t): ...        # bu kare "kayıp" değil, "geçtik"
================================================================================
"""
import bisect
import csv
import math
import os

ESIK_DEG = 85.0     # |azimut| bunun üstündeyse hedef görüntü düzleminin ARKASINDA


class ArkaBekci:
    """Bir koşu dizini için (t -> hedef arkamızda mı) sorgusu."""

    def __init__(self, kosu_dizini, esik_deg=ESIK_DEG):
        self.esik = esik_deg
        self.T = []
        self.AZ = []
        # koşu dizini (<ad>/k01/meta.csv) ya da doğrudan k* dizini kabul edilir
        y = os.path.join(kosu_dizini, "k01", "meta.csv")
        if not os.path.exists(y):
            y = os.path.join(kosu_dizini, "meta.csv")
        if not os.path.exists(y):
            return
        for r in csv.DictReader(open(y)):
            v = []
            for k in ("t", "hedef_x", "hedef_y", "drone_x", "drone_y",
                      "drone_yaw"):
                x = r.get(k)
                try:
                    v.append(float(x) if x not in (None, "", "nan") else None)
                except Exception:
                    v.append(None)
            if any(x is None for x in v):
                continue
            t, hx, hy, dx, dy, yw = v
            ker = math.degrees(math.atan2(hy - dy, hx - dx))
            self.T.append(t)
            self.AZ.append(abs((ker - yw + 180.0) % 360.0 - 180.0))

    @property
    def var(self):
        return bool(self.T)

    def azimut(self, t):
        """t anına EN YAKIN truth örneğindeki |azimut| (derece) veya None.

        ⚠ meta.csv 1 Hz'tir; §5.3 gereği hızlı değişen bir büyüklük için
          yetersiz olurdu. Ama "arkada mı" ikili bir durumdur ve geçiş
          anında azimut 0° -> 180° atlar; 1 Hz bu atlamayı kaçırmaz,
          yalnız sınırını ±0.5 s belirsiz bırakır."""
        if not self.T or t is None:
            return None
        i = bisect.bisect_left(self.T, t)
        if i >= len(self.T):
            i = len(self.T) - 1
        elif i > 0 and abs(self.T[i - 1] - t) < abs(self.T[i] - t):
            i -= 1
        return self.AZ[i]

    def arkada(self, t):
        a = self.azimut(t)
        return a is not None and a >= self.esik
