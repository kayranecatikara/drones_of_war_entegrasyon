# -*- coding: utf-8 -*-
"""
================================================================================
ANA GÜDÜM DÖNGÜSÜ — DoW
================================================================================
FAZLAR
  KALKIS  : yerden güvenli yüksekliğe DİKEY tırman (yatay komut YOK).
  ISTASYON: hedefin kuyruğundaki istasyon noktasına otur ve orada KAL.
            Kaynak: Ayar.GPS_KAYNAK ("truth" = geliştirme, "filtre" = yarışma).
  GORSEL  : yönelim YALNIZ kameradan (Ayar.GORSEL_AKTIF ile açılır).

⛔ YARIŞMA KURALI (CLAUDE.md §10) — ÜSTÜN KISIT
  Görsel temas VARKEN GPS güdümü YASAK. Yapısal olarak uygulanır: GORSEL
  fazda gps modülü hiç ÇAĞRILMAZ; ibvs.komut() imzasında hedef konumu YOKTUR.

⚠ GELİŞTİRME KİPİ (2026-08-22, kullanıcı kararı)
  GPS_KAYNAK varsayılanı "truth". Amaç: istasyon tutmayı filtre gürültüsünden
  arındırılmış olarak düzeltmek. Bu bitince "filtre"ye dönülecek.
  GORSEL_AKTIF varsayılanı False — önce GPS düzelsin.
================================================================================
"""
import math

from dow.ayarlar import Ayar
from dow.sdk.baglanti import DowBaglanti
from dow.gudum.cevirici import HizCubukCevirici
from dow.gudum import gps as GPS
from dow.gudum import ibvs
from dow.fusion.gnss_filtre import GNSSDuzeltici


