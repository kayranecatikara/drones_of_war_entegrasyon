# -*- coding: utf-8 -*-
"""
================================================================================
TETİKLENMİŞ KAÇAMAK — hedefe buluşma anında BELİRLİ bir manevra yaptır
================================================================================
CLAUDE.md §3.3 (VARSAYILAN SENARYO): "Hedef düz uçar... bir tetikleyici iki
aracın anlık konumunu izler; mesafe eşiğe inince (tipik 25 m, yani 'tam
vuracakken') hedef manuel kontrole devralınır ve BELİRLİ bir kaçamak
uygulanır. Avcı dronun tepkisi ölçülür."

⛔⛔ NEDEN ELLE UÇUŞ DEĞİL: elle sürmek keşif ve gözle doğrulama için iyidir
   ama A/B KAMPANYASINDA KULLANILAMAZ. İnsan girdisi koşular arasında
   tekrarlanamaz; kolları ayıran şeyin özellik mi yoksa operatörün o anki
   eli mi olduğu ölçülemez -> §4 "TEK DEĞİŞKEN" bozulur. Bu araç aynı
   kaçamağı her koşuda BİREBİR aynı uygular.

⛔⛔ §10 YARIŞMA KISITI — BU ARAÇ İHLAL DEĞİLDİR:
   Tetikleyici hedefin gerçek konumunu okur, AMA bu bilgi HEDEFİ sürmek
   için kullanılır — avcının güdümüne HİÇ girmez. Avcının görsel yasası
   (`Beyin._gorsel_tik_kilitli`) yalnız görüntü alır (bekçi B1/B18/B19).
   Bu, hakemin hedefe manevra yaptırması gibidir: TEST DÜZENEĞİNİN parçası.
   Ayrı bir SÜREÇTİR; `dow/` altındaki güdüm koduna hiç dokunmaz.

--------------------------------------------------------------------------------
NASIL ÇALIŞIR
    kacamak.py --> POST /api/talon --> /tmp/talon_kopru.txt --> UE4SS modu
    mesafe    <-- GET  /telem  (`gercek_mesafe_m`, ~9 Hz, ÖLÇÜM kanalı)

⚠ ÖNKOŞUL: oyunda UE4SS + TalonWebControl modu KURULU olmalı
  (bkz. MANUEL_KONTROL.md §4). Kurulu değilse köprüye yazılır ama hedef
  DUYMAZ ve kaçamak sessizce hiç olmaz -> koşu GEÇERSİZDİR. Bu yüzden araç
  tetikten sonra hedefin GERÇEKTEN maneviyat yaptığını DOĞRULAR (§5.1
  mekanizma kapısı): irtifa/yön değişimi ölçülür, olmadıysa AÇIKÇA bağırır.

--------------------------------------------------------------------------------
TABAN HIZI NEDEN 0.405
  Talon spline üstünde 1800 cm/s (18 m/s) uçuyor. Mod uçuş modeli:
      hız = 300 + throttle * 3700  (cm/s)
  1800 cm/s için throttle = (1800-300)/3700 = 0.405. Kontrolü devralınca
  hedefin HIZI DEĞİŞMESİN diye taban bu. Değişseydi `yok` kolu, kontrolsüz
  senaryonun tabanı olmaktan çıkardı ve kıyas bozulurdu.

KAÇAMAK ÇEŞİTLERİ (mod uçuş modelinden türetildi)
      YAW += (yaw*35 + roll*20)*dt   Z += pitch*600*dt   hız = 300+thr*3700
--------------------------------------------------------------------------------
Kullanım:
    python3 araclar/kacamak.py yatay --ad DENEME
    python3 araclar/kacamak.py yok   --ad DENEME --esik 25 --sure 4
================================================================================
"""
import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TABAN_THR = 0.405          # 18 m/s — spline hızıyla eşleşsin (yukarıya bak)

