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
⛔⛔ 2026-08-22 — ÜÇ EKLEMEM GERİ ALINDI. DÜRÜST KAYIT:

Görsel fazda hedefi vuramayınca üst üste "iyileştirme" ekledim ve HER BİRİ
işi KÖTÜLEŞTİRDİ. Ölçülen en yakın menzil medyanı:

  GV02  dikey kadraj regülasyonu (yalnız)   12.05 m   ISABET 1/4  <- EN İYİ
  GV03  + lead                              13.75 m   isabet 0/3
  GV04  + merkez freni                      13.00 m   isabet 0/3
  GV06  + sakin kamera                      16.08 m   isabet 0/3
  GV07  + tam yaw bandı + lead 0.5         ~19    m   isabet 0/2

HATAM: her kararı n=3 koşuyla verdim. CLAUDE.md §5.4 tam bunu yasaklıyor
("n<4 iken hüküm cümlesi kurulmaz") ve üç kez yaşandığı yazılı. Sakin
kameranın tespit kazancı (+5.7 puan) gerçek olabilir ama İSABETE
dönüşmedi; kalan ikisi için elimde kazanç gösteren hiçbir veri yok.

GERİ DÖNÜŞ: GV02 yapılandırması (yalnız dikey kadraj regülasyonu) TABAN
kabul edilir; n>=6 ile doğrulanır; sonra her ekleme AYRI ve DÖNÜŞÜMLÜ
A/B ile, n>=4/kol sınanır. Kod duruyor, anahtarlar KAPALI.
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

    # --- ⭐ SAKİN KAMERA (ÖLÇÜMLE BULUNDU, n=416 görsel kare) ---
    # Tespit kaybının sebebi HIZ DEĞİL, KONTROL EFORU:
    #      büyüklük     tespit VAR   tespit YOK
    #   |yaw komutu|        0.103        0.194   (1.9x)
    #   |roll|              0.095        0.200   (2.1x)
    #   |throttle|          0.300        0.669   (2.2x)
    #   |pitch|             0.249        0.258   (fark YOK)
    #   hız                 21.1         19.9    (fark YOK)
    # Kamera GÖVDEYE SABİT: araç yattıkça/döndükçe görüntü sallanıyor ve
    # 46 pikselik hedef bulanıklaşıyor. ana_kontrol.py'de de yazıyor:
    #   "Roll HEP 0 (bank yok — bank hedefi kadrajdan atıp kamerayı yere
    #    ceviriyordu)."
    # ÇARE: hızı LOS yönünde değil, ARACIN KENDİ BURNU yönünde komut et.
    #   Burnu hedefe yaw çevirir; roll ~0 kalır, kamera sabitlenir.
    SAKIN_KAMERA  = False   # ⛔ GERİ ALINDI (aşağıdaki nota bak)
    #                        kill-switch; False = eski (LOS yönünde) davranış
    # ⚠ YAW BANT GENİŞLİĞİ GERİ AÇILDI (GV06 dersi):
    #   Ölçümde suçlu üç büyüklüktü: roll (2.1x), throttle (2.2x), yaw (1.9x).
    #   SAKIN_KAMERA roll'u YAPISAL olarak sıfırladı; artık yaw'ı kısmaya
    #   gerek yok. Kısmanın BEDELİ ölçüldü: hedef 21.7 °/s dönüyor, kazanç
    #   1.5 ile kalıcı nişan hatası 21.7/1.5 = 14.5° kalıyor -> sürekli
    #   YANDAN uçuyoruz, menzil kapanmıyor (GV05: 18.9 -> 37.4 m geri açıldı).
    YAW_KAZANC    = 3.0
    YAW_HIZ_TAVAN = 120.0   # °/s
    VZ_TAVAN_GORSEL = 4.0   # m/s; dikey de kamerayı sallıyor -> kıs

    # --- lead (öngörü) ---
    # LEAD: kalıcı izleme gecikmesini kapatır. Gecikme = w_hedef / KAZANC.
    #   21.7 °/s ve kazanç 3.0 -> 7.2° kalıcı hata. lead = LEAD_SURE * w
    #   bunu kapatmalı: LEAD_SURE ~ 1/KAZANC = 0.33 s. Pay bırakıp 0.5.
    LEAD_SURE     = 0.0     # ⛔ GERİ ALINDI (aşağıdaki nota bak)
    LEAD_MENZIL_M = 6.4     # m; bu menzilin altında lead söner
    LEAD_MAX_DEG  = 25.0    # °; lead açısı tavanı

    # --- DİKEY: KADRAJ REGÜLASYONU ("alttan vuruş") ---
    # ⛔ ÖNCEKİ YASA ÇÖKTÜ (GV01, 3 koşu, ölçüldü):
    #   Hız vektörü doğrudan hedefe nişanlanıyordu (saf takip). Bu, hedefin
    #   İRTİFASINA TIRMANMAK demek: 24° yükselişte 28·sin(24°)=11.4 m/s
    #   tırmanma komutu. 6.8 m'lik farkı 0.6 s'de kapatıp hedefin hizasına
    #   çıkıyor; kamera 26.5° YUKARI baktığı için oradan hedef GÖRÜNMÜYOR.
    #   Sonuç: görsel fazda tespit %90 -> %12-15, isabet 0/3.
    #
    # YENİ YASA: hedefi KADRAJDA sabit bir yükseklikte tut (cy -> cy_ref).
    #   Kamera gövdeye sabit ve TILT° yukarı baktığı için "hedefi kadrajın
    #   şurasında tut" demek, "hedefin ALTINDA şu açıyla kal" demektir —
    #   geometri kendiliğinden çıkar, ayrıca hesaplamaya gerek yok.
    #   GİRDİ YALNIZ PİKSEL: menzil/irtifa/GPS KULLANILMAZ.
    #
    #   cy > cy_ref  -> hedef kadrajda AŞAĞIDA -> biz YÜKSEKTEYİZ -> ALÇAL
    #   cy < cy_ref  -> hedef kadrajda YUKARIDA -> biz ALÇAKTAYIZ -> TIRMAN
    K_CY          = 0.06    # (m/s)/px; kadraj dikey hatası -> dikey hız
    CY_REF_UZAK   = 470.0   # px; UZAKTA hedefi merkezin ÜSTÜNDE tut (altta kal)
    CY_REF_YAKIN  = 540.0   # px; YAKINDA merkeze getir (nişan al, vur)
    # Geçiş kutu boyutuyla: kutu bu değerden büyükse "yakın" sayılır.
    CY_GECIS_PX_UZAK = 40.0   # px (≈25 m)
    CY_GECIS_PX_YAKIN= 90.0   # px (≈11 m)
    VZ_MAX_TIRMAN = 33.5    # m/s; ÖLÇÜLDÜ
    VZ_MAX_ALCAL  = 6.95    # m/s; ÖLÇÜLDÜ (⚠ 4.8 kat asimetrik; hover'da.
                            #   İleri uçuşta 15.6'ya çıkıyor ama tabanı alıyoruz)

    # --- MERKEZ FRENİ (Gazebo'dan taşınmamıştı) ---
    # "Önce ortala, sonra ilerle." Hedef kadrajın kenarındayken tam gaz
    # gitmek onu kadrajdan ATIYOR: araç yatıyor, kamera gövdeye sabit
    # olduğu için görüntü sallanıyor, tespit kopuyor.
    # ÖLÇÜLDÜ (GV02): görsel fazda cx 991 -> 1292 (merkez 960) kaçtı ve
    # tespit %90'dan %22'ye düştü.
    # r = merkeze normalize sapma (0 = tam ortada, 1 = kadraj kenarı)
    # v *= max(FREN_TABAN, 1 - MERKEZ_FREN * r)
    MERKEZ_FREN  = 0.0     # ⛔ GERİ ALINDI (aşağıdaki nota bak)
    FREN_TABAN   = 0.35    # asla tam durma; biraz kapanış kalsın

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

    # --- 4b) İSTENEN KADRAJ YERİ (dikey nişan) — fren de bunu kullanır ---
    kg = _kirp((boyut - cfg.CY_GECIS_PX_UZAK) /
               max(1e-6, cfg.CY_GECIS_PX_YAKIN - cfg.CY_GECIS_PX_UZAK), 0.0, 1.0)
    cy_ref = cfg.CY_REF_UZAK + kg * (cfg.CY_REF_YAKIN - cfg.CY_REF_UZAK)

    # --- 5) HIZ: kutu boyutu hatası üzerinden PI ---
    # Denge kutusu = TEMAS kutusu -> hata hep pozitif, hız tavanda oturur.
    hedef_boyut = KAM.MENZIL_C / cfg.HUCUM_MENZIL_M
    hata_px = hedef_boyut - boyut
    hiz_I = _kirp(hiz_I + cfg.K_I * hata_px * dt, -cfg.I_MAX, cfg.I_MAX)
    v_istek = cfg.K_FWD * hata_px + hiz_I
    v = _kirp(v_istek, cfg.V_MIN, cfg.V_HUCUM)

    # MERKEZ FRENİ: İSTENEN kadraj yerinden ne kadar sapmışsa o kadar yavaşla.
    # ⚠ Dikeyde referans KADRAJ MERKEZİ DEĞİL, cy_ref'tir: hedefi bilerek
    #   merkezin üstünde tutuyoruz (alttan yaklaşma), bu SAPMA SAYILMAZ.
    rx = (cx - KAM.CX) / KAM.CX
    ry = (cy - cy_ref) / KAM.CY
    r = math.hypot(rx, ry)
    fren = max(cfg.FREN_TABAN, 1.0 - cfg.MERKEZ_FREN * r) if cfg.MERKEZ_FREN > 0 else 1.0
    v *= fren
    tani["ibvs_hata_px"] = hata_px
    tani["ibvs_v"] = v
    tani["ibvs_sapma"] = r
    tani["ibvs_fren"] = fren

    # --- 6) YATAY: SAKİN KAMERA -> hız BURUN yönünde ---
    # LOS yönünde komut vermek, burun henüz dönmemişken YANAL hız ister;
    # çevirici bunu ROLL'a çevirir ve kamera yatar (tespit ölür).
    # Burun yönünde komut verince yanal talep ~0 -> roll ~0.
    yon = math.radians(own_yaw_deg if cfg.SAKIN_KAMERA else yaw_hedef)
    vx = v * math.cos(yon)
    vy = v * math.sin(yon)

    # --- 7) DİKEY: KADRAJ REGÜLASYONU (piksel -> dikey hız) ---
    # Yakınlaştıkça nişan merkeze kayar: uzakta altta kal, yakında vur.
    e_cy = cy - cy_ref                      # + = hedef kadrajda AŞAĞIDA
    vz_yukari = -cfg.K_CY * e_cy            # aşağıdaysa ALÇAL
    if cfg.SAKIN_KAMERA:
        vz_yukari = _kirp(vz_yukari, -cfg.VZ_TAVAN_GORSEL, cfg.VZ_TAVAN_GORSEL)
    vz_yukari = _kirp(vz_yukari, -cfg.VZ_MAX_ALCAL, cfg.VZ_MAX_TIRMAN)
    vz_ned = -vz_yukari            # NED: pozitif = AŞAĞI
    tani["ibvs_vz_yukari"] = vz_yukari
    tani["ibvs_cy_ref"] = cy_ref
    tani["ibvs_e_cy"] = e_cy
    tani["ibvs_yakinlik"] = kg

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
