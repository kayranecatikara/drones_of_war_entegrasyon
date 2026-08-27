# -*- coding: utf-8 -*-
"""ANGAJMAN KAPISI — "yaklaşsın ama çarpmasın" (TEMAS kapısı).

Kullanıcı: kilit için min %6 kaplama YETER, ama çarpışma için drone GİTTİKÇE
YAKLAŞMALI. Yani drone TAM HIZLA, %6'dan temasa kadar SÜREKLİ yaklaşır (durmaz,
standoff yok); kilit kümülatif 5 sn dolana kadar YALNIZ son fiziksel TEMASI
bekletir — temas kenarına (TEMAS_MENZIL_M) gelince tutunur, izin gelince çarpar.

Kanıtlar: (1) %6 kaplamada bile durmaz, yaklaşmaya devam eder; (2) yalnız temas
kenarında tutunur; (3) izin gelince çarpar; (4) hız hiç kısılmaz.
"""
import os

import dow.gudum.ibvs as ibvs
from dow.gudum.ibvs import IbvsCfg, KAM
from dow.ayarlar import Ayar

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GATE = Ayar.TEMAS_MENZIL_M          # temas kenarı kapısı (2 m); ana.py bunu geçer


def _call(boyut_px, takip_menzil):
    """Merkezde `boyut_px` kutu. Döner: (v, menzil_m, takip_kilidi)."""
    (vx, vy), vz, yaw, hiz_I, tani = ibvs.komut(
        960, 540, boyut_px, boyut_px * 0.6, 0.0, 0.0, 0.0,
        hiz_I=0.0, dt=0.1, takip_menzil=takip_menzil)
    return tani["ibvs_v"], tani["ibvs_menzil_m"], tani["ibvs_takip_kilidi"]


# ---------------- GİTTİKÇE YAKLAŞMA (asıl düzeltme) ----------------
def test_yuzde6ta_DURMAZ_yaklasmaya_devam():
    # 120 px ≈ %6.25 kaplama (kilit eşiği), menzil ~8 m > temas.
    # Kilit birikebilir AMA drone burada TUTUNMAZ — temasa kadar yaklaşmaya devam.
    v, R, kilit = _call(120, _GATE)
    assert R > _GATE and v > 0 and kilit == 0

def test_uzakta_tam_hiz():
    v, R, kilit = _call(20, _GATE)                 # ~50 m
    assert v > 0 and kilit == 0


# ---------------- SON TEMAS kapısı ----------------
def test_temas_kenarinda_tutunur_carpmaz():
    v, R, kilit = _call(900, _GATE)                # R ~1.1 m <= temas
    assert R <= _GATE and v == 0.0 and kilit == 1

def test_izin_varken_temasa_dalar():
    v, R, kilit = _call(900, None)                 # izin var -> çarpar
    assert R <= _GATE and v > 0 and kilit == 0


# ---------------- HIZ hiç kısılmıyor ----------------
def test_hiz_KISILMIYOR():
    v_kapi, _, _ = _call(120, _GATE)               # kapı açık, orta menzil
    v_serbest, _, _ = _call(120, None)
    assert abs(v_kapi - v_serbest) < 1e-6          # AYNI hız — kısıtlama yok


# ---------------- bağlantı yerinde mi (kaynak denetimi) ----------------
def _oku(p):
    with open(os.path.join(_KOK, p), encoding="utf-8") as f:
        return f.read()

def test_ana_temas_kapisi_FSM_STRIKE_e_bagli():
    """Angajman (tam dalış) artık FSM STRIKE durumunun türevi (2026-08-27)."""
    k = _oku("dow/ana.py")
    assert "self._fsm_state" in k
    assert "self.cfg.TEMAS_MENZIL_M" in k and "takip_menzil=_tmenzil" in k
    assert "State.STRIKE" in k          # tam hücum yalnız STRIKE'ta

def test_kosu_izni_enjekte_ediyor():
    k = _oku("araclar/kosu.py")
    assert "beyin.angajman_izin = PANEL.angajman_izin()" in k

def test_ayar_kapisi_var():
    assert hasattr(Ayar, "ANGAJMAN_KAPI") and hasattr(Ayar, "TEMAS_MENZIL_M")
