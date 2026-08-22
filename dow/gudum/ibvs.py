# -*- coding: utf-8 -*-
"""
================================================================================
GÖRSEL GÜDÜM (IBVS) — Gazebo yasası, DoW sabitleriyle
================================================================================
YAPI AYNEN TAŞINDI (Seçenek A): saf takip + kutu boyutundan PI hız yasası.
DEĞİŞEN yalnız SABİTLER; hepsi DoW'da ÖLÇÜLDÜ.

TERİMLER (CLAUDE.md §0.2 — hiçbiri tanımsız bırakılmaz)
  * IBVS (görüntü-tabanlı görsel servolama): kontrol hatası doğrudan
    GÖRÜNTÜ UZAYINDA tanımlanır (piksel), 3B konum kestirmeye gerek yok.
  * saf takip (pure pursuit): hız vektörünü her an hedefe DOĞRU çevir.
    Basit ve dayanıklı; kusuru, kaçan hedefte "kuyruktan" takip etmesi.
  * LOS (görüş hattı): araçtan hedefe giden doğru.
  * kapanma hızı: menzilin azalma hızı (−dR/dt).
  * lead (öngörü): nişanı hedefin gideceği yöne ÖNE almak.
  * PI: Oransal + İntegral kontrolcü. P anlık hatayla, I birikmiş hatayla
    orantılı çıktı üretir; I kalıcı hatayı (sabit fark) kapatır.

YARIŞMA KURALI (CLAUDE.md §10) — YAPISAL GARANTİ
  Bu modülün girdileri: bbox pikselleri + KENDİ IMU'muz (roll/pitch/yaw).
  Hedefin GPS'i FONKSİYON İMZASINDA YOK -> görsel fazda kural ihlali
  yapısal olarak İMKÂNSIZ (Gazebo'daki B5 bekçisinin emsali).

DoW'DA ÖLÇÜLEN SABİTLER (Gazebo değeri -> DoW değeri, neden)
  MENZIL_C   296.8 px·m @640  ->  997 px·m @1920
      Gazebo hedefi 1.28 m kanatlıydı, DoW Talon'u 1.718 m. 1920'ye
      ölçeklenmiş Gazebo sabiti 557 olurdu -> 1.79 KAT yanlış.
  V_HUCUM    18.0 m/s -> 28.0 m/s
      DoW Talon'u 17.98 m/s uçuyor. 18 ile kapanma 0.02 m/s = ASLA
      yakalayamayız. Araç 34.6 m/s yapabiliyor; 28 -> kapanma ~10 m/s.
      (Tavanın tamamı kullanılmadı: toplam hız bütçesi dikeyle paylaşılıyor.)
  kamera     FX=166.6/CX=320 @640 -> f=540.4/CX=960 @1920, TILT 26.5°
      Ölçüldü, artık 2.6 px. Ayrıntı: dow/gorus/kamera.py
  VZ tavanı  ±15 simetrik -> +33.5 / -6.95 ASİMETRİK
      Ölçüldü. Simetrik varsaymak alçalma komutunu ~5 kat abartır.

⭐ YAPISAL UYUM: aracın dikey asimetrisi (güçlü tırmanma, zayıf alçalma)
   güdümün ihtiyacıyla ÖRTÜŞÜYOR. Kamera 26.5° YUKARI baktığı için hedefi
   kadrajda tutmak aracı hedefin ALTINDA tutar; oradan hedefe gitmek
   TIRMANMAKTIR — bol yetkimiz olan yön. Gazebo'daki "alttan vuruş"
   tasarımı DoW aracına tesadüfen değil, doğal olarak oturuyor.
================================================================================
"""
import math
from dow.gorus import kamera as KAM


