# -*- coding: utf-8 -*-
"""
================================================================================
DOW KAMERA MODELİ — ÖLÇÜLDÜ (2026-08-21, kendi uçuşumuz)
================================================================================
Kamera gövdeye SABİT (gimbal yok) ve burnun TILT derece YUKARISINA bakar.
Araç Angle Mode'da öne yatınca kamera da onunla aşağı döner — bu telafi
edilmezse hedef kadrajın altından kaçar. (2026-08-21'de tam bunu yaşadık:
pitch 0.28 komutu gövdeyi 17° yatırdı, kamera ekseni 25° -> 8°'ye indi,
hedef kadrajdan çıktı ve dedektör "bulamadı" sandık.)

KALİBRASYON YÖNTEMİ
  Truth geometriden (menzil, yükseliş, kerteriz) + kendi roll/pitch'imizden
  hedefin kadraj konumu öngörüldü; ölçülen bbox merkeziyle en küçük kareler.
  fx=fy kısıtlı (kare piksel FİZİKSEL zorunluluk) + aykırı değer atmalı.
  SONUÇ: artık 2.6 px, n=614 (kısıtsız serbest çözümde artık 170 px'ti).

ÖLÇÜLEN DEĞERLER
  TILT = 26.50°   f = 540.4 px   -> HFOV 121.2°, VFOV 90.0°  @1920x1080

BELİRSİZLİK (soruldu: "26.5 kesin değer mi?")
  Artık eğrisi KESKİN bir çukur yapıyor (n=635 iç küme):
     TILT 25.00 -> artık 5.10 px      (README'nin değeri)
     TILT 26.00 -> artık 3.10 px
     TILT 26.50 -> artık 2.56 px      <- EN İYİ
     TILT 27.00 -> artık 2.80 px
     TILT 28.00 -> artık 5.14 px
  BOOTSTRAP (60 yeniden örnekleme): 26.57° ± 0.11°, %5-95: 26.50-26.75
  => 25° KESİN OLARAK ELENİR: orada artık İKİ KATINA çıkıyor.

  Kalan pay SİSTEMATİK: f ile TILT fitte birbirine bağlı (eğride ikisi
  birlikte artıyor). Ölçüm paketinin bağımsız f=531.4 değeri dayatılırsa
  TILT ~26.2 çıkar. Gerçek değer 26.2-26.6 bandında; her hâlükârda 25 değil.
  SEÇİM: 26.50 (kendi kurulumumuzda, kendi ölçümümüzle).

  KIYAS: ölçüm paketi f=531.4/HFOV 122.07/VFOV 90.93/tilt 22.9
         README        HFOV 125 / tilt 25
  ⚠ Ölçüm paketi kendi kurulumunda "1536x864 mantıksal uzay, 1.25 Windows DPI
    ölçeği" notu düşmüş. Proton altında DPI zinciri FARKLI; bu yüzden onların
    f'i bize doğrudan taşınmaz. Kendi ölçümümüz esastır.

MENZİL SABİTİ (ayrı ölçüm, n=59 gerçek tespit)
  C = kutu_genisligi x menzil = 997 px·m  (%25-75: 855-1060)
  Geometrik beklenen f*S = 540.4*1.718 = 928 -> ölçülen/beklenen = 1.07
  (bbox kanat uçlarından biraz taşıyor; ampirik değer kullanılır)
  ⚠ Gazebo sabitimiz 1920'ye ölçeklenince 557 olurdu -> 1.79 KAT YANLIŞ.

İŞARET SÖZLEŞMESİ (ölçüldü)
  get_drone_rotation() -> (roll, pitch, yaw) DERECE.
  pitch NEGATİF = burun AŞAĞI (ileri uçuş). Ölçülen bant: -21°..0°.
================================================================================
"""
import math

IMG_W, IMG_H = 1920, 1080
CX, CY = IMG_W/2.0, IMG_H/2.0

TILT_DEG = 26.50        # ölçüldü; kamera ekseninin burna göre YUKARI açısı
F_PX     = 540.4        # ölçüldü; fx = fy (kare piksel)
MENZIL_C = 997.0        # px·m; R = MENZIL_C / kutu_genisligi
KANAT_M  = 1.718        # Talon kanat açıklığı (belge)

HFOV_DEG = 2*math.degrees(math.atan(CX/F_PX))
VFOV_DEG = 2*math.degrees(math.atan(CY/F_PX))


def menzil(kutu_genislik_px):
    """Kutu genişliğinden menzil (m). Delik-iğne benzer üçgenler: p = C/R."""
    if kutu_genislik_px <= 0:
        return None
    return MENZIL_C / float(kutu_genislik_px)