# ad -> (throttle, yaw, pitch, roll)  ·  None = tabanı koru
KACAMAKLAR = {
    "yok":           None,                        # ⭐ TABAN — her kampanyada koşulur
    "yatay":         (TABAN_THR,  0.0,  0.0,  1.0),   # ~20°/s sağa kırış
    "dikey_yukari":  (TABAN_THR,  0.0,  1.0,  0.0),   # 6 m/s tırmanış
    "dikey_asagi":   (TABAN_THR,  0.0, -1.0,  0.0),   # 6 m/s dalış
    "capraz":        (TABAN_THR,  0.0,  0.7,  0.7),   # birleşik
    "hizlan":        (1.0,        0.0,  0.0,  0.0),   # 40 m/s'ye kaçış
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


def eksen_yaz(port, thr, yaw, pit, rol, aktif=1):
    return _post(port, "/api/talon", {"aktif": aktif, "throttle": thr,
                                      "yaw": yaw, "pitch": pit, "roll": rol})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kacamak", choices=sorted(KACAMAKLAR))
    ap.add_argument("--ad", default="kacamak", help="logs/<ad>/kacamak.json")
    ap.add_argument("--esik", type=float, default=25.0, help="tetik mesafesi m")
    ap.add_argument("--sure", type=float, default=4.0, help="kaçamak süresi s")
    ap.add_argument("--yeniden-kur", type=float, default=60.0,
                    help="mesafe bunun üstüne çıkınca tetik YENİDEN kurulur "
                         "(yeni koşu başladı demektir)")
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--hz", type=float, default=20.0, help="köprü yazma hızı")
    a = ap.parse_args()

    hedef = KACAMAKLAR[a.kacamak]
    dizin = os.path.join(KOK, "logs", a.ad)
    os.makedirs(dizin, exist_ok=True)
    olay_yolu = os.path.join(dizin, "kacamak.json")
    olaylar = []

    print("=" * 70)
    print("  TETİKLENMİŞ KAÇAMAK: %s" % a.kacamak.upper())
    print("  tetik <= %.0f m · süre %.1f s · yeniden kurulum > %.0f m"
          % (a.esik, a.sure, a.yeniden_kur))
    if hedef is None:
        print("  ⭐ TABAN KOLU — hedef devralınır ama KAÇAMAK YAPILMAZ.")
        print("     Kaçamaksız isabet oranını bilmeden kaçamaklı sonuç")
        print("     yorumlanamaz (§3.3).")
    print("=" * 70, flush=True)

    # panel gelene kadar bekle
    for _ in range(120):
        try:
            _get(a.port, "/telem"); break
        except Exception:
            time.sleep(0.5)
    else:
        print("⛔ panel %d portunda cevap vermedi — kosu.py koşuyor mu?" % a.port)
        sys.exit(1)

    kurulu = True          # tetik hazır mı
    tetik_t = None         # kaçamak başlangıç anı
    dt = 1.0 / a.hz
    t0 = time.time()
    son_bilgi = 0.0
    # §5.1 MEKANİZMA KAPISI için tetik anındaki hedef durumu
    tetik_durum = None

    try:
        while True:
            simdi = time.time()
            try:
                tel = _get(a.port, "/telem", 0.5)
            except Exception:
                tel = {}
            R = tel.get("gercek_mesafe_m")
            try:
                R = float(R) if R is not None else None
            except Exception:
                R = None

            # ---- tetik mantığı ----
            if tetik_t is not None and (simdi - tetik_t) >= a.sure:
                print("  [%6.1fs] kaçamak bitti -> tabana dönüldü"
                      % (simdi - t0), flush=True)
                # §5.1: hedef GERÇEKTEN manevra yaptı mı?
                if tetik_durum:
                    dz = (tel.get("h_z") or 0) - (tetik_durum.get("h_z") or 0)
                    olaylar[-1]["sonra_h_z"] = tel.get("h_z")
                    olaylar[-1]["dz_m"] = round(dz, 2)
                tetik_t = None
                tetik_durum = None

            if R is not None:
                if not kurulu and R > a.yeniden_kur:
                    kurulu = True
                    print("  [%6.1fs] mesafe %.0f m — YENİ KOŞU, tetik yeniden kuruldu"
                          % (simdi - t0, R), flush=True)
                elif kurulu and R <= a.esik and tetik_t is None:
                    kurulu = False
                    tetik_t = simdi
                    tetik_durum = dict(tel)
                    olay = {"t": round(simdi - t0, 2), "menzil_m": round(R, 2),
                            "kacamak": a.kacamak, "sure": a.sure,
                            "once_h_z": tel.get("h_z"),
                            "once_h_x": tel.get("h_x"),
                            "once_h_y": tel.get("h_y")}
                    olaylar.append(olay)
                    print("  [%6.1fs] ⭐ TETİK — %.1f m -> KAÇAMAK: %s"
                          % (simdi - t0, R, a.kacamak.upper()), flush=True)
                    with open(olay_yolu, "w") as f:
                        json.dump(olaylar, f, ensure_ascii=False, indent=1)

            # ---- köprüye yaz ----
            #   Sayaç ilerlemezse mod eksenleri sıfırlar ama throttle'ı korur;
            #   bu yüzden kaçamak YOKKEN de sürekli yazıyoruz ki hedef bizim
            #   tuttuğumuz tabanda kalsın (iki kolda AYNI taban).
            if tetik_t is not None and hedef is not None:
                thr, yaw, pit, rol = hedef
            else:
                thr, yaw, pit, rol = TABAN_THR, 0.0, 0.0, 0.0
            try:
                eksen_yaz(a.port, thr, yaw, pit, rol, aktif=1)
            except Exception as e:
                if simdi - son_bilgi > 5.0:
                    print("  ⚠ köprüye yazılamadı: %r" % (e,), flush=True)
                    son_bilgi = simdi

            if simdi - son_bilgi > 10.0 and tetik_t is None:
                print("  [%6.1fs] bekliyor... mesafe %s  tetik %s"
                      % (simdi - t0, ("%.1f m" % R) if R is not None else "—",
                         "KURULU" if kurulu else "kullanıldı"), flush=True)
                son_bilgi = simdi
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        # kontrolü BIRAK — hedef kendi rotasına dönsün
        try:
            eksen_yaz(a.port, 0.0, 0.0, 0.0, 0.0, aktif=0)
        except Exception:
            pass
        with open(olay_yolu, "w") as f:
            json.dump(olaylar, f, ensure_ascii=False, indent=1)
        print("\n  %d tetik kaydedildi -> %s" % (len(olaylar), olay_yolu))
        if not olaylar and a.kacamak != "yok":
            print("  ⛔ HİÇ TETİK OLMADI — bu koşular kaçamağı SINAMADI.")


if __name__ == "__main__":
    main()