class Beyin:
    def __init__(self, cfg=Ayar, dedektor=None):
        self.cfg = cfg
        self.b = DowBaglanti()
        self.cev = HizCubukCevirici()
        self.izleyici = GPS.HedefIzleyici()
        self.filtre = GNSSDuzeltici()        # KULLANICININ kodu — DEĞİŞTİRİLMEDİ
        self.det = dedektor                  # yalnız GORSEL_AKTIF iken
        self.durum = "KALKIS"
        self._zemin_z = None
        self._son_tespit = None
        self._son_tespit_t = 0.0
        self._kilit = 0
        self.hiz_I = 0.0
        self.tani = {}

    # ---------------- yardımcı ----------------
    def spawn_sifirla(self):
        """Drone yeniden doğduğunda: faz başa, zemin YENİDEN alınır.
        (Yeni spawn = gerçekten yerdeyiz; zemin referansı burada meşru.)"""
        self.durum = "KALKIS"
        self._zemin_z = None
        self._son_tespit = None
        self._kilit = 0
        self.hiz_I = 0.0
        self.izleyici.sifirla()
        self.cev.sifirla()

    def hedef_konumu(self, t):
        """Seçili kaynağa göre hedef konumu (m) ya da None.
        ⛔ YALNIZ görsel temas YOKKEN çağrılır."""
        if self.cfg.GPS_KAYNAK == "truth":
            tr = self.b.truth()
            return tr["hedef_m"] if tr else None
        hx, hy, hz = self.b.hedef_konum_bozuk()
        temiz = self.filtre.guncelle(hx * 100, hy * 100, hz * 100)
        if temiz is None:
            return None
        return (temiz[0] / 100.0, temiz[1] / 100.0, temiz[2] / 100.0)

    # ---------------- görsel ----------------
    def gorsel_tik(self, img_rgb, t):
        if not self.cfg.GORSEL_AKTIF or self.det is None:
            return None
        d = self.det.bul(img_rgb)
        if d is None:
            return None
        self._son_tespit = d
        self._son_tespit_t = t
        return d

    # ---------------- ana adım ----------------
    def adim(self, t, dt):
        """Bir kontrol tiki. Döner: (thr, pitch, roll, yaw) ya da None
        (None = bağlantı yok, tik atlandı)."""
        if not self.b.canli():
            self.tani = {"durum": "BAGLANTI_YOK"}
            return None

        dp = self.b.konum()
        yon = self.b.yonelim()
        own_roll = math.degrees(yon[0]); own_pitch = math.degrees(yon[1])
        own_yaw = math.degrees(yon[2])
        v_olculen = self.b.hiz_vektoru()

        if self._zemin_z is None:
            self._zemin_z = dp[2]
        yukseklik = dp[2] - self._zemin_z

        hp = self.hedef_konumu(t)
        hv = self.izleyici.guncelle(hp, t) if hp else (0.0, 0.0, 0.0)

        self.tani = {"durum": self.durum, "yukseklik": yukseklik,
                     "hedef_var": int(hp is not None)}

        # ---- KALKIS ----
        if self.durum == "KALKIS":
            hedef_z = hp[2] if hp else None
            zaten_yuksek = hedef_z is not None and dp[2] >= hedef_z - 20.0
            if zaten_yuksek or yukseklik >= self.cfg.KALKIS_ALT_M - self.cfg.KALKIS_TOL_M:
                self.durum = "ISTASYON"
            else:
                thr, _, _, _ = self.cev.cevir(
                    (0.0, 0.0, -self.cfg.KALKIS_VZ), v_olculen,
                    math.radians(own_yaw), 0.0)
                self.b.komut(thr, 0.0, 0.0, 0.0, True)   # yatay komut YOK
                return thr, 0.0, 0.0, 0.0

        # ---- GORSEL DEVRİ (yalnız Ayar.GORSEL_AKTIF iken) ----
        # ⛔ DEVİR KAPISI GPS MENZİLİYLE KAPILIDIR. Menzili KUTUDAN almak
        #   ölümcül: dedektör 140 m'de dev yanlış-pozitif üretiyor, kutudan
        #   hesaplanan menzil 1.3 m çıkıyor, kapı açılıyor ve güdüm "temas"
        #   sanıp tam hücum veriyor -> araç yere çakılıyor (2026-08-21, iki
        #   koşu, "Player ☠"). GPS burada MEŞRU: görsel temas HENÜZ YOK.
        if self.cfg.GORSEL_AKTIF and self._son_tespit is not None:
            taze = (t - self._son_tespit_t) <= 0.35
            if taze:
                self._kilit += 1
                cx, cy, w, h, conf = self._son_tespit
                from dow.gorus import kamera as KAM
                from dow.gorus.dedektor import DEVIR_MENZIL_M
                R_kutu = KAM.menzil(max(w, h))
                gps_menzil = math.dist(dp, hp) if hp else 1e9
                gps_ok = gps_menzil <= self.cfg.DEVIR_GPS_MENZIL_M
                self.tani["devir_gps_m"] = gps_menzil
                self.tani["devir_kutu_m"] = R_kutu if R_kutu else -1
                if (self.durum != "GORSEL" and self._kilit >= 3 and gps_ok
                        and R_kutu is not None and R_kutu <= DEVIR_MENZIL_M):
                    self.durum = "GORSEL"; self.hiz_I = 0.0
            else:
                self._kilit = 0
                if self.durum == "GORSEL" and (t - self._son_tespit_t) > 1.0:
                    self.durum = "ISTASYON"

        if self.durum == "GORSEL":
            cx, cy, w, h, conf = self._son_tespit
            (vx, vy), vz_ned, yaw_hedef, self.hiz_I, ti = ibvs.komut(
                cx, cy, w, h, own_yaw, own_pitch, own_roll, self.hiz_I, dt)
            self.tani.update(ti)
            e = (yaw_hedef - own_yaw + 180.0) % 360.0 - 180.0
            yaw_rate = max(-self.cfg.YAW_RATE_MAX,
                           min(self.cfg.YAW_RATE_MAX, 3.0 * e))
            thr, pitch, roll, yaw = self.cev.cevir(
                (vx, vy, vz_ned), v_olculen, math.radians(own_yaw), yaw_rate)
            self.b.komut(thr, pitch, roll, yaw, True)
            self.tani.update(self.cev.tani)
            return thr, pitch, roll, yaw

        # ---- ISTASYON ----
        if hp is None:
            self.b.komut(self.cev._vz_cubuk(0.0), 0.0, 0.0, 0.0, True)
            self.tani["durum"] = "HEDEF_YOK"
            return self.cev._vz_cubuk(0.0), 0.0, 0.0, 0.0

        (vx, vy), vz_ned, yaw_rate, ti = GPS.komut(
            dp, own_yaw, hp, hv, self.izleyici.yon_deg, self.cfg,
            self.izleyici.omega)
        self.tani.update(ti)

        thr, pitch, roll, yaw = self.cev.cevir(
            (vx, vy, vz_ned), v_olculen, math.radians(own_yaw), yaw_rate)
        self.b.komut(thr, pitch, roll, yaw, True)
        self.tani.update(self.cev.tani)
        return thr, pitch, roll, yaw
