# -*- coding: utf-8 -*-
"""
================================================================================
ANA GÜDÜM DÖNGÜSÜ — DoW
================================================================================
FAZLAR
  ARAMA / YAKLASMA : hedef GÖRSEL olarak yok -> GPS güdümü (bozuk GPS,
                     gnss_filtre.py ile temizlenir). Hedefe yaklaşır.
  GORSEL           : ardışık N geçerli tespit + menzil <= 50 m -> devir.
                     Bundan sonra YÖNELİM YALNIZ KAMERADAN.

⛔ YARIŞMA KURALI (CLAUDE.md §10) — ÜSTÜN KISIT
  Görsel temas VARKEN GPS güdümü YASAK. Bu kural burada YAPISAL olarak
  uygulanır: GORSEL fazda gps modülü hiç ÇAĞRILMAZ ve filtrenin çıktısı
  komut yoluna GİRMEZ. ibvs.komut() imzasında hedef GPS'i zaten YOKTUR.

DÖNGÜ HIZI
  Görsel kol dedektörle sınırlı: uyarlanabilir çözünürlükte 10.8-17.5 FPS.
  Komut gönderimi bundan bağımsız olarak her tikte yapılır (son geçerli
  hedefe göre) -> araç komutsuz kalmaz.
================================================================================
"""
import math, time, sys
import numpy as np

from dow.sdk.baglanti import DowBaglanti
from dow.gudum.cevirici import HizCubukCevirici
from dow.gudum import ibvs
from dow.gorus import kamera as KAM
from dow.gorus.dedektor import Dedektor, DEVIR_MENZIL_M
from dow.fusion.gnss_filtre import GNSSDuzeltici


class Cfg:
    LOOP_HZ        = 50.0
    # --- KALKIS ---
    # ⛔ DERS (2026-08-21): kalkış fazı YOKTU. Drone yerde doğuyor, GPS fazı
    #   anında 25 m/s yatay hız istiyor, çevirici aracı 60° öne yatırıyor ve
    #   araç burnunu yere sokup PATLIYOR ("Player ☠"). İki koşu böyle gitti.
    #   Çare: güvenli irtifaya DİKEY tırman, yatay komut VERME.
    KALKIS_ALT_M   = 45.0    # m; ZEMİNE GÖRELİ tırmanılacak yükseklik.
                             # ⛔ DERS: bunu MUTLAK sanmıştım. b.irtifa()
                             #   DÜNYA Z'si döndürüyor ve zemin ~48 m; drone
                             #   doğar doğmaz "45'i geçtim" deyip kalkışı
                             #   ATLIYOR, yerdeyken yatay komut alıp
                             #   takılıp kalıyordu.
    KALKIS_VZ      = 12.0    # m/s; tırmanma hızı (tavan 33.5, temkinli)
    KALKIS_TOL_M   = 3.0
    VIS_N_KILIT    = 3       # ardışık geçerli tespit -> GORSEL faza geç
    # Görsel devir, GPS menzili bu değerin altına inmeden AÇILMAZ.
    # Yanlış-pozitiflerin ürettiği sahte "yakın menzil"i yapısal olarak eler.
    DEVIR_GPS_MENZIL_M = 60.0
    VIS_BAYAT_S    = 0.35    # tespit bu kadar eskiyse yok say
    VIS_KAYIP_S    = 1.0     # bu kadar kayıpta GPS'e geri dön
    # GPS fazı: hedefin ALTINDA ve gerisinde dur ki görsel devir kurulabilsin
    GPS_V_MAX      = 25.0    # m/s
    GPS_STANDOFF_M = 35.0    # m; hedefin bu kadar gerisine nişan al
    GPS_ALT_OFS_K  = 0.466   # irtifa ofseti = K*menzil (kamera 26.5° yukarı)
    GPS_ALT_OFS_MAX= 25.0    # m


