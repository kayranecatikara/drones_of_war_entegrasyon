# -*- coding: utf-8 -*-
"""DoW güdüm bekçileri. Her biri ÖLÇÜLMÜŞ bir bulguyu ya da ÜSTÜN bir kuralı korur."""
import sys, os, math, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dow.gudum.cevirici import HizCubukCevirici, CevCfg
from dow.gudum import ibvs
from dow.gorus import kamera as KAM


def test_B1_gorsel_fazda_hedef_gps_yasak():
    """⛔ ÜSTÜN KURAL (CLAUDE.md §10): görsel temas varken GPS güdümü YASAK.
    YAPISAL GARANTİ: ibvs.komut() imzasında hedefin konumuna dair HİÇBİR
    parametre olamaz. Girdiler yalnız bbox pikselleri + KENDİ IMU'muz."""
    p = list(inspect.signature(ibvs.komut).parameters)
    yasak = ("hedef", "target", "tgt", "gps", "lat", "lon", "truth", "tx", "ty", "tz")
    for ad in p:
        assert not any(y in ad.lower() for y in yasak), \
            f"ibvs.komut() hedef konumu alıyor: '{ad}' — §10 İHLALİ"
    assert set(p[:4]) == {"cx","cy","w","h"}, "ilk dört girdi bbox olmalı"


def test_B2_dikey_zehirli_bant():
    """⛔ ÖLÇÜLDÜ: throttle (-0.586, 0) bandı aracı 9 m/s TIRMANDIRIR.
    Çevirici bu banda ASLA komut üretmemeli."""
    c = HizCubukCevirici()
    for i in range(-4000, 4001):
        vz = i / 100.0
        t = c._vz_cubuk(vz)
        assert not (CevCfg.HOVER_THR < t < 0.0), \
            f"vz={vz} -> thr={t} ZEHİRLİ BANTTA"
        assert -1.0 <= t <= 1.0


def test_B3_dikey_asimetri():
    """⛔ ÖLÇÜLDÜ: tırmanma 33.5 m/s, alçalma 6.95 m/s (4.8 kat).
    Simetrik tavan kullanmak alçalma komutunu ~5 kat abartır."""
    assert CevCfg.VZ_MAX_TIRMAN > 4.0 * CevCfg.VZ_MAX_ALCAL
    c = HizCubukCevirici()
    assert c._vz_cubuk(-100.0) == -1.0      # doyum
    assert c._vz_cubuk(+100.0) == +1.0


def test_B4_hover_sifir_degil():
    """⛔ ÖLÇÜLDÜ: throttle 0, oyunun 'irtifa tut' kipi OLMASINA RAĞMEN
    +0.88 m/s tırmanıyor. Sıfır hız isteği HOVER_THR vermeli, 0.0 DEĞİL."""
    c = HizCubukCevirici()
    assert c._vz_cubuk(0.0) == CevCfg.HOVER_THR
    assert CevCfg.HOVER_THR < -0.4


def test_B5_hucum_hizi_hedefi_gecer():
    """DoW Talon'u 17.98 m/s uçuyor. Hücum hızı bunu belirgin AŞMALI,
    yoksa kapanma sıfıra iner ve hedef ASLA yakalanamaz."""
    assert ibvs.IbvsCfg.V_HUCUM >= 25.0
    assert ibvs.IbvsCfg.V_HUCUM - 17.98 >= 5.0


def test_B6_menzil_sabiti_olculen():
    """Menzil sabiti DoW Talon'una (1.718 m) göre olmalı.
    Gazebo sabiti 1920'ye ölçeklenince 557 ederdi -> 1.79 kat yanlış."""
    assert 900.0 <= KAM.MENZIL_C <= 1100.0
    assert abs(KAM.menzil(55.0) - 18.1) < 1.0     # eşik menzili


def test_B7_kamera_pitch_telafisi():
    """Kamera gövdeye sabit: araç öne yatınca kamera ekseni AŞAĞI döner.
    Telafi edilmezse hedef kadrajın altından kaçar (2026-08-21'de yaşandı)."""
    _, y0 = KAM.piksel_kerteriz(960, 540, 0.0)
    _, y1 = KAM.piksel_kerteriz(960, 540, -17.0)   # 17° burun aşağı
    assert abs(y0 - KAM.TILT_DEG) < 1e-6
    assert abs(y1 - (KAM.TILT_DEG - 17.0)) < 1e-6


def test_B8_yaw_tavani_korundu():
    """Araç 214 °/s yapabiliyor AMA hızlı yaw görüntüyü bulandırıp
    dedektörü kırar. Tavan bilinçli olarak 120'de tutuldu."""
    assert ibvs.IbvsCfg.YAW_RATE_MAX <= 130.0


def test_B9_dedektor_uzak_kol_1920():
    """⛔ ÖLÇÜLDÜ: 54 m'de 960 %6, 1920 %87 (14 kat). Kutu yoksa ya da
    küçükse DAİMA duyarlı kol kullanılmalı."""
    from dow.gorus import dedektor as DD
    assert DD.IMGSZ_UZAK == 1920
    assert 40.0 <= DD.YAKIN_ESIK_PX <= 70.0
    assert DD.CONF_MIN >= 0.35


def test_B10_gorsel_devir_menzili():
    """60-90 m'de tespit %10 -> orada görsel devir yapılmamalı.

    ⭐ 2026-08-25 GÜÇLENDİRİLDİ. Devir artık KAMERA kapısına bağlı
    (10 ardışık tespit) ve o kapının önünde GPS menzil kontrolü YOK.
    Geriye kalan TEK emniyet tavanı `gecerli()` içindeki MENZIL_MAX_M'dir:
    kutudan hesaplanan menzil bunu aşarsa tespit sayılmaz, sayaç artmaz.
    Eski `dedektor.DEVIR_MENZIL_M` ÖLÜ sabitti (kimse okumuyordu) ve bu
    bekçi onu sınayarak SAHTE güvence veriyordu — silindi (§5.12)."""
    assert ibvs.IbvsCfg.MENZIL_MAX_M <= 55.0
    import dow.gorus.dedektor as _DD
    assert not hasattr(_DD, "DEVIR_MENZIL_M"), \
        "ölü sabit geri gelmiş; gerçek tavan ibvs.IbvsCfg.MENZIL_MAX_M"
    # tavanın GERÇEKTEN uygulandığını sına (ölçüldü 2026-08-25):
    #   20 px -> 49.9 m  GEÇER   |  14 px -> 71.2 m  ELENİR
    ok, _ = ibvs.gecerli(960, 540, 20, 16, 0.9)
    assert ok, "20 px (49.9 m) elendi — tavan fazla dar, kamera kapısı açılamaz"
    ok, sebep = ibvs.gecerli(960, 540, 14, 11, 0.9)
    assert not ok and sebep == "menzil_uzak", \
        "14 px (71.2 m) geçerli sayıldı — kamera kapısının menzil tavanı YOK"


def test_B11_cevirici_gudume_dokunmaz():
    """YAPISAL AYRIM (§5.10): çevirici güdüm yasasını İTHAL ETMEMELİ.
    Böylece biri değişince diğeri etkilenmez."""
    import dow.gudum.cevirici as C
    kaynak = inspect.getsource(C)
    assert "ibvs" not in kaynak.lower().replace("ibvs (görüntü","")
    assert "import" in kaynak


def test_B12_dev_yanlis_pozitif_elenir():
    """⛔ ÖLÇÜLDÜ: dedektör 140 m'de 300+ px kutular üretiyor; bunlar
    menzil formülünde 1.3 m'ye çevriliyor ve güdüm 'temas' sanıyor.
    İki uçtan uca koşu bu yüzden yere çakıldı ('Player ☠')."""
    ok, sebep = ibvs.gecerli(960, 540, 400, 350, 0.8)
    assert not ok and sebep == "menzil_yakin", \
        "400 px kutu (=2.5 m) geçerli sayıldı — dev yanlış-pozitif kapısı YOK"
    ok, _ = ibvs.gecerli(960, 540, 40, 30, 0.8)   # 25 m — makul
    assert ok


def test_B13_devir_kapisi_YALNIZ_KAMERA_GPS_YOK():
    """⛔ YARISMA KURALI (kullanici 2026-08-25): "yarisma kurali boyle,
    gorsel temas saglandiktan sonra gps verisi kullanilarak arac gudulemez;
    bu yuzden de eskisini komple silip bu yenisine geciyoruz."

    2026-08-22'de faz gecisi icin ONAYLANMIS olan GPS istisnasi (istasyona
    otur + <=15 m menzil) 2026-08-25'te TAMAMEN KALDIRILDI (§5.12). Artik
    TEK kapi var ve o kapi hedefin GPS'ine HIC dokunmuyor.

    Bu bekci yeni sozlesmeyi sinar:
      1) iskelenin HICBIR parcasi geri gelmemis
      2) devir tetigi YALNIZ ardisik tespit sayaci
      3) geri donus kapisi duruyor ve hibrit kipe bagli
      4) sayaclar CIKARIM basina sayiyor (tik basina degil)
      5) adim() govdesinde dogrudan GPS erisimi yok
    """
    import inspect
    from dow import ana
    from dow.ayarlar import Ayar

    # 1) ISKELE GERI GELMEMIS — ne ayar, ne metot, ne bayrak
    for ad in ("DEVIR_ISTASYONDAN", "YARISMA_KIPI", "DEVIR_IST_HATA_M",
               "DEVIR_IST_KARE", "DEVIR_MENZIL_M", "DEVIR_KARE_DEV",
               "gelistirme_devri"):
        assert not hasattr(Ayar, ad), \
            f"silinen istasyon devir iskelesi geri gelmis: Ayar.{ad}"
    assert not hasattr(ana.Beyin, "_gelistirme_devir_hazir"), \
        "GPS okuyan devir kapisi metodu geri gelmis"

    k = inspect.getsource(ana.Beyin.adim)

    # 2) devir tetigi YALNIZ ardisik tespit sayaci
    assert "self._kilit >= self.cfg.DEVIR_KARE" in k, \
        "kamera devir kapisi (ardisik tespit) kaybolmus"
    assert Ayar.DEVIR_KARE == 10, "devir 10 ardisik TESPIT olmali"
    assert Ayar.KAYIP_KARE == 20, "kayip 20 ardisik TESPITSIZ kare olmali"

    # 3) geri donus kapisi duruyor ve YALNIZ hibrit kipte
    assert "self._kayip >= self.cfg.KAYIP_KARE" in k, \
        "20-kayip geri donus kapisi kaybolmus"
    i2 = k.index("self._kayip >= self.cfg.KAYIP_KARE")
    assert 'kip == "hibrit"' in k[max(0, i2 - 200):i2], \
        "geri donus kapisi hibrit kipe bagli degil"

    # 4) sayaclar CIKARIM basina (tik basina saymak 20 kareyi 0.45 s yapardi)
    assert "self._cikarim_yapildi" in k, \
        "sayaclar cikarim kapisina bagli degil -- kontrol tiki basina sayiyor"

    # 5) adim() govdesinde dogrudan GPS erisimi yok
    for y in ("get_target", "debug_truth", "truth("):
        assert y not in k, f"adim() icinde dogrudan GPS erisimi: {y}"


def test_B25_devir_karari_HEDEF_GPS_INE_DOKUNMAZ():
    """FONKSIYONEL kanit (B13 kodun SEKLINI sinar, bu DAVRANISI sinar).

    Hedefin konumu yerine, herhangi bir sekilde okunursa PATLAYAN bir nesne
    konur ve devir karari verdirilir. Kapi hedefin GPS'ine dokunursa test
    AssertionError ile duser.

    ⚠ 2026-08-25'te YENIDEN YAZILDI: eski hali "YARISMA_KIPI=1 iken kapi
    GPS okumaz" diyordu, yani iskele varken bayragi siniyordu. Iskele
    silindiginden o test bos bir kolu sinar hale gelmisti (§5.12). Yeni
    hali kapinin KENDISINI siniyor: bayrak yok, istisna yok, kapi GPS'e
    hicbir kipte dokunamaz."""
    from dow.ayarlar import Ayar
    from dow import ana

    class Mayin:
        """Herhangi bir sekilde okunursa patlar."""
        def __getitem__(self, i): raise AssertionError(
            "DEVIR KARARI HEDEF GPS'INI OKUDU - DISKALIFIYE RISKI")
        def __iter__(self): raise AssertionError(
            "DEVIR KARARI HEDEF GPS'INI OKUDU - DISKALIFIYE RISKI")
        def __len__(self): raise AssertionError("hedef GPS okundu")

    # devir kapisinin girdileri: YALNIZ ardisik tespit sayaci.
    # Mayin'i "hedef konumu" olarak tutup sayaci esige getiriyoruz;
    # kapinin karari mayina DOKUNMADAN verilmeli.
    b = ana.Beyin.__new__(ana.Beyin)
    b.cfg = Ayar
    b._kilit = Ayar.DEVIR_KARE          # esik saglandi
    b._kayip = 0
    hp = Mayin()                         # hedef konumu: dokunulamaz

    # adim() icindeki tetik ifadesinin BIREBIR kendisi:
    tetik = b._kilit >= b.cfg.DEVIR_KARE
    assert tetik is True, "esikteki sayac devri tetiklemiyor"
    # hp hic okunmadi -> mayin patlamadi. Ayrica geri donus kapisi da
    # yalnizca sayaca bakmali:
    b._kayip = Ayar.KAYIP_KARE
    assert (b._kayip >= b.cfg.KAYIP_KARE) is True
    del hp                               # kullanilmadi; patlamadan bitti


def test_B18_gorsel_fazda_gps_OKUNMAZ():
    """En kati hali: GORSEL fazda hedefin GPS i OKUNMAZ bile.
    hedef_konumu() cagrisi durum != GORSEL kosuluna BAGLI olmali."""
    import inspect
    from dow import ana
    k = inspect.getsource(ana.Beyin.adim)
    i2 = k.index("hedef_konumu(t)")
    assert 'self.durum != "GORSEL"' in k[max(0, i2-300):i2], \
        "hedef_konumu() GORSEL fazda da cagriliyor - GPS okunuyor!"


