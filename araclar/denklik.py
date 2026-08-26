# -*- coding: utf-8 -*-
"""
================================================================================
BİT BİT DENKLİK — bir özellik silinirken güdüm çıktısı DEĞİŞMEMELİ (§5.12)
================================================================================
CLAUDE.md §5.12: "Bit bit denklik: silmeden önceki HEAD ile silinmiş hâl aynı
girdilerde karşılaştırılır; güdüm çıktısı (vx, vy, vz, yaw) BİREBİR AYNI
olmalı. Fark çıkarsa silme sırasında davranış değişmiş demektir — geri al."

NASIL: SDK yerine SAHTE bir bağlantı konur (deterministik, betimlenmiş bir
yörünge), `Beyin.adim()` N tik koşturulur ve her tikin (thr, pitch, roll,
yaw) çıktısı + faz + sayaçlar bir imzaya yazılır.

⚠ RASTGELELİK YASAK: sahte bağlantı tamamen belirlenimcidir (sabit tohum
  yok, çünkü hiç rastgele sayı üretilmiyor). Aynı girdi -> aynı imza.

⚠ BU BİR GÜDÜM TESTİ DEĞİL, DENKLİK TESTİDİR. "Doğru mu uçuyor" sorusunu
  sormaz; "değişiklik davranışı etkiledi mi" sorusunu sorar.

Kullanım:
    python3 araclar/denklik.py yaz  logs/denklik_once.json   # silmeden ÖNCE
    python3 araclar/denklik.py yaz  logs/denklik_sonra.json  # silmeden SONRA
    python3 araclar/denklik.py kiyas logs/denklik_once.json logs/denklik_sonra.json
================================================================================
"""
import json
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


class SahteBaglanti:
    """Belirlenimci sahte SDK. Hedef düz uçar, drone arkadan yaklaşır."""

    def __init__(self):
        self.t = 0.0
        self.komutlar = []

    # --- Beyin'in kullandığı arayüz ---
    def canli(self):
        return True

    def konum(self):
        # drone: 0'dan başlar, hedefe doğru 20 m/s ile kapanır, tırmanır
        return (self.t * 20.0, 0.5 * self.t, 40.0 + min(20.0, 6.0 * self.t))

    def yonelim(self):
        # roll/pitch/yaw (rad) — küçük, belirlenimci salınım
        return (math.radians(3.0 * math.sin(self.t)),
                math.radians(-2.0), math.radians(4.0 * math.sin(0.5 * self.t)))

    def hiz_vektoru(self):
        return (20.0, 0.5, -min(6.0, 6.0 * self.t))

    def komut(self, thr, pitch, roll, yaw, arm):
        self.komutlar.append((thr, pitch, roll, yaw, arm))

    def truth(self):
        # hedef: 120 m ileride, 15 m/s ile aynı yönde
        return {"hedef_m": (120.0 + self.t * 15.0, 0.0, 60.0)}

    def hedef_konum_bozuk(self):
        h = self.truth()["hedef_m"]
        return (h[0], h[1], h[2])