class Beyin:
    def __init__(self, kayit=None):
        self.b = DowBaglanti()
        self.cev = HizCubukCevirici()
        self.det = Dedektor()
        self.filtre = GNSSDuzeltici()      # KULLANICININ filtresi — DEĞİŞTİRİLMEDİ
        self.durum = "KALKIS"
        self.hiz_I = 0.0
        self._kilit = 0
        self._son_tespit = None
        self._son_tespit_t = 0.0
        self._son_az = None
        self._son_az_t = None
        self._gps_menzil = 1e9        # görsel devir kapısı (bkz. adim())
        self._zemin_z = None          # spawn anındaki dünya Z'si (zemin)
        self.kayit = kayit
        self.tani = {}

    def spawn_sifirla(self):
        """Drone yeniden doğduğunda fazı başa alır.
        ⚠ _zemin_z SIFIRLANMAZ: zemin görev boyunca DEĞİŞMEZ ve onu yeniden
          almak kaçak tırmanmanın kök nedeniydi (bkz. adim() içindeki not)."""
        self.durum = "KALKIS"; self.hiz_I = 0.0
        self._kilit = 0; self._son_tespit = None
        self.det.sifirla()

    # ---------- görsel ----------
    def _los_hizi(self, azimut, t):
        """LOS'un dönüş hızı (°/s) — lead için. YALNIZ kameradan türetilir."""
        if self._son_az is None or self._son_az_t is None:
            self._son_az, self._son_az_t = azimut, t; return 0.0
        dt = t - self._son_az_t
        if dt < 1e-3: return 0.0
        h = (azimut - self._son_az)/dt
        self._son_az, self._son_az_t = azimut, t
        return max(-90.0, min(90.0, h))

    def gorsel_tik(self, img, t):
        """Kareyi işle; geçerli tespiti sakla. Döngüden BAĞIMSIZ hızda çağrılır."""
        d = self.det.bul(img)
        if d is None:
            return None
        cx, cy, w, h, conf = d
        ok, sebep = ibvs.gecerli(cx, cy, w, h, conf)
        self.tani["vis_conf"] = conf
        self.tani["vis_red"] = sebep
        self.tani["vis_imgsz"] = self.det.son_imgsz
        if not ok:
            return None
        self._son_tespit = (cx, cy, w, h, conf)
        self._son_tespit_t = t
        return self._son_tespit

    # ---------- ana adım ----------
    def adim(self, t, dt):
        # ⛔ SAĞLIK KAPISI: bağlantı ölürse telemetri DONAR ama hata vermez.
        #   Donmuş veriyle uçmak, uçmamaktan kötüdür (araç son komutu sürdürür).
        if not self.b.canli():
            self.tani["durum"] = "BAGLANTI_YOK"
            # ⛔ BURADA durum="KALKIS" YAPIYORDUM — YANLIŞTI. Her bağlantı
            #   kesintisi (saniyede bir olabiliyor) fazı kalkışa atıyordu;
            #   spawn_sifirla() da zemin referansını O ANKİ irtifadan yeniden
            #   alınca araç "yerdeyim" sanıp 45 m DAHA tırmanıyordu. Sonuç:
            #   irtifa 48 -> 855 m kaçak tırmanma (ölçüldü, koşu #9).
            #   Kesinti FAZI DEĞİŞTİRMEZ; yalnız o tik atlanır.
            self._kilit = 0; self._son_tespit = None
            # ⛔ BURADA _zemin_z'yi de SIFIRLIYORDUM — YANLIŞTI.
            #   Zemin referansı bir sonraki tikte O ANKİ irtifadan alınıyordu;
            #   araç 100 m'deyse "yukseklik=0" sanıp 45 m DAHA tırmanıyordu.
            #   Sonuç: 100 m'ye çık, 50'ye düş, tekrar tırman — kalıcı dikey
            #   salınım (bir koşuda tiklerin YARISI KALKIS fazında geçti).
            #   Zemin DEĞİŞMEZ; yalnız gercek RESPAWN'da sıfırlanır.
            return None
        yon = self.b.yonelim()                       # radyan
        own_roll = math.degrees(yon[0]); own_pitch = math.degrees(yon[1])
        own_yaw  = math.degrees(yon[2])
        v_olculen = self.b.hiz_vektoru()             # Unreal, m/s

        # ---- KALKIS: güvenli irtifaya kadar YALNIZ dikey komut ----
        irtifa = self.b.irtifa()
        if self._zemin_z is None:
            self._zemin_z = irtifa      # ilk tik = zemin referansı
        yukseklik = irtifa - self._zemin_z
        self.tani["yukseklik"] = yukseklik
        if self.durum == "KALKIS":
            # İKİNCİ, BAĞIMSIZ ÇIKIŞ: zemin referansı bozulsa bile hedefin
            # irtifasına ulaştıysak kalkış BİTMİŞTİR (yapısal emniyet).
            hedef_z = self.tani.get("gps_tz", 0.0)
            zaten_yuksek = hedef_z > 1.0 and irtifa >= hedef_z - 20.0
            if zaten_yuksek or yukseklik >= Cfg.KALKIS_ALT_M - Cfg.KALKIS_TOL_M:
                self.durum = "ARAMA"
            else:
                thr, pitch, roll, yaw = self.cev.cevir(
                    (0.0, 0.0, -Cfg.KALKIS_VZ), v_olculen,
                    math.radians(own_yaw), 0.0)
                # yatay kanalları SIFIRLA: yerde yatırma YOK
                self.b.komut(thr, 0.0, 0.0, 0.0, True)
                self.tani["durum"] = "KALKIS"; self.tani["irtifa"] = irtifa
                return thr, 0.0, 0.0, 0.0

        taze = (self._son_tespit is not None and
                (t - self._son_tespit_t) <= Cfg.VIS_BAYAT_S)

        # ---- faz makinesi ----
        if taze:
            self._kilit += 1
            cx, cy, w, h, conf = self._son_tespit
            R_kutu = KAM.menzil(max(w, h))
            # ⛔ DERS (2026-08-21): burada devir kapısı R_kutu'ya bakıyordu.
            #   Ama R_kutu tam da elemek istediğimiz YANLIŞ-POZİTİF tarafından
            #   üretiliyor: 140 m'deyken dedektör dev bir kutu buluyor, R_kutu
            #   1.3 m çıkıyor, kapı açılıyor ve güdüm "hedef 1 metrede" sanıp
            #   tam hücum veriyor -> araç yere çakılıyor ("Player ☠", 2 koşu).
            #   ÇARE: devri GPS MENZİLİYLE kapıla. Görsel temas HENÜZ YOK
            #   olduğu için GPS kullanmak yarışma kuralına (§10) UYGUNDUR;
            #   devirden SONRA GPS zaten hiç çağrılmaz.
            gps_ok = self._gps_menzil <= Cfg.DEVIR_GPS_MENZIL_M
            if (self.durum != "GORSEL" and self._kilit >= Cfg.VIS_N_KILIT
                    and gps_ok and R_kutu is not None
                    and R_kutu <= DEVIR_MENZIL_M):
                self.durum = "GORSEL"
                self.hiz_I = 0.0
            self.tani["devir_gps_m"] = self._gps_menzil
            self.tani["devir_kutu_m"] = R_kutu if R_kutu else -1
        else:
            self._kilit = 0
            if self.durum == "GORSEL" and (t - self._son_tespit_t) > Cfg.VIS_KAYIP_S:
                self.durum = "ARAMA"
                self.det.sifirla()

        # ---- komut üret ----
        if self.durum == "GORSEL":
            cx, cy, w, h, conf = self._son_tespit
            azimut, _ = KAM.piksel_kerteriz(cx, cy, own_pitch, own_roll)
            los_h = self._los_hizi(azimut, t)
            (vx, vy), vz_ned, yaw_hedef, self.hiz_I, ti = ibvs.komut(
                cx, cy, w, h, own_yaw, own_pitch, own_roll,
                self.hiz_I, dt, los_hiz_deg_s=los_h)
            self.tani.update(ti)
            yaw_rate = self._yaw_rate(yaw_hedef, own_yaw)
        else:
            (vx, vy), vz_ned, yaw_rate = self._gps_komut(t, own_yaw)

        thr, pitch, roll, yaw = self.cev.cevir(
            (vx, vy, vz_ned), v_olculen, math.radians(own_yaw), yaw_rate)
        self.b.komut(thr, pitch, roll, yaw, True)
        self.tani.update(self.cev.tani)
        self.tani["durum"] = self.durum
        return thr, pitch, roll, yaw

    @staticmethod
    def _yaw_rate(yaw_hedef_deg, own_yaw_deg):
        e = (yaw_hedef_deg - own_yaw_deg + 180.0) % 360.0 - 180.0
        return max(-ibvs.IbvsCfg.YAW_RATE_MAX,
                   min(ibvs.IbvsCfg.YAW_RATE_MAX, 3.0*e))

    # ---------- GPS fazı ----------
    def _gps_komut(self, t, own_yaw):
        """⛔ YALNIZ görsel temas YOKKEN çağrılır (yarışma kuralı §10).
        Bozuk hedef GPS'i KULLANICININ filtresinden geçirilir."""
        hx, hy, hz = self.b.hedef_konum_bozuk()          # metre
        temiz = self.filtre.guncelle(hx*100, hy*100, hz*100)   # filtre cm bekler
        if temiz is None:
            return (0.0, 0.0), 0.0, 0.0
        tx, ty, tz = temiz[0]/100.0, temiz[1]/100.0, temiz[2]/100.0
        dx_, dy_, dz_ = self.b.konum()
        dx = tx - dx_; dy = ty - dy_
        d_h = math.hypot(dx, dy)
        R = math.hypot(d_h, tz - dz_)
        # kamera 26.5° yukarı bakıyor -> hedefin ALTINDA dur ki kadrajda kalsın
        ofs = min(Cfg.GPS_ALT_OFS_MAX, Cfg.GPS_ALT_OFS_K * max(R, 1.0))
        z_hedef = tz - ofs
        # standoff: hedefin gerisine nişan al (üstünden geçmeyelim)
        if d_h > 1e-3:
            ux, uy = dx/d_h, dy/d_h
            nx = tx - ux*Cfg.GPS_STANDOFF_M; ny = ty - uy*Cfg.GPS_STANDOFF_M
        else:
            nx, ny = tx, ty
        ex, ey = nx - dx_, ny - dy_
        e = math.hypot(ex, ey)
        v = min(Cfg.GPS_V_MAX, 0.8*e)
        vx = v*ex/e if e > 1e-3 else 0.0
        vy = v*ey/e if e > 1e-3 else 0.0
        vz_ned = -max(-ibvs.IbvsCfg.VZ_MAX_ALCAL,
                      min(ibvs.IbvsCfg.VZ_MAX_TIRMAN, 0.9*(z_hedef - dz_)))
        ker = math.degrees(math.atan2(dy, dx))
        self.tani["gps_menzil"] = R
        self.tani["gps_tz"] = tz            # filtrenin verdiği hedef irtifası
        self.tani["gps_zhedef"] = z_hedef
        self.tani["gps_ez"] = z_hedef - dz_
        self.tani["gps_ofs"] = ofs
        self._gps_menzil = R
        return (vx, vy), vz_ned, self._yaw_rate(ker, own_yaw)