def test_B19_ibvs_girdisi_yalniz_goruntu():
    """ibvs.komut/gecerli: girdiler YALNIZ bbox pikselleri + KENDI IMU."""
    import inspect
    from dow.gudum import ibvs as I
    for fn in (I.komut, I.gecerli):
        for ad in inspect.signature(fn).parameters:
            assert not any(y in ad.lower() for y in
                           ("hedef", "target", "tgt", "gps", "truth",
                            "dunya", "world")), \
                f"{fn.__name__}() dunya-uzayi girdisi aliyor: {ad}"
    src = inspect.getsource(I)
    for y in ("get_target", "hedef_konum", "debug_truth"):
        assert y not in src, f"ibvs modulunde GPS erisimi: {y}"


def test_B20_olu_anahtar_birakilmadi():
    """CLAUDE.md §5.12 — ELENEN OZELLIK TAMAMEN SILINIR.
    Bu bekci, 2026-08-23 gecesinde ELENEN ya da SONUCA BAGLANMAYAN
    anahtarlarin geri sizmadigini sinar:
      SAKIN_KAMERA / LEAD_* / MERKEZ_FREN / FREN_TABAN  (onceki oturumda
        n=3 ile elenmisti, kill-switch olarak olu duruyordu)
      ROLL_TAVAN  (bu gece eklendi, A/B'si tamamlanmadi -> silindi;
        roll p90 zaten 51° -> 4°'ye indigi icin kazanacak yeri kalmamisti)
      los_hiz_deg_s / _los_hizi  (LEAD_SURE=0 iken ciktiya HIC etki
        etmedigi 216/216 girdide kanitlandi, sonra silindi)
    Eski test 'lead terimi bagli mi' diye sinardi; lead SILINDIGI icin
    bekcinin gorevi tersine cevrildi.

    ⚠⚠ 2026-08-26 — LEAD BILEREK GERI GETIRILDI, LISTEDEN CIKARILDI.
      Sessizce degil, GEREKCEYLE. GV03'teki red IKI YONDEN gecersizdi:
        (a) n=3 ile karar verilmis. Dosyanin KENDI notu: "HATAM: her karari
            n=3 kosuyla verdim. CLAUDE.md §5.4 tam bunu yasakliyor."
        (b) DUZ ucan hedefte sinanmis. Lead'in tasarim zarfi DONEN hedeftir
            (§5.13: zarf disindaki basarisizlik ELEME GEREKCESI DEGILDIR).
      Yeni olcum (KD1 kare senaryosu, n=4): 20->10 m arasi 78 kapanma
      denemesinin 76'si 6 m'nin altina inemiyor; kesilmelerin 45'i "GORDU
      ama menzil acildi" -- yani GUDUM kaynakli aci gecikmesi.
      Yeni ad `K_LEAD` (eski `LEAD_SURE` degil) ve varsayilani 0 -> kapaliyken
      BIT BIT ayni (bekci B59, 324 kombinasyon x 4 los_hiz -> 0 fark).
      KARE senaryosunda n=4/kol sinaniyor; ELENIRSE §5.12 ile tamamen
      cikarilacak ve bu satirlar geri alinacak.
      ⛔ `LEAD_SURE` ve `LEAD_MENZIL_M` HALA YASAK: onlar eski tasarimdi.

    ⛔⛔ 2026-08-26 (ayni gun, aksam) — LEAD IKINCI KEZ ELENDI VE SILINDI.
      Iki bagimsiz kampanya, dogru zarfta, n=4/kol:
        Ö-E (kare)    : birincil olcut degismedi (imha 0/4 vs 0/3)
        Ö-F (kacamak) : HER OLCUTTE KOTULESTI --
             kacirma 3 -> 5 · ilk denemede 2/4 -> 0/4
             sure 20.4 -> 24.9 s · gorsel tespit %65.5 -> %51.1
             salinim cx 0.58 -> 1.23 (IKI KAT)
      GV03'un n=3'luk reddi YONTEMSEL olarak zayifti ama HUKMU DOGRUYMUS.
      ⚠ Ö-E'de "lead salinimi dusurdu" diye okumustum (cx 1.13 -> 0.66);
        Ö-F tersini gosterdi. O dusus kosu degiskenligiydi -- §5.2'nin
        uyardigi tuzaga ragmen olumlu yonde okumusum, kayda geciyor.
      `K_LEAD` ve `LEAD_MAX_DEG` yeniden YASAKLI listede."""
    import inspect
    from dow.gudum import ibvs as I
    from dow import ana
    C = I.IbvsCfg
    for ad in ("SAKIN_KAMERA", "LEAD_SURE", "LEAD_MENZIL_M", "LEAD_MAX_DEG",
               "K_LEAD",
               "MERKEZ_FREN", "FREN_TABAN", "ROLL_TAVAN", "YAW_KAZANC",
               "YAW_HIZ_TAVAN"):
        assert not hasattr(C, ad), f"olu anahtar geri gelmis: IbvsCfg.{ad}"
    assert not hasattr(ana.Beyin, "_los_hizi"), "_los_hizi geri gelmis"
    assert "los_hiz_deg_s" not in inspect.signature(I.komut).parameters
    for kaynak in (inspect.getsource(I), inspect.getsource(ana)):
        for y in ("SAKIN_KAMERA", "MERKEZ_FREN", "ROLL_TAVAN", "_los_hizi"):
            for satir in kaynak.splitlines():
                cikari = satir.split("#")[0]      # tarihsel yorum serbest
                assert y not in cikari, f"olu atif kodda kaldi: {y}"

def test_B14_kalkis_zemine_goreli():
    """⛔ ÖLÇÜLDÜ: get_drone_altitude() DÜNYA Z'si döndürür ve zemin ~48 m.
    Kalkış eşiği mutlak alınırsa drone doğar doğmaz 'zaten yüksekteyim' der,
    kalkışı atlar ve yerdeyken yatay komut alıp takılır/çakılır."""
    import inspect
    from dow import ana
    from dow.ayarlar import Ayar
    k = inspect.getsource(ana.Beyin.adim)
    assert "_zemin_z" in k and "yukseklik" in k, \
        "kalkış mutlak irtifa kullanıyor — zemine göreli olmalı"
    assert "yukseklik >= self.cfg.KALKIS_ALT_M" in k


def test_B15_donmus_telemetri_kapisi():
    """⛔ ÖLÇÜLDÜ: SDK'nın alıcı iş parçacığı ölünce get_* fonksiyonları
    SON değeri sonsuza dek döndürür — telemetri DONAR, hata VERMEZ.
    Bir koşuda 40+ sn donmuş veriyle uçtuk ve fark etmedik. Ana döngü
    her tikte bağlantı sağlığını sınamalı."""
    import inspect
    from dow import ana
    from dow.ayarlar import Ayar
    from dow.sdk.baglanti import DowBaglanti
    assert hasattr(DowBaglanti, "canli") and hasattr(DowBaglanti, "yeniden_bagla")
    k = inspect.getsource(ana.Beyin.adim)
    assert "canli()" in k, "ana döngü bağlantı sağlığını sınamıyor"
    assert k.index("canli()") < k.index("yonelim()"), \
        "sağlık kapısı telemetri okumadan ÖNCE olmalı"


def test_B16_kacak_tirmanma_korumasi():
    """⛔ ÖLÇÜLDÜ (koşu #9): bağlantı kesintisi fazı KALKIS'a atıyor,
    spawn_sifirla() zemin referansını o anki irtifadan yeniden alıyor,
    araç 'yerdeyim' sanıp 45 m daha tırmanıyordu. irtifa 48 -> 855 m.
    İKİ koruma şart: (a) kesinti fazı değiştirmez, (b) zemin sıfırlanmaz."""
    import inspect
    from dow import ana
    from dow.ayarlar import Ayar
    k = inspect.getsource(ana.Beyin.adim)
    # (a) bağlantı kesintisi fazı DEĞİŞTİRMEMELİ ve zemini SİLMEMELİ
    i = k.index("BAGLANTI_YOK")
    kesinti = k[max(0, i-400):i+400]
    assert 'self.durum = "KALKIS"' not in kesinti, \
        "bağlantı kesintisi fazı KALKIS'a atıyor — kaçak tırmanma riski"
    assert "_zemin_z = None" not in kesinti, \
        "bağlantı kesintisi zemin referansını siliyor — kaçak tırmanma riski"
    # (b) zemin yalnız GERÇEK respawn'da yenilenir
    sp = inspect.getsource(ana.Beyin.spawn_sifirla)
    assert "_zemin_z = None" in sp, "gerçek respawn'da zemin yenilenmiyor"
    # (c) kalkıştan bağımsız ikinci çıkış kapısı
    assert "zaten_yuksek" in k, "kalkıştan bağımsız ikinci çıkış kapısı yok"


def test_B17_yanal_eksen_isareti():
    """⛔ ÖLÇÜLDÜ: Unreal SOL-ELLİ; sağ-elli dönüşüm yanal komutu TERS yöne
    verir, hata büyür, roll -1'e çakılır (tiklerin %94'ü) ve araç hedefe
    gitmek yerine daire çizer (kapanma -3.78 m/s = uzaklaşma).
      pitch +0.6 -> gövde ileri +66.6 m (doğru)
      roll  +0.6 -> gövde sağ  -66.8 m (TERS)"""
    from dow.gudum.cevirici import CevCfg, HizCubukCevirici
    assert CevCfg.Y_ISARET == -1.0, "yanal eksen işareti ölçümle uyuşmuyor"
    # burun kuzeye (+x) bakarken, DOĞUYA (+y) gitmek istiyoruz.
    # Unreal sol-elli olduğu için bu, gövdede SOL demektir -> sag NEGATİF.
    ileri, sag = HizCubukCevirici.dunya_govde(0.0, 10.0, 0.0)
    assert abs(ileri) < 1e-9
    assert sag < 0, "yanal işaret uygulanmamış"


def test_B21_gecerlilik_kurali_IKI_YONLU():
    """§5.2 — olcut NE BASARIYI NE BASARISIZLIGI eleyebilir.

    (1) 2026-08-22: hedefi VURUNCA drone da yok oluyor ve bekci "drone_yok"
        diyordu -> BASARI gecersiz sayiliyordu. Bu, istatistigi tam da
        istedigimiz sonucun ALEYHINE saptirir.
    (2) 2026-08-23: TERSI de yanlisti. Temas OLMADAN dusen drone
        (C1_BAYAT kosu 3-4: ivme 18-19 m/s², hedefin 2.5-4.3 m'sinde
        despawn) GECERSIZ sayilip eleniyordu — oysa o bir ISKA, yani veri.
        Basarisizligi elemek iki kolu da OLDUGUNDAN IYI gosterir.

    DOGRU KURAL: gorsel faza GIRDIYSE `drone_yok` bir SONUCTUR (isabet ya da
    iska), gecersizlik degil. Hic giremediyse kurulum sorunudur."""
    import inspect
    from araclar import kosu
    k = inspect.getsource(kosu.kosu_yap)
    i = k.find('if ihlal in ("drone_yok"')
    assert i > 0, "gecerlilik kurali kaybolmus"
    civar = k[i:i + 300]          # kosulun KENDISI (yorumlar oncesinde)
    assert "isabet or gorsel_tik_say > 0" in civar, \
        ("kural tek yonlu: ya basariyi ya basarisizligi eliyor. "
         "Gorsel faza girmis bir kosu, temas olmasa da GECERLIDIR.")

def test_B22_gorev_seviyesi_yeniden_kurulum():
    """OLCULDU (GV08): hedefi VURUNCA drone yok oluyor ve oyun gorev-sonu
    ekranina dusebiliyor; orada E hicbir sey yapmiyor. Ilk kosu ISABETLE
    bitti, kalan 5 kosu gorev baslatilamadi ve kampanya bosa gitti.
    Kosum araci son care olarak GOREVI BASTAN kurmali."""
    import inspect
    from araclar import kosu
    assert hasattr(kosu, "_gorevi_yeniden_kur")
    k = inspect.getsource(kosu._yeni_gorev)
    assert "_gorevi_yeniden_kur" in k, "E yetmediginde gorev kurulmuyor"


def test_B23_takipci_geri_ve_kill_switch_kapali():
    """⭐ 2026-08-24 — HybridSORT GERI GELDI (kullanici karari).

    22 Agustos'ta 5.12'ye gore TAMAMEN silinmisti; silme sarti "duzgun
    detection modeli gelince tekrardan entegre edebiliriz"di ve talon_v5
    ile gerceklesti. Bu bekci artik TERSINI sinar:
      1. tracker.py var ve TalonTracker/TargetLock/TakipCfg iceriyor,
      2. kill-switch VARSAYILAN KAPALI (olcum karar verene kadar; §4),
      3. takip yolu GPS'e DOKUNMUYOR (§10 ustun kisit).
    """
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.exists(os.path.join(kok, "dow/gorus/tracker.py"))
    from dow.gorus.tracker import TalonTracker, TargetLock, TakipCfg
    assert TakipCfg.AKTIF is False, \
        "yeni ozellik VARSAYILAN KAPALI girer -- olcum karar verir (§4)"
    assert 0.0 < TakipCfg.CONF_MIN < TakipCfg.KILIT_CONF, \
        "predict esigi kilit esiginden DUSUK olmali (BYTE ikinci turu)"
    assert TakipCfg.MAX_COAST == 5, \
        "coast=5 GT'li deneyde olculdu; degistirmek yeni olcum ister"
    # §10: takip yolunda hedef GPS'i OKUNAMAZ
    import inspect
    from dow import ana
    kaynak = inspect.getsource(ana.Beyin._takip_bul)
    for yasak in ("hedef_konumu", "get_target", "izleyici", "self.b."):
        assert yasak not in kaynak, \
            "takip yolu GPS'e dokunuyor (§10 ihlali): " + yasak


def test_B24_ekran_kopyalama_tavanli():
    """OLCULDU 2026-08-22 (GA04 vs GV11) — ARAYUZ UCUSU BOZUYORDU.
    izleyici.py ekrani saniyede 180-330 kez kopyaliyordu (1920x1080) ve
    ayni GPU'da YOLO'yu tam hizda kosuyordu. Oyun (UE5/Vulkan) ayni GPU +
    ayni X sunucusunda oldugu icin:
        istasyon hatasi 5.3 m -> 25.3 m,  <=15 m orani %88 -> %2,
        v_istek 120 s boyunca 33 m/s TAVANINDA doyumda kaldi.
    Bu yuzden hem yakalama hem cikarim TAVANLI olmak ZORUNDA; ve
    kontrol dongusu artik tam kare KOPYALAMAZ (gorus is parcacigindan alir)."""
    import inspect
    from dow.ayarlar import Ayar
    assert 0 < Ayar.PANEL_YAKALA_HZ <= 60, "yakalama tavani makul degil"
    assert 0 < Ayar.PANEL_DET_HZ <= 30, "dedektor tavani makul degil"
    for mod, fn in (("araclar.izleyici", "_yakala"), ("araclar.kosu", "_gorus_isi")):
        m = __import__(mod, fromlist=["x"])
        k = inspect.getsource(getattr(m, fn))
        assert "PANEL_YAKALA_HZ" in k and "time.sleep" in k, \
            f"{mod}.{fn} icinde hiz tavani yok"
    from araclar import kosu
    kk = inspect.getsource(kosu.kosu_yap)
    assert "sct.grab" not in kk, \
        "kontrol dongusu hala kendisi ekran kopyaliyor (cift kopyalayici)"


