# -*- coding: utf-8 -*-
"""
================================================================================
KADEMELİ MANEVRA — yakında HAFİF, görsel fazda SERT
================================================================================
KULLANICI (2026-08-27): *"hedef araç ile drone arasındaki mesafe yakınken
hedef araca hafif, görsel güdüm fazındayken sert manevralar yaptırıp
droneun bu manevralara karşı nasıl reaksiyon verdiğini test edelim."*
Ayrıca: *"kare ve daire senaryoları hiç gerçeğe uygun değil, çok zor."*

⛔ KARE/DAİRE'DEN FARKI — VE NEDEN BU DAHA GERÇEKÇİ:
  Desen araçları hedefi KOŞU BOYUNCA devralıp kapalı bir şekil çizdiriyordu.
  Bu hem gerçekçi değil hem de hedefi sürekli YATIK tutuyordu. Burada hedef
  çoğu zaman KENDİ ROTASINDA uçar; yalnız iki anda, kısa süreliğine
  devralınır.

⭐⭐ NEDEN YATIŞ SINIRI VAR — 2026-08-27'de ÖLÇÜLDÜ VE GÖZLE DOĞRULANDI:
  Hedef sert yattığında kanatlar kameraya KENARDAN gelir ve siluet ince bir
  çizgiye iner. Kullanıcının *"kanatları yok oluyor"* dediği şey budur.
  Aynı ~10 m menzilde karşılaştırıldı:
      hedef yatışı  4.9°  -> NET uçak silueti (kanatlar açık)
      hedef yatışı 33-60° -> KANATSIZ koyu leke
  Ölçülen tespit (kadrajda ve 10-25 m): düz %90 · 25-40° %49 · 40°+ %52.

  ⚠ SUÇLU `isDead` DEĞİL: kontrol AÇIKKEN hedef DÜZ uçarken kanatlar
    yerindeydi (2026-08-27 taze kare). Yani kısa devralma modeli bozmuyor;
    bozan şey MANEVRANIN KENDİSİNİN gerektirdiği yatış.

  Bu yüzden şiddetler yatış tavanına göre seçildi (kullanıcı kararı):
      HAFİF : roll 0.35 -> ~7°/s dönüş, yatış ~20°  (hedef GÖRÜNÜR kalır)
      SERT  : roll 0.70 -> ~14°/s dönüş, yatış ~35° (tespit düşer ama
              araç hedefi tamamen kaybetmez -> güdümün tepkisi ÖLÇÜLEBİLİR)
  Kalibrasyon: mod uçuş modeli `YAW += roll*20 °/s`, görsel yatış `roll*45°`
  (2026-08-26'da simde ölçüldü: roll 1.0 -> 19.4°/s, doğrusal).

--------------------------------------------------------------------------------
ÜÇ EVRE
  1. menzil > YAKIN_M            -> aktif=0 · hedef KENDİ ROTASINDA
  2. menzil <= YAKIN_M, faz≠GORSEL -> HAFİF manevra
  3. faz == GORSEL                -> SERT manevra
  Evre 1'e dönülürse kontrol BIRAKILIR (kanatlar sağlam kalsın).

⛔ §10: bu araç HEDEFİ sürer; avcının güdümüne hiç dokunmaz. Ayrı süreçtir
   ve `dow/` altındaki güdüm kodunu ithal etmez (bekçi B55).

Kullanım:
    python3 araclar/manevra.py kademeli --ad KM1/kademeli__t1
    python3 araclar/manevra.py yok      --ad KM1/yok__t1
================================================================================
"""
import argparse
import json
import math
import os
import signal
import sys
import time
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABAN_THR = 0.405              # 18 m/s — spline hızıyla eşleşir

HAFIF_ROLL = 0.35              # ~7°/s dönüş, yatış ~20°
SERT_ROLL = 0.70               # ~14°/s dönüş, yatış ~35°

