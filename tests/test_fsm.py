# -*- coding: utf-8 -*-
"""GÖREV FSM birim testleri (hamidiyesim'den taşınan mission_fsm).

Şartname akışı: SEARCH→APPROACH→DETECT→TRACK_LOCK→ENGAGE→STRIKE (+TRACK_LOST).
FSM kilit SÜRELERİNİ Girdi'den alır (kendi saymaz) — testte doğrudan verilir.
"""
from dow.fsm.mission_fsm import GorevFSM, Girdi, State


def _fsm():
    return GorevFSM(log_fn=lambda s: None)


def _adim(fsm, t, tespit, anlik, kum=0.0, kes=0.0):
    return fsm.step(Girdi(t=t, tespit_var=tespit, anlik_kilit=anlik,
                          kumulatif_sn=kum, kesintisiz_sn=kes))


def _sur(fsm, t0, sure, tespit, anlik, kum=0.0, kes=0.0, dt=0.05):
    """t0..t0+sure boyunca sabit girdiyle ilerlet; son durumu döndür."""
    t = t0
    st = fsm.durum.state
    n = int(round(sure / dt))
    for i in range(n + 1):
        t = t0 + i * dt
        st = _adim(fsm, t, tespit, anlik, kum, kes)
    return st, t


# ---------------- MUTLU YOL ----------------
def test_search_baslar():
    assert _fsm().durum.state is State.SEARCH

def test_ilk_tespit_APPROACH():
    fsm = _fsm()
    assert _adim(fsm, 0.1, True, False) is State.APPROACH

def test_anlik_kilit_DETECT():
    fsm = _fsm()
    _adim(fsm, 0.1, True, False)          # APPROACH
    assert _adim(fsm, 0.15, True, True) is State.DETECT

def test_dogrulama_TRACK_LOCK():
    fsm = _fsm()
    _adim(fsm, 0.1, True, False)
    _adim(fsm, 0.15, True, True)          # DETECT
    # 0.30 sn doğrulama penceresi + tutarlılık -> TRACK_LOCK
    st, _ = _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)
    assert st is State.TRACK_LOCK

def test_tam_yol_STRIKE():
    fsm = _fsm()
    _adim(fsm, 0.1, True, False)
    _adim(fsm, 0.15, True, True)
    _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)    # TRACK_LOCK
    # kümülatif 5 -> ENGAGE
    st, t = _sur(fsm, 1.0, 0.2, True, True, kum=5.0, kes=5.0)
    assert st is State.STRIKE           # kümül.5 + kesint.3 -> STRIKE


# ---------------- KAPILAR (guard'lar) ----------------
def test_tek_kare_tespit_TRACK_LOCK_OLMAZ():
    """Doğrulama olmadan (anlık tespit) TRACK_LOCK'a geçilmez (şartname 6.1.1)."""
    fsm = _fsm()
    _adim(fsm, 0.1, True, False)
    st = _adim(fsm, 0.12, True, True)     # DETECT (tek kare)
    assert st is State.DETECT             # daha doğrulanmadı

def test_kumulatif_yetmez_ENGAGE_OLMAZ():
    fsm = _fsm()
    _adim(fsm, 0.1, True, False); _adim(fsm, 0.15, True, True)
    _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)   # TRACK_LOCK
    st, _ = _sur(fsm, 1.0, 0.3, True, True, kum=4.0, kes=4.0)  # kümül<5
    assert st is State.TRACK_LOCK         # ENGAGE'e geçmez

def test_kesintisiz_yetmez_STRIKE_OLMAZ():
    """Kümülatif 5 (ENGAGE) ama kesintisiz <3 -> STRIKE YOK."""
    fsm = _fsm()
    _adim(fsm, 0.1, True, False); _adim(fsm, 0.15, True, True)
    _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)   # TRACK_LOCK
    st, _ = _sur(fsm, 1.0, 0.3, True, True, kum=5.0, kes=2.0)  # kümül5, kesint2
    assert st is State.ENGAGE             # ENGAGE evet, STRIKE hayir


# ---------------- KAYIP / KURTARMA ----------------
def test_kilit_kayip_TRACK_LOST():
    fsm = _fsm()
    _adim(fsm, 0.1, True, False); _adim(fsm, 0.15, True, True)
    _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)   # TRACK_LOCK
    # >KILIT_KAYIP_SN (2 sn) anlık kilit yok -> TRACK_LOST
    st, _ = _sur(fsm, 1.0, 2.5, False, False, kum=0.0, kes=0.0)
    assert st is State.TRACK_LOST

def test_track_lost_yeniden_tespit_APPROACH():
    fsm = _fsm()
    _adim(fsm, 0.1, True, False); _adim(fsm, 0.15, True, True)
    _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)
    _sur(fsm, 1.0, 2.5, False, False)     # TRACK_LOST
    assert _adim(fsm, 4.0, True, False) is State.APPROACH

def test_track_lost_STRIKE_e_gitmez():
    """TRACK_LOST'tan asla doğrudan STRIKE'a gidilmez (güvenlik)."""
    fsm = _fsm()
    _adim(fsm, 0.1, True, False); _adim(fsm, 0.15, True, True)
    _sur(fsm, 0.15, 0.5, True, True, kum=0.5, kes=0.5)
    st, _ = _sur(fsm, 1.0, 2.5, False, False)
    # kilit süreleri dolu gelse bile TRACK_LOST'ta STRIKE guard'ı yok
    st2 = _adim(fsm, 4.0, True, True, kum=9.0, kes=9.0)
    assert st2 is State.APPROACH