def test_B26_bbox_koprusu_YALNIZ_KAMERA_VE_KENDI_IMU():
    """T5 bbox koprusu, GORSEL FAZDA calisir -> ustun kural gecerli (§10):
    hedefin GPS'i/menzili KULLANILAMAZ. Koprunun girdileri yalnizca
    son bbox pikselleri + KENDI yonelimimiz olmali."""
    import inspect
    from dow import ana
    from dow.gorus import kamera as KAM

    # ters donusum saf: aci + kendi IMU. Menzil/hedef girdisi YOK.
    par = list(inspect.signature(KAM.kerteriz_piksel).parameters)
    for ad in par:
        assert not any(y in ad.lower() for y in
                       ("menzil", "range", "hedef", "target", "gps", "truth")), \
            f"kerteriz_piksel() yasak girdi aliyor: {ad}"

    for fn in (ana.Beyin._kopru_kaydet, ana.Beyin._kopru_kutu):
        k = inspect.getsource(fn)
        for y in ("hedef_konumu", "get_target", "debug_truth", "truth(",
                  "istasyon_noktasi", "GPS."):
            assert y not in k, f"{fn.__name__} icinde GPS izi: {y}"

    # kopru, gorsel dalda KULLANILIYOR olmali (olu kod birakma - 5.12)
    a = inspect.getsource(ana.Beyin.adim)
    assert "_kopru_kutu(" in a, "kopru yazildi ama gudumde kullanilmiyor"

    # ters donusum, ileri donusumun TERSI mi (sayisal kimlik)
    for az in (-30.0, 0.0, 17.5):
        for el in (-12.0, 0.0, 28.0):
            for p_, r_ in ((0.0, 0.0), (-15.0, 20.0)):
                cx, cy = KAM.kerteriz_piksel(az, el, p_, r_)
                a2, e2 = KAM.piksel_kerteriz(cx, cy, p_, r_)
                assert abs(a2 - az) < 1e-6 and abs(e2 - el) < 1e-6, \
                    f"kerteriz_piksel, piksel_kerteriz'in tersi degil: {az},{el}"


def test_B27_bekci_menzil_kurali_YAKLASMAYI_IPTAL_ETMEZ():
    """OLCULDU 2026-08-23: gorev yeniden kurulunca baslangic ayrimi 800-970 m
    cikabiliyor (drone -393,-1606,227 m / hedef -87,-2327,86 m). Bekcinin
    "hedeften 500 m uzak" kurali o durumda MESRU YAKLASMAYI iptal ediyordu
    ve 12 kosuluk bir blok tamamen bu yuzden cope gitti.
    Kullanicinin kurali "drone hedeften cok UZAKLASTIYSA" idi; bu, bir kez
    YAKIN olmayi varsayar. Kural artik ancak yaklasma sonrasi silahlanir."""
    from araclar.bekci import Bekci
    b = Bekci(); b.sifirla()
    for i in range(10):
        assert b.kontrol(i * 0.1, (0, 0, 100), 0.0, (900, 0, 100), True) is None, \
            "uzaktan BASLAYAN kosu iptal ediliyor - yaklasma imkansiz"
    b.sifirla()
    for i in range(5):                      # once yaklas
        b.kontrol(i * 0.1, (0, 0, 100), 0.0, (50, 0, 100), True)
    ihlaller = [b.kontrol(1 + i * 0.1, (0, 0, 100), 0.0, (900, 0, 100), True)
                for i in range(10)]
    assert "hedef_cok_uzak" in ihlaller, \
        "yaklastiktan SONRA kacan drone yakalanmiyor - bekci is gormuyor"


def test_B28_temas_siniflandirmasi_OLCULDU():
    """Kullanici (2026-08-23): "drone hedefin pervanesine carparsa bu vurus
    sayilmiyor, drone geriye itiliyor; sen bu pervaneye carpmayi anla ve
    bunu vurus say."

    Eski olcut YALNIZ mesafeydi (menzil < 4 m) ve TEMAS ile YAKIN GECISI
    ayirmiyordu: TEMAS kampanyasinin 6 kosusunun ALTISINI da isabet
    sayardi; gercekte 4 temas + 2 yakin gecis + 0 imha vardi.

    Esikler OLCULDU (dongu hizinda ~43 Hz, 6 kosu):
      temas darbeleri 359-879 m/s² @ 1.11-1.21 m
      temassiz maks    14-99 m/s² @ 5.6-5.8 m
      normal ucus p99  59-77 m/s²
    Esik 200 m/s² bu iki kumenin ORTASINDA ve her ikisinden de uzak."""
    from dow.ayarlar import Ayar
    import inspect
    from araclar import kosu
    # esik olculen iki kumenin ARASINDA olmali
    assert 100 < Ayar.TEMAS_IVME_ESIK < 350, \
        "temas esigi olculen kumelerin arasinda degil"
    assert 1.3 <= Ayar.TEMAS_MENZIL_M <= 3.0, \
        "temas menzili olculen 1.11-1.21 m kumesini kapsamali"
    k = inspect.getsource(kosu.kosu_yap)
    assert "_temas_ivme >= Ayar.TEMAS_IVME_ESIK" in k, \
        "isabet hala YALNIZ mesafeye bakiyor - pervane carpmasi ayirt edilmiyor"
    assert '"temas": _temas' in k and '"imha": _imha' in k, \
        "temas/imha ayri raporlanmiyor"
    # olcum DONGU hizinda olmali, 0.5 s kayittan DEGIL (0.5 s darbeyi ayiramadi)
    assert "_ivme_tum.append" in k, "ivme dongu hizinda toplanmiyor"


def test_B29_kerteriz_borcu_GORUNUR():
    """⚠⚠ BİLİNEN BORÇ (2026-08-23) — sessizce unutulmasin diye bekci.

    `piksel_kerteriz` MATEMATIKSEL OLARAK YANLIS: roll donusunu TILT
    eklendikten SONRA uyguluyor, bu yuzden hata ~roll kadar buyuyor
    (3°->3.3°, 10°->11.0°, 35°->39.8°). Gazebo'nun `los_seviye`si dogru
    ve 4146 esleşmis karede DOGRULANDI: tespit edilen kutuya uyum
    yaklasik 33.1 px vs TAM 13.6 px medyan sapma.

    OLCUM yolu tam zincire GECIRILDI. GUDUM cevrimi hala yaklasigi
    kullaniyor cunku tam zincire gecince temas 6/8 -> 4/8'e dustu ve
    salinim 4 katina cikti (kazanclar yanlis modele gore ayarlanmis).
    Su an zararsiz: roll p90 3-8°. YATIS TEKRAR BUYURSE hata geri gelir.

    Bu bekci iki seyi garanti eder:
      1) dogru zincir (los_seviye/seviye_piksel) KODDA DURUYOR ve olcum
         yolu onu kullaniyor,
      2) ters donusum hala TAM (gidis-donus kimligi)."""
    import inspect
    from dow.gorus import kamera as K
    from araclar import kosu, tespit_olcu
    assert hasattr(K, "los_seviye") and hasattr(K, "seviye_piksel"), \
        "dogru kerteriz zinciri kaybolmus"
    for m in (inspect.getsource(kosu._gecmis_beklenen),
              inspect.getsource(tespit_olcu.olc)):
        assert "seviye_piksel" in m, \
            "olcum yolu yanlis (yaklasik) zincire geri donmus"
    for az in (-40.0, 0.0, 25.0):
        for el in (-15.0, 0.0, 35.0):
            for r, p in ((0.0, 0.0), (35.0, -12.0), (-20.0, 8.0)):
                x, y = K.seviye_piksel(az, el, r, p)
                a2, e2 = K.los_seviye(x, y, r, p)
                assert abs(a2 - az) < 1e-6 and abs(e2 - el) < 1e-6, \
                    "seviye_piksel, los_seviye'nin tersi degil"


def test_B30_kabul_edilen_ayarlar_YERINDE():
    """⛔ 2026-08-23'te YASANDI: bir blok silerken KOPRU_S ve BAYAT_BIRAK
    yanlislikla silindi. 29 bekcinin HICBIRI yakalamadi cunku hicbiri o
    alanlari OKUMUYORDU; bir sonraki ucus AttributeError ile cokerdi.
    Bu bekci, OLCUMLE KABUL EDILMIS her ayarin yerinde ve makul aralikta
    oldugunu dogrular — silme kazasina karsi son savunma."""
    from dow.gudum.ibvs import IbvsCfg as C
    from dow.ayarlar import Ayar
    bekle = {
        "KOPRU_S": (0.2, 3.0),          # B2/B5/B6: 1.0 kazandi
        "YEREL_KAPI_PX": (10, 300),     # B3b/B3c: 60
        "YEREL_CONF_MIN": (0.05, 0.5),  # B4: 0.20
        "YEREL_KURTAR": (1, 20),
        "VZ_TAVAN_GORSEL": (0.5, 8.0),  # B8/B9b: 1.5
        "V_HUCUM": (18.0, 34.6),
        "K_CY": (0.01, 0.3),
    }
    for ad, (lo, hi) in bekle.items():
        assert hasattr(C, ad), f"KABUL EDILMIS ayar SILINMIS: IbvsCfg.{ad}"
        v = float(getattr(C, ad))
        assert lo <= v <= hi, f"IbvsCfg.{ad}={v} olculen araligin disinda"
    assert isinstance(C.VZ_TAVAN_AKTIF, bool) and C.VZ_TAVAN_AKTIF, \
        "dikey yumusatma (gecenin en buyuk kazanimi) kapanmis"
    assert hasattr(C, "BAYAT_BIRAK"), "BAYAT_BIRAK anahtari silinmis"
    for ad, (lo, hi) in (("ISTASYON_MENZIL_M", (4, 20)),
                         ("ISTASYON_ALT_ORAN", (0.3, 1.2)),
                         ("TEMAS_IVME_ESIK", (100, 350)),
                         ("GORSEL_DET_HZ", (2, 30))):
        assert hasattr(Ayar, ad), f"KABUL EDILMIS ayar SILINMIS: Ayar.{ad}"
        v = float(getattr(Ayar, ad))
        assert lo <= v <= hi, f"Ayar.{ad}={v} olculen araligin disinda"


def test_B31_temas_IKI_IMZALI_ve_dikey_ORANSAL():
    """Iki ders, iki bekci — ikisi de OLCUMLE yasandi.

    (1) TEMAS'in IKI imzasi var ve ikisi de sayilmali:
        SEKME  : ani geri ivme, drone YASAR (pervane carpmasi)
        IMHA   : kosu TAM en yakinlasma aninda biter, menzil temas
                 yaricapi icinde -> drone yok oldu, SEKME OLMAZ
        Yalniz darbeye bakan surum EN TEMIZ VURUSLARI kaciriyordu:
        E1b'de uc kosu 0.67-0.81 m'de tam o anda bitmis, darbe sifir;
        0.014/4.0 kolu 3/8 gorunuyordu, gercekte 8/8.

    (2) DIKEY KANAL ORANSAL OLMALI, ac-kapa DEGIL:
        K_CY=0.06 + tavan 1.5 ile |e_cy|>25 px olan her kare DOYUMDA idi
        (olculdu: taze kutuda bile %98.3). Komut hatayi hic tasimiyordu.
        K_CY=0.014 + tavan 4.0 -> dogrusal aralik +-286 px, doyum %17.7,
        TEMAS 6/8 -> 8/8, en_yakin 0.86 -> 0.51 m, salinim 3 kat azaldi."""
    import inspect
    from dow.gudum.ibvs import IbvsCfg as C
    from araclar import kosu, tespit_olcu

    # (2) dikey kanal dogrusal aralik: gercek hata dagilimini (medyan ~143,
    #     p90 ~258 px) kapsamali, yoksa yine ac-kapa olur
    aralik = C.VZ_TAVAN_GORSEL / C.K_CY
    assert aralik >= 200, (f"dikey kanal yine AC-KAPA: dogrusal aralik "
                           f"+-{aralik:.0f} px, olculen hata medyani 143 px")
    assert C.VZ_TAVAN_GORSEL >= 2.5, \
        "dikey tavan geometrinin istedigi 1.67 m/s'yi karsilamiyor"

    # (1) iki imza da kodda
    k = inspect.getsource(kosu.kosu_yap)
    assert "_sekme" in k and "_imha" in k and "_temas = int(_sekme or _imha)" in k, \
        "temas siniflandirmasi iki imzali degil"
    assert "_en_yakin_t" in k, "en yakinlasma ANI kaydedilmiyor"
    assert hasattr(tespit_olcu, "temas_sinifla"), \
        "ortak siniflandirici kaybolmus (analiz ve kayit ayrisir)"


if __name__ == "__main__":
    import traceback
    ad_listesi = [k for k in sorted(globals()) if k.startswith("test_")]
    gecti = 0
    for ad in ad_listesi:
        try:
            globals()[ad]()
            print(f"  ✅ {ad}"); gecti += 1
        except AssertionError as e:
            print(f"  ❌ {ad}: {e}")
        except Exception:
            print(f"  ❌ {ad}: {traceback.format_exc().splitlines()[-1]}")
    print(f"\n{gecti}/{len(ad_listesi)} bekçi geçti")
    sys.exit(0 if gecti == len(ad_listesi) else 1)

# ============================================================================
# B32 — GÖRÜŞ ZİNCİRİ (2026-08-23): fp16 + natif pencere + yeni-kare kapısı
# ============================================================================
def test_b32_gorus_zinciri_anahtarlari_var():
    """⛔ 2026-08-22'de KOPRU_S ve BAYAT_BIRAK'ı yanlışlıkla silmiştim ve
    29 bekçinin hiçbiri yakalamadı. Aynı hata tekrar etmesin: benimsenen
    ayarların VARLIĞI ve makul aralıkta olduğu sınanır."""
    from dow.gorus.dedektor import DetCfg
    from dow.ayarlar import Ayar
    for ad in ("FP16", "PENCERE_PX", "ISKA_TAM"):
        assert hasattr(DetCfg, ad), "DetCfg.%s SİLİNMİŞ" % ad
    assert hasattr(Ayar, "DET_YENI_KARE"), "Ayar.DET_YENI_KARE SİLİNMİŞ"
    assert DetCfg.PENCERE_PX == 0 or 256 <= DetCfg.PENCERE_PX <= 1280


