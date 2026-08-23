# -*- coding: utf-8 -*-
"""
================================================================================
UÇUŞ BEKÇİSİ — sapıtmayı CANLI yakala, koşuyu İPTAL et
================================================================================
NEDEN VAR (kullanıcı kuralı 2026-08-22):
  "aracın irtifası 1000 metre falan olduysa, başlangıç konumundan çok
   uzaklaştıysa görevi durdurup yeniden başlatalım. boşa çok süre gidiyor;
   drone hedeften çok uzaklaşmış ama hâlâ aynı uçuştan analiz yapmaya
   çalışıyorsun."

Yaşandı: bir koşuda drone 855 m'ye tırmandı, bir başkasında hedeften 5.8 km
uzaklaştı — ikisi de 4-5 dakika boyunca sürdü ve o veriler ÇÖPE gitti.

Gazebo'daki `tools/ucus_bekci.py`'nin DoW karşılığı. Fark: orada bekçi ayrı
bir süreçti ve İHLAL basıp çıkıyordu; burada döngünün İÇİNDE çalışır ve
koşuyu ANINDA iptal eder — DoW'da yeniden başlatmak saniyeler sürüyor.

SAĞLIK BANDI (ardışık BEKCI_ESIK örnek = süreklilik aranır; tekil sıçrama
alarm üretmez):
    zemine göreli irtifa   < BEKCI_ALT_MAX_M
    hedefe menzil          < BEKCI_MENZIL_MAX_M
    spawn'a menzil         < BEKCI_SPAWN_MAX_M
    telemetri              BEKCI_DONMA_S'den uzun DONMAMALI
    bağlantı               canlı olmalı
================================================================================
"""
import math
import time
from dow.ayarlar import Ayar


class Bekci:
    def __init__(self, cfg=Ayar):
        self.cfg = cfg
        self.sifirla()

    # ⛔ 2026-08-23: menzil kuralı ancak drone bir kez YAKINLAŞTIKTAN sonra
    #   silahlanır. Kullanıcının kuralı "drone hedeften çok UZAKLAŞTIYSA"
    #   idi; bu, bir kez yakın olmayı varsayar. Görev yeniden kurulunca
    #   başlangıç ayrımı 800-970 m çıkabiliyor (ölçüldü: drone -393,-1606,
    #   227 m / hedef -87,-2327, 86 m) ve kural MEŞRU YAKLAŞMAYI iptal
    #   ediyordu — 12 koşuluk bir blok tamamen bu yüzden çöpe gitti.
    MENZIL_SILAH_M = 200.0

    def sifirla(self):
        self._sayac = {}
        self._son_poz = None
        self._yakinlasti = False
        self._son_degisim_t = None
        self.spawn = None
        self.ihlal = None          # iptal sebebi (str) ya da None
        self.gecmis = []           # (t, kural) — teşhis

    def _say(self, kural, kotu, t):
        n = self._sayac.get(kural, 0)
        n = n + 1 if kotu else 0
        self._sayac[kural] = n
        if n >= self.cfg.BEKCI_ESIK and self.ihlal is None:
            self.ihlal = kural
            self.gecmis.append((t, kural))
        return n

    def kontrol(self, t, drone_p, zemin_z, hedef_p, bagli):
        """Her tikte çağrılır. İhlal varsa sebebi (str) döner, yoksa None."""
        c = self.cfg
        if not c.BEKCI_AKTIF:
            return None
        if self.spawn is None and drone_p is not None:
            self.spawn = drone_p

        # 1) bağlantı
        if self._say("baglanti_yok", not bagli, t) and self.ihlal:
            return self.ihlal
        if not bagli:
            return None

        # 2) telemetri DONDU mu (SDK iş parçacığı ölünce son değer sonsuza
        #    dek döner; hata VERMEZ — bu yüzden ayrıca sınanır)
        if self._son_poz is None or math.dist(drone_p, self._son_poz) > 0.05:
            self._son_poz = drone_p
            self._son_degisim_t = t
        elif self._son_degisim_t is not None and (t - self._son_degisim_t) > c.BEKCI_DONMA_S:
            self.ihlal = "telemetri_dondu"
            self.gecmis.append((t, self.ihlal))
            return self.ihlal

        # 3) irtifa tavanı (zemine göreli)
        yuk = drone_p[2] - (zemin_z if zemin_z is not None else drone_p[2])
        self._say("irtifa_tavani", yuk > c.BEKCI_ALT_MAX_M, t)

        # 4) hedeften UZAKLAŞMA — ancak bir kez YAKINLAŞTIKTAN sonra
        if hedef_p is not None:
            d_hedef = math.dist(drone_p, hedef_p)
            if d_hedef <= self.MENZIL_SILAH_M:
                self._yakinlasti = True          # kural artık silahlı
            self._say("hedef_cok_uzak",
                      self._yakinlasti and d_hedef > c.BEKCI_MENZIL_MAX_M, t)

        # 5) spawn'dan uzaklaşma (saha 220 m; bunun 7 katı = kesin kaçak)
        if self.spawn is not None:
            self._say("spawn_cok_uzak",
                      math.dist(drone_p, self.spawn) > c.BEKCI_SPAWN_MAX_M, t)

        return self.ihlal

    def rapor(self):
        if self.ihlal is None:
            return "sağlıklı"
        return f"İHLAL: {self.ihlal}"
