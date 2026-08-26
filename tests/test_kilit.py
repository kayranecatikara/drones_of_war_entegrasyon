# -*- coding: utf-8 -*-
"""KİLİT KÜMÜLATİF/KESİNTİSİZ + ANGAJMAN İZNİ TESTİ.

Şartname 6.1.4: 10 sn pencerede KÜMÜLATİF >= 5 sn.
Kullanıcı kuralı (2026-08-26): ek olarak EN UZUN KESİNTİSİZ >= 3 sn; ikisi
AYNI pencerede birlikte, kümülatif 5 sn ZORUNLU kapı, 3 sn kesintisiz ek şart.

`_kilit_suresi`/`_kilit_kesintisiz_max` gerçek saat yerine `_kilit_pencere`'nin
son örneğini 'şimdi' alır -> deterministik, sahte zaman çizgisiyle test edilir.
"""
import dow.panel as panel
from dow.panel import (_kilit_suresi, _kilit_kesintisiz_max, angajman_izin,
                       kilit_degerlendir, KILIT_GEREK, KILIT_KESINTISIZ_GEREK)

T0 = 1000.0


def kur(spans, sure, dt=0.1):
    """spans: [(a,b),...] KİLİTLİ aralıklar (sn); gerisi kilitsiz. `sure` sn."""
    panel._kilit_pencere.clear()
    n = int(round(sure / dt))
    for i in range(n + 1):
        t = i * dt
        panel._kilit_pencere.append((T0 + t, any(a <= t < b for a, b in spans)))


def yakin(x, hedef, tol=0.25):
    return abs(x - hedef) <= tol


# ---------------- A) KÜMÜLATİF ----------------
def test_bos_pencere_sifir():
    kur([], 1.0)
    assert _kilit_suresi() == 0.0

def test_araliksiz_3sn_kumulatif():
    kur([(1, 4)], 10.0)
    assert yakin(_kilit_suresi(), 3.0)

def test_araliksiz_5sn_kumulatif_gercekci():
    kur([(1, 6)], 10.0)               # öncesinde kilitsiz kareler var
    assert yakin(_kilit_suresi(), 5.0) and _kilit_suresi() >= KILIT_GEREK

def test_sartname_ornegi_1_2_2_kumulatif_5():
    kur([(1, 2), (3, 5), (6, 8)], 10.0)   # 1+2+2 = 5 kesikli
    assert _kilit_suresi() >= KILIT_GEREK

def test_kesikli_4sn_yetmez():
    kur([(0, 1), (2, 3), (4, 5), (6, 7)], 10.0)
    assert _kilit_suresi() < KILIT_GEREK

def test_pencere_kaymasi_eski_kilit_duser():
    kur([(0, 5)], 14.0)              # son örnek t=14; [0,5) çoğu 10 sn dışında
    assert yakin(_kilit_suresi(), 1.0, 0.3)


# ---------------- B) KESİNTİSİZ ----------------
def test_kesintisiz_max_araliksiz_3sn():
    kur([(1, 4)], 10.0)
    assert yakin(_kilit_kesintisiz_max(), 3.0)

def test_kesintisiz_reset_kopma():
    kur([(1, 3.9), (4.0, 6.9)], 10.0)     # araya kilitsiz kare -> reset
    assert _kilit_kesintisiz_max() < KILIT_KESINTISIZ_GEREK    # ~2.9

def test_kesintisiz_kumulatiften_dusuk():
    kur([(1, 3), (4, 6), (7, 8)], 10.0)   # küm 5, en uzun streak 2
    assert yakin(_kilit_suresi(), 5.0) and yakin(_kilit_kesintisiz_max(), 2.0)


# ---------------- C) KİLİT KAPISI (merkez + kaplama) ----------------
def test_kapi_merkez_buyuk_kilit():
    panel._kilit_pencere.clear()
    kl, av, pct = kilit_degerlendir((960, 540, 200, 120))
    assert kl and av and pct >= 6.0

def test_kapi_merkez_kucuk_yok():
    kl, av, pct = kilit_degerlendir((960, 540, 50, 30))
    assert (not kl) and av and pct < 6.0

def test_kapi_kenar_yok():
    kl, av, pct = kilit_degerlendir((100, 540, 200, 120))
    assert (not kl) and (not av)


# ---------------- D) ANGAJMAN İZNİ = TEK ŞART küm>=5 (kesintisiz kapıda DEĞİL) --
def test_izin_kumulatif3_yok():
    kur([(1, 4)], 10.0)                    # küm 3 < 5
    izin, kum, kes = angajman_izin()
    assert not izin and yakin(kum, 3.0)

def test_izin_kumulatif4_yok():
    kur([(1, 5)], 10.0)                    # küm 4 < 5
    assert not angajman_izin()[0]

def test_izin_kumulatif5_kesikli_var():
    kur([(1, 3), (4, 6), (7, 8)], 10.0)    # küm 5 (kesikli, en uzun 2) -> İZİN
    assert angajman_izin()[0]              # 3 sn kesintisiz ARANMAZ

def test_izin_sartname_ornegi_kabul():
    kur([(1, 2), (3, 5), (6, 8)], 10.0)    # küm 5 (1+2+2) -> İZİN
    assert angajman_izin()[0]

def test_izin_araliksiz_5sn_tek_blok():
    kur([(1, 6)], 10.0)                    # küm 5 aralıksız -> İZİN
    izin, kum, kes = angajman_izin()
    assert izin and yakin(kum, 5.0)

def test_izin_kumulatif6_var():
    kur([(1, 3.5), (4, 6.5), (7, 8)], 10.0)   # küm 6 -> İZİN
    assert angajman_izin()[0]

def test_izin_pencere_kaymasi_yok():
    kur([(0, 3), (11, 14)], 14.0)         # eski düştü, küm 3 kalır -> YOK
    assert not angajman_izin()[0]

def test_kesintisiz_kapiyi_acmaz():
    kur([(1, 5)], 10.0)                    # kes 4>=3 AMA küm 4<5
    izin, kum, kes = angajman_izin()
    assert (not izin) and yakin(kes, 4.0)  # kesintisiz dolu -> yine de izin YOK