def imza_uret(n_tik=400, dt=0.02):
    """N tik koştur, her tikin çıktısını topla."""
    from dow.ayarlar import Ayar
    from dow import ana
    from dow.gudum import ibvs

    Ayar.GORSEL_AKTIF = True
    Ayar.GPS_KAYNAK = "truth"

    b = ana.Beyin.__new__(ana.Beyin)
    b.cfg = Ayar
    b.b = SahteBaglanti()
    from dow.gudum.cevirici import HizCubukCevirici
    from dow.gudum import gps as GPS
    from dow.gorus.iz import Iz
    import threading
    b.cev = HizCubukCevirici()
    b.izleyici = GPS.HedefIzleyici()
    from dow.fusion.gnss_filtre import GNSSDuzeltici
    b.filtre = GNSSDuzeltici()
    b.det = None
    b._det_ms = 0.0; b._det_pencere = 0; b._son_tespit_kare_t = 0.0
    b._red_konum = 0; b._red_boyut = 0
    b.iz = Iz(); b.iz.sifirla()
    b._kilit_g = threading.RLock()
    b.takip = None; b.kilit = None; b._takip_hata = None
    b._takip_id = -1; b._takip_kaynak = ""; b._takip_coast = -1; b._takip_n = 0
    b.durum = "KALKIS"; b._zemin_z = None
    b._son_tespit = None; b._son_tespit_t = 0.0
    b._bu_kare_tespit = False; b._cikarim_yapildi = True
    b._kopru = None; b._yerel_aday = 0; b._yerel_kayip = 0; b._yerel_uygun = 0
    b._kopru_say = 0; b._bayat_birak_say = 0
    b._terminal_kabul = 0        # Ö-A mekanizma sayacı
    b._son_azimut = None; b._son_azimut_t = None   # Ö-E lead durumu
    b._los_hiz = 0.0
    b._kilit = 0; b._kayip = 0
    b._son_komut = (0.0, 0.0, 0.0, 0.0)
    b.hiz_I = 0.0; b.tani = {}

    kayit = []
    t = 0.0
    for i in range(n_tik):
        b.b.t = t
        # ⚠ TESPİT ENJEKSİYONU: dedektör yok; kutuyu ELLE, belirlenimci
        #   olarak veriyoruz ki görsel faz da sınansın. 40. tikten sonra
        #   hedef "görünür" ve kutu büyür.
        if i >= 40:
            ilerleme = min(1.0, (i - 40) / 200.0)
            w = 20.0 + 60.0 * ilerleme
            cx = 960.0 + 120.0 * math.sin(0.05 * i)
            cy = 540.0 - 40.0 * ilerleme
            b._son_tespit = (cx, cy, w, w * 0.8, 0.85)
            b._son_tespit_t = t
            b._son_tespit_kare_t = t
            b._bu_kare_tespit = True
        else:
            b._bu_kare_tespit = False
        b._cikarim_yapildi = (i % 5 == 0)      # ~10 Hz çıkarım, 50 Hz tik

        cikti = b.adim(t, dt)
        kayit.append({
            "i": i,
            "durum": b.durum,
            "cikti": None if cikti is None else [round(x, 9) for x in cikti],
            "kilit": b._kilit, "kayip": b._kayip,
            "hiz_I": round(b.hiz_I, 9),
        })
        t += dt
    return {"n_tik": n_tik, "dt": dt, "kayit": kayit}


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    if sys.argv[1] == "yaz":
        hedef = sys.argv[2] if len(sys.argv) > 2 else "logs/denklik.json"
        d = imza_uret()
        os.makedirs(os.path.dirname(os.path.join(KOK, hedef)), exist_ok=True)
        with open(os.path.join(KOK, hedef), "w") as f:
            json.dump(d, f)
        fazlar = {}
        for r in d["kayit"]:
            fazlar[r["durum"]] = fazlar.get(r["durum"], 0) + 1
        print("✔ imza yazıldı: %s  (%d tik)" % (hedef, d["n_tik"]))
        print("  faz dağılımı: %s" % fazlar)
        return
    if sys.argv[1] == "kiyas":
        a = json.load(open(os.path.join(KOK, sys.argv[2])))
        b_ = json.load(open(os.path.join(KOK, sys.argv[3])))
        if a["n_tik"] != b_["n_tik"]:
            print("⛔ tik sayısı farklı"); sys.exit(1)
        fark = []
        for x, y in zip(a["kayit"], b_["kayit"]):
            if x != y:
                fark.append((x["i"], x, y))
        if not fark:
            print("✅ BİT BİT AYNI — %d tikin hepsinde güdüm çıktısı, faz ve"
                  " sayaçlar birebir örtüşüyor." % a["n_tik"])
            sys.exit(0)
        print("⛔ %d TİKTE FARK VAR — silme sırasında DAVRANIŞ DEĞİŞTİ."
              % len(fark))
        for i, x, y in fark[:5]:
            print("   tik %d\n     önce : %s\n     sonra: %s" % (i, x, y))
        sys.exit(1)


if __name__ == "__main__":
    main()