def _kirp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class IbvsCfg:
    # --- hız yasası ---
    V_HUCUM       = 28.0    # m/s; hücum hızı tavanı (hedef 17.98 -> kapanma ~10)
    V_MIN         = 0.0     # m/s; asla geri gitme
    HUCUM_MENZIL_M= 1.0     # m; PI'nın sıfır noktası = TEMAS menzili.
                            # "Şu menzilde dur" noktası YOK -> hata hep pozitif
                            # kalır, hız tavanda oturur, sabit kapanma.
    K_FWD         = 0.35    # (m/s)/px; P kazancı  (Gazebo'dan AYNEN)
    K_I           = 0.04    # (m/s)/(px·s); I kazancı (Gazebo'dan AYNEN)
    I_MAX         = 8.0     # m/s; integral doyumu (windup önleyici)

    # --- yaw ---
    K_YAW         = 1.0     # tam düzeltme (Gazebo'dan AYNEN)
    YAW_RATE_MAX  = 120.0   # °/s. Araç 214 yapabiliyor AMA hızlı yaw
                            # görüntüyü bulandırıp dedektörü kırar -> KORUNDU.
    YAW_OLU_BAND  = 1.0     # °; altında yaw komutu güncellenmez

    # --- lead (öngörü) ---
    LEAD_SURE     = 0.4     # s (Gazebo'dan AYNEN)
    LEAD_MENZIL_M = 6.4     # m; bu menzilin altında lead söner
    LEAD_MAX_DEG  = 25.0    # °; lead açısı tavanı

    # --- dikey ---
    K_ELEV        = 1.0     # nişan yükselişi -> dikey hız ölçeği
    VZ_MAX_TIRMAN = 33.5    # m/s; ÖLÇÜLDÜ
    VZ_MAX_ALCAL  = 6.95    # m/s; ÖLÇÜLDÜ (⚠ 4.8 kat asimetrik)
    # Hedefi kadrajda tutmak için aracı hedefin ALTINDA tut: nişan noktası
    # hedefin bu kadar ALTINA konur (açı olarak). Gazebo'daki "alttan vuruş".
    ALT_NISAN_DEG = 0.0     # °; 0 = doğrudan hedefe nişanla

    # --- geçerlilik ---
    CONF_MIN      = 0.40    # ÖLÇÜLDÜ (dow/gorus/dedektor.py)
    BOYUT_MIN_PX  = 8.0     # px; bundan küçük kutu güvenilmez
    MENZIL_MAX_M  = 50.0    # m; ötesinde görsel devir YOK (tespit %10)
    MENZIL_MIN_M  = 3.0     # m; ALTINDAKİ kutu = dev yanlış-pozitif.
                            # 997/3 = 332 px'lik kutu demek; hedef bu boyuta
                            # ancak TEMAS anında ulaşır. Dedektör 140 m'de
                            # bu boyutta kutular üretiyordu (ölçüldü).