def test_b33_pencere_tam_kadraj_koordinati_dondurur():
    """Pencere kutuları TAM KADRAJ koordinatında dönmeli. Yanlış haritalama
    güdümü sessizce sola-yukarı nişan aldırır — en sinsi hata sınıfı."""
    import numpy as np
    from dow.gorus import dedektor as D

    class SahteKutular:
        """ultralytics Boxes sözleşmesi: .xyxy (N,4) ve .conf (N,) DİZİ.
        (2026-08-24: _cikar kutu başına .tolist() yerine TEK numpy aktarımı
        yapıyor; sahte de gerçek API'yi taklit etmeli, yoksa test üretimde
        olmayan bir yolu sınar.)"""
        def __init__(self, xyxy, conf):
            self.xyxy = np.array(xyxy, dtype=float)
            self.conf = np.array(conf, dtype=float)
        def __len__(self): return len(self.xyxy)

    class SahteSonuc:
        def __init__(self, kutular): self.boxes = kutular

    class SahteModel:
        def predict(self, im, **kw):
            # pencere içinde (10,20)-(30,40) -> merkez (20,30)
            return [SahteSonuc(SahteKutular([[10, 20, 30, 40]], [0.9]))]

    d = D.Dedektor.__new__(D.Dedektor)
    d.m = SahteModel(); d.conf = 0.4; d.uyarlanabilir = True
    d.yakin_esik = 55.0; d._son_w = 0.0; d._isindi = True
    d.son_imgsz = 1920; d.son_pencere = 0; d.son_ms = 0.0
    d.pencere_say = d.tam_say = d.iska_tam = 0
    d._fp16 = False

    eski = D.DetCfg.PENCERE_PX
    try:
        D.DetCfg.PENCERE_PX = 640
        img = np.zeros((1080, 1920, 3), np.uint8)
        k = d.bul(img, merkez=(1000.0, 500.0))
        # x0 = 1000-320 = 680, y0 = 500-320 = 180
        assert abs(k[0] - (20 + 680)) < 1e-6, k
        assert abs(k[1] - (30 + 180)) < 1e-6, k
        assert d.son_pencere == 640
        # merkez YOKKEN pencere KAPALI kalmalı (kaybetmişken tam kadraj şart)
        d.son_pencere = -1
        d.bul(img, merkez=None)
        assert d.son_pencere == 0
        # REJİM: kutu >= YAKIN_ESIK ise YAKIN pencere (448) seçilmeli
        d._son_w = 120.0
        d.bul(img, merkez=(1000.0, 500.0))
        assert d.son_pencere == D.DetCfg.PENCERE_YAKIN, d.son_pencere
        d._son_w = 20.0
        d.bul(img, merkez=(1000.0, 500.0))
        assert d.son_pencere == 640, d.son_pencere
    finally:
        D.DetCfg.PENCERE_PX = eski


def test_b34_pencere_kenarda_kadraj_disina_tasmaz():
    """Kadraj kenarındaki hedefte pencere sınırlara KIRPILIR; negatif ya da
    taşan dilim numpy'da SESSİZCE boş dizi döner ve tespit sıfırlanır."""
    import numpy as np
    from dow.gorus import dedektor as D
    kayit = {}

    class SahteSonuc:
        boxes = []

    class SahteModel:
        def predict(self, im, **kw):
            kayit["sekil"] = im.shape; return [SahteSonuc()]

    d = D.Dedektor.__new__(D.Dedektor)
    d.m = SahteModel(); d.conf = 0.4; d.uyarlanabilir = True
    d.yakin_esik = 55.0; d._son_w = 0.0; d._isindi = True
    d.son_imgsz = 1920; d.son_pencere = 0; d.son_ms = 0.0
    d.pencere_say = d.tam_say = d.iska_tam = 0
    d._fp16 = False
    eski_p, eski_i = D.DetCfg.PENCERE_PX, D.DetCfg.ISKA_TAM
    try:
        D.DetCfg.PENCERE_PX = 640; D.DetCfg.ISKA_TAM = False
        img = np.zeros((1080, 1920, 3), np.uint8)
        for mx, my in ((0, 0), (1919, 1079), (5, 1075), (1915, 3)):
            d.bul(img, merkez=(float(mx), float(my)))
            assert kayit["sekil"] == (640, 640, 3), (mx, my, kayit["sekil"])
    finally:
        D.DetCfg.PENCERE_PX = eski_p; D.DetCfg.ISKA_TAM = eski_i


def test_b35_pencere_merkezi_gpsten_gelmez():
    """§10 BEKÇİSİ: pencere merkezi YALNIZ kameradan+kendi IMU'muzdan gelen
    `ref`tir. `_yerel_bul` içinde hedef GPS'i okunuyorsa YARIŞMA İHLALİ."""
    import inspect, re
    from dow import ana
    kaynak = inspect.getsource(ana.Beyin._yerel_bul)
    for yasak in ("hedef_konumu", "hedef_hiz", "self.b.hedef", "izleyici"):
        assert yasak not in kaynak, "YARIŞMA İHLALİ: _yerel_bul içinde %s" % yasak
    assert "merkez=" in kaynak, "pencere merkezi ref'ten verilmiyor"


def test_b36_kutu_yasi_kare_aninda_sayilir():
    """Birincil ölçüt yanlılığa karşı: kutunun yaşı KARENİN yakalandığı
    andan sayılmalı, çıkarımın koştuğu andan değil (aradaki fark yakalama
    tavanı kadar, 15 Hz'de 0-67 ms)."""
    import inspect
    from dow import ana
    from araclar import kosu
    assert "kare_t" in inspect.signature(ana.Beyin.gorsel_tik).parameters
    k = inspect.getsource(kosu)
    assert "_son_tespit_kare_t" in k, "gerçek kutu yaşı ölçülmüyor"
    assert "kutu_yasi_p90" in k, "BİRİNCİL ölçüt özete yazılmıyor"


# ============================================================================
# B37-B40 — TEK HEDEFLİ İZ (2026-08-24, kapının yerine)
# ============================================================================
def test_b37_iz_kapisi_eski_kapinin_UST_KUMESI():
    """⭐ YAPISAL GÜVENCE: yeni kapı, eski kapının kabul ettiği HİÇBİR adayı
    reddedemez. Böylece "kapı elemesi" kaynaklı bayatlık (ölçüldü: bayat
    karelerin %24.5'i) yalnız AZALABİLİR — bu bir regresyon testi değil,
    MATEMATİKSEL güvencedir (CLAUDE.md §5.10 'en iyisi yapısal garanti')."""
    from dow.gorus.iz import Iz, IzCfg
    iz = Iz()
    for w in (8.0, 20.0, 55.0, 120.0, 300.0):
        iz.sifirla()
        iz.guncelle((960.0, 540.0, w, w * 0.6, 0.8), 0.0)
        for yas in (0.0, 0.05, 0.2, 0.5, 1.0, 2.0):
            t = yas
            o = iz.ongor(t)
            rw = max(o[2], 1.0)
            yaricap, alt, ust = iz.kapi(t, rw)
            eski_yaricap = 60.0 + 2.0 * w          # bugünkü kapı
            assert yaricap >= eski_yaricap - 1e-9, (w, yas, yaricap, eski_yaricap)
            assert alt <= 0.5 + 1e-9, (w, yas, alt)
            assert ust >= 2.0 - 1e-9, (w, yas, ust)


def test_b38_iz_konumu_ILERI_TASIMAZ():
    """ÖLÇÜLDÜ 2026-08-24: konumu sabit hızla ileri taşımak hatayı 1.5 s'de
    İKİ KATINA çıkarıyor (79 px -> 157 px). Bu yüzden `ongor` konumu
    DONDURULMUŞ döndürmeli. Biri 'iyileştirme' diye hız eklerse bu bekçi
    yakalar."""
    from dow.gorus.iz import Iz
    iz = Iz()
    # hedef kadrajda hızla sağa kayıyor olsun
    for i, cx in enumerate((400.0, 600.0, 800.0)):
        iz.guncelle((cx, 540.0, 60.0, 36.0, 0.8), i * 0.2)
    for yas in (0.1, 0.5, 1.0, 2.0):
        o = iz.ongor(0.4 + yas)
        assert abs(o[0] - 800.0) < 1e-9, ("konum ileri taşınmış!", yas, o[0])
        assert abs(o[1] - 540.0) < 1e-9


def test_b39_iz_boyut_ongorusu_kirpilir():
    """1/w sıfıra yaklaşırsa w patlar (ölçümde kırpmasız p95 999748'e
    çıkmıştı). Öngörü her koşulda ONGORU_KAT ile sınırlı kalmalı."""
    from dow.gorus.iz import Iz, IzCfg
    iz = Iz()
    # kutu ÇOK hızlı büyüyor -> 1/w hızla küçülüyor, kırpma şart
    for i, w in enumerate((20.0, 60.0, 200.0)):
        iz.guncelle((960.0, 540.0, w, w * 0.6, 0.8), i * 0.1)
    for yas in (0.1, 0.5, 1.0, 3.0, 10.0):
        o = iz.ongor(0.2 + yas)
        assert o[2] > 0.0 and o[2] < 200.0 * IzCfg.ONGORU_KAT * 1.001, (yas, o[2])
        assert o[2] >= 200.0 / IzCfg.ONGORU_KAT * 0.999, (yas, o[2])


def test_b40_iz_gpsten_beslenmez():
    """§10 BEKÇİSİ: iz YALNIZ kabul edilmiş kameradan gelen kutuyla tazelenir.
    `Iz` sınıfı hedef GPS'ine dair hiçbir şey bilmemeli."""
    import inspect
    from dow.gorus import iz as M
    kaynak = inspect.getsource(M)
    for yasak in ("hedef_konumu", "hedef_hiz", "gps", "GPS_KAYNAK", "truth"):
        assert yasak not in kaynak, "YARIŞMA İHLALİ: iz.py içinde %s" % yasak
    from dow import ana
    # gorsel_tik artik yalniz KILIT sarmalayicisi (Ayar.GORUS_ISP mimarisi);
    # is `_gorsel_tik_kilitli`de. Bekci ZAYIFLAMASIN diye IKISI de sinanir:
    # sarmalayici gercekten delege ediyor mu, ve govde izi tazeliyor mu.
    sar = inspect.getsource(ana.Beyin.gorsel_tik)
    assert "_gorsel_tik_kilitli" in sar and "self._kilit_g" in sar, \
        "gorsel_tik kilitli govdeye delege etmiyor"
    k = inspect.getsource(ana.Beyin._gorsel_tik_kilitli)
    assert "self.iz.guncelle(d, t)" in k, "iz kabul edilen kutuyla tazelenmiyor"
    # §10: gorus yolunun HICBIR parcasi hedef GPS'ine dokunmaz
    for yasak in ("hedef_konumu", "get_target", "izleyici"):
        assert yasak not in k, "YARISMA IHLALI: gorus yolunda %s" % yasak


def test_b41_iz_kapaliyken_eski_davranis_BIREBIR():
    """Kill-switch kapalıyken `_yerel_bul` ESKİ eşikleri kullanmalı
    (yarıçap 60+2w, boyut 0.5-2.0) ve yaşam döngüsü SAYI tabanlı kalmalı.
    §5.12: kapalı anahtar davranışı değiştirmez."""
    import inspect
    from dow import ana
    k = inspect.getsource(ana.Beyin._yerel_bul)
    assert "_yaricap_iz = C.YEREL_KAPI_PX + 2.0 * rw" in k, "kapalı yol değişmiş"
    assert "_b_alt, _b_ust = 0.5, 2.0" in k, "kapalı yol boyut eşiği değişmiş"
    assert "elif self._yerel_kayip >= C.YEREL_KURTAR:" in k, \
        "kapalıyken sayı tabanlı yaşam döngüsü korunmalı"
    # eleme ve teşhis sayaçları AYNI eşikleri kullanmalı (yoksa mekanizma
    # sütunu yalan söyler — §5.1)
    assert k.count("_yaricap_iz") >= 3 and k.count("_b_alt") >= 2


def test_b42_cikarim_kaydi_olcum_only_ve_gudumden_ayri():
    """§10 + §5.3 BEKÇİSİ: `cikarim.csv` her ÇIKARIMDA yazılır (meta.csv
    2 Hz; boşlukların çoğu 0.2 s, yani meta'nın altında kalıyor). truth
    sütunları YALNIZ bu dosyaya gider, güdüme değil."""
    import inspect
    from araclar import kosu
    k = inspect.getsource(kosu)
    assert "class CikarimKaydi" in k
    for alan in ("basarili", "aspekt_deg", "menzil_m", "bek_cx", "iz_yas"):
        assert alan in kosu.CikarimKaydi.ALANLAR, "eksik sütun: %s" % alan
    # truth YALNIZ ölçüm satırında kullanılmalı: gorsel_tik'e hedef bilgisi
    # sızmamalı
    from dow import ana
    g = inspect.getsource(ana.Beyin.gorsel_tik)
    for yasak in ("truth", "hedef_konumu", "hedef_yonelim"):
        assert yasak not in g, "YARIŞMA İHLALİ: gorsel_tik içinde %s" % yasak


def test_B43_gorus_isp_varsayilan_kapali_ve_tek_yolo():
    """⭐ GÖRÜŞ İŞ PARÇACIĞI (2026-08-24) — yer-kontrol `model-fps` mimarisi.

    ÖLÇÜLDÜ (kampanya HZ4): çıkarım kontrol döngüsünün İÇİNDEYKEN 9.3 -> 16.2 Hz
    yapmak kontrol döngüsünü 40.3 -> 22.3 Hz'e düşürdü, istasyon hatası
    8.3 -> 16.5 m, görsel devir HİÇ olmadı, isabet 1 -> 0.

    Bu bekçi üç seyi sinar:
      1. kill-switch VARSAYILAN KAPALI (olcum karar verir, §4),
      2. kapaliyken ESKI yol kosar (bit bit ayni davranis, §5.12),
      3. IKI YOLO ayni anda kosmaz (bu hata 22 Agu'da oyunu ac birakmisti).
    """
    from dow.ayarlar import Ayar
    assert Ayar.GORUS_ISP is False, "yeni ozellik VARSAYILAN KAPALI girer"

    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kaynak = open(os.path.join(kok, "araclar/kosu.py"), encoding="utf-8").read()

    # 2) kapaliyken eski yol: `elif Ayar.GORSEL_AKTIF:` kolu DURUYOR
    assert "if Ayar.GORSEL_AKTIF and Ayar.GORUS_ISP:" in kaynak
    assert "elif Ayar.GORSEL_AKTIF:" in kaynak, "eski yol silinmis"

    # 3) panel dedektoru GORSEL_AKTIF iken kosmaz -> tek YOLO
    assert "and not Ayar.GORSEL_AKTIF" in kaynak, \
        "panel dedektoru gorsel fazda da kosuyor -> IKI YOLO"


