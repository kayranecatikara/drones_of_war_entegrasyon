# -*- coding: utf-8 -*-
"""
================================================================================
KANAT TESTİ — `isDead` hedefin görünüşünü bozuyor mu, bırakınca düzeliyor mu?
================================================================================
KULLANICI (2026-08-27): *"talonun bazı uçuşlarda kanatları yok oluyor o neden
acaba, detection modelinin tespitini de kötüleştirir bu."*

GÖZLE DOĞRULANDI (KD1 kareleri, aynı ~11 m menzil):
  taban  (devralma YOK)  -> net uçak silueti, kanatlar açık
  daire  (isDead=true)   -> KANATSIZ koyu gövde + kopmuş gibi parlak çizgi

MANUEL_KONTROL.md bu riski not etmiş ama ÖLÇMEMİŞ:
  *"isDead=true yan etkisi: oyunun gözünde Talon'u 'düşmüş' saydırabilir...
    Kapatınca geri düzeliyor, ama bu AYRICA DOĞRULANMADI."*

Bu araç o boşluğu kapatır: TEK uçuşta kontrolü AÇIP KAPATARAK, aynı sahnede,
eşleştirilmiş ölçüm yapar. Menzil ve aspekt iki durumda da benzer kalır.

⛔ NEDEN ESKİ LOGLARDAN ÇIKMIYOR: kaçamak koşularında devralma tetikten
   SONRA sürüyor, yani "önce/sonra" aynı zamanda "uzak/yakın" demek —
   menzil karıştırıcısı ayrılamıyor (denendi: 20-30 m'de devralınan daha
   İYİ, 30-40 m'de daha kötü, n=31; sinyal yok).

Kullanım (kosu.py AYRI terminalde koşarken):
    python3 araclar/kanat_testi.py --tur 6 --sure 5
================================================================================
"""
import argparse
import json
import os
import statistics as st
import sys
import time
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABAN_THR = 0.405


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
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--tur", type=int, default=6, help="aç/kapa tur sayısı")
    ap.add_argument("--sure", type=float, default=5.0, help="her durum kaç s")
    ap.add_argument("--basla", type=float, default=45.0,
                    help="menzil bunun altına inince ölçüme başla")
    a = ap.parse_args()

    for _ in range(240):
        try:
            _get(a.port, "/telem"); break
        except Exception:
            time.sleep(0.5)
    else:
        print("⛔ panel cevap vermedi — kosu.py koşuyor mu?"); sys.exit(1)

    print("  menzil < %.0f m olmasını bekliyorum..." % a.basla, flush=True)
    t0 = time.time()
    while time.time() - t0 < 180:
        try:
            R = _get(a.port, "/telem", 0.5).get("gercek_mesafe_m")
        except Exception:
            R = None
        if isinstance(R, (int, float)) and R < a.basla:
            break
        time.sleep(0.3)
    print("  başlıyor (menzil %s m)\n" % R, flush=True)

    sonuc = {"acik": [], "kapali": []}      # (tespit?, menzil, kutu)
    for tur in range(a.tur):
        for durum, aktif in (("kapali", 0), ("acik", 1)):
            t1 = time.time()
            n = ok = 0
            mz = []
            ku = []
            while time.time() - t1 < a.sure:
                try:
                    _post(a.port, "/api/talon",
                          {"aktif": aktif, "throttle": TABAN_THR,
                           "yaw": 0.0, "pitch": 0.0, "roll": 0.0, "kip": 0})
                except Exception:
                    pass
                try:
                    t = _get(a.port, "/telem", 0.4)
                except Exception:
                    t = {}
                R = t.get("gercek_mesafe_m")
                w = t.get("vis_w")
                yas = t.get("vis_yas")
                if isinstance(R, (int, float)):
                    n += 1
                    mz.append(R)
                    # taze kutu = son 0.25 s içinde gerçek tespit
                    if isinstance(yas, (int, float)) and yas <= 0.25:
                        ok += 1
                        if isinstance(w, (int, float)):
                            ku.append(w)
                time.sleep(0.12)
            if n:
                sonuc[durum].append((ok / n, st.median(mz),
                                     st.median(ku) if ku else float("nan")))
                print("  tur %d · kontrol %-6s tespit %%%3.0f · menzil %5.1f m · kutu %s"
                      % (tur + 1, "AÇIK" if aktif else "kapalı",
                         100 * ok / n, st.median(mz),
                         ("%.0f px" % st.median(ku)) if ku else "—"),
                      flush=True)

    try:
        _post(a.port, "/api/talon", {"aktif": 0, "throttle": 0.0, "yaw": 0.0,
                                     "pitch": 0.0, "roll": 0.0, "kip": 0})
    except Exception:
        pass

    print("\n" + "=" * 64)
    for d, ad in (("kapali", "KONTROL KAPALI (kanat VAR)"),
                  ("acik", "KONTROL AÇIK (isDead)")):
        v = sonuc[d]
        if not v:
            continue
        print("  %-28s tespit %%%.0f · menzil %.1f m · kutu %s"
              % (ad, 100 * st.median([x[0] for x in v]),
                 st.median([x[1] for x in v]),
                 ("%.0f px" % st.median([x[2] for x in v if x[2] == x[2]]))
                 if any(x[2] == x[2] for x in v) else "—"))
    if sonuc["acik"] and sonuc["kapali"]:
        ka = st.median([x[0] for x in sonuc["kapali"]])
        ac = st.median([x[0] for x in sonuc["acik"]])
        print("\n  SONUÇ: %s"
              % ("⛔ isDead TESPİTİ BOZUYOR (%.0f -> %.0f puan)"
                 % (100 * ka, 100 * ac) if ka - ac > 0.15 else
                 "✅ belirgin fark YOK — isDead tespiti bozmuyor"))
    print("=" * 64)


if __name__ == "__main__":
    main()