def piksel_aci(cx_px, cy_px):
    """Kadraj konumundan KAMERA EKSENİNE göre (yatay, dikey) açı (derece).
    dikey>0 = kamera ekseninin ÜSTÜNDE."""
    return (math.degrees(math.atan((cx_px - CX)/F_PX)),
            math.degrees(math.atan((CY - cy_px)/F_PX)))


def piksel_kerteriz(cx_px, cy_px, own_pitch_deg, own_roll_deg=0.0):
    """Kadraj konumundan GÖVDE-BAĞIMSIZ kerteriz (derece):
    (azimut, yükseliş). Kendi pitch/roll'umuz telafi edilir.

    ⚠ YARIŞMA KURALI (§10): girdi YALNIZ bbox pikselleri + KENDİ IMU'muz.
      Hedefin GPS'i kullanılmaz -> görsel fazda meşrudur (ego-motion telafisi).
    """
    yat, dik = piksel_aci(cx_px, cy_px)
    # kamera ekseni: burun + TILT yukarı; gövde pitch'i (negatif=burun aşağı)
    # kamera eksenini o kadar aşağı çevirir.
    yukselis = dik + TILT_DEG + own_pitch_deg
    # roll, yatay/dikey bileşenleri karıştırır (küçük açı için birinci derece)
    if own_roll_deg:
        r = math.radians(own_roll_deg)
        c, s = math.cos(r), math.sin(r)
        yat, yukselis = yat*c - yukselis*s, yat*s + yukselis*c
    return yat, yukselis


def kerteriz_piksel(azimut_deg, yukselis_deg, own_pitch_deg, own_roll_deg=0.0):
    """`piksel_kerteriz`in TAM TERSİ: gövde-bağımsız kerterizden kadraj
    konumu (cx, cy).

    ⭐ YARIŞMA KURALI AÇISINDAN TEMİZ: girdisi yalnız AÇI + KENDİ IMU'muz.
      Menzil, hedef konumu, GPS — hiçbiri yok. (`beklenen_kadraj` bundan
      farklıdır: o menzil ve truth geometri ister, güdümde KULLANILMAZ.)

    KULLANIM: bbox köprüsü. İki çıkarım arasında (10 Hz -> 100 ms) ve tespit
    boşluklarında, son kutunun ATALET YÖNÜNÜ sabit tutup KENDİ dönüşümüzü
    telafi ederek kutunun kadrajda nereye kaydığını hesaplarız. Araç
    yattıkça (ölçüldü: roll p90 52.7°) hedef kadrajda hızla kayıyor;
    köprü bu kaymayı kapatır.
    """
    # ⚠ SIRA ÖNEMLİ. İleri dönüşüm (piksel_kerteriz) şunu yapıyor:
    #      dik  = piksel açısı
    #      yuk  = dik + TILT + pitch          <- ÖNCE kaydır
    #      (yat, yuk) roll ile +r döndürülür  <- SONRA döndür
    #   Tersi bu yüzden ÖNCE −r döndürüp SONRA kaydırmayı geri almalı.
    #   (İlk yazımımda sıra terstim: yatışlıyken 30° girdide 3.9° hata
    #    veriyordu — yani köprünün EN ÇOK gerektiği anda bozuluyordu.
    #    Bekçi B26'nın gidiş-dönüş kimlik sınaması yakaladı.)
    yat, yuk = azimut_deg, yukselis_deg
    if own_roll_deg:
        r = math.radians(own_roll_deg); c, s_ = math.cos(r), math.sin(r)
        yat, yuk = yat*c + yuk*s_, -yat*s_ + yuk*c
    dik = yuk - TILT_DEG - own_pitch_deg
    return (CX + F_PX*math.tan(math.radians(yat)),
            CY - F_PX*math.tan(math.radians(dik)))


def beklenen_kadraj(menzil_m, yukselis_deg, azimut_deg, own_pitch_deg, own_roll_deg=0.0):
    """TERS yön (yalnız DOĞRULAMA/ölçüm için; güdümde KULLANILMAZ çünkü
    hedefin GPS'ini gerektirir). (cx, cy, beklenen_kutu_px)"""
    dik = yukselis_deg - TILT_DEG - own_pitch_deg
    yat = azimut_deg
    if own_roll_deg:
        r = math.radians(-own_roll_deg); c,s = math.cos(r), math.sin(r)
        yat, dik = yat*c - dik*s, yat*s + dik*c
    return (CX + F_PX*math.tan(math.radians(yat)),
            CY - F_PX*math.tan(math.radians(dik)),
            MENZIL_C/max(menzil_m, 1e-6))