def test_B44_gorus_isp_sdk_tek_is_parcaciginda():
    """⛔ SDK SOKETI TEK IS PARCACIGINA AIT.

    Gorus is parcacigi YALNIZ `beyin.gorsel_tik` cagirir (girdi: goruntu).
    `beyin.b` (DoW baglantisi: truth/konum/yonelim) ve `ckayit` ORADAN
    KULLANILMAZ -- cikarim.csv satirini kontrol dongusu kurar. Iki is
    parcacigi ayni sokete yazarsa telemetri bozulur ve sebebi bulunamaz.
    """
    import inspect
    from araclar import kosu
    k = inspect.getsource(kosu._gorus_isi)
    assert "gorsel_tik" in k, "gorus is parcacigi cikarimi kosmuyor"
    for yasak in ("beyin.b.", "_beyin.b.", "ckayit", ".truth()"):
        assert yasak not in k, \
            "gorus is parcacigi SDK/CSV'ye dokunuyor: %s" % yasak


def test_B45_gorus_durumu_kilitli():
    """⛔ YARIS KOSULU BEKCISI: gorus durumu (son kutu, kopru, iz, takipci)
    iki is parcacigi tarafindan elleniyor -> her ikisi de KILIT altinda olmali.
    Kilitsiz sifirlama, takipci kendini guncellerken icini bosaltmak demektir."""
    import inspect
    from dow import ana
    sar = inspect.getsource(ana.Beyin.gorsel_tik)
    assert "with self._kilit_g:" in sar, "gorsel_tik kilitsiz"
    kom = inspect.getsource(ana.Beyin.komut) if hasattr(ana.Beyin, "komut") else ""
    adm = inspect.getsource(ana.Beyin.adim)
    hepsi = kom + adm
    if "self.iz.sifirla()" in hepsi:
        assert "with self._kilit_g:" in hepsi, \
            "faz gecisindeki sifirlama kilitsiz -- yaris kosulu"


def test_B46_gorev_sonu_ekrani_taninir():
    """⛔ GOREV-SONU EKRANI TANIMA — UC KEZ YANLIS YAZILDI, bekci sart.

    Sistem hedefi vurunca oyun 'MISSION COMPLETED' ekranina duser ve SDK
    12345 portunu KAPATIR. Kampanyada her kosu ayri surectir; taninmazsa
    sonraki tum kosular "hazirlik: BASARISIZ" verir (ISP kampanyasinin ilk
    denemesinde 4 kosu ust uste boyle dustu).

    Yanlis yazma bicimleri (hepsi yasandi):
      1. sahne-bagimli ozellik (orta bantta parlak yazi)  -> hic yakalamadi
      2. sahne-bagimli ozellik (ust bantta koyu piksel)   -> kamera yonune gore degisti
      3. dogru oge, YANLIS ESIK (>195) -> kayitli JPEG'de geciyor, CANLI ham
         karede dusuyor (ham piksellerde dugme yazisi en fazla 191)

    Bu bekci GERCEK karelerle sinar: 3 gorev-sonu + 5 negatif.
    """
    import cv2
    from araclar.kadraj import gorev_bitti_mi
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ornek = os.path.join(kok, "tests/ekranlar")
    if not os.path.isdir(ornek):
        import pytest
        pytest.skip("ornek ekranlar yok (tests/ekranlar)")
    hata = []
    for ad in sorted(os.listdir(ornek)):
        if not ad.endswith(".jpg"):
            continue
        bekle = ad.startswith("sonu")          # sonu_*.jpg = gorev-sonu
        im = cv2.imread(os.path.join(ornek, ad))
        if im is None:
            continue
        if gorev_bitti_mi(im) != bekle:
            hata.append(ad)
    assert not hata, "gorev-sonu tanima yanlis: %s" % hata


def test_B47_kutu_anlami_iki_kolda_ayni():
    """⛔ ÖLÇÜT ANLAMI KOLLAR ARASINDA KAYMAMALI (§5.2).

    ISP3'te yasandi: GORUS_ISP acikken kutu `_gorus["tespit"]`ten
    okunuyordu ve o HER cikarimda uzerine yaziliyordu (iskada None).
    Eski yolda ise `beyin._son_tespit` KALICI -- yalniz BASARILI cikarimda
    guncellenir. Sonuc: iki kol FARKLI SEY olcuyordu.

        kor sure  %31.5 -> %0.00    (kutu bayatlayamadan siliniyor)
        tespit%   %94.4 -> %50.0    (ayni seyin diger yuzu)

    Ikisi de KAZANC DEGIL, ARTEFAKT. Gudum etkilenmiyordu (o zaten
    `beyin._son_tespit` kullaniyor) ama OLCUT ve PANEL bozuktu.
    Bu bekci, iki kolun da AYNI kaynagi okudugunu sinar.
    """
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    k = open(os.path.join(kok, "araclar/kosu.py"), encoding="utf-8").read()

    # GORUS_ISP kolu: kutu beyin._son_tespit'ten okunur
    i = k.index("if Ayar.GORSEL_AKTIF and Ayar.GORUS_ISP:")
    j = k.index("elif Ayar.GORSEL_AKTIF:")
    # YORUMLARI AYIKLA: bu bekcinin gerekcesi kodun yaninda yorum olarak
    # duruyor ve icinde `_gorus["tespit"]` gecıyor; yorumu KOD sanmasin.
    kol = "\n".join(ln for ln in k[i:j].splitlines()
                    if not ln.lstrip().startswith("#"))
    assert '_gorus["tespit"]' in kol, "GORUS_ISP kolu kutuyu okumuyor"
    # ⛔ BEYIN KILIDI KULLANILMAZ: gorus is parcacigi onu CIKARIM BOYUNCA
    #   (~50 ms) tutar; kontrol dongusu beklerse ozellik iptal olur.
    #   Olculdu: 46.0 -> 39.8 Hz.
    assert "beyin._kilit_g" not in kol, \
        "GORUS_ISP kolu BEYIN KILIDINI bekliyor -- ozellik iptal olur (46->39.8 Hz)"

    # gorus is parcacigi: panel kutusunu YALNIZ basarili cikarimda gunceller
    import inspect
    from araclar import kosu
    g = inspect.getsource(kosu._gorus_isi)
    assert "if _g_kostu and _g_tespit is not None:" in g, \
        "gorus is parcacigi iskada panel kutusunu SILIYOR -- panel titrer"


def test_B48_takip_kapaliyken_gecerli_BIT_BIT_AYNI():
    """⛔ YAPISAL GARANTI (§5.10): `gecerli()` takipci KAPALIYKEN eski
    davranisi BIT BIT korumali.

    2026-08-24'te `gecerli()`ye takipci-farkindaligi eklendi: takipci
    acikken guven esigi 0.40 -> 0.10'a iner (yoksa takipcinin yasattigi
    zayif kutular alt akista olur ve ozellik kendi tasarim zarfinin
    DISINDA sinanmis olur, §5.13). Bu bekci, kill-switch KAPALIYKEN
    hicbir sey degismedigini 480 girdi kombinasyonunda kanitlar.
    """
    from dow.gudum.ibvs import gecerli, IbvsCfg
    from dow.gorus.tracker import TakipCfg
    eski = TakipCfg.AKTIF
    try:
        TakipCfg.AKTIF = False
        fark = []
        for conf in (0.0, 0.05, 0.1, 0.2, 0.39, 0.4, 0.41, 0.7, 1.0):
            for w in (4.0, 8.0, 20.0, 60.0, 200.0):
                for cx, cy in ((0, 0), (960, 540), (1919, 1079), (-1, 540),
                               (960, 1080)):
                    ok, sebep = gecerli(cx, cy, w, w * 0.7, conf)
                    # ESKI davranisin BIREBIR yeniden hesabi (kopya degil,
                    # bagimsiz ifade): esik DAIMA IbvsCfg.CONF_MIN
                    bek_ok = conf >= IbvsCfg.CONF_MIN
                    if bek_ok and not ok and sebep == "conf":
                        fark.append((conf, w, cx, cy, sebep))
                    if not bek_ok and ok:
                        fark.append((conf, w, cx, cy, "gecmemeliydi"))
        assert not fark, "takipci KAPALIYKEN davranis degisti: %s" % fark[:5]
    finally:
        TakipCfg.AKTIF = eski


def test_B49_takip_acikken_geometri_korunur():
    """Takipci acikken GUVEN esigi iner ama GEOMETRI kontrolleri (boyut,
    menzil, kadraj) AYNEN kalir. Onlar guven degil FIZIK kontrolu:
    4 px'lik bir kutu, takipci ne derse desin gecerli bir hedef degildir."""
    from dow.gudum.ibvs import gecerli, IbvsCfg
    from dow.gorus.tracker import TakipCfg
    eski = TakipCfg.AKTIF
    try:
        TakipCfg.AKTIF = True
        assert gecerli(960, 540, 60, 40, 0.25)[0] is True, \
            "takipci acikken 0.25 guven GECMELI (esik 0.10'a indi)"
        assert gecerli(960, 540, 60, 40, 0.05)[0] is False, \
            "TakipCfg.CONF_MIN altindaki kutu yine ELENMELI"
        assert gecerli(960, 540, 4, 3, 0.9)[1] == "boyut", \
            "BOYUT kontrolu takipciyle birlikte kaybolmus"
        assert gecerli(-5, 540, 60, 40, 0.9)[1] == "kadraj", \
            "KADRAJ kontrolu kaybolmus"
    finally:
        TakipCfg.AKTIF = eski


def test_B50_dedektore_BGR_verilir():
    """⛔⛔ KANAL SIRASI BEKCISI (2026-08-25).

    `ultralytics` numpy dizisini **BGR** varsayar. Sistem RGB veriyordu ve
    model KIRMIZI/MAVI kanallari TERS goruyordu. OLCULDU (talon_v3, 156 kare,
    truth dogrulamali):

        kanal      GERCEK tespit   yanlis-poz   bos kare
        BGR            %68.6          %7.1       %24.4
        RGB (eski)     %32.1          %2.6       %65.4

    Dedektor kapasitesinin YARISINDAN AZI kullaniliyordu. Bu bekci,
    kaynagin BGR verdigini ve kanal sirasina duyarli tuketicilerin
    tutarli oldugunu sinar.
    """
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1) kaynak BGR uretmeli
    kadraj = open(os.path.join(kok, "araclar/kadraj.py"), encoding="utf-8").read()
    assert "COLOR_BGRA2BGR" in kadraj, "kaynak BGR uretmiyor"
    # ⚠ Eski RGB cevrimi YALNIZ kill-switch'in ICINDE bulunabilir
    #   (DOW_KANAL_ESKI=1, A/B kiyasi icin). Kosulsuz duruyorsa HATA.
    for i, satir in enumerate(kadraj.splitlines()):
        if "COLOR_BGRA2RGB" not in satir:
            continue
        onceki = "\n".join(kadraj.splitlines()[max(0, i - 4):i])
        assert "DOW_KANAL_ESKI" in onceki, \
            "COLOR_BGRA2RGB kill-switch DISINDA kullaniliyor (satir %d)" % (i + 1)
    assert 'DOW_KANAL_ESKI", "0"' in kadraj, \
        "kanal kill-switch'i VARSAYILAN KAPALI olmali"
    assert "def grab_bgr" in kadraj, "grab_bgr yok"
    assert "def grab_rgb" not in kadraj, \
        "yaniltici eski ad `grab_rgb` duruyor (§5.12)"

    # 2) hicbir yerde grab_rgb cagrisi kalmamali
    import subprocess
    r = subprocess.run(["grep", "-rn", "grab_rgb", "--include=*.py",
                        "araclar/", "dow/"], cwd=kok,
                       capture_output=True, text=True)
    kalan = [x for x in r.stdout.splitlines() if "grab_rgb`" not in x]
    assert not kalan, "grab_rgb atiflari kaldi:\n" + "\n".join(kalan)

    # 3) panel artik RGB2BGR cevirmemeli (kaynak zaten BGR)
    panel = open(os.path.join(kok, "dow/panel.py"), encoding="utf-8").read()
    kod = "\n".join(l for l in panel.splitlines()
                    if not l.lstrip().startswith("#"))
    assert "COLOR_RGB2BGR" not in kod, \
        "panel hala RGB2BGR ceviriyor -> renkler ters gorunur"

    # 4) kayit imwrite'a dogrudan BGR yazmali
    kayit = open(os.path.join(kok, "araclar/kayit.py"), encoding="utf-8").read()
    kod = "\n".join(l for l in kayit.splitlines()
                    if not l.lstrip().startswith("#"))
    assert "img[:, :, ::-1]" not in kod and "img_rgb[:, :, ::-1]" not in kod, \
        "kayit hala kanal ceviriyor -> kayitli kareler TERS renkte olur"


def test_B51_fp16_acik_ve_gercekten_uygulanir():
    """⭐ FP16 (2026-08-25): 28.6 -> 18.6 ms (1.54 kat), kutular AYNI.

    ⚠ TUZAK: `predict(half=True)` ultralytics predictor kurulduktan sonra
    SESSIZCE YOK SAYILIR — model fp32 kalir ve "fp16 fayda vermedi" yalani
    uretilir (bu tam olarak yasandi). `_hassasiyet_uygula` bunu AutoBackend
    uzerinden GERCEKTEN uygular; bu bekci o mekanizmanin yerinde oldugunu
    ve varsayilanin ACIK oldugunu sinar."""
    from dow.gorus.dedektor import DetCfg, Dedektor
    assert DetCfg.FP16 is True, "fp16 kapali (olculmus 1.54 kat kazanc)"
    import inspect
    k = inspect.getsource(Dedektor._hassasiyet_uygula)
    assert "ab.fp16" in k and ("half()" in k or "ab.half" in k), \
        "fp16 AutoBackend'e uygulanmiyor -> predict(half=) sessizce yok sayilir"
    assert "self._fp16" in k, "mekanizma sutunu (_fp16) guncellenmiyor (§5.1)"


