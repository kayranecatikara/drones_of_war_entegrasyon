# -*- coding: utf-8 -*-
"""
================================================================================
MERKEZİ AYARLAR — panelden CANLI değiştirilebilir
================================================================================
Gazebo'daki `bbox_ibvs.Cfg` ile aynı desen: SINIF NİTELİKLERİ. Güdüm döngüsü
her karede `Ayar.<ALAN>` okur; panel sınıf niteliğini değiştirince bir sonraki
kareden itibaren geçerli olur — UÇUŞ SIRASINDA, yeniden başlatmadan.
(CLAUDE.md §6'nın DoW karşılığı.)
================================================================================
"""
import os


def _f(ad, v):  return float(os.environ.get(ad, v))
def _b(ad, v):  return os.environ.get(ad, str(int(v))).strip() not in ("0", "", "false", "False")


class _IbvsKopru:
    """Panelin IBVS ayarlarını canlı değiştirebilmesi için köprü:
    Ayar.<ALAN> okunduğunda/yazıldığında IbvsCfg'ye yansır."""
    pass


class Ayar:
    # ================= AŞAMA ANAHTARLARI =================
    # ⚠ GELİŞTİRME KİPİ (2026-08-22, kullanıcı kararı):
    #   Şimdilik BOZUK GPS + filtre yerine DOĞRUDAN TRUTH kullanılıyor.
    #   Amaç: GPS güdümünün kendisini (istasyon tutma) filtre gürültüsünden
    #   ARINDIRILMIŞ olarak düzeltmek. Bu iş bitince GPS_KAYNAK="filtre"
    #   yapılıp gnss_filtre.py yeniden devreye alınacak.
    #   ⛔ YARIŞMADA "truth" KULLANILAMAZ — orada bu kanal gelmez.
    GPS_KAYNAK   = os.environ.get("DOW_GPS_KAYNAK", "truth")   # "truth" | "filtre"

    # ⚠ Görsel faz ŞİMDİLİK KAPALI (kullanıcı kararı): önce GPS istasyon
    #   tutma düzelsin, sonra görsele geçilsin. Kapalıyken dedektör hiç
    #   koşmaz -> döngü 10 FPS yerine ~50 Hz olur, testler ÇOK hızlanır.
    GORSEL_AKTIF = _b("DOW_GORSEL", False)

    # DEDEKTÖRÜ SADECE GÖSTER — güdüme GİRMEZ.
    # Kullanıcı panelde hedefin nasıl algılandığını görmek istiyor ama
    # güdüm GPS'te kalmalı. Bu anahtar dedektörü yalnız PANEL için koşturur;
    # çıktısı Beyin'e ASLA verilmez (GORSEL_AKTIF ayrı anahtardır).
    DEDEKTOR_GOSTER = _b("DOW_DET_GOSTER", True)
    DEDEKTOR_HZ     = _f("DOW_DET_HZ", 2.0)   # panel için çıkarım hızı

    # ================= KALKIŞ =================
    KALKIS_ALT_M   = _f("DOW_KALKIS_ALT", 45.0)   # zemine göreli
    KALKIS_VZ      = _f("DOW_KALKIS_VZ", 12.0)
    KALKIS_TOL_M   = 3.0

    # ================= İSTASYON (GPS fazının HEDEFİ) =================
    # Gazebo'daki çözülmüş tasarım: hedefin KUYRUĞUNDA, biraz ALTINDA dur.
    # Kamera 26.5° YUKARI baktığı için "altında" olmak hedefi kadraja sokar.
    # ⭐ ÖLÇÜLDÜ (GA03 taraması + GA04 n=4 doğrulaması): 15 m EN İYİ NOKTA.
    #   35 m -> ist_hata 6.28 m, tespit %48, kutu 20 px
    #   25 m -> ist_hata 5.63 m, tespit %77, kutu 29 px
    #   15 m -> ist_hata 5.28 m, tespit %90, kutu 46 px   <- SEÇİLDİ
    #    8 m -> ist_hata 4.81 m, tespit %79 (hedef kadraja SIĞMIYOR)
    ISTASYON_MENZIL_M = _f("DOW_IST_MENZIL", 15.0)  # hedefin kaç m ARKASINDA
    ISTASYON_ALT_M    = _f("DOW_IST_ALT", 15.0)     # kaç m ALTINDA (oran 0 ise)
    # Alt ofseti menzile ORANTILI tut: h = R * ORAN. tan(26.5°)=0.499 ->
    # 0.45 seçildi (hedef kadraj merkezinin hafif ÜSTÜNDE dursun; gökyüzü
    # arka planı ve "alttan yaklaşma" Gazebo'da da tercih edilmişti).
    ISTASYON_ALT_ORAN = _f("DOW_IST_ALT_ORAN", 0.45)
    # İleri besleme: hedefin hızı komuta DOĞRUDAN eklenir. Bu olmadan saf P
    # kontrolcü hareketli hedefi ASLA yakalayamaz (kalıcı gecikme hatası).
    ISTASYON_KP     = _f("DOW_IST_KP", 0.9)         # 1/s; konum hatası -> hız
    ISTASYON_KP_Z   = _f("DOW_IST_KPZ", 0.9)
    ISTASYON_ILERI  = _b("DOW_IST_ILERI", True)     # hedef hızı ileri besle
    # DÖNÜŞ ileri beslemesi: istasyon noktasının hedef etrafındaki süpürme
    # hızı (w x r). Kill-switch — ölçümle karar verilecek.
    ISTASYON_DONUS_ILERI = _b("DOW_IST_DONUS", False)
    V_MAX           = _f("DOW_V_MAX", 33.0)         # m/s (araç 34.6 yapabiliyor)
    VZ_MAX_TIRMAN   = 33.5
    VZ_MAX_ALCAL    = 6.95
    YAW_RATE_MAX    = _f("DOW_YAW_MAX", 120.0)      # °/s

    # ================= GÖRSEL DEVİR =================
    # ⛔⛔ YARIŞMA KURALI (kullanıcı 2026-08-22, DİSKALİFİYE SEBEBİ):
    #   "Görsel güdüm sırasında GPS verisini ASLA kullanma; mesafe verisini
    #    bile GPS'ten çekme. Görsel güdüm algoritmasına GPS verisini dahil
    #    etmek diskalifiye sebebi."
    #   Bu yüzden devir kapısı ARTIK GPS MENZİLİNE BAKMIYOR. Kapı tamamen
    #   KAMERA verisinden: ardışık N geçerli tespit.
    #   Yanlış-pozitife karşı koruma (eskiden GPS kapısı yapıyordu) şimdi:
    #     (a) ardışık 10 kare şartı — 10 kare üst üste aynı sahte kutu zor
    #     (b) ibvs.gecerli(): conf >= 0.40, kutu boyutu MENZIL_MIN..MAX
    #         aralığında (3-50 m). 140 m'de üretilen dev yanlış-pozitif
    #         (menzil 1.3 m) bu kapıdan GEÇEMEZ.
    DEVIR_KARE      = int(_f("DOW_DEVIR_KARE", 10))   # ardışık TESPİT -> görsel
    KAYIP_KARE      = int(_f("DOW_KAYIP_KARE", 20))   # ardışık TESPİTSİZ -> GPS

    # ================= BEKÇİ (uçuş sağlık bandı) =================
    BEKCI_AKTIF        = _b("DOW_BEKCI", True)
    BEKCI_ALT_MAX_M    = _f("DOW_B_ALT", 300.0)   # zemine göreli tavan
    BEKCI_MENZIL_MAX_M = _f("DOW_B_MENZIL", 500.0)
    BEKCI_SPAWN_MAX_M  = _f("DOW_B_SPAWN", 1500.0)
    BEKCI_DONMA_S      = _f("DOW_B_DONMA", 4.0)   # telemetri bu kadar donarsa
    BEKCI_ESIK         = 3                        # ardışık ihlal -> iptal

    # ================= KAYIT =================
    KAYIT_AKTIF   = _b("DOW_KAYIT", True)
    KAYIT_ARALIK  = _f("DOW_KAYIT_ARALIK", 0.5)   # s; kare + telemetri

    # ================= DÖNGÜ =================
    LOOP_HZ = _f("DOW_LOOP_HZ", 50.0)


