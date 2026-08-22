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


def test_B13_devir_kapisi_YALNIZ_KAMERA():
    """YARISMA KURALI (kullanici 2026-08-22): gorsel gudum sirasinda GPS
    kullanmak DISKALIFIYE sebebi. Devir kapisi da GPS e bakmamali.
    Onceki surum GPS menzilini kapi olarak kullaniyordu; kural netlesince
    KALDIRILDI. Yerine: ardisik kare sayaci + kamera-ici gecerlilik kapisi."""
    import inspect
    from dow import ana
    from dow.ayarlar import Ayar
    k = inspect.getsource(ana.Beyin.adim)
    bas = k.index("kilit_kare")
    devir = k[max(0, bas-900):bas+300]
    for y in ("hedef_konumu", "truth", "get_target", "gps_menzil"):
        assert y not in devir, f"devir kapisinda GPS izi: {y}"
    assert Ayar.DEVIR_KARE >= 10, "devir 10 ardisik kare olmali"
    assert Ayar.KAYIP_KARE >= 20, "kayip 20 ardisik kare olmali"


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


def test_B20_lead_terimi_bagli():
    """OLCULDU (GV02): lead terimi ibvs.komut() a HIC gecilmiyordu.
    Saf takip capraz hedefin gerisinde kaldi: cx 991 -> 1292 (merkez 960),
    sonra tespit koptu. LOS hizi YALNIZ kameradan turetilmeli."""
    import inspect, ast as A, textwrap as T
    from dow import ana
    assert "los_hiz_deg_s=" in inspect.getsource(ana.Beyin.adim), \
        "ibvs.komut() lead terimi ALMIYOR"
    fn = A.parse(T.dedent(inspect.getsource(ana.Beyin._los_hizi))).body[0]
    fn.body = [n for n in fn.body if not (isinstance(n, A.Expr)
               and isinstance(n.value, A.Constant)
               and isinstance(n.value.value, str))]
    kod = A.dump(fn)
    for y in ("hedef_konum", "truth", "get_target"):
        assert y not in kod, f"LOS hizi KODU GPS e erisiyor: {y}"
    assert list(inspect.signature(ana.Beyin._los_hizi).parameters)[1:] == \
        ["azimut_deg", "t"], "LOS hizi fazladan girdi aliyor"


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


def test_B21_isabet_gecersizlik_sayilmaz():
    """OLCUM HATASI: hedefi vurunca drone da yok oluyor -> bekci
    drone_yok diyor ve kosuyu GECERSIZ sayiyordu. Basari, basarisizlik
    gibi isaretleniyordu; istatistik tam da istedigimiz sonucun ALEYHINE
    sistematik saptiriyordu."""
    import inspect
    from araclar import kosu
    k = inspect.getsource(kosu.kosu_yap)
    assert "if isabet and ihlal in" in k, \
        "isabet sonrasi despawn hala gecersizlik sayiliyor"


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