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
import collections
import math
import threading

from dow.ayarlar import Ayar
from dow.sdk.baglanti import DowBaglanti
from dow.gudum.cevirici import HizCubukCevirici
from dow.gudum import gps as GPS
from dow.gorus.iz import Iz, IzCfg
from dow.gorus.tracker import TalonTracker, TargetLock, TakipCfg
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
        self._det_ms = 0.0                   # §5.1 mekanizma sütunları
        self._det_pencere = 0
        self._son_tespit_kare_t = 0.0        # ÖLÇÜM-ONLY (güdüme girmez)
        # ⭐ Ö-N DURUŞ GEÇMİŞİ — (t, roll, pitch, yaw) derece, ~4 s derinlik.
        #   Kare 145 ms bayat geldiği için köprünün kaydettiği yön, KARENİN
        #   ÇEKİLDİĞİ ANIN duruşuyla hesaplanmalı. Bu tampon o anı bulur.
        #   ⚠ Kendi IMU'muz — §10 temiz, hedefe dair hiçbir veri yok.
        self._durus_gecmis = collections.deque(maxlen=250)
        self._telafi_px = 0.0                # §5.1 mekanizma sütunu
        self._red_konum = 0; self._red_boyut = 0   # ÖLÇÜM-ONLY (kapı teşhisi)
        self._terminal_kabul = 0   # §5.1 Ö-A mekanizma sütunu: terminal
                                   # süreklilik istisnasıyla kaç kutu geçti
        self.iz = Iz()                       # tek hedefli iz (dow/gorus/iz.py)
        # ⭐ HYBRIDSORT TAKİPÇİSİ (2026-08-24) — TENBEL kurulur: boxmot ağır
        #   import, ve takip KAPALIYKEN hiç yüklenmemeli. `_takip_kur()` ilk
        #   kullanımda kurar; kurulamazsa takip sessizce KAPALI kalır ve
        #   sistem eski kapı yoluyla çalışmaya DEVAM eder (zarif bozulma).
        # ⭐ GÖRÜŞ KİLİDİ (Ayar.GORUS_ISP): çıkarım ayrı iş parçacığında
        #   koşarken görüş durumunu (son kutu, köprü, iz, takipçi) İKİ iş
        #   parçacığı birden ellemesin. RLock, çünkü gorsel_tik içinden
        #   çağrılan yardımcılar da aynı kilidi isteyebilir.
        #   ⚠ Kilit KAPALI kipte de vardır ama çekişme olmaz (tek iş parçacığı).
        self._kilit_g = threading.RLock()
        self.takip = None; self.kilit = None; self._takip_hata = None
        self._takip_id = -1; self._takip_kaynak = ""; self._takip_coast = -1
        self._takip_n = 0                    # §5.1 mekanizma: kaç izle döndü
        self.durum = "KALKIS"
        self._zemin_z = None
        self._son_tespit = None
        self._son_tespit_t = 0.0
        self._bu_kare_tespit = False
        self._cikarim_yapildi = True   # çıkarım bu tikte koştu mu (sayaç kapısı)
        self._kopru = None             # T5: son kutunun ATALET yönü
        self._yerel_aday = 0           # §5.1 mekanizma (T4)
        self._yerel_kayip = 0          # ardışık kapı başarısızlığı
        self._yerel_uygun = 0
        if hasattr(self, "iz"): self.iz.sifirla()
        self._kopru_say = 0            # §5.1 mekanizma sütunu
        self._bayat_birak_say = 0      # §5.1 mekanizma sütunu (B)
        self._kilit = 0
        self._kayip = 0
        self._son_komut = (0.0, 0.0, 0.0, 0.0)
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
        self._cikarim_yapildi = True   # çıkarım bu tikte koştu mu (sayaç kapısı)
        self._kopru = None             # T5: son kutunun ATALET yönü
        self._yerel_aday = 0           # §5.1 mekanizma (T4)
        self._yerel_kayip = 0          # ardışık kapı başarısızlığı
        self._yerel_uygun = 0
        if hasattr(self, "iz"): self.iz.sifirla()
        self._kopru_say = 0            # §5.1 mekanizma sütunu
        self._bayat_birak_say = 0      # §5.1 mekanizma sütunu (B)
        self._terminal_kabul = 0       # §5.1 mekanizma sütunu (Ö-A)
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
    def gorsel_tik(self, img_rgb, t, kare_t=None):
        """Bir kamera karesini işle. GİRDİ YALNIZ GÖRÜNTÜ — GPS yok.

        `kare_t` SADECE ÖLÇÜMDÜR (karenin ekrandan alındığı an). Güdüm ve
        köprü `_son_tespit_t`yi kullanmaya devam eder — bu parametre güdüm
        davranışını DEĞİŞTİRMEZ. Neden gerekti: `vis_yas` çıkarımın koştuğu
        andan sayıyordu, oysa kutu KARENİN yakalandığı anın dünyasını
        anlatır. Aradaki fark yakalama tavanı kadar (15 Hz -> 0-67 ms) ve
        birincil ölçütümüz kutu yaşı olduğu için bu yanlılık kabul edilemez."""
        with self._kilit_g:
            return self._gorsel_tik_kilitli(img_rgb, t, kare_t)

    def _gorsel_tik_kilitli(self, img_rgb, t, kare_t=None):
        self._bu_kare_tespit = False
        if not self.cfg.GORSEL_AKTIF or self.det is None:
            return None
        if TakipCfg.AKTIF and self._takip_kur():
            d = self._takip_bul(img_rgb, t)
        elif ibvs.IbvsCfg.YEREL_KAPI_PX > 0:
            d = self._yerel_bul(img_rgb, t)
        else:
            d = self.det.bul(img_rgb, merkez=(self._son_tespit[0],
                                              self._son_tespit[1])
                             if self._son_tespit else None)
        # §5.1 MEKANİZMA SÜTUNLARI — özellik gerçekten çalıştı mı
        self._det_ms = self.det.son_ms
        self._det_pencere = self.det.son_pencere
        if d is None:
            return None
        cx, cy, w, h, conf = d
        # ⭐ Ö-A: terminal süreklilik istisnası için SON KABUL EDİLEN kutunun
        #   genişliği ve yaşı geçilir. İkisi de PİKSEL/ZAMAN — GPS yok (§10).
        _sw = self._son_tespit[2] if self._son_tespit else None
        _sy = (t - self._son_tespit_t) if self._son_tespit else None
        ok, _sebep = ibvs.gecerli(cx, cy, w, h, conf, son_w=_sw, son_yas=_sy)
        if not ok:
            return None
        if _sebep == "terminal":
            self._terminal_kabul += 1     # §5.1 MEKANİZMA SÜTUNU
        self._son_tespit = d
        self._son_tespit_t = t
        self._son_tespit_kare_t = kare_t if kare_t else t   # ÖLÇÜM-ONLY
        self._bu_kare_tespit = True
        self._kopru_kaydet(d, t, kare_t)
        self.iz.guncelle(d, t)          # iz YALNIZ kabul edilen kutuyla tazelenir
        return d

    # ---------------- TAKİP: HYBRIDSORT + KİLİTLİ KİMLİK ----------------
    def _takip_kur(self):
        """Takipçiyi TENBEL kur. Dönüş: kullanılabilir mi."""
        if self.takip is not None:
            return True
        if self._takip_hata is not None:
            return False                       # bir kez denendi, olmadı
        try:
            self.takip = TalonTracker()
            self.kilit = TargetLock(self.takip,
                                    lock_conf=TakipCfg.KILIT_CONF,
                                    max_coast=TakipCfg.MAX_COAST)
            return True
        except Exception as e:                 # boxmot yok / sürüm uyumsuz
            self._takip_hata = repr(e)
            print("[TAKİP] kurulamadı (%s) -> KAPI yoluna dönülüyor." % self._takip_hata)
            return False

    def _takip_bul(self, img_rgb, t):
        """Kapı YERİNE zamansal takip. Girdi YALNIZ görüntü (§10 temiz — GPS yok).

        AKIŞ
          1. Dedektör DÜŞÜK eşikte (TakipCfg.CONF_MIN, ör. 0.10) TÜM kutuları
             verir. Kapıdan farkı: zayıf kutu ATILMAZ, takipçiye sunulur.
          2. HybridSort kutuları kareler arası eşleştirir. Zayıf kutu YENİ iz
             açamaz (BYTE ikinci turu) ama mevcut izi YAŞATIR.
          3. TargetLock kilitli kimliğin kutusunu döndürür; o karede eşleşme
             yoksa en fazla MAX_COAST kare Kalman ÖNGÖRÜSÜYLE köprüler.

        NEDEN KAPIDAN İYİ OLABİLİR: kapı, kutuyu SON KUTUYA olan uzaklığına
        bakarak eler ve bir kez kaybedince referans bayatlar — reddettikçe
        daha çok reddeder (ölçüldü: kutu yaşı >0.3 s olan karelerin %24.5'i).
        Takipçide referans, ivmesiyle birlikte ÖNGÖRÜLEN bir Kalman durumudur
        ve düşük güvenli kutu onu tazeleyebilir.

        ⚠ NEDEN BOZULABİLİR: takipçi yanlış-pozitife kilitlenirse hatayı
        SİLMEZ, MAX_COAST kare boyunca UZATIR. 22 Ağustos'ta tam bu yaşandı.
        Çare TargetLock'un iki koruması: (a) güçlü tespit sürekli başka
        yerdeyse kilit bırakılır, (b) kutu tek karede fiziksel olmayan
        mesafeye sıçrarsa kimlik şüpheli sayılır ve o kare çıktı verilmez.
        """
        import numpy as _np
        adaylar = self.det.bul_hepsi(img_rgb, TakipCfg.CONF_MIN, merkez=None)
        self._yerel_aday = len(adaylar)
        self._yerel_uygun = 0
        self._red_konum = self._red_boyut = 0      # kapı sütunları takipte boş
        if adaylar:
            dets = _np.array([[a[0]-a[2]/2.0, a[1]-a[3]/2.0,
                               a[0]+a[2]/2.0, a[1]+a[3]/2.0, a[4], 0.0]
                              for a in adaylar], dtype=_np.float32)
            _b = max(adaylar, key=lambda a: a[4])
            best = {"bbox": (_b[0]-_b[2]/2.0, _b[1]-_b[3]/2.0,
                             _b[0]+_b[2]/2.0, _b[1]+_b[3]/2.0), "conf": _b[4]}
        else:
            dets = _np.empty((0, 6), dtype=_np.float32)
            best = None
        izler = self.takip.update(dets, img_rgb)
        self._takip_n = int(len(izler))
        o = self.kilit.step(izler, best)
        if o is None:
            self._takip_id = -1; self._takip_kaynak = ""; self._takip_coast = -1
            self._yerel_kayip += 1
            return None
        self._takip_id = int(o["id"])
        self._takip_kaynak = o["kaynak"]           # "eslesme" | "tahmin"
        self._takip_coast = int(o["coast"])
        self._yerel_uygun = 1
        self._yerel_kayip = 0
        x1, y1, x2, y2 = o["bbox"]
        return ((x1+x2)/2.0, (y1+y2)/2.0, x2-x1, y2-y1, float(o["conf"]))

    # ---------------- T4: YERELLİK KAPISI ----------------
    def _yerel_bul(self, img_rgb, t):
        """Düşük eşikte tüm kutuları al, hedefin OLMASI GEREKEN yerine göre ele.

        Referans konum: önce T5 köprüsü (kendi dönüşümüz telafi edilmiş),
        yoksa son kutu. Referans yoksa normal argmax'a düşülür.
        ⭐ GİRDİ YALNIZ: görüntü + son kutu + KENDİ IMU'muz (§10 temiz)."""
        C = ibvs.IbvsCfg
        yon = self.b.yonelim()
        oy, op, orl = (math.degrees(yon[2]), math.degrees(yon[1]),
                       math.degrees(yon[0]))
        ref = self._kopru_kutu(oy, op, orl, t) or self._son_tespit
        # ⛔ KİLİTLENME ÇARESİ: üst üste YEREL_KURTAR kez hiçbir aday
        #   geçmediyse referans bayatlamış demektir; kapıyı AÇ ve düz
        #   argmax'la yeniden yakala. (B3'te bu yoktu ve kapı bir kere
        #   kaybedince bir daha asla bulamıyordu.)
        # ⭐ YAŞAM DÖNGÜSÜ. İZ AÇIKKEN sayı yerine SÜRE tabanlı: kilitlenmenin
        #   kaynağı "5 ıska görmeden açılma" kuralıydı (9 Hz'de 0.55 s
        #   TASARLANMIŞ körlük). Süre tabanlı kural, çıkarım hızından
        #   bağımsızdır ve kapı zaten yaşla genişlediği için nadiren gerekir.
        if IzCfg.AKTIF:
            if self.iz.yas(t) > IzCfg.OMUR_S:
                ref = None
        elif self._yerel_kayip >= C.YEREL_KURTAR:
            ref = None
        # ⭐ NATİF PENCERE (ROI) MERKEZİ = ref. Aynı referans hem pencereyi
        #   konumlandırır hem adayları eler. ref None ise (kurtarma) pencere
        #   de kapanır ve TAM KADRAJ taranır — kaybetmişken duyarlılık şart.
        #   Girdi yalnız kamera + kendi IMU'muz; GPS YOK (§10).
        adaylar = self.det.bul_hepsi(img_rgb, C.YEREL_CONF_MIN,
                                     merkez=(ref[0], ref[1]) if ref else None)
        self._yerel_aday = len(adaylar)
        self._yerel_uygun = 0
        if not adaylar:
            self._yerel_kayip += 1
            return None
        if ref is None:                       # referans yok/bayat -> argmax
            self._yerel_kayip = 0
            return max(adaylar, key=lambda a: a[4])
        rx, ry, rw = ref[0], ref[1], max(ref[2], 1.0)
        # ⭐ İZ: boyutu 1/w üzerinden ÖNGÖR, kapıyı YAŞLA GENİŞLET.
        #   Konum DONDURULMUŞ kalır (ölçüldü: ileri taşımak 1.5 s'de hatayı
        #   İKİ KATINA çıkarıyor). Eşikler dow/gorus/iz.py başlığında.
        _iz_yas = -1.0
        if IzCfg.AKTIF and self.iz.var:
            _o = self.iz.ongor(t)
            if _o:
                rw = max(_o[2], 1.0); _iz_yas = _o[3]
            _yaricap_iz, _b_alt, _b_ust = self.iz.kapi(t, rw)
        else:
            _yaricap_iz = C.YEREL_KAPI_PX + 2.0 * rw
            _b_alt, _b_ust = 0.5, 2.0
        self._iz_yas = _iz_yas
        self._iz_w = round(rw, 1)
        # ⭐ ÖLÇÜM-ONLY (2026-08-24): kapı adayları HANGİ filtreyle eliyor?
        #   ÖLÇÜLDÜ (HZ2, 148 kare): kutu yaşı >0.3 s olan karelerin
        #   %71.4'ünde model kutu BULMUŞ ama kapı HEPSİNİ elemiş. Yani
        #   "gecikme"nin baskın sebebi dedektör değil, BİZİM kapımız.
        #   Hangi filtrenin elediğini bilmeden düzeltme körlemesine olur.
        self._red_konum = self._red_boyut = 0
        for _a in adaylar:
            _k = math.hypot(_a[0]-rx, _a[1]-ry) <= _yaricap_iz
            _b = _b_alt <= _a[2]/rw <= _b_ust
            if not _k: self._red_konum += 1
            if _k and not _b: self._red_boyut += 1
        yaricap = _yaricap_iz
        uygun = [a for a in adaylar
                 if math.hypot(a[0]-rx, a[1]-ry) <= yaricap
                 and _b_alt <= a[2]/rw <= _b_ust]
        self._yerel_uygun = len(uygun)
        if not uygun:
            self._yerel_kayip += 1
            return None
        self._yerel_kayip = 0
        # ⚠ SEÇİM KURALI: referansa en yakın DEĞİL, EN YÜKSEK GÜVENLİ.
        #   "En yakın" seçmek, yerellik kapısından geçen bir çöp kutuyu
        #   referansa kilitleyip sürüklenmeye yol açıyor; dedektörün kendi
        #   kanıtı (güven) devrede kalmalı. Yerellik zaten YANLIŞ YERİ eledi.
        return max(uygun, key=lambda a: a[4])

    # ---------------- T5: BBOX KÖPRÜSÜ (ölü-hesap) ----------------
    def _durus_ara(self, hedef_t):
        """Geçmişten `hedef_t` anına EN YAKIN duruşu bul.

        Dönüş: (roll, pitch, yaw, bulunan_t) — geçmiş boşsa None.
        ⚠ EN YAKIN seçilir; kontrol döngüsü ~42 Hz olduğu için çözünürlük
          ~24 ms. Telafi edilen gecikme ~145 ms, yani oran ~6 — §5.3'ün
          istediği 5 katın üstünde.
        """
        if not self._durus_gecmis:
            return None
        en = min(self._durus_gecmis, key=lambda k: abs(k[0] - hedef_t))
        return (en[1], en[2], en[3], en[0])

    def _kopru_kaydet(self, d, t, kare_t=None):
        """Tespit anında kutunun ATALET yönünü sakla.

        ⭐ GİRDİ YALNIZ: bbox pikselleri + KENDİ IMU'muz. Hedefin GPS'i,
          menzili, hiçbiri yok -> görsel fazda meşru (§10).

        ⭐ Ö-N GECİKME TELAFİSİ (IbvsCfg.GECIKME_TELAFI):
          Kare `kare_t` anında çekildi ama biz onu `t` anında işliyoruz.
          Arada gövde döndü. Telafi AÇIKKEN yön, KARENİN ÇEKİLDİĞİ anın
          duruşuyla hesaplanır; köprünün ileri taşıması zaten doğru
          çalıştığı için sonuç bugüne doğru yansır.
          KAPALIYKEN davranış bit bit eskisi gibidir.
        """
        yon = self.b.yonelim()
        oy, op, orl = (math.degrees(yon[2]), math.degrees(yon[1]),
                       math.degrees(yon[0]))
        cx, cy, w, h, conf = d

        self._telafi_px = 0.0
        if ibvs.IbvsCfg.GECIKME_TELAFI and kare_t and kare_t < t:
            g = self._durus_ara(kare_t)
            if g is not None:
                k_roll, k_pitch, k_yaw, _bt = g
                # §5.1 MEKANİZMA: telafi nişan noktasını kaç piksel kaydırdı.
                #   Aynı atalet yönünü İKİ duruşla kadraja yansıtıp farkına
                #   bakarız. 0 ise özellik ATIL demektir.
                az0, el0 = ibvs.KAM.piksel_kerteriz(cx, cy, op, orl)
                az1, el1 = ibvs.KAM.piksel_kerteriz(cx, cy, k_pitch, k_roll)
                p0 = ibvs.KAM.kerteriz_piksel(az0, el0, op, orl)
                p1 = ibvs.KAM.kerteriz_piksel(az1, el1, op, orl)
                if all(v == v for v in p0 + p1):
                    self._telafi_px = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
                oy, op, orl = k_yaw, k_pitch, k_roll

        az, el = ibvs.KAM.piksel_kerteriz(cx, cy, op, orl)
        self._kopru = {"az": oy + az, "el": el, "w": w, "h": h,
                       "conf": conf, "t": t}

    def _kopru_kutu(self, own_yaw, own_pitch, own_roll, t):
        """Saklanan atalet yönünü BUGÜNKÜ duruşumuzla kadraja geri yansıt.

        NEDEN: çıkarım 10 Hz (100 ms) ve tespit boşlukları var; o sürede
        araç yatıyor/dönüyor (ölçüldü: roll p90 52.7°, yani 100 ms'de
        kolayca 5-10° gövde dönüşü) ve gövdeye SABİT kamera yüzünden hedef
        kadrajda kayıyor. Güdüm bayat pikselle nişan alıyor. Köprü, kendi
        dönüşümüzü telafi ederek kutuyu kadrajda ileri taşır.
        SINIRI: hedefin KENDİ hareketini bilmez; bu yüzden KOPRU_S kadar
        yaşar, sonra düşer."""
        k = self._kopru
        if not k or ibvs.IbvsCfg.KOPRU_S <= 0:
            return None
        if (t - k["t"]) > ibvs.IbvsCfg.KOPRU_S:
            return None
        az = (k["az"] - own_yaw + 180.0) % 360.0 - 180.0
        cx, cy = ibvs.KAM.kerteriz_piksel(az, k["el"], own_pitch, own_roll)
        if not (0 <= cx < ibvs.KAM.IMG_W and 0 <= cy < ibvs.KAM.IMG_H):
            return None
        return (cx, cy, k["w"], k["h"], k["conf"])

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
        # ⭐ Ö-N: duruşu zaman damgasıyla sakla (kontrol döngüsü ~42 Hz ->
        #   250 kayıt ≈ 6 s). Köprü, bayat karenin ÇEKİLDİĞİ anın duruşunu
        #   buradan çeker. Bu satır özellik KAPALIYKEN de çalışır (sadece
        #   liste doldurur, davranış değiştirmez) — tampon her zaman hazır
        #   olsun ki panelden canlı açılış anında geçmiş boş kalmasın.
        self._durus_gecmis.append((t, own_roll, own_pitch, own_yaw))
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

        self.tani = {"det_ms": round(self._det_ms, 2),
                     "det_pencere": self._det_pencere,
                     # §5.1 TAKİP MEKANİZMA SÜTUNLARI — "özellik gerçekten
                     # çalıştı mı" sorusunu bunlar cevaplar. takip_n=0 olan
                     # bir DENEY koşusu veri noktası değil, GEÇERSİZ koşudur.
                     "takip_id": self._takip_id,
                     "takip_kaynak": self._takip_kaynak,   # eslesme|tahmin|""
                     "takip_coast": self._takip_coast,     # kaç kare öngörü
                     "takip_n": self._takip_n,             # aktif iz sayısı
                     "iz_yas": round(getattr(self, "_iz_yas", -1.0), 3),
                     "iz_w": getattr(self, "_iz_w", 0.0),
                     "red_konum": self._red_konum,
                     "red_boyut": self._red_boyut,
                     "terminal_kabul": self._terminal_kabul,   # §5.1 Ö-A
                     "yerel_kayip": self._yerel_kayip,
                     "durum": self.durum, "yukseklik": yukseklik,
                     "hedef_var": int(hp is not None),
                     # §5.1 mekanizma sütunları — tani her tik SIFIRDAN
                     # kurulduğu için gorsel_tik'in yazdıkları siliniyordu;
                     # kalıcı alanlardan yeniden yayınlanıyor.
                     "yerel_aday": self._yerel_aday,
                     "yerel_uygun": self._yerel_uygun,
                     "kopru_kare": self._kopru_say,
                     "telafi_px": round(self._telafi_px, 1),
                     "bayat_birak": self._bayat_birak_say}

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
        # ---- GÜDÜM KİPİ (panelden canlı) ----
        from dow.ayarlar import kip_oku
        kip = kip_oku()          # panelden CANLI seçilir (paylaşımlı dosya)
        self.tani["kip"] = kip
        if kip == "gps" and self.durum == "GORSEL":
            self.durum = "ISTASYON"       # kip değişti -> görselden çık

        # ---- DEVİR SAYAÇLARI (yalnız KAMERA verisi) ----
        # Kullanıcının şartı: 10 ardışık TESPİT -> görsel; 20 ardışık
        # TESPİTSİZ kare -> GPS'e dön.
        if self.cfg.GORSEL_AKTIF and self._cikarim_yapildi:
            # ⚠ SAYAÇLAR ÇIKARIM BAŞINA SAYAR, kontrol tiki başına DEĞİL.
            #   Çıkarım 10 Hz, kontrol ~48 Hz; tik başına saymak "20 ardışık
            #   tespitsiz kare" kuralını 0.4 saniyeye indirirdi.
            if self._bu_kare_tespit:
                self._kilit += 1
                self._kayip = 0
            else:
                self._kayip += 1
                self._kilit = 0
            self.tani["kilit_kare"] = self._kilit
            self.tani["kayip_kare"] = self._kayip
            # ---- ⭐ DEVİR KAPISI — YALNIZ KAMERA (2026-08-25) ----
            # ⛔ GPS'e BAKMAZ. Eskiden burada "istasyona otur + ≤15 m menzil"
            #   diye ikinci bir kapı vardı ve hedefin GPS'ini okuyordu;
            #   yarışma kuralı gereği (§10) TAMAMEN SİLİNDİ (§5.12).
            #   Tek tetik: ardışık TESPİT sayacı. Sayaç `_cikarim_yapildi`
            #   kapısının arkasında olduğu için ÇIKARIM başına artar
            #   (~9 Hz -> 10 kare ≈ 1.1 s), kontrol tiki başına DEĞİL.
            if (kip != "gps" and self.durum != "GORSEL"
                    and self._kilit >= self.cfg.DEVIR_KARE):
                self.durum = "GORSEL"; self.hiz_I = 0.0
            # "gorsel" kipinde GERİ DÖNÜLMEZ; yalnız "hibrit"te geri dönüş var
            elif (kip == "hibrit" and self.durum == "GORSEL"
                    and self._kayip >= self.cfg.KAYIP_KARE):
                self.durum = "ISTASYON"
                # ⚠ GÖRÜŞ KİLİDİ: bu satırlar KONTROL iş parçacığında koşar,
                #   gorsel_tik ise (GORUS_ISP açıkken) GÖRÜŞ iş parçacığında.
                #   Kilitsiz sıfırlamak, takipçi kendini güncellerken içini
                #   boşaltmak demektir.
                with self._kilit_g:
                    self._son_tespit = None
                    self.iz.sifirla()   # temas koptu: eski iz yeni yakalamayı ELEMESİN
                    if self.kilit is not None:
                        self.kilit.reset()   # ve eski KİMLİK yeni yakalamayı ELEMESİN

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
            _tsp = self._son_tespit
            if ibvs.IbvsCfg.KOPRU_S > 0:
                _kb = self._kopru_kutu(own_yaw, own_pitch, own_roll, t)
                if _kb is not None:
                    _tsp = _kb
                    if not self._bu_kare_tespit:
                        self._kopru_say += 1
                elif (ibvs.IbvsCfg.BAYAT_BIRAK
                      and (t - self._son_tespit_t) > ibvs.IbvsCfg.KOPRU_S):
                    # B: köprü doldu -> hedef KAYIP. Eski ham kutuya nişan
                    #    almaya devam etmek, hayalete uçmaktır.
                    _tsp = None
                    self._bayat_birak_say += 1
            self.tani["bayat_birak"] = self._bayat_birak_say
            if _tsp is None:
                t_, p_, r_, y_ = self._son_komut
                kopru = (t_, p_, 0.0, 0.0)
                self.b.komut(*kopru, True)
                self.tani["durum"] = "GORSEL_KOPRU"
                self._son_komut = kopru
                return kopru
            self.tani["kopru_kare"] = self._kopru_say
            cx, cy, w, h, conf = _tsp
            # ⛔ LEAD: LOS dönüş hızı YALNIZ kameradan türetilir (bbox
            #   azimutunun türevi). GV02'de bu terim BAĞLANMAMIŞTI (lead=0)
            #   ve saf takip çapraz giden hedefin gerisinde kalıyordu:
            #   cx 991 -> 1190 -> 1292 (merkez 960), sonra tespit koptu.
            (vx, vy), vz_ned, yaw_hedef, self.hiz_I, ti = ibvs.komut(
                cx, cy, w, h, own_yaw, own_pitch, own_roll, self.hiz_I, dt,
                own_vz=v_olculen[2])      # Unreal Z yukarı; KENDİ hızımız
            self.tani.update(ti)
            # ⚠ ÖLÇÜM-ONLY (2026-08-27): görsel fazda araç düz uçuşta
            #   22.1 m/s, istasyon fazında 25.6 m/s ölçüldü — aynı araç,
            #   aynı düz uçuş, 4 m/s fark. Kapanma bütçesi zaten ~4 m/s
            #   olduğu için bu açık kritik. Sebebi bulmak için KOMUT ile
            #   GERÇEKLEŞENİ 20 Hz'te yan yana loglamak şart; `ibvs_v` hiç
            #   loglanmıyordu ve meta.csv 1 Hz olduğu için §5.3'ü ihlal
            #   ediyordu. Güdüme HİÇBİR etkisi yok, yalnız CSV.
            self.tani["olcum_hiz"] = round(
                math.hypot(v_olculen[0], v_olculen[1]), 2)
            self.tani["olcum_vz"] = round(v_olculen[2], 2)
            e = (yaw_hedef - own_yaw + 180.0) % 360.0 - 180.0
            _tv = self.cfg.YAW_RATE_MAX
            yaw_rate = max(-_tv, min(_tv, 3.0 * e))
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
            dp, own_yaw, hp, hv, self.izleyici.yon_deg, self.cfg)
        self.tani.update(ti)

        thr, pitch, roll, yaw = self.cev.cevir(
            (vx, vy, vz_ned), v_olculen, math.radians(own_yaw), yaw_rate)
        self.b.komut(thr, pitch, roll, yaw, True)
        self.tani.update(self.cev.tani)
        return thr, pitch, roll, yaw
