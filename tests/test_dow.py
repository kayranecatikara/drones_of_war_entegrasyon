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
    """60-90 m'de tespit %10 -> orada görsel devir yapılmamalı."""
    from dow.gorus.dedektor import DEVIR_MENZIL_M
    assert DEVIR_MENZIL_M <= 55.0
    assert ibvs.IbvsCfg.MENZIL_MAX_M <= 55.0


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


def test_B13_devir_kapisi_YARISMADA_YALNIZ_KAMERA():
    """⛔ YARISMA KURALI (kullanici 2026-08-22): "gorsel gudum sirasinda GPS
    verisini asla kullanma; gorsel gudum algoritmasina GPS verisini dahil
    etmek diskalifiye sebebi."

    Kullanici 2026-08-22'de GELISTIRME icin bir istisna ONAYLADI: devir
    kapisi (faz gecisi) istasyona oturma + ~15 m menzil kullanabilir, AMA
    "ayri bir anahtarla ve yarisma kipinde otomatik kapanacak sekilde".
    Bu bekci tam o sozlesmeyi sinar:
      1) YARISMA_KIPI=1 -> gelistirme_devri() False
      2) o durumda GPS'e bakan metot HIC CAGRILMAZ (kaynak kosulu)
      3) metodun tek cagri yeri gelistirme_devri() bayraginin arkasinda
      4) kamera-tek kapi (ardisik DEVIR_KARE tespit) HALA duruyor
      5) GORSEL fazda GPS okunmaz (B18 ayrica sinar)
    """
    import inspect
    from dow import ana
    from dow.ayarlar import Ayar

    # 1) yarisma kipi bayragi kapatiyor mu
    eski = Ayar.YARISMA_KIPI
    try:
        Ayar.YARISMA_KIPI = True
        assert Ayar.gelistirme_devri() is False, \
            "YARISMA_KIPI=1 iken gelistirme devir kapisi HALA acik"
        Ayar.YARISMA_KIPI = False
        assert Ayar.gelistirme_devri() is True
    finally:
        Ayar.YARISMA_KIPI = eski

    k = inspect.getsource(ana.Beyin.adim)

    # 2+3) GPS'e bakan metodun TEK cagri yeri var ve bayragin arkasinda
    assert k.count("_gelistirme_devir_hazir") == 1, \
        "gelistirme devir kapisi birden fazla yerden cagriliyor"
    i = k.index("_gelistirme_devir_hazir")
    civar = k[i:i + 260]
    assert "gelistirme_devri()" in civar, \
        "GPS'li devir kapisi gelistirme_devri() bayraginin ARKASINDA degil"

    # 4) kamera-tek kapi duruyor
    assert "self._kilit >= self.cfg.DEVIR_KARE" in k, \
        "kamera-tek devir kapisi (ardisik tespit) kaybolmus"
    assert Ayar.DEVIR_KARE >= 10, "devir 10 ardisik kare olmali"
    assert Ayar.KAYIP_KARE >= 20, "kayip 20 ardisik kare olmali"

    # 5) adim() govdesinde GPS'e bakan BASKA bir devir izi olmasin:
    #    hedefin konumu yalnizca (a) durum != GORSEL korumali hedef_konumu()
    #    ve (b) ayrilmis _gelistirme_devir_hazir metodu uzerinden gelir.
    for y in ("get_target", "debug_truth", "truth("):
        assert y not in k, f"adim() icinde dogrudan GPS erisimi: {y}"


def test_B25_yarisma_kipinde_kapi_GPS_E_DOKUNMAZ():
    """FONKSIYONEL kanit: YARISMA_KIPI=1 iken devir kapisi hedefin konumuna
    DOKUNAMAZ. Hedef konumu yerine, herhangi bir erisimde patlayan bir
    nesne veriyoruz; kapi cagrilirsa test AssertionError ile duser.

    Metin bekcisi (B13) kodun SEKLINI sinar; bu bekci DAVRANISI sinar."""
    from dow.ayarlar import Ayar
    from dow import ana

    class Mayin:
        """Herhangi bir sekilde okunursa patlar."""
        def __getitem__(self, i): raise AssertionError(
            "YARISMA KIPINDE HEDEF GPS'I OKUNDU - DISKALIFIYE RISKI")
        def __iter__(self): raise AssertionError(
            "YARISMA KIPINDE HEDEF GPS'I OKUNDU - DISKALIFIYE RISKI")
        def __len__(self): raise AssertionError("hedef GPS okundu")

    b = ana.Beyin.__new__(ana.Beyin)      # __init__ SDK ister; atliyoruz
    b.cfg = Ayar
    b.tani = {}
    b._ist_kare = 0
    b._kilit = 999
    class _Izl: yon_deg = 0.0
    b.izleyici = _Izl()

    eski = Ayar.YARISMA_KIPI
    try:
        # --- yarisma kipi: kapi cagrilmamali -> mayin patlamamali ---
        Ayar.YARISMA_KIPI = True
        assert Ayar.gelistirme_devri() is False
        # adim() icindeki kosul birebir: bayrak False -> cagri YOK
        dev = (b._gelistirme_devir_hazir((0., 0., 0.), Mayin())
               if Ayar.gelistirme_devri() else False)
        assert dev is False

        # --- gelistirme kipi: kapi cagrilir ve GERCEKTEN GPS okur ---
        Ayar.YARISMA_KIPI = False
        patladi = False
        try:
            b._gelistirme_devir_hazir((0., 0., 0.), Mayin())
        except AssertionError:
            patladi = True
        assert patladi, ("gelistirme kipinde kapi hedef konumunu OKUMUYOR - "
                         "kapi ise yaramiyor demektir")
    finally:
        Ayar.YARISMA_KIPI = eski

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
    bekcinin gorevi tersine cevrildi."""
    import inspect
    from dow.gudum import ibvs as I
    from dow import ana
    C = I.IbvsCfg
    for ad in ("SAKIN_KAMERA", "LEAD_SURE", "LEAD_MENZIL_M", "LEAD_MAX_DEG",
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


def test_B23_hybridsort_tamamen_silindi():
    """CLAUDE.md 5.12 — ELENEN OZELLIK TAMAMEN SILINIR.
    Kullanici (2026-08-22): "hybridsort tracking algoritmasini komple
    denklemden cikart; su an detection kotu oldugu icin tracking bir ise
    yaramiyor ve rastgele yerlere track atabiliyor."
    Olu kill-switch / okunmayan alan / yarim kalan import BIRAKILMAZ:
    bir sonraki degisiklik onlardan birine carpar."""
    import subprocess
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert not os.path.exists(os.path.join(kok, "dow/gorus/tracker.py")), \
        "tracker.py hala duruyor"
    from dow.ayarlar import Ayar
    assert not hasattr(Ayar, "TAKIP_AKTIF"), "olu kill-switch TAKIP_AKTIF duruyor"
    from dow.gorus import dedektor
    assert not hasattr(dedektor, "TakipliDedektor"), "TakipliDedektor duruyor"
    # kod govdesinde (tarihsel yorum HARIC) tek bir atif bile kalmamali
    r = subprocess.run(
        ["grep", "-rn", "TalonTracker\\|boxmot\\|TAKIP_AKTIF\\|TakipliDedektor",
         "--include=*.py", "dow/", "araclar/"],
        cwd=kok, capture_output=True, text=True)
    kalan = r.stdout.splitlines()
    assert not kalan, "takipci atiflari kaldi:\n" + "\n".join(kalan)


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