# Panelin canlı değiştirebileceği alanlar (tip, etiket, min, max)
CANLI = {
    "ISTASYON_MENZIL_M": ("f", "İstasyon menzili (m)", 5, 120),
    "ISTASYON_ALT_M":    ("f", "İstasyon alt ofseti (m)", 0, 60),
    "ISTASYON_ALT_ORAN": ("f", "Alt ofset oranı (h=R*oran)", 0, 0.9),
    "ISTASYON_KP":       ("f", "İstasyon Kp (1/s)", 0.05, 3.0),
    "ISTASYON_KP_Z":     ("f", "İstasyon Kp dikey", 0.05, 3.0),
    "ISTASYON_ILERI":    ("b", "Hedef hızı ileri besle", 0, 1),
    "ISTASYON_DONUS_ILERI": ("b", "DÖNÜŞ ileri beslemesi (w×r)", 0, 1),
    "V_MAX":             ("f", "Hız tavanı (m/s)", 5, 34),
    "YAW_RATE_MAX":      ("f", "Yaw tavanı (°/s)", 20, 214),
    "KALKIS_ALT_M":      ("f", "Kalkış yüksekliği (m)", 10, 150),
    "GORSEL_AKTIF":      ("b", "GÖRSEL faz açık (güdüm)", 0, 1),
    "DEDEKTOR_GOSTER":   ("b", "Dedektörü panelde göster", 0, 1),
    "DEDEKTOR_HZ":       ("f", "Dedektör hızı (Hz)", 0.5, 10),
    "V_HUCUM":           ("f", "Hücum hızı (m/s)", 18, 34),
    "MERKEZ_FREN":       ("f", "Merkez freni", 0, 3),
    "K_CY":              ("f", "Dikey kadraj kazancı", 0.01, 0.3),
    "GPS_KAYNAK":        ("s", "GPS kaynağı (truth/filtre)", 0, 0),
    "BEKCI_AKTIF":       ("b", "Bekçi açık", 0, 1),
}