def komut(cx, cy, w, h, own_yaw_deg, own_pitch_deg, own_roll_deg,
          hiz_I, dt, cfg=IbvsCfg, los_hiz_deg_s=0.0):
    """IBVS kontrol yasası.

    GİRDİ (hedefin GPS'i YOK — yapısal garanti):
      cx, cy, w, h  : tespit kutusu (piksel) — TEK canlı hedef kaynağı
      own_*         : KENDİ yönelimimiz (derece) — kendi IMU'muz
      hiz_I         : hız integralinin o anki değeri (m/s); çağıran taşır
      dt            : adım süresi (s)
      los_hiz_deg_s : LOS'un dönüş hızı (°/s) — lead için; kameradan türetilir

    ÇIKTI: (v_ned, vz, yaw_hedef_deg, hiz_I_yeni, tani)
      v_ned = (vx, vy) m/s DÜNYA yatay düzleminde (NED: x kuzey, y doğu)
      vz    = m/s, NED (POZİTİF = AŞAĞI; çevirici ters çevirir)
    """
    tani = {}

    # --- 1) MENZİL: kutu boyutundan (benzer üçgenler, p = C/R) ---
    boyut = max(w, h)                      # köşegen yerine en büyük eksen
    R = KAM.menzil(boyut) if boyut > 0 else None
    tani["ibvs_boyut_px"] = boyut
    tani["ibvs_menzil_m"] = R if R else -1

    # --- 2) KERTERİZ: kadraj konumundan, KENDİ duruşumuz telafi edilerek ---
    azimut, yukselis = KAM.piksel_kerteriz(cx, cy, own_pitch_deg, own_roll_deg)
    tani["ibvs_azimut"] = azimut
    tani["ibvs_yukselis"] = yukselis

    # --- 3) LEAD: nişanı LOS dönüş hızıyla öne al; yakında söner ---
    lead_olcek = 1.0
    if R and R > 0:
        lead_olcek = _kirp(R / cfg.LEAD_MENZIL_M, 0.0, 1.0)
    lead = _kirp(cfg.LEAD_SURE * lead_olcek * los_hiz_deg_s,
                 -cfg.LEAD_MAX_DEG, cfg.LEAD_MAX_DEG)
    tani["ibvs_lead"] = lead

    # --- 4) YAW: burnu hedefe çevir (+ lead) ---
    eps_yaw = azimut + lead
    if abs(eps_yaw) < cfg.YAW_OLU_BAND:
        eps_yaw = 0.0
    yaw_hedef = own_yaw_deg + cfg.K_YAW * eps_yaw
    tani["ibvs_eps_yaw"] = eps_yaw

    # --- 5) HIZ: kutu boyutu hatası üzerinden PI ---
    # Denge kutusu = TEMAS kutusu -> hata hep pozitif, hız tavanda oturur.
    hedef_boyut = KAM.MENZIL_C / cfg.HUCUM_MENZIL_M
    hata_px = hedef_boyut - boyut
    hiz_I = _kirp(hiz_I + cfg.K_I * hata_px * dt, -cfg.I_MAX, cfg.I_MAX)
    v_istek = cfg.K_FWD * hata_px + hiz_I
    v = _kirp(v_istek, cfg.V_MIN, cfg.V_HUCUM)
    tani["ibvs_hata_px"] = hata_px
    tani["ibvs_v"] = v

    # --- 6) HIZI LOS YÖNÜNE DAĞIT ---
    # Hız DAİMA LOS (nişan) yönünde: hedef dönünce hız vektörü de döner,
    # dondurulmuş taşıyıcının yana savurma hatası YAPISAL OLARAK imkânsız.
    nisan_yukselis = yukselis - cfg.ALT_NISAN_DEG
    ce = math.cos(math.radians(nisan_yukselis))
    se = math.sin(math.radians(nisan_yukselis))
    # yatay bileşen, KOMUT EDİLEN yaw yönünde (burun hedefe dönüyor)
    yon = math.radians(yaw_hedef)
    vx = v * ce * math.cos(yon)
    vy = v * ce * math.sin(yon)

    # --- 7) DİKEY: nişan yükselişine göre, ASİMETRİK tavanla ---
    vz_yukari = cfg.K_ELEV * v * se
    vz_yukari = _kirp(vz_yukari, -cfg.VZ_MAX_ALCAL, cfg.VZ_MAX_TIRMAN)
    vz_ned = -vz_yukari            # NED: pozitif = AŞAĞI
    tani["ibvs_vz_yukari"] = vz_yukari

    return (vx, vy), vz_ned, yaw_hedef, hiz_I, tani


def gecerli(cx, cy, w, h, conf, cfg=IbvsCfg):
    """Bu tespit güdüme girebilir mi? (§5.1 mekanizma kapısı için ayrı tutuldu)"""
    if conf < cfg.CONF_MIN: return False, "conf"
    boyut = max(w, h)
    if boyut < cfg.BOYUT_MIN_PX: return False, "boyut"
    R = KAM.menzil(boyut)
    if R is None or R > cfg.MENZIL_MAX_M: return False, "menzil_uzak"
    if R < cfg.MENZIL_MIN_M: return False, "menzil_yakin"   # dev yanlış-pozitif
    if not (0 <= cx < KAM.IMG_W and 0 <= cy < KAM.IMG_H): return False, "kadraj"
    return True, ""