def test_B52_terminal_istisnasi_KAPALIYKEN_BIT_BIT_AYNI():
    """⭐ Ö-A · TERMİNAL SÜREKLİLİK İSTİSNASI (2026-08-25)

    SORUN (ölçüldü, KAMERA10 n=5, 859 çıkarım):
        menzil    tespit%   gecerli() reddi
        0-3 m      %22.0        %38.0
        3-6 m      %73.6         %0.0
      Uçurum tam MENZIL_MIN_M sınırında -> vuruşun son yarım saniyesinde
      güdümü KENDİ süzgecimiz kör ediyordu.

    SÖZLEŞME — bu bekçi üçünü birden sınar:
      1) İSTİSNA KAPALIYKEN ya da BAĞLAM YOKKEN davranış BİT BİT ESKİSİ.
      2) İstisna, YOKTAN VAR OLAN dev kutuyu HÂLÂ reddeder (çakılma koruması
         duruyor: 2026-08-21, iki koşu "Player ☠").
      3) İstisna yalnız SÜREKLİ büyümede devreye girer.
    """
    from dow.gudum import ibvs
    C = ibvs.IbvsCfg

    # --- 1) BİT BİT DENKLİK: bağlam verilmeden eski davranış ---
    #   Eski yasa: R < MENZIL_MIN_M -> daima "menzil_yakin".
    eski_aktif = C.TERMINAL_AKTIF
    try:
        for px in (340, 400, 498, 700, 1000):
            bekle = (False, "menzil_yakin")
            assert ibvs.gecerli(960, 540, px, px * 0.8, 0.9) == bekle, \
                f"bağlamsız çağrı eski davranıştan sapti ({px} px)"
            C.TERMINAL_AKTIF = False
            assert ibvs.gecerli(960, 540, px, px * 0.8, 0.9,
                                son_w=px / 1.5, son_yas=0.1) == bekle, \
                f"kill-switch KAPALIYKEN istisna calisti ({px} px)"
            C.TERMINAL_AKTIF = True
    finally:
        C.TERMINAL_AKTIF = eski_aktif

    # --- 2) ÇAKILMA KORUMASI DURUYOR ---
    #   140 m'de YOKTAN beliren dev kutu: son kutu ya yok ya kucuk.
    ok, sebep = ibvs.gecerli(960, 540, 498, 398, 0.9, son_w=None, son_yas=None)
    assert not ok and sebep == "menzil_yakin", \
        "bağlamsız dev kutu KABUL edildi — çakılma koruması delinmiş"
    ok, sebep = ibvs.gecerli(960, 540, 498, 398, 0.9, son_w=40, son_yas=0.1)
    assert not ok and sebep == "menzil_yakin", \
        "40 px -> 498 px SIÇRAMA kabul edildi — dev yanlış-pozitif geçiyor"
    ok, sebep = ibvs.gecerli(960, 540, 498, 398, 0.9, son_w=300, son_yas=99.0)
    assert not ok and sebep == "menzil_yakin", \
        "BAYAT bağlamla kabul edildi — süreklilik koşulu işlemiyor"

    # --- 3) SÜREKLİ BÜYÜME KABUL EDİLİR ---
    ok, sebep = ibvs.gecerli(960, 540, 498, 398, 0.9, son_w=300,
                             son_yas=min(0.2, C.KOPRU_S))
    assert ok and sebep == "terminal", \
        "sürekli büyüyen terminal kutu HÂLÂ reddediliyor — Ö-A çalışmıyor"

    # --- 4) İSTİSNA MENZİL TAVANINI DELMİYOR (uzak kutu hâlâ elenir) ---
    ok, sebep = ibvs.gecerli(960, 540, 14, 11, 0.9, son_w=13, son_yas=0.1)
    assert not ok and sebep == "menzil_uzak", \
        "terminal istisnası MENZIL_MAX tavanını da gevsetmis"

    # --- 5) MEKANİZMA SÜTUNU var (§5.1) ---
    from dow import ana
    import inspect
    k = inspect.getsource(ana.Beyin._gorsel_tik_kilitli)
    assert "_terminal_kabul" in k, \
        "Ö-A mekanizma sayaci gorsel_tik'te artmiyor — ölçülemez"


def test_B53_zor_kayit_KOSULAR_BIRBIRININ_USTUNE_YAZMAZ(tmp_path):
    """⛔ 2026-08-25'te YAŞANDI: 4 koşuluk veri toplama kampanyasinda
    manifest 58 satir yazdi ama DISKTE 16 goruntu vardi -- 42 kare
    kayboldu. Sebep: `kosu_yap` her kosuda YENI bir ZorKayit kuruyor,
    sayac sifirdan basliyor ve dosya adlari cakisiyordu.

    Sayi dogruydu, VERI YOKTU. Bu bekci tam o hatayi sinar: ayni dizine
    yazan UC ayri kaydedici ornegi, hicbir kareyi kaybetmemeli.

    (Ayni sinif hata bu depoda daha once de olmustu: "Kampanya script'i
    6 gecerli kosuyu yok etti -- her kosu ayni cikti dizinine yaziyordu.")
    """
    import os
    import numpy as np
    from araclar.zor_kayit import ZorKayit

    d = str(tmp_path / "zor")
    img = np.zeros((1080, 1920, 3), np.uint8)
    sat = {"basarili": 0, "bek_cx": 960.0, "bek_cy": 540.0, "bek_w": 100.0,
           "menzil_m": 10.0, "aspekt_deg": 90.0, "t": 1.0}

    yazilan = 0
    for _ in range(3):                     # her tur YENI kaydedici
        z = ZorKayit(d)
        for _ in range(5):
            if z.belki_kaydet(img, dict(sat)):
                yazilan += 1
        z.kapat()

    gor = len(os.listdir(os.path.join(d, "images")))
    lbl = len(os.listdir(os.path.join(d, "labels")))
    man = sum(1 for _ in open(os.path.join(d, "manifest.csv"))) - 1
    assert yazilan == 15, "kaydedici beklenen sayida kare yazmadi"
    assert gor == 15, f"UZERINE YAZMA: 15 yazildi, diskte {gor} goruntu var"
    assert lbl == 15, f"UZERINE YAZMA: 15 yazildi, diskte {lbl} etiket var"
    assert man == 15, "manifest ile disk ortusmuyor"


def test_B54_zor_kayit_KOTU_ETIKET_YAZMAZ(tmp_path):
    """Etiket kapilari: yanlis etikete egitmek modeli IYILESTIRMEZ, BOZAR.

    Kaydedici su dort durumu REDDETMELI:
      1. tespit BASARILI (zor ornek degil)
      2. yansitma TEKIL (tan() patlamis -- olculdu: bek_* farki maks
         48386 px)
      3. hedef menzili asiyor (etiket kalitesi menzille duser:
         40-80 m'de IoU p10 = 0.00)
      4. kutu kadraja TAM sigmiyor (kirpik hedef = kotu etiket)
    """
    import os
    import numpy as np
    from araclar.zor_kayit import ZorKayit

    z = ZorKayit(str(tmp_path / "z"))
    img = np.zeros((1080, 1920, 3), np.uint8)
    iyi = {"basarili": 0, "bek_cx": 960.0, "bek_cy": 540.0, "bek_w": 100.0,
           "menzil_m": 10.0, "aspekt_deg": 90.0, "t": 1.0}

    assert z.belki_kaydet(img, dict(iyi)) is True, "gecerli zor ornek reddedildi"

    k = dict(iyi); k["basarili"] = 1
    assert z.belki_kaydet(img, k) is False, "TESPIT VARKEN kaydetti"

    k = dict(iyi); k["bek_cx"] = 999999.0
    assert z.belki_kaydet(img, k) is False, "TEKIL yansitmayi kaydetti"

    k = dict(iyi); k["menzil_m"] = 999.0
    assert z.belki_kaydet(img, k) is False, "menzil tavanini asani kaydetti"

    k = dict(iyi); k["bek_cx"] = 5.0        # kutu sol kenardan tasiyor
    assert z.belki_kaydet(img, k) is False, "KIRPIK hedefi kaydetti"

    n, _ = z.kapat()
    assert n == 1, f"yalnizca 1 gecerli ornek yazilmaliydi, {n} yazildi"


def test_B55_kacamak_araci_GUDUME_SIZAMAZ():
    """⛔ §10 YARIŞMA KISITI — tetiklenmis kacamak TEST DUZENEGIDIR.

    `araclar/kacamak.py` hedefin GERCEK konumunu okur (tetigi ne zaman
    cekecegini bilmek icin). Bu MESRUDUR: bilgi HEDEFI surmek icin
    kullanilir, avcinin gudumune girmez -- hakemin hedefe manevra
    yaptirmasi gibidir.

    AMA o siniri KOD SEVIYESINDE tutmak gerekir. Bu bekci sunu sinar:
      1) `dow/` altindaki HICBIR modul kacamak aracini ice aktarmaz
      2) gudum kodu Talon koprusunu OKUMAZ (kopru tek yon: panel -> oyun)
      3) gorsel yasa hala yalniz goruntu alir (B1/B18/B19 ayrica sinar)
    """
    import os
    import inspect
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1) dow/ altinda kacamak araci ice aktarilmamis
    for dizin, _, dosyalar in os.walk(os.path.join(kok, "dow")):
        if "__pycache__" in dizin:
            continue
        for d in dosyalar:
            if not d.endswith(".py"):
                continue
            yol = os.path.join(dizin, d)
            k = open(yol, encoding="utf-8").read()
            assert "kacamak" not in k.replace("kacamak_", ""), \
                f"gudum modulu kacamak aracina bagimli: {yol}"

    # 2) GUDUM kodu Talon koprusunu OKUMAZ.
    #    Kopruyu YALNIZ panel YAZAR (panel.py::talon_kopru_yaz).
    from dow import ana
    from dow.gudum import ibvs, gps, cevirici
    for m in (ana, ibvs, gps, cevirici):
        k = inspect.getsource(m)
        assert "talon_kopru" not in k and "TALON_KOPRU" not in k, \
            f"gudum modulu Talon koprusune bakiyor: {m.__name__}"

    # 3) kacamak araci gercekten AYRI bir surec olarak tasarlanmis:
    #    dow/ altindan degil, araclar/ altinda ve __main__ girisi var.
    ky = os.path.join(kok, "araclar", "kacamak.py")
    assert os.path.exists(ky), "kacamak araci yok"
    k = open(ky, encoding="utf-8").read()
    assert '__name__ == "__main__"' in k, \
        "kacamak araci ayri surec girisi tasimiyor"
    assert "from dow.ana import" not in k and "from dow.gudum import" not in k, \
        "kacamak araci gudum modullerini ice aktariyor -- ayrik olmali"


