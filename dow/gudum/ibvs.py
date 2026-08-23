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
import os

from dow.gorus import kamera as KAM


def _fi(ad, v):   # env ile geçersiz kılınabilir (kampanya kill-switch'i)
    return float(os.environ.get(ad, v))


def _b_i(ad, v):
    return os.environ.get(ad, str(int(v))).strip() not in ("0", "", "false", "False")


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

    VZ_TAVAN_GORSEL = _fi("DOW_VZ_TAVAN_GORSEL", 1.5)   # m/s

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

    # T6 · DİKEY YUMUŞATMA — |throttle| tespiti en çok bozan büyüklüktü
    #   (2.2 kat). VZ_TAVAN_GORSEL zaten var ama YALNIZ SAKIN_KAMERA
    #   açıkken uygulanıyordu; bu anahtar onu bağımsız kılar.
    # ⭐⭐ GİRDİ 2026-08-23 gecesi — GECENİN EN BÜYÜK KAZANIMI.
    #   B7, n=4/kol, dönüşümlü A/B:
    #      ölçüt          KAPALI     AÇIK
    #      isabet          3/4        4/4
    #      en_yakin       3.00 m     0.72 m
    #      koşular   2.16·1.55·3.84·5.14   0.69·0.82·0.56·0.76
    #      tespit%        20.70      50.90   (2.5 KAT)
    #      doğru%         89.20      95.05
    #      yanlış%        10.80       4.95
    #      görsel faz     27.15 s    38.40 s
    #      roll p90       12.60°      5.55°
    #   ARALIKLAR HİÇ ÖRTÜŞMÜYOR: kontrol [1.55-5.14], deney [0.56-0.82].
    #   İlan edilen birincil ölçüt (tespit%) +30 PUAN; her geçerlilik eşi
    #   de aynı yönde -> kazanç junk kutudan gelmiyor.
    #   MEKANİZMA: kamera GÖVDEYE SABİT. Dikey komut throttle'ı sıçratıyor,
    #   araç dikeyde savruluyor ve 70 px'lik hedef bulanıklaşıyor. İlk
    #   oturumda ölçülmüştü: |throttle| 0.300 (tespit VAR) / 0.669 (YOK) —
    #   2.2 kat, ölçülen EN BÜYÜK ayırıcı. Tavan tam o büyüklüğü kısıyor.
    VZ_TAVAN_AKTIF = _b_i("DOW_VZ_TAVAN", True)

    # T5 · BBOX KÖPRÜSÜ (ölü-hesap) — Gazebo'da vardı, DoW'a taşınmamıştı.
    #   Çıkarım 10 Hz; aradaki ~100 ms'de ve tespit boşluklarında güdüm
    #   BAYAT kutuyla çalışıyor. Kutunun ATALET YÖNÜNÜ sabit tutup KENDİ
    #   dönüşümüzü telafi ederek kutuyu kadrajda ileri taşırız.
    #   ⭐ GİRDİ YALNIZ: son kutu + KENDİ IMU'muz. GPS YOK, menzil YOK.
    #   KOPRU_S = köprünün geçerli kaldığı azami süre (s). 0 = kapalı.
    # ⭐ GİRDİ 2026-08-22 gecesi — B2, n=4/kol, dönüşümlü A/B:
    #      ölçüt            KOPRU=0    KOPRU=0.5
    #      isabet             1/4        4/4
    #      en_yakin medyan   5.44 m     1.94 m   (-64%)
    #      tespit%           26.30      34.20
    #      doğru%            76.35      80.25
    #      yanlış%           23.65      19.75
    #      roll p90          48.65°     27.05°   (-44%)
    #   Geçerlilik eşleri (§5.2) tuttu: tespit% junk kutuyla yükselseydi
    #   doğru% düşer / yanlış% artardı; ikisi de TERS yönde gitti.
    #   Tek olumsuz sinyal kadraj% 97->90 idi; incelendi: kadraj dışı
    #   kareler YAKINDA değil UZAKTA (medyan 14-18 m, ıska sonrası yeniden
    #   yaklaşma) ve fark 390 karede 6 kare — gürültü.
    #   MEKANİZMA: köprü kutuyu tazeleyince nişan hatası küçülüyor, yanal
    #   talep düşüyor, çevirici daha az yatış üretiyor (roll p90 yarıya
    #   iniyor) ve gövdeye sabit kamera daha az sallanınca dedektör de
    #   iyileşiyor — tek değişiklik iki ölçütü birden düzeltiyor.
    KOPRU_S       = _fi("DOW_KOPRU_S", 1.0)   # B5 taramasi: 0.3/0.5/1.0 -> 1.0 kazandi

    # T4 · YERELLİK KAPISI — düşük eşik + "hedef nerede olmalı" kısıtı.
    #   Görsel fazda hedefin kadrajda NEREDE olduğunu bir önceki kutumuzdan
    #   (ve T5 köprüsünden) biliyoruz. O yüzden dedektör eşiğini düşürüp
    #   (0.40 -> YEREL_CONF_MIN) adayları YERELLİKLE eleyebiliriz:
    #     - merkez, beklenen yerin YEREL_KAPI_PX + 2*son_kutu içinde
    #     - genişlik, son genişliğin 0.5-2.0 katı
    #   Kazanç: 0.40 eşiğinin ALTINDA kalan soluk tespitler kurtarılır
    #   (ölçüldü: eşik 0.10'da tespit %49 / 0.40'ta %40 — 9 puan orada).
    #   Yanlış-pozitif riski: argmax'ı OSD çalıyordu; yerellik bunu keser.
    #   ⭐ TAMAMEN KAMERA İÇİ — GPS yok (§10).  0 = kapalı.
    # ⭐ GİRDİ 2026-08-23 gecesi — B3b+B3c havuzlanmış, n=5/kol, dönüşümlü:
    #      ölçüt          YEREL=0    YEREL=60
    #      isabet          4/5        5/5
    #      en_yakin       1.84 m     1.87 m   (berabere)
    #      tespit%        28.00      25.00    (aralıklar İÇ İÇE: 20-43 vs
    #                                          23-31 -> AYIRT EDİLEMİYOR)
    #      doğru%         74.50      79.70
    #      yanlış%        25.50      20.30
    #      kadraj%        96.40     100.00
    #      roll p90       31.60°      8.30°   (-74%; 5 koşunun 4'ü ≤9.3)
    #   İlan edilen birincil ölçüt (tespit%) FARK GÖSTERMEDİ; zaten kapı
    #   açıkken "tespit" tanımı değişiyor (dedektör buldu VE yerellikten
    #   geçti), yani kollar arası aynı şeyi ölçmüyor. Ölçüt sonradan
    #   değiştirilmedi (§5.6) — ayırt edemediği söylendi. Kalan HER ölçüt
    #   tek yönde. CLAUDE.md §4: salınan araç, aynı sonucu üretse bile kötüdür.
    #   ⚠ İlk uygulamam ELENMİŞTİ (B3: isabet 1/4, görsel faz 4.85 s):
    #     kapı bir kez kaybedince kilitleniyordu. YEREL_KURTAR ve "en yüksek
    #     güvenli" seçim kuralı bunu çözdü.
    YEREL_KAPI_PX = _fi("DOW_YEREL_KAPI", 60.0)
    YEREL_CONF_MIN = _fi("DOW_YEREL_CONF", 0.20)
    # ⛔ KİLİTLENME ÇARESİ (B3'te ölçüldü): referans bayatlayınca hiçbir aday
    #   kapıdan geçmiyor, kapı asla yeniden yakalayamıyor ve görsel faz
    #   ~5 s'de düşüyordu (tespit %33 -> %15-18, isabet 2/2 -> 0/4).
    #   Bu kadar ardışık başarısızlıktan sonra kapı AÇILIR ve düz argmax'a
    #   dönülür; ilk yeni tespit referansı tazeler.
    YEREL_KURTAR  = 5

    # --- geçerlilik ---
    CONF_MIN      = 0.40    # ÖLÇÜLDÜ (dow/gorus/dedektor.py)
    BOYUT_MIN_PX  = 8.0     # px; bundan küçük kutu güvenilmez
    MENZIL_MAX_M  = 50.0    # m; ötesinde görsel devir YOK (tespit %10)
    MENZIL_MIN_M  = 3.0     # m; ALTINDAKİ kutu = dev yanlış-pozitif.
                            # 997/3 = 332 px'lik kutu demek; hedef bu boyuta
                            # ancak TEMAS anında ulaşır. Dedektör 140 m'de
                            # bu boyutta kutular üretiyordu (ölçüldü).