# ⭐⭐ MANEVRA YÖNÜ AVCIDAN UZAĞA — 2026-08-27, KM1'de ölçülen kusurun çaresi.
#   KM1'de yön SABİTTİ (hep sağa) ve senaryo TUTARSIZ çıktı: manevralı
#   süreler 9.5 · 65.2 · 26.8 · 10.8 s. Üçü tabandan HIZLI, biri felaket.
#   Sebep geometri: sabit yön bazen hedefi avcıya DOĞRU çeviriyor, yani
#   manevra bazen İŞİMİZİ KOLAYLAŞTIRIYOR. Kaçamak sayılmaz.
#   Çare: her manevrada avcının hedefe göre bağıl kerterizi hesaplanır ve
#   hedef TERS yöne döndürülür.
#
#   İŞARET (simde ölçüldü 2026-08-26): mod `YAW += roll*20 °/s` ve
#   `X += cos(YAW)*v, Y += sin(YAW)*v` -> POZİTİF roll YAW'ı ARTIRIR,
#   yani +x'ten +y'ye doğru (saat yönünün TERSİ) döndürür.
#   Avcı hedefin SOLUNDAYSA (bağıl kerteriz > 0) saat yönü tersi ona DOĞRU
#   gider -> ters yön seçilir.  roll = -sign(bağıl) * şiddet
#
#   ⛔ §10: bu hesap HEDEFİ sürer; avcının güdümü bu bilgiyi GÖRMEZ.
#      Hakemin hedefe manevra yaptırması gibidir (bekçi B55).
YON_UZAGA = True


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
    ap.add_argument("kip", choices=["kademeli", "yok"])
    ap.add_argument("--ad", default="manevra")
    ap.add_argument("--yakin", type=float, default=45.0,
                    help="hafif manevranın başladığı menzil (m)")
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--hz", type=float, default=20.0)
    a = ap.parse_args()

    signal.signal(signal.SIGTERM,
                  lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    dizin = os.path.join(KOK, "logs", a.ad)
    os.makedirs(dizin, exist_ok=True)
    olay_yolu = os.path.join(dizin, "manevra.json")

    print("=" * 66)
    print("  KADEMELİ MANEVRA: %s" % a.kip.upper())
    if a.kip == "yok":
        print("  ⭐ TABAN — hedef HİÇ devralınmaz, kendi rotasında uçar.")
        print("     Manevrasız sonucu bilmeden manevralı sonuç yorumlanamaz.")
    else:
        print("  menzil <= %.0f m ve faz≠GORSEL -> HAFİF (roll %.2f, ~20° yatış)"
              % (a.yakin, HAFIF_ROLL))
        print("  faz == GORSEL                  -> SERT  (roll %.2f, ~35° yatış)"
              % SERT_ROLL)
        print("  aksi halde                     -> BIRAK (hedef kendi rotasında)")
    print("=" * 66, flush=True)

    for _ in range(240):
        try:
            _get(a.port, "/telem"); break
        except Exception:
            time.sleep(0.5)
    else:
        print("⛔ panel cevap vermedi — kosu.py koşuyor mu?"); sys.exit(1)

    dt = 1.0 / a.hz
    t0 = time.time()
    son_evre = None
    son_bilgi = 0.0
    olaylar = []          # (t, evre, menzil)
    sayac = {"bos": 0, "hafif": 0, "sert": 0}
    hedef_iz = []         # (t, hx, hy) — hedefin yönünü kestirmek için
    yon_isaret = 1.0      # evre başında seçilir, evre boyunca SABİT kalır

    try:
        while True:
            simdi = time.time()
            try:
                tel = _get(a.port, "/telem", 0.5)
            except Exception:
                tel = {}
            R = tel.get("gercek_mesafe_m")
            faz = str(tel.get("durum", "") or "")
            try:
                R = float(R) if R is not None else None
            except Exception:
                R = None

            if a.kip == "yok":
                evre = "bos"
            elif faz.startswith("GORSEL"):
                evre = "sert"
            elif R is not None and R <= a.yakin:
                evre = "hafif"
            else:
                evre = "bos"
            sayac[evre] += 1

            # --- hedefin yörüngesini izle (yön kestirimi için) ---
            hx = tel.get("t_x") if tel.get("t_x") is not None else tel.get("h_x")
            hy = tel.get("t_y") if tel.get("t_y") is not None else tel.get("h_y")
            dx_, dy_ = tel.get("d_x"), tel.get("d_y")
            if hx is not None and hy is not None:
                hedef_iz.append((simdi, hx, hy))
                if len(hedef_iz) > 40:
                    hedef_iz.pop(0)

            if evre != son_evre:
                # ⭐ YÖN SEÇİMİ — evre BAŞINDA bir kez, sonra sabit.
                #   Evre içinde her tikte yeniden hesaplamak, hedef dönerken
                #   işareti çevirip manevrayı ZIKZAK yapardı.
                if evre != "bos" and YON_UZAGA and len(hedef_iz) >= 5 \
                        and dx_ is not None and dy_ is not None:
                    _t, _x0, _y0 = hedef_iz[0]
                    _, _x1, _y1 = hedef_iz[-1]
                    if (abs(_x1 - _x0) + abs(_y1 - _y0)) > 1.0:
                        h_yon = math.atan2(_y1 - _y0, _x1 - _x0)
                        av_ker = math.atan2(dy_ - _y1, dx_ - _x1)
                        bagil = (av_ker - h_yon + math.pi) % (2 * math.pi) - math.pi
                        yon_isaret = -1.0 if bagil > 0 else 1.0
                olaylar.append({"t": round(simdi - t0, 2), "evre": evre,
                                "menzil": R, "faz": faz,
                                "yon": yon_isaret})
                print("  [%6.1fs] evre -> %-6s  menzil %s  faz %-9s yön %s"
                      % (simdi - t0, evre.upper(),
                         ("%.1f m" % R) if R is not None else "—", faz or "—",
                         "SAĞ" if yon_isaret < 0 else "SOL"),
                      flush=True)
                son_evre = evre

            if evre == "bos":
                akt, thr, rol = 0, 0.0, 0.0
            elif evre == "hafif":
                akt, thr, rol = 1, TABAN_THR, HAFIF_ROLL * yon_isaret
            else:
                akt, thr, rol = 1, TABAN_THR, SERT_ROLL * yon_isaret
            try:
                _post(a.port, "/api/talon",
                      {"aktif": akt, "throttle": thr, "yaw": 0.0,
                       "pitch": 0.0, "roll": rol, "kip": 0})
            except Exception as e:
                if simdi - son_bilgi > 5.0:
                    print("  ⚠ köprüye yazılamadı: %r" % (e,), flush=True)
                    son_bilgi = simdi
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            _post(a.port, "/api/talon", {"aktif": 0, "throttle": 0.0,
                                         "yaw": 0.0, "pitch": 0.0,
                                         "roll": 0.0, "kip": 0})
        except Exception:
            pass
        with open(olay_yolu, "w") as f:
            json.dump({"kip": a.kip, "olaylar": olaylar, "sayac": sayac}, f)
        top = max(1, sum(sayac.values()))
        print("\n  evre payları: boş %%%.0f · hafif %%%.0f · sert %%%.0f"
              % (100 * sayac["bos"] / top, 100 * sayac["hafif"] / top,
                 100 * sayac["sert"] / top))
        print("  %d evre geçişi -> %s" % (len(olaylar), olay_yolu))
        if a.kip == "kademeli" and sayac["sert"] == 0:
            print("  ⛔ SERT evre HİÇ olmadı — görsel faza girilmemiş, "
                  "bu koşu manevrayı SINAMADI.")


if __name__ == "__main__":
    main()
