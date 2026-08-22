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
        self._bu_kare_tespit = False
        self._kilit = 0
        self._kayip = 0
        self._son_komut = (0.0, 0.0, 0.0, 0.0)
        self._los_az = None; self._los_t = None; self._los_hiz = 0.0
        self.hiz_I = 0.0
        self.tani = {}

    # ---------------- yardımcı ----------------
    def spawn_sifirla(self):
        """Drone yeniden doğduğunda: faz başa, zemin YENİDEN alınır.
        (Yeni spawn = gerçekten yerdeyiz; zemin referansı burada meşru.)"""
        self.durum = "KALKIS"
        self._zemin_z = None
        self._son_tespit = None
        self._bu_kare_tespit = False
        self._kilit = 0; self._kayip = 0
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
    def ibvs_sifirla(self):
        self._los_az = None; self._los_t = None; self._los_hiz = 0.0

    def _los_hizi(self, azimut_deg, t):
        """LOS'un dönüş hızı (°/s) — LEAD terimi için.
        ⛔ GİRDİ YALNIZ KAMERA: bbox azimutunun zaman türevi. GPS YOK.
        EMA ile yumuşatılır; dedektör ~10 Hz ve gürültülü."""
        if self._los_az is None or self._los_t is None:
            self._los_az, self._los_t = azimut_deg, t
            return 0.0
        dt = t - self._los_t
        if dt < 0.02:
            return self._los_hiz
        ham = (azimut_deg - self._los_az) / dt
        if abs(ham) < 200.0:
            self._los_hiz = 0.35 * ham + 0.65 * self._los_hiz
        self._los_az, self._los_t = azimut_deg, t
        return self._los_hiz

    def gorsel_tik(self, img_rgb, t):
        """Bir kamera karesini işle. GİRDİ YALNIZ GÖRÜNTÜ — GPS yok."""
        self._bu_kare_tespit = False
        if not self.cfg.GORSEL_AKTIF or self.det is None:
            return None
        d = self.det.bul(img_rgb)
        if d is None:
            return None
        cx, cy, w, h, conf = d
        ok, _sebep = ibvs.gecerli(cx, cy, w, h, conf)
        if not ok:
            return None
        self._son_tespit = d
        self._son_tespit_t = t
        self._bu_kare_tespit = True
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

        # ⛔⛔ YARIŞMA KURALI: GÖRSEL fazda GPS'e DOKUNULMAZ — okunmaz bile.
        #   hedef_konumu() YALNIZ görsel temas YOKKEN çağrılır. Böylece
        #   "görsel güdüm sırasında GPS kullanımı" fiziksel olarak imkânsız.
        hp = None; hv = (0.0, 0.0, 0.0)
        if self.durum != "GORSEL":
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
        # ---- DEVİR SAYAÇLARI (yalnız KAMERA verisi) ----
        # Kullanıcının şartı: 10 ardışık TESPİT -> görsel; 20 ardışık
        # TESPİTSİZ kare -> GPS'e dön.
        if self.cfg.GORSEL_AKTIF:
            if self._bu_kare_tespit:
                self._kilit += 1
                self._kayip = 0
            else:
                self._kayip += 1
                self._kilit = 0
            self.tani["kilit_kare"] = self._kilit
            self.tani["kayip_kare"] = self._kayip
            if self.durum != "GORSEL" and self._kilit >= self.cfg.DEVIR_KARE:
                self.durum = "GORSEL"; self.hiz_I = 0.0
                self.ibvs_sifirla()
            elif self.durum == "GORSEL" and self._kayip >= self.cfg.KAYIP_KARE:
                self.durum = "ISTASYON"; self._son_tespit = None

        if self.durum == "GORSEL":
            if self._son_tespit is None:
                # ⛔ DERS (GV01): burada son komutu AYNEN tutuyordum. Son komut
                #   sert bir dönüşse (roll ±1) araç 20 kare boyunca KÖR halde
                #   fırıl fırıl dönüyordu ve hedefi bir daha bulamıyordu.
                #   Köprüde DÖNÜŞ SIFIRLANIR; ileri ve dikey korunur —
                #   hedef kadrajda kaldığı yerde kalsın.
                t_, p_, r_, y_ = self._son_komut
                kopru = (t_, p_, 0.0, 0.0)
                self.b.komut(*kopru, True)
                self.tani["durum"] = "GORSEL_KOPRU"
                self._son_komut = kopru
                return kopru
            cx, cy, w, h, conf = self._son_tespit
            # ⛔ LEAD: LOS dönüş hızı YALNIZ kameradan türetilir (bbox
            #   azimutunun türevi). GV02'de bu terim BAĞLANMAMIŞTI (lead=0)
            #   ve saf takip çapraz giden hedefin gerisinde kalıyordu:
            #   cx 991 -> 1190 -> 1292 (merkez 960), sonra tespit koptu.
            from dow.gorus import kamera as _KAM
            _az, _ = _KAM.piksel_kerteriz(cx, cy, own_pitch, own_roll)
            los_h = self._los_hizi(_az, t)
            (vx, vy), vz_ned, yaw_hedef, self.hiz_I, ti = ibvs.komut(
                cx, cy, w, h, own_yaw, own_pitch, own_roll, self.hiz_I, dt,
                los_hiz_deg_s=los_h)
            self.tani["los_hiz"] = los_h
            self.tani.update(ti)
            # SAKİN KAMERA: yaw döngüsü de yumuşatıldı (ölçüm: sert yaw
            # tespiti öldürüyor — |yaw| 0.103 VAR / 0.194 YOK)
            e = (yaw_hedef - own_yaw + 180.0) % 360.0 - 180.0
            _kz = ibvs.IbvsCfg.YAW_KAZANC if ibvs.IbvsCfg.SAKIN_KAMERA else 3.0
            _tv = ibvs.IbvsCfg.YAW_HIZ_TAVAN if ibvs.IbvsCfg.SAKIN_KAMERA \
                  else self.cfg.YAW_RATE_MAX
            yaw_rate = max(-_tv, min(_tv, _kz * e))
            thr, pitch, roll, yaw = self.cev.cevir(
                (vx, vy, vz_ned), v_olculen, math.radians(own_yaw), yaw_rate)
            self.b.komut(thr, pitch, roll, yaw, True)
            self.tani.update(self.cev.tani)
            self._son_komut = (thr, pitch, roll, yaw)
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
