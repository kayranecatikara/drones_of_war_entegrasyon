# -*- coding: utf-8 -*-
"""
================================================================================
DESEN SÜRÜCÜSÜ — hedefi koşu boyunca KARE / DAİRE çizdir
================================================================================
Kullanıcı (2026-08-26): *"bu repodaki kare ve daire çizimini bizede çek ve
aracı bu senaryolarda uçururken de güdüm algoritmalarını test edelim...
dairede vs. görsel güdümle aracı vurabilmeliyiz."*

⛔ `kacamak.py`'DEN FARKI — İKİSİ AYRI ŞEY:
    kacamak.py : hedef kendi rotasında uçar, mesafe 25 m'ye inince
                 devralınır ve BELİRLİ bir manevra 4 s uygulanır.
                 -> ANLIK manevraya tepkiyi ölçer.
    desen.py   : hedef KOŞU BOYUNCA kapalı bir desen çizer.
                 -> SÜREKLİ manevraya tepkiyi ölçer.

  Bu ayrım önemli: KC1 anlık kaçamağı ölçtü ve kaçırmaların sebebinin
  aspekt körlüğü olduğunu gösterdi (kuyrukta %56-74, yanda %6-46).
  Sürekli dönüşte hedef aspekti SÜREKLİ kayar; bu daha zor bir sınav.

⭐ DESEN NEDEN OYUN TARAFINDA SÜRÜLÜYOR
  Geometri UE4SS modunda hesaplanıyor, tarayıcıda/burada değil. Ağ gecikmesi
  ve süreç takılması kenar uzunluğunu bozardı. Modda 30 ms'lik tikle
  ölçülüyor; ölçülmüş: 65 kenar üst üste, hepsi 40.1 m (hedef 40 m).
  Buradan giden tek şey `kip` alanı.

  KARE  : 40 m kenar, 90° sağa, 90°/s köşe dönüşü
  DAİRE : 35 m çap (yarıçap 17.5 m)

⚠ DESEN KİPİNDE joystick eksenleri devre dışı; yalnız THROTTLE geçerli
  (desenin hızını ayarlar). İrtifa mod tarafından sabit tutulur.

⭐ TABAN HIZI 0.405 — KEYFİ DEĞİL: Talon spline üstünde 1800 cm/s uçuyor,
  mod modeli `hız = 300 + throttle*3700` -> (1800-300)/3700 = 0.405.
  Desende de aynı hız korunsun ki senaryolar arasında TEK değişken
  DESENİN KENDİSİ olsun (§4).

⛔ §10 TEMİZ: bu araç HEDEFİ sürer, avcının güdümüne hiç dokunmaz. Ayrı bir
  SÜREÇTİR; `dow/` altındaki güdüm koduna hiçbir şey ithal etmez. Bekçi B55
  bu sınırı kod seviyesinde tutar.

Kullanım:
    python3 araclar/desen.py kare  --ad KD1/kare__t1
    python3 araclar/desen.py daire --ad KD1/daire__t1
    python3 araclar/desen.py taban --ad KD1/taban__t1   (devralma YOK)
================================================================================
"""
import argparse
import json
import os
import signal
import sys
import time
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TABAN_THR = 0.405            # 18 m/s — spline hızıyla eşleşsin

# ad -> mod `kip` değeri.  None = hiç devralma (hedef kendi rotasında)
DESENLER = {
    "taban": None,           # ⭐ KIYAS ÇİZGİSİ — hedef spline rotasında
    "kare":  1,              # 40 m kenar, 90° sağa
    "daire": 2,              # 35 m çap
}


def _post(port, yol, veri, zaman_asimi=1.0):
    r = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, yol),
        data=json.dumps(veri).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(r, timeout=zaman_asimi) as c:
        return json.loads(c.read() or b"{}")


def _get(port, yol, zaman_asimi=1.0):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, yol),
                                timeout=zaman_asimi) as c:
        return json.loads(c.read() or b"{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("desen", choices=sorted(DESENLER))
    ap.add_argument("--ad", default="desen", help="logs/<ad>/desen.json")
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--hz", type=float, default=20.0)
    a = ap.parse_args()

    # kampanya betiği bu süreci `kill` ile durduruyor -> temizlik çalışsın
    signal.signal(signal.SIGTERM,
                  lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    kip = DESENLER[a.desen]
    dizin = os.path.join(KOK, "logs", a.ad)
    os.makedirs(dizin, exist_ok=True)
    olay_yolu = os.path.join(dizin, "desen.json")

    print("=" * 66)
    print("  DESEN: %s" % a.desen.upper())
    if kip is None:
        print("  ⭐ TABAN — hedef DEVRALINMAZ, kendi spline rotasında uçar.")
        print("     Desensiz isabet oranını bilmeden desenli sonuç")
        print("     yorumlanamaz (§3.3 `yok` kolunun karşılığı).")
    else:
        print("  kip=%d · hedef koşu BOYUNCA bu deseni çizer" % kip)
    print("=" * 66, flush=True)

    for _ in range(120):                    # panel gelene kadar bekle
        try:
            _get(a.port, "/telem"); break
        except Exception:
            time.sleep(0.5)
    else:
        print("⛔ panel %d portunda cevap vermedi — kosu.py koşuyor mu?" % a.port)
        sys.exit(1)

    dt = 1.0 / a.hz
    t0 = time.time()
    son_bilgi = 0.0
    # §5.1 MEKANİZMA İZİ — hedefin yörüngesi; desen gerçekten çizildi mi
    iz = []
    try:
        while True:
            simdi = time.time()
            try:
                tel = _get(a.port, "/telem", 0.5)
            except Exception:
                tel = {}

            # hedef konumunu kaydet (truth kanalı; her fazda dolu)
            hx, hy, hz = (tel.get("t_x"), tel.get("t_y"), tel.get("t_z"))
            if hx is None:
                hx, hy, hz = tel.get("h_x"), tel.get("h_y"), tel.get("h_z")
            if hx is not None and len(iz) < 6000:
                iz.append([round(simdi - t0, 2), hx, hy, hz])

            if kip is not None:
                try:
                    _post(a.port, "/api/talon",
                          {"aktif": 1, "throttle": TABAN_THR,
                           "yaw": 0.0, "pitch": 0.0, "roll": 0.0, "kip": kip})
                except Exception as e:
                    if simdi - son_bilgi > 5.0:
                        print("  ⚠ köprüye yazılamadı: %r" % (e,), flush=True)
                        son_bilgi = simdi

            if simdi - son_bilgi > 15.0:
                R = tel.get("gercek_mesafe_m")
                print("  [%6.1fs] %s · menzil %s"
                      % (simdi - t0, a.desen,
                         ("%.1f m" % R) if isinstance(R, (int, float)) else "—"),
                      flush=True)
                son_bilgi = simdi
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        if kip is not None:
            try:                              # kontrolü BIRAK
                _post(a.port, "/api/talon",
                      {"aktif": 0, "throttle": 0.0, "yaw": 0.0,
                       "pitch": 0.0, "roll": 0.0, "kip": 0})
            except Exception:
                pass
        with open(olay_yolu, "w") as f:
            json.dump({"desen": a.desen, "kip": kip, "iz": iz}, f)
        print("\n  hedef izi %d nokta -> %s" % (len(iz), olay_yolu))


if __name__ == "__main__":
    main()