def komut(cx, cy, w, h, own_yaw_deg, own_pitch_deg, own_roll_deg,
          hiz_I, dt, cfg=IbvsCfg):
    """IBVS kontrol yasası.

    GİRDİ (hedefin GPS'i YOK — yapısal garanti):
      cx, cy, w, h  : tespit kutusu (piksel) — TEK canlı hedef kaynağı
      own_*         : KENDİ yönelimimiz (derece) — kendi IMU'muz
      hiz_I         : hız integralinin o anki değeri (m/s); çağıran taşır
      dt            : adım süresi (s)

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

    # --- 4) YAW: burnu hedefe çevir (+ lead) ---
    eps_yaw = azimut
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

    tani["ibvs_hata_px"] = hata_px
    tani["ibvs_v"] = v

    # --- 6) YATAY: hız LOS (nişan) yönünde ---
    yon = math.radians(yaw_hedef)
    vx = v * math.cos(yon)
    vy = v * math.sin(yon)

    # --- 7) DİKEY: KADRAJ REGÜLASYONU (piksel -> dikey hız) ---
    # Yakınlaştıkça nişan merkeze kayar: uzakta altta kal, yakında vur.
    e_cy = cy - cy_ref                      # + = hedef kadrajda AŞAĞIDA
    vz_yukari = -cfg.K_CY * e_cy            # aşağıdaysa ALÇAL
    if cfg.VZ_TAVAN_AKTIF:                          # T6
        _v0 = vz_yukari
        vz_yukari = _kirp(vz_yukari, -cfg.VZ_TAVAN_GORSEL, cfg.VZ_TAVAN_GORSEL)
        tani["ibvs_vz_kirpildi"] = int(_v0 != vz_yukari)   # §5.1 mekanizma
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
