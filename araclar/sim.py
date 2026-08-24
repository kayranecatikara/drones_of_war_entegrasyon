# -*- coding: utf-8 -*-
"""
================================================================================
SİM HAZIRLIĞI — kampanya öncesi oyunu/görevi ayağa kaldır
================================================================================
Gece boyunca insansız çalışmanın önkoşulu. Bugün üç kez elle müdahale
gerekti; her biri ~4 dakika kaybettirdi.

    python3 araclar/sim.py            -> hazır değilse hazırlar, 0/1 döner

DURUMLAR ve ÇARE:
  TCP 12345 açık                    -> hazır, dokunma
  oyun ayakta ama port kapalı       -> drone despawn/görev bitti -> 'E'
  'E' de yetmiyor                   -> görevi BAŞTAN kur (goreve_gir.sh)
  oyun hiç yok                      -> görevi baştan kur
⚠ pkill deseni köşeli parantezle kırılır (CLAUDE.md §9: kendi kabuğunu öldürme)
"""
import os, subprocess, sys, time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _port_acik(p=12345):
    try:
        return subprocess.run(["ss", "-ltn"], capture_output=True, text=True,
                              timeout=5).stdout.find(f":{p}") >= 0
    except Exception:
        return False


def _oyun_var():
    return subprocess.run(["pgrep", "-f", "DronesOfWa[r]-Win64"],
                          capture_output=True).returncode == 0


def _bekle(sn=10, p=12345):
    for _ in range(sn):
        if _port_acik(p):
            return True
        time.sleep(1)
    return False


def _e_bas():
    env = dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":1"))
    try:
        subprocess.run([sys.executable, "-c",
                        "import sys;sys.path.insert(0,%r)\n"
                        "from araclar.kadraj import oyunu_one_al, yeniden_dogur\n"
                        "oyunu_one_al(); yeniden_dogur()" % KOK],
                       cwd=KOK, env=env, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _gorev_kur(zaman_asimi=420):
    betik = os.path.join(KOK, "calistirma_betikleri", "goreve_gir.sh")
    try:
        subprocess.run([betik], cwd=KOK, timeout=zaman_asimi,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  görev kurulamadı: {e}", flush=True)
    return _bekle(20)


def _odakla():
    """⛔ HER DENEMEDEN ÖNCE OYUN PENCERESİNİ ÖNE AL.

    YAŞANDI İKİ KEZ (2026-08-23 ve 24): `goreve_gir.sh` menü tuşlarını
    xdotool ile gönderiyor, ama tuşlar ODAKTAKİ pencereye gider. Bir
    tarayıcı/editör penceresi öndeyse tuşlar oraya düşer ve sim
    "❌ HAZIRLANAMADI" der — oyun aslında sapasağlam açıktır, sadece
    başlık ekranında bekler. Bir kampanya bu yüzden hiç koşmadı.
    """
    try:
        from araclar.kadraj import oyunu_one_al
        oyunu_one_al(); time.sleep(1.0)
    except Exception:
        pass


def hazir_ol(deneme=3):
    """Sim hazır olana kadar yükseltilerek dener. True/False döner."""
    for i in range(deneme):
        if _port_acik():
            return True
        if _oyun_var():
            _odakla()
            print(f"  [sim {i+1}/{deneme}] port kapalı, 'E' deneniyor", flush=True)
            _e_bas()
            if _bekle(8):
                return True
        print(f"  [sim {i+1}/{deneme}] görev baştan kuruluyor (~2 dk)", flush=True)
        if _gorev_kur():
            return True
    return _port_acik()


if __name__ == "__main__":
    ok = hazir_ol()
    print("✅ SİM HAZIR" if ok else "❌ SİM HAZIRLANAMADI", flush=True)
    sys.exit(0 if ok else 1)
