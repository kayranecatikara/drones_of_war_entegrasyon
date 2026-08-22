# -*- coding: utf-8 -*-
"""
================================================================================
GPS FAZI — İSTASYON TUTMA
================================================================================
AMAÇ: hedefin KUYRUĞUNDAKİ bir noktaya hızla oturmak ve orada KALMAK.
Görsel devir oradan yapılır. (Gazebo'daki çözülmüş "istasyon ofseti" tasarımı.)

⛔ YARIŞMA KURALI (§10): bu modül YALNIZ görsel temas YOKKEN çağrılır.
   Görsel faz başlayınca gps.komut() hiç çalıştırılmaz.

TERİMLER (CLAUDE.md §0.2)
  * istasyon: hedefe göre SABİT bir göreli konum (kuyruğunda R m, altında h m).
    Hedef hareket ettikçe istasyon da hareket eder.
  * ileri besleme (feedforward): hatayı beklemeden, bilinen bozucuyu doğrudan
    komuta eklemek. Burada bozucu = hedefin kendi hızı.
  * kalıcı gecikme hatası: saf P kontrolcü, hareketli bir referansı izlerken
    hep GERİDE kalır. Hata ancak v = Kp·e kadar hız üretebildiği için,
    hedef V hızla giderken denge e = V/Kp'de kurulur — SIFIRA İNMEZ.
    Kp=0.9 ve V=18 m/s ise kalıcı hata 20 m. İleri besleme bunu SIFIRLAR.

NEDEN ÖNEMLİ (ölçüldü 2026-08-22):
  İleri beslemesiz sürümde araç hedefe hiç oturamadı; menzil 100-255 m arası
  salındı, kapanma hızı medyan -3.78 m/s (yani UZAKLAŞIYORDU).
================================================================================
"""
import math
from dow.ayarlar import Ayar


def _kirp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _wrap(a):
    return (a + 180.0) % 360.0 - 180.0


class HedefIzleyici:
    """Hedefin konumundan HIZINI ve YÖNÜNÜ türetir.

    Neden gerekli: SDK'nın `get_target_speed()` alanı DAİMA 0 (234587 örnekte
    doğrulandı). Hız konumdan türetilmek ZORUNDA.
    EMA ile yumuşatılır: ham fark 5 Hz veriyle çok gürültülü olur."""

    def __init__(self, ema=0.25, min_dt=0.08, w_ema=0.20):
        self.ema = ema
        self.w_ema = w_ema
        self.min_dt = min_dt
        self._p = None
        self._t = None
        self.v = (0.0, 0.0, 0.0)      # m/s
        self.hiz = 0.0
        self.yon_deg = None           # hedefin gidiş yönü (derece)
        self.omega = 0.0              # rad/s; hedefin DÖNÜŞ hızı (z ekseni)

    def guncelle(self, p, t):
        if self._p is None:
            self._p, self._t = p, t
            return self.v
        dt = t - self._t
        if dt < self.min_dt:
            return self.v
        ham = tuple((p[i] - self._p[i]) / dt for i in range(3))
        # aykırı sıçrama koruması (ışınlanma / bozuk paket)
        if math.sqrt(sum(c * c for c in ham)) < 80.0:
            a = self.ema
            self.v = tuple(a * ham[i] + (1 - a) * self.v[i] for i in range(3))
        self._p, self._t = p, t
        self.hiz = math.hypot(self.v[0], self.v[1])
        if self.hiz > 1.0:
            yeni = math.degrees(math.atan2(self.v[1], self.v[0]))
            if self.yon_deg is not None and dt > 0:
                d = (yeni - self.yon_deg + 180.0) % 360.0 - 180.0
                w = math.radians(d) / dt
                if abs(w) < 2.0:                      # >115°/s = gürültü
                    a = self.w_ema
                    self.omega = a * w + (1 - a) * self.omega
            self.yon_deg = yeni
        return self.v

    def sifirla(self):
        self._p = self._t = None
        self.v = (0.0, 0.0, 0.0); self.hiz = 0.0
        self.yon_deg = None; self.omega = 0.0


def istasyon_noktasi(hedef_p, hedef_yon_deg, cfg=Ayar):
    """Hedefin KUYRUĞUNDAKİ istasyon noktası (m, Unreal dünya ekseni).
    Yön bilinmiyorsa (hedef duruyorsa) hedefin kendisi + alt ofset."""
    hx, hy, hz = hedef_p
    # ALT OFSETİ MENZİLE ORANTILI: kamera TILT° YUKARI baktığı için hedefin
    # kadrajın ORTASINDA durması h = R·tan(TILT) ister. Sabit h kullanmak,
    # menzil değişince hedefi kadrajda yukarı/aşağı kaydırır.
    # ISTASYON_ALT_ORAN=0 -> eski davranış (sabit ISTASYON_ALT_M).
    if cfg.ISTASYON_ALT_ORAN > 0:
        z = hz - cfg.ISTASYON_MENZIL_M * cfg.ISTASYON_ALT_ORAN
    else:
        z = hz - cfg.ISTASYON_ALT_M
    if hedef_yon_deg is None:
        return hx, hy, z
    r = math.radians(hedef_yon_deg)
    return (hx - math.cos(r) * cfg.ISTASYON_MENZIL_M,
            hy - math.sin(r) * cfg.ISTASYON_MENZIL_M,
            z)