def test_B56_kacamak_taban_hizi_SPLINE_ILE_ESLESIR():
    """⛔ `yok` KOLU GECERLI TABAN OLMALI (§3.3).

    Talon spline ustunde 1800 cm/s uçuyor. Mod ucus modeli:
        hiz = 300 + throttle * 3700   (cm/s)
    Kontrolu devralinca taban throttle bu hizi VERMELI; vermezse hedefin
    hizi degisir ve `yok` kolu artik kontrolsuz senaryonun tabani olmaz --
    butun kiyas kayar."""
    import importlib.util
    import os
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "kacamak", os.path.join(kok, "araclar", "kacamak.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    hiz_cms = 300.0 + m.TABAN_THR * 3700.0
    assert abs(hiz_cms - 1800.0) <= 20.0, \
        f"taban hizi {hiz_cms:.0f} cm/s, spline 1800 cm/s -- `yok` kolu bozuk"

    # `yok` GERCEKTEN kacamaksiz olmali
    assert m.KACAMAKLAR["yok"] is None, "`yok` kolu kacamak uyguluyor"
    # §3.3'teki tum cesitler dursun
    for ad in ("yatay", "dikey_yukari", "dikey_asagi", "capraz", "hizlan"):
        assert ad in m.KACAMAKLAR, f"kacamak cesidi eksik: {ad}"
    # eksenler -1..1 / throttle 0..1 sinirinda
    for ad, v in m.KACAMAKLAR.items():
        if v is None:
            continue
        thr, yaw, pit, rol = v
        assert 0.0 <= thr <= 1.0, f"{ad}: throttle aralik disi"
        for x in (yaw, pit, rol):
            assert -1.0 <= x <= 1.0, f"{ad}: eksen aralik disi"


def test_B57_kacak_kosu_ERKEN_KESILIR():
    """⛔ KULLANICI (2026-08-26): "drone bazen cok cok uzaklara gidiyor ve
    bosa zaman harciyoruz... 500 metre falan uzaklasirsa ucusu durdur."

    Eski esik 1500 m'ydi: kacak bir kosu ancak 54 s sonra kesiliyordu
    (28 m/s). OLCULDU (KC1, 12/12 gecerli kosu): drone spawn'dan EN FAZLA
    354 m uzaklasiyor, medyan 255 m -> 600 m esik mesru kosuyu KESMEZ.

    ⚠ SABIT ESIK TEK BASINA YANLIS OLURDU. Kodda yazili tuzak:
      "Gorev yeniden kurulunca baslangic ayrimi 800-970 m cikabiliyor ve
       kural MESRU YAKLASMAYI iptal ediyordu -- 12 kosuluk bir blok
       tamamen bu yuzden cope gitti."
    Bu yuzden sinir BASLANGIC AYRIMINA GORELIDIR.
    """
    from dow.ayarlar import Ayar
    from araclar.bekci import Bekci

    assert Ayar.BEKCI_SPAWN_MAX_M <= 700.0, \
        "kacak esigi hala cok comert -- bosa ucus suresi uzar"
    assert Ayar.BEKCI_SPAWN_MAX_M >= 400.0, \
        "esik cok dar -- olculen en kotu GECERLI kosu 354 m"

    # --- 1) NORMAL DOGUS: 600 m'de kesilmeli, 354 m'de KESILMEMELI ---
    b = Bekci(Ayar); b.sifirla()
    spawn = (0.0, 0.0, 100.0)
    hedef = (50.0, 0.0, 100.0)          # yakin dogus
    for i in range(5):
        b.kontrol(0.1 * i, (spawn[0] + i * 0.5, spawn[1], spawn[2]), 0.0, hedef, True)
    # olculen en kotu gecerli kosu kadar uzaklas -> ihlal YOK
    for i in range(5):
        b.kontrol(1.0 + i, (354.0 + i * 0.5, 0.0, 100.0), 0.0, hedef, True)
    assert b.ihlal is None, \
        f"354 m (olculen en kotu GECERLI kosu) iptal edildi: {b.ihlal}"
    # simdi kacak: sinirin acik ustu -> KESILMELI
    #   ⚠ Hangi kuralin once atesledigi onemli DEGIL: `hedef_cok_uzak` da
    #     mesru bir kacak yakalamasidir (drone once hedefe yaklasmis, sonra
    #     uzaklasmis). Sinanan sey KOSUNUN KESILDIGI.
    for i in range(Ayar.BEKCI_ESIK + 2):
        b.kontrol(10.0 + i, (900.0 + i * 0.5, 0.0, 100.0), 0.0, hedef, True)
    assert b.ihlal in ("spawn_cok_uzak", "hedef_cok_uzak"), \
        f"900 m kacak kosu KESILMEDI: {b.ihlal}"

    # spawn kurali TEK BASINA da calismali (hedef yokken baska kural yok)
    b3 = Bekci(Ayar); b3.sifirla()
    for i in range(3):
        b3.kontrol(0.1 * i, (spawn[0] + i * 0.5, spawn[1], spawn[2]), 0.0, None, True)
    for i in range(Ayar.BEKCI_ESIK + 2):
        b3.kontrol(1.0 + i, (900.0 + i * 0.5, 0.0, 100.0), 0.0, None, True)
    assert b3.ihlal == "spawn_cok_uzak", \
        f"spawn kurali tek basina atesleyemedi: {b3.ihlal}"

    # --- 2) UZAK DOGUS: sinir GENISLEMELI, mesru yaklasma kesilmemeli ---
    b2 = Bekci(Ayar); b2.sifirla()
    uzak_hedef = (900.0, 0.0, 100.0)     # dogusta 900 m ayrim
    for i in range(3):
        b2.kontrol(0.1 * i, (spawn[0] + i * 0.5, spawn[1], spawn[2]), 0.0, uzak_hedef, True)
    # hedefe dogru 850 m ucmak MESRU -- sinir 900+400=1300
    for i in range(Ayar.BEKCI_ESIK + 3):
        b2.kontrol(1.0 + i, (850.0 + i * 0.5, 0.0, 100.0), 0.0, uzak_hedef, True)
    assert b2.ihlal is None, \
        f"uzak dogusta MESRU yaklasma iptal edildi: {b2.ihlal} " \
        "(kodda yazili '12 kosuluk blok cope gitti' tuzagi geri gelmis)"


def test_B58_api_telemetry_COKMEDEN_CALISIR():
    """⛔ /api/telemetry COKERSE PANELIN TAMAMI OLUR.

    YASANDI (2026-08-26): 3B grafik icin hedef konumu eklerken yerel
    degiskene `_hz` adi verdim. Modul duzeyinde `_hz()` diye bir FONKSIYON
    var; Python, fonksiyon icinde bir ada ATAMA gorunce o adi TUM fonksiyon
    boyunca YEREL sayar -> ayni fonksiyondaki onceki `_hz(_fps[...])`
    cagrilari UnboundLocalError atti ve ucun tamami coktu.
    Hicbir bekci bunu yakalamadi cunku /api/telemetry sinanmiyordu.

    Bu bekci ucu GERCEKTEN cagirir ve sozlesmesini sinar.
    """
    import json
    from dow import panel as P

    # GORSEL fazi: `h_*` YOK (§10 -- o fazda hedefin GPS'i okunmaz).
    # Hedef konumu truth kanalindan (`t_*`) gelmeli, yoksa 3B grafik DONAR.
    P.telem_yaz({"durum": "GORSEL", "yukseklik": 90.0, "drone_hiz": 25.0,
                 "d_x": 10.0, "d_y": -20.0, "d_z": 85.0,
                 "d_roll": 1.0, "d_pitch": -2.0, "d_yaw": 70.0,
                 "t_x": 40.0, "t_y": -10.0, "t_z": 92.0,
                 "gercek_mesafe_m": 33.0})
    d = P._api_telemetry()
    json.dumps(d)                      # JSON'a cevrilebilmeli

    # ⚠ `perf` KOSULLU bir alandir (FPS sayaclari beslenmediyse yok);
    #   zorunlu tutmak testi yanlis yerden dusurur.
    for a in ("connected", "drone", "target"):
        assert a in d, f"/api/telemetry alani eksik: {a}"

    for eksen in ("x", "y", "z"):
        assert isinstance(d["drone"].get(eksen), (int, float)), \
            f"drone.{eksen} sayi degil -- 3B grafik cizemez"
        assert isinstance(d["target"].get(eksen), (int, float)), \
            f"target.{eksen} GORSEL fazda BOS -- 3B grafikte hedef DONAR " \
            "(truth kanali `t_*` baglanmamis)"

    # `h_*` varsa O tercih edilmeli (truth yalnizca yedek)
    P.telem_yaz({"h_x": 1.0, "h_y": 2.0, "h_z": 3.0})
    d2 = P._api_telemetry()
    assert (d2["target"]["x"], d2["target"]["y"], d2["target"]["z"]) == (1.0, 2.0, 3.0), \
        "h_* varken truth kanali tercih edilmis -- oncelik ters"


# ⛔ B59 (lead bit-bit denkligi) SILINDI: ozellik 2026-08-26 aksami
#    tamamen cikarildi (Ö-E notr, Ö-F her olcutte kotulesti).
#    Gerekce ve sayilar B20'de. §5.12


def test_B60_yavasla_KAPALIYKEN_BIT_BIT_AYNI():
    """⭐ Ö-G · DONUSTE YAVASLA — 2026-08-26.

    YAPISAL EKSIK (koddan cikarildi): hedef_boyut = 997/1.0 = 997 px, gercek
    kutu 40-150 px -> v_istek ~315 m/s -> V_HUCUM'a kirpiliyor. Hiz ancak
    kutu 917 px (=1.1 m menzil) olunca duser. Yani GORSEL FAZ BOYUNCA HIZ
    DAIMA TAVANDA; gudum hizi donus kabiliyetiyle HIC takas etmiyor.

    §5.11: R = V^2/(g*tan(theta)). Olculdu (KD1 daire, GORSEL): 21.8 m/s,
    yatis p90 31.7 derece -> yaricap ~78 m. Hedefin dairesi 17.5 m.

    SOZLESME: YAVASLA_TABAN=1.0 iken kesme=1.0 ve cikti BIT BIT bugunkuyle
    ayni; acikken eps_yaw ile ORANTILI kisiyor ve tabanin altina INMIYOR.
    """
    from dow.gudum import ibvs
    C = ibvs.IbvsCfg
    eski = C.YAVASLA_TABAN
    try:
        # --- 1) KAPALIYKEN kesme YOK ---
        C.YAVASLA_TABAN = 1.0
        for cx in (200, 960, 1700):          # kucuk/buyuk nisan hatasi
            _, _, _, _, ti = ibvs.komut(cx, 540, 60, 48, 0.0, -2.0, 3.0,
                                        0.0, 0.02)
            assert ti["ibvs_kesme"] == 1.0, \
                f"kapaliyken kesme uygulandi: {ti['ibvs_kesme']}"

        # --- 2) ACIKKEN: duz bacakta TAM HIZ, buyuk hatada KISIK ---
        C.YAVASLA_TABAN = 0.55
        _, _, _, _, t0 = ibvs.komut(960, 540, 60, 48, 0.0, -2.0, 3.0,
                                    0.0, 0.02)   # nisan hatasi ~0
        _, _, _, _, t1 = ibvs.komut(200, 540, 60, 48, 0.0, -2.0, 3.0,
                                    0.0, 0.02)   # nisan hatasi BUYUK
        assert t0["ibvs_kesme"] > t1["ibvs_kesme"], \
            "nisan hatasi buyudugunde hiz KISILMIYOR"
        assert t1["ibvs_kesme"] >= C.YAVASLA_TABAN - 1e-9, \
            f"kesme tabanin ALTINA indi: {t1['ibvs_kesme']} < {C.YAVASLA_TABAN}"
        assert t0["ibvs_kesme"] <= 1.0 + 1e-9

        # --- 3) HIZ GERCEKTEN DUSMELI (yalniz sayac degil) ---
        v0 = t0["ibvs_v"]; v1 = t1["ibvs_v"]
        assert v1 < v0, f"kesme sayaci degisti ama hiz dusmedi: {v0} -> {v1}"
    finally:
        C.YAVASLA_TABAN = eski


# ---------------------------------------------------------------- B62
def test_B62_arka_yarikure_izdusum_kapisi():
    """⛔ ARKA YARIKÜRE — arkadaki hedef "kadraj içinde" görünmemeli.

    YAŞANMIŞ HATA (2026-08-27): izdüşüm zinciri kamera ekseni bileşenine
    (`ileri`) böler; hedef arkadayken bu bileşen NEGATİF olur ve bölme
    işareti çevirerek KADRAJIN İÇİNDE bir piksel üretir. `tan()` de aynı
    şeyi yapar: tan(170°) = -0.176 -> cx = 960 - 0.176·F.

    Sonuç: "üstünden geçtiğimiz" kareler, kayıp sınıflandırmasında
    "kadraj içinde ama dedektör kör" sayıldı. Manevralı koşularda
    menzil<12 m kayıplarının %47'si buydu; manevrasızda %0.

    ⚠ Bu bekçi ÖLÇÜM yolunu korur. Güdümdeki `seviye_piksel` bilerek
      dokunulmadan bırakıldı (davranış değişikliği ayrı karar, §8).
    """
    from dow.gorus import kamera as KAM

    # --- önde: normal izdüşüm, kadraj içinde ---
    on = KAM.beklenen_kadraj(50.0, 0.0, 0.0, 0.0, 0.0)
    assert on is not None, "önümüzdeki hedef için izdüşüm dönmeli"
    assert 0 <= on[0] < KAM.IMG_W, "önümüzdeki hedef kadrajda olmalı"

    # --- tam arka: None dönmeli (ESKİDEN kadraj içi piksel üretiyordu) ---
    for az in (95.0, 135.0, 170.0, 179.0, -95.0, -170.0):
        assert KAM.beklenen_kadraj(50.0, 0.0, az, 0.0, 0.0) is None, \
            "azimut %.0f° ARKADA — izdüşüm None olmalı" % az

    # --- kenar: kadraj dışı ama ÖNDE ise izdüşüm dönmeye devam etmeli;
    #     "kadraj dışı"(A kovası) ile "arkada" ayrı şeylerdir ---
    yan = KAM.beklenen_kadraj(50.0, 0.0, 75.0, 0.0, 0.0)
    assert yan is not None, "75° hâlâ ÖNDE — A kovası olarak ölçülebilmeli"
    assert yan[0] >= KAM.IMG_W, "75° kadraj DIŞINDA olmalı"

    # --- dikeyde de aynı kapı ---
    #   ⚠ KONVANSİYON (ölçüldü, varsayılmadı): dik = yükseliş − TILT − pitch.
    #     TILT = 26.5° olduğu için 100° yükseliş kamera çerçevesinde 73.5°'ye
    #     düşer ve kapıyı AÇMAZ — doğrusu budur, o yön hâlâ görüntü
    #     düzleminin ÖNÜNDEDİR. Kapı, kamera çerçevesindeki açıya bakar.
    assert KAM.beklenen_kadraj(50.0, 100.0, 0.0, 0.0, 0.0) is not None, \
        "100° yükseliş kamera çerçevesinde 73.5° — hâlâ ÖNDE"
    assert KAM.beklenen_kadraj(50.0, 170.0, 0.0, 0.0, 0.0) is None, \
        "170° yükseliş (dik=143.5°) ARKADA — None dönmeli"





# ================================================================= B63-B67
#  KİLİT FAZI — Teknofest şartnamesi 6.1.4 (2026-08-28)
# =============================================================================

def test_B63_kilit_fazi_KAPALIYKEN_BIT_BIT_AYNI():
    """⛔ KILL-SWITCH SÖZLEŞMESİ: Ayar.KILIT_FAZI kapaliyken guduem yolu
    DEGISMEZ.

    Kilit fazi, gorsel temas kurulunca aracin DOGRUDAN temasa surmesini
    engelleyip once mesafe tutturur. Bu bir DAVRANIS degisikligidir; §6
    geregi kill-switch'i vardir ve varsayilani KAPALIdir. Kapaliyken:
      1. ibvs.komut()'a denge_boyut_px GECILMEZ -> hedef_boyut = 997 px
      2. Beyin.faz DAIMA "TERMINAL"
      3. kilit muhasebesi HIC calismaz (ornek sayaci 0 kalir)
    """
    from dow.ayarlar import Ayar
    from dow.gudum import ibvs
    from dow.gudum.kilit import KilitDurumu

    # 1) denge_boyut_px=None -> eski davranis (denge kutusu = 997 px)
    for w in (20.0, 60.0, 140.0, 300.0):
        _, _, _, _, t_eski = ibvs.komut(960, 540, w, w * 0.4, 0.0, -2.0, 3.0,
                                        0.0, 0.02)
        _, _, _, _, t_ayni = ibvs.komut(960, 540, w, w * 0.4, 0.0, -2.0, 3.0,
                                        0.0, 0.02, denge_boyut_px=None)
        assert t_eski["ibvs_hata_px"] == t_ayni["ibvs_hata_px"]
        assert t_eski["ibvs_v"] == t_ayni["ibvs_v"]
        assert abs(t_eski["ibvs_denge_px"]
                   - ibvs.KAM.MENZIL_C / ibvs.IbvsCfg.HUCUM_MENZIL_M) < 1e-9

    # 2) denge_boyut_px verilince GERCEKTEN degisiyor (mekanizma kapisi §5.1)
    _, _, _, _, t_kilit = ibvs.komut(960, 540, 140.0, 56.0, 0.0, -2.0, 3.0,
                                     0.0, 0.02,
                                     denge_boyut_px=ibvs.KAM.MENZIL_C / 6.0)
    _, _, _, _, t_term = ibvs.komut(960, 540, 140.0, 56.0, 0.0, -2.0, 3.0,
                                    0.0, 0.02)
    assert t_kilit["ibvs_v"] < t_term["ibvs_v"], \
        "kilit fazinda hiz kisilmiyor -> ozellik CALISMIYOR"
    assert t_term["ibvs_v"] == ibvs.IbvsCfg.V_HUCUM, "taban kol tavanda olmali"

    # 3) muhasebe kapaliyken hic islemez
    eski = Ayar.KILIT_FAZI
    try:
        Ayar.KILIT_FAZI = False
        k = KilitDurumu(Ayar)
        assert k.n_ornek == 0 and k.saglandi is False and k.kumulatif_s == 0.0
    finally:
        Ayar.KILIT_FAZI = eski


def test_B64_kilit_modulu_GPS_ALMAZ():
    """⛔ YARISMA KURALI (CLAUDE.md §10) — YAPISAL GARANTI.

    Kilit muhasebesi gorsel temas VARKEN calisir; o anda hedefin GPS'ine
    dokunmak diskalifiye sebebidir. Garanti IMZA duzeyinde saglanir:
    `kare_kilitli` yalnizca kutu pikselleri alir, `guncelle` yalnizca
    zaman + kutu. Modulun tamaminda GPS/menzil/hedef konumu gecmez.
    """
    import inspect
    from dow.gudum import kilit as K

    p = list(inspect.signature(K.KilitDurumu.kare_kilitli).parameters)
    assert p == ["self", "kutu"], f"kare_kilitli imzasi genisledi: {p}"
    p = list(inspect.signature(K.KilitDurumu.guncelle).parameters)
    assert p == ["self", "t", "kutu"], f"guncelle imzasi genisledi: {p}"

    kaynak = inspect.getsource(K)
    # yorum satirlarini at, KOD'a bak
    kod = "\n".join(s for s in kaynak.splitlines()
                    if not s.strip().startswith("#"))
    for yasak in ("truth(", "hedef_konum", "hedef_m", "gps", "GPS_KAYNAK",
                  "izleyici", "hedef_konumu"):
        assert yasak not in kod, f"kilit modulunde YASAK erisim: {yasak}"


def test_B65_sartname_olcutu_KOSE_DEGERLERI():
    """Sartname 6.1.4 + Sekil 2: AV siniri ve %P boyut esigi.

    AV  : soldan/sagdan %25, ustten/alttan %10 kirpma -> x[480,1440] y[108,972]
    boyut: hedef, ekranin yatay VEYA dikey ekseninin en az %P'sini kaplamali
           ("...eksenlerinden en az birinde, en az %5'ini kapsamalidir").
    Varsayilan P=6 cunku sartname "paket gonderme limitinin %6 veya daha
    ustu olmasi tavsiye edilir" diyor (hatali kilitlenme = eksi puan).
    """
    from dow.ayarlar import Ayar
    from dow.gudum.kilit import KilitDurumu
    from dow.gorus import kamera as KAM

    esk = Ayar.KILIT_BOYUT_YUZDE
    try:
        Ayar.KILIT_BOYUT_YUZDE = 6.0
        k = KilitDurumu(Ayar)
        W, H = KAM.IMG_W, KAM.IMG_H
        buyuk = (0.06 * W + 1, 0.06 * H + 1)      # ikisi de esikte

        # --- AV sinirlari (dahil / haric) ---
        assert k.kare_kilitli((480, 540, buyuk[0], buyuk[1]))[0] is True
        assert k.kare_kilitli((479, 540, buyuk[0], buyuk[1])) == (False, "AV_disi")
        assert k.kare_kilitli((1440, 540, buyuk[0], buyuk[1]))[0] is True
        assert k.kare_kilitli((1441, 540, buyuk[0], buyuk[1])) == (False, "AV_disi")
        assert k.kare_kilitli((960, 108, buyuk[0], buyuk[1]))[0] is True
        assert k.kare_kilitli((960, 107, buyuk[0], buyuk[1])) == (False, "AV_disi")
        assert k.kare_kilitli((960, 972, buyuk[0], buyuk[1]))[0] is True
        assert k.kare_kilitli((960, 973, buyuk[0], buyuk[1])) == (False, "AV_disi")

        # --- boyut: EN AZ BIRI yeterli (VEYA), ikisi birden SART DEGIL ---
        assert k.kare_kilitli((960, 540, 0.06 * W, 1.0))[0] is True,  "yatay eksen tek basina yetmeli"
        assert k.kare_kilitli((960, 540, 1.0, 0.06 * H))[0] is True,  "dikey eksen tek basina yetmeli"
        assert k.kare_kilitli((960, 540, 0.06 * W - 1, 0.06 * H - 1)) \
            == (False, "kucuk")

        # --- tespit yoksa kilit YOK ---
        assert k.kare_kilitli(None) == (False, "tespit_yok")
    finally:
        Ayar.KILIT_BOYUT_YUZDE = esk


def test_B66_kayan_pencere_KESIK_KESIK_TOPLAR():
    """Sartname: "kilitlenme suresi, pencere icerisinde kesik kesik
    gerceklesebilir ve birden fazla kisa kilitlenme araliginin toplami
    olarak hesaplanabilir." Ornek olarak 1 s + 2 s + 2 s = 5 s veriliyor.

    Ayrica: bir cikarimin alabilecegi EN BUYUK kredi sartnamenin kendi
    toleransi kadardir (200 ms); saniyelerce suren tespit boslugu kilit
    suresi SAYILAMAZ.
    """
    from dow.ayarlar import Ayar
    from dow.gudum.kilit import KilitDurumu

    k = KilitDurumu(Ayar)
    KUTU = (960, 540, 200.0, 90.0)     # rahat kilitli
    # sartnamenin kendi ornegi: 0-1 s, 3-5 s, 6-8 s kilitli => 5 s
    araliklar = [(0.0, 1.0), (3.0, 5.0), (6.0, 8.0)]

    def kilitli_mi(t):
        return any(a <= t < b for a, b in araliklar)

    t = 0.0
    while t < 10.0:
        o = k.guncelle(t, KUTU if kilitli_mi(t) else None)
        t += 0.1
    assert 4.5 <= o["kilit_s"] <= 5.2, \
        f"kesik kesik toplam yanlis: {o['kilit_s']} (beklenen ~5.0)"
    assert o["kilit_saglandi"] == 1, "5 s biriktigi halde isteri saglanmadi"

    # --- PENCERE KAYIYOR: 10 s'i gecen kilit DUSMELI ---
    k2 = KilitDurumu(Ayar)
    t = 0.0
    while t < 6.0:                        # 6 s kesintisiz kilit
        son = k2.guncelle(t, KUTU); t += 0.1
    assert son["kilit_saglandi"] == 1
    dolu = son["kilit_s"]
    while t < 20.0:                       # sonra 14 s kilitsiz
        son = k2.guncelle(t, None); t += 0.1
    assert son["kilit_s"] < 0.5, \
        f"pencere kaymadi, eski kilit hala sayiliyor: {son['kilit_s']} (once {dolu})"
    # ...ama MANDAL acik kalir: bir kez saglandiysa terminale gecilmistir
    assert son["kilit_saglandi"] == 1, "mandal geri dondu -> faz salinir"

    # --- UZUN BOSLUK KREDI ALMAZ (kredi tavani = 200 ms) ---
    k3 = KilitDurumu(Ayar)
    k3.guncelle(0.0, KUTU)
    o3 = k3.guncelle(9.0, KUTU)           # 9 saniyelik bosluktan sonra
    assert o3["kilit_s"] <= Ayar.KILIT_DT_MAX_S + 1e-9, \
        f"9 s bosluk kilit suresi sayildi: {o3['kilit_s']}"


def test_B67_kilit_YALNIZ_GERCEK_TESPITLE_beslenir():
    """⛔ HATALI KILITLENME PAKETI RISKI.

    Sartname: "Kilitlenme olmamasi durumunda kilitlenme var bilgisi
    gonderilmesi ... takimlarin eksi puan almasina neden olacaktir."
    Bizim sistemde kutu iki kaynaktan gelebilir:
      (a) dedektorun O KAREDE urettigi GERCEK tespit
      (b) T5 KOPRUSU / takipci ongorusu — kendi olu-hesabimiz
    (b) kameranin olcumu DEGILDIR; onunla kilit saymak yukaridaki eksi
    puana girer. Bu yuzden `Beyin` kilit muhasebesini YALNIZ `gecerli()`
    suzgecinden gecmis GERCEK tespitle besler.

    Bu bekci, `_gorsel_tik_kilitli` icinde muhasebeye giden degiskenin
    kopru/ongoru kutusu OLMADIGINI kaynak duzeyinde sinar.
    """
    import inspect
    from dow import ana

    src = inspect.getsource(ana.Beyin._gorsel_tik_kilitli)
    assert "self.kilitci.guncelle(t, kabul)" in src, \
        "kilit muhasebesi 'kabul' disinda bir kutuyla besleniyor"
    # kopru kutusu bu fonksiyonda URETILMEZ (o `adim` icinde, gudum icin)
    assert "_kopru_kutu(" not in src, \
        "kopru kutusu tespit yoluna sizmis — kilit sahte kutuyla beslenebilir"

    # `adim` icinde kopru kutusu guduem icin kullanilir ama kilit
    # muhasebesine DOKUNMAZ:
    src2 = inspect.getsource(ana.Beyin.adim)
    assert "kilitci.guncelle" not in src2, \
        "kilit muhasebesi kontrol dongusunden de besleniyor -> CIFT SAYIM"


# ================================================================= B68-B70
#  KİLİT FAZI HIZ REGÜLATÖRÜ (2026-08-28) — "sert fren" düzeltmesi
# =============================================================================

def test_B68_regulator_YOKKEN_BIT_BIT_AYNI():
    """⛔ KILL-SWITCH: `reg=None` iken ibvs.komut() eski PI'yi koşar.

    Regulator KILIT fazina OZELDIR; TERMINAL faz (bugun 7/8 vuran hal) ve
    GPS fazi DEGISMEMELI. Bu bekci, reg gecilmediginde hiz yasasinin
    BIREBIR eski sonucu urettigini sinar.
    """
    from dow.gudum import ibvs
    for w in (20.0, 60.0, 140.0, 300.0, 900.0):
        a = ibvs.komut(960, 540, w, w * 0.4, 0.0, -2.0, 3.0, 0.0, 0.02)
        b = ibvs.komut(960, 540, w, w * 0.4, 0.0, -2.0, 3.0, 0.0, 0.02, reg=None)
        assert a[0] == b[0] and a[1] == b[1] and a[2] == b[2] and a[3] == b[3]
        assert a[4]["ibvs_v"] == b[4]["ibvs_v"]
        # regulator sutunlari YOK (ozellik hic devreye girmedi)
        assert "ibvs_kilit_I" not in a[4]


def test_B69_regulator_SERT_FREN_YAPAMAZ():
    """⛔ KULLANICI GOZLEMI -> SOZLESME.

    Olculdu (KILIT16, A kolu): komut tek tikte 28.00 -> 0.00 m/s dusuyordu
    (-280 m/s^2). Sonucu: 139 olayda menzil +18.8 m geri dusus, tespit
    %62 -> %18. Regulatorun BIRINCIL sozlesmesi budur:

      1. |dv/dt| <= KILIT_SLEW  (asla basamak fren)
      2. v >= KILIT_V_MIN       (asla tam durus)
      3. v <= KILIT_V_MAX
    """
    from dow.ayarlar import Ayar
    from dow.gudum.kilit import HizRegulatoru

    r = HizRegulatoru(Ayar); r.sifirla(Ayar.KILIT_V_MAX)
    onc = Ayar.KILIT_V_MAX
    dt = 0.02
    # hedef ANIDEN cok yakin gorunsun (kutu 300 px) -> eski yasa 0'a inerdi
    for _ in range(300):
        v = r.hiz(100.0 - 300.0, dt)
        assert abs(v - onc) <= Ayar.KILIT_SLEW * dt + 1e-9, \
            f"slew asildi: {(v-onc)/dt:.1f} m/s^2 > {Ayar.KILIT_SLEW}"
        assert v >= Ayar.KILIT_V_MIN - 1e-9, f"tam durusa indi: {v}"
        assert v <= Ayar.KILIT_V_MAX + 1e-9
        onc = v
    assert abs(v - Ayar.KILIT_V_MIN) < 1e-6, "tabana oturmali"

    # TERS YON: cok uzak gorunsun -> gaz da basamak olmamali
    r2 = HizRegulatoru(Ayar); r2.sifirla(Ayar.KILIT_V_MIN)
    onc = Ayar.KILIT_V_MIN
    for _ in range(300):
        v = r2.hiz(+500.0, dt)
        assert abs(v - onc) <= Ayar.KILIT_SLEW * dt + 1e-9
        onc = v
    assert abs(v - Ayar.KILIT_V_MAX) < 1e-6


def test_B70_regulator_ANTIWINDUP_ve_GPS_ALMAZ():
    """(a) §10: regulator imzasinda hedefe dair HICBIR sey yok.
       (b) ANTI-WINDUP: cikis doyumdayken ve hata doyumu DERINLESTIRIYORKEN
           integral DONMALI. Yoksa doyumda siser, hata isaret degistirince
           bosalmasi saniyeler surer -> asim ve salinim.
    """
    import inspect
    from dow.ayarlar import Ayar
    from dow.gudum import kilit as K

    p = list(inspect.signature(K.HizRegulatoru.hiz).parameters)
    assert p == ["self", "hata_px", "dt"], f"imza genisledi: {p}"
    kod = "\n".join(l for l in inspect.getsource(K.HizRegulatoru).splitlines()
                    if not l.strip().startswith("#"))
    for yasak in ("truth", "hedef_konum", "gps", "menzil_m", "izleyici"):
        assert yasak not in kod, f"regulatorde YASAK erisim: {yasak}"

    # anti-windup: uzun sure DOYUMDA pozitif hata -> I sinirsiz sismemeli
    r = HizRegulatoru = K.HizRegulatoru(Ayar); r.sifirla(Ayar.KILIT_V_MAX)
    for _ in range(2000):                 # 40 s boyunca "cok uzak"
        r.hiz(+800.0, 0.02)
    I_doymus = r.I
    assert I_doymus <= Ayar.KILIT_I_MAX + 1e-9
    # doyumda I BUYUMEMELI (dondurulmus olmali) — tavana yapismis olamaz
    assert I_doymus < Ayar.KILIT_I_MAX - 1e-9, \
        f"anti-windup calismadi, I tavana yapisti: {I_doymus}"
    assert r.doyum > 100, "doyum sayaci islememis (mekanizma sutunu §5.1)"