def komut(drone_p, drone_yaw_deg, hedef_p, hedef_v, hedef_yon_deg, cfg=Ayar,
          hedef_omega=0.0):
    """İstasyon tutma komutu.

    ÇIKTI: (v_dunya=(vx,vy), vz_ned, yaw_rate_deg_s, tani)
      vz_ned: POZİTİF = AŞAĞI (çevirici ters çevirir)

    YASA:  v = v_hedef (ileri besleme) + Kp * (istasyon - konum)
      İlk terim hedefle aynı hızda uçmayı sağlar (kalıcı hata SIFIR),
      ikinci terim istasyona oturtur.
    """
    sx, sy, sz = istasyon_noktasi(hedef_p, hedef_yon_deg, cfg)
    ex = sx - drone_p[0]
    ey = sy - drone_p[1]
    ez = sz - drone_p[2]

    ff_x, ff_y, ff_z = (hedef_v if cfg.ISTASYON_ILERI else (0.0, 0.0, 0.0))

    # DÖNÜŞ İLERİ BESLEMESİ — istasyon noktasının KENDİ hızı
    # ------------------------------------------------------------------
    # İstasyon hedefin R m ARKASINDA. Hedef w rad/s ile dönerken istasyon
    # noktası hedefin etrafında SÜPÜRÜR: v_istasyon = v_hedef + w x r.
    # Bu terim olmadan dönüşlerde kalıcı gecikme kalır.
    # ÖLÇÜLDÜ (GA01, 4 koşu): hata YALNIZ yatayda (6.21 m) ve PERİYODİK —
    # minimumlar/maksimumlar ~16 s'de bir, yani hedefin dönüş aralığında.
    # Dikey hata zaten +0.08 m (kusursuz), sorun tamamen dönüşte.
    # Büyüklük: w=0.379 rad/s (21.7°/s) ve R=35 m -> w*R = 13.3 m/s.
    # Yani EKSİK olan terim, hedef hızının %74'ü kadar.
    w = hedef_omega if cfg.ISTASYON_DONUS_ILERI else 0.0
    rx = sx - hedef_p[0]
    ry = sy - hedef_p[1]
    ff_x += -w * ry
    ff_y += +w * rx

    vx = ff_x + cfg.ISTASYON_KP * ex
    vy = ff_y + cfg.ISTASYON_KP * ey
    # yatay hız tavanı — YÖNÜ koruyarak kırp
    n = math.hypot(vx, vy)
    if n > cfg.V_MAX:
        vx *= cfg.V_MAX / n; vy *= cfg.V_MAX / n

    vz_yukari = ff_z + cfg.ISTASYON_KP_Z * ez
    vz_yukari = _kirp(vz_yukari, -cfg.VZ_MAX_ALCAL, cfg.VZ_MAX_TIRMAN)

    # BURUN: her zaman HEDEFE dönük (kamera hedefe baksın ki görsel devir
    # kurulabilsin). İstasyona değil, HEDEFE.
    ker = math.degrees(math.atan2(hedef_p[1] - drone_p[1],
                                  hedef_p[0] - drone_p[0]))
    yaw_hata = _wrap(ker - drone_yaw_deg)
    yaw_rate = _kirp(3.0 * yaw_hata, -cfg.YAW_RATE_MAX, cfg.YAW_RATE_MAX)

    d_ist = math.sqrt(ex * ex + ey * ey + ez * ez)
    d_hedef = math.dist(drone_p, hedef_p)
    tani = {
        "ist_x": sx, "ist_y": sy, "ist_z": sz,
        "ist_hata_m": d_ist,          # ⭐ BİRİNCİL ÖLÇÜT
        "ist_hata_yatay": math.hypot(ex, ey),
        "ist_hata_dikey": ez,
        "hedef_menzil_m": d_hedef,
        "hedef_hiz": math.hypot(hedef_v[0], hedef_v[1]),
        "hedef_yon": hedef_yon_deg if hedef_yon_deg is not None else -999,
        "yaw_hata": yaw_hata,
        "v_istek": math.hypot(vx, vy),
        "hedef_omega_deg": math.degrees(hedef_omega),
        "donus_ff": math.hypot(w * ry, w * rx),
    }
    return (vx, vy), -vz_yukari, yaw_rate, tani
