# -*- coding: utf-8 -*-
"""
================================================================================
KİLİT REGÜLATÖRÜ — ÇEVRİMDIŞI KAPALI ÇEVRİM DENEME TEZGÂHI
================================================================================
⛔ BU BİR KANIT ARACI DEĞİLDİR (CLAUDE.md §2). Çevrimdışı benzetim yalnız
   HİPOTEZ üretir; kabul kararını yalnız TAZE UÇUŞ + VİDEO + LOG verir.
   Amacı tek: 20 farklı ayarı 20 uçuşla değil, saniyeler içinde eleyip
   uçuşa YALNIZ makul adayları çıkarmak.

────────────────────────────────────────────────────────────────────────────
ARAÇ MODELİ — hepsi BU DEPODA ÖLÇÜLDÜ, uydurma sabit yok
────────────────────────────────────────────────────────────────────────────
  1. ÇEVİRİCİNİN İÇ DÖNGÜSÜ saf-P'dir (dow/gudum/cevirici.py, K_V = 1.5):
         a_istenen = K_V · (v_komut − v_ölçülen)
     Saf-P kontrolcü KALICI HATA (sarkma) bırakır — integral yok.
  2. ÖLÇÜLDÜ (KILIT16, 16 uçuş, meta.csv + cikarim.csv):
         ISTASYON  komut 33.0 -> gerçekleşen 25.6   açık 7.4 m/s
         GÖRSEL    komut 28.0 -> gerçekleşen 20.6   açık 7.4 m/s
     Sarkmayı sürükleme katsayısı c ile modelliyoruz:
         dv/dt = K_V·(v_komut − v) − c·v
     Kararlı hâl: v = K_V·v_komut/(K_V + c).
     33 -> 25.6 çözülünce  c = 0.434.  Denetim: 28 -> 21.7 (ölçülen 20.6).
     ⚠ Model KABA: tek noktadan kalibre, sürükleme doğrusal varsayıldı.
       Bu yüzden buradan çıkan sayı KARAR değil, ADAY SIRALAMASIDIR.
  3. İvme tavanı 34 m/s² (çeviricinin A_MAX'ı).
  4. Kutu–menzil sabiti: w·R ≈ 869 px·m (76+16 uçuş, ölçüldü).
     Güdüm ise menzili MENZIL_C = 997 ile kuruyor -> denge kutusu
     `997/KILIT_MENZIL_M` piksel; gerçek menzil `869/kutu`.
  5. Tespit boşluğu: karelerin ~%38'inde kutu yok (ölçüldü). Boşlukta
     güdüm SON kutuyu kullanır (köprü) — burada da öyle modellendi.

Kullanım:
    python3 araclar/kilit_sim.py            # aday taraması
    python3 araclar/kilit_sim.py --iz       # seçilen adayın zaman serisi
================================================================================
"""
import argparse
import random

K_V   = 1.5
C_DRAG = 0.434
A_MAX = 34.0
KUTU_C = 869.0          # px·m — GERÇEK
MENZIL_C = 997.0        # px·m — güdümün kullandığı (kalibrasyon farkı KASITLI)
HEDEF_HIZ = 18.0
DT = 0.02               # kontrol tiki 50 Hz
CIKARIM_DT = 0.11       # ~9 Hz
TESPIT_ORANI = 0.62     # ölçüldü
# ⭐⭐ SERT FREN -> KÖRLÜK BAĞI — kullanıcının GÖZLE gördüğü, sonra ÖLÇÜLEN
#   geri besleme. Sert fren komutu çeviricide burun yukarı basamağına
#   dönüşüyor, araç duruşu bir anda değişiyor, kamera savruluyor ve
#   dedektör hedefi kaybediyor.
#   ÖLÇÜLDÜ (KILIT16 A kolu, 139 sert fren olayı):
#     fren sonrası 3 s içinde tespit oranı  %62 -> %18
#     aynı 3 s'te menzil  4.4 m -> 23.5 m  (medyan +18.8 m geri düşüş)
#   Bu bağ modelde YOKKEN model taban ayarını 12/12 kilit sanıyordu;
#   gerçek uçuşta taban 4/8 idi. Bağ eklenince model tabanı DOĞRU
#   üretiyor — modelin sıralamasına ancak ondan sonra güvenilir.
FREN_ESIK    = -40.0    # m/s²; bunun altındaki dv/dt "sert fren"
FREN_KORLUK_S = 3.0     # s; ölçülen körlük penceresi
FREN_TESPIT  = 0.18     # ölçüldü
SURE = 150.0

# Kilit ölçütü (kullanıcı kararı 2026-08-28: eşik %5)
ESIK_PX = 0.05 * 1920   # 96 px
PENCERE = 10.0
GEREKLI = 5.0
DT_MAX = 0.20


class Regulator:
    """KILIT fazı hız regülatörü — sınanan şey BU."""

    def __init__(self, denge_px, k_fwd, i_max, v_min, v_max, slew=None,
                 antiwindup=True, asimetrik=None):
        self.denge_px = denge_px
        self.k_fwd = k_fwd; self.i_max = i_max
        self.v_min = v_min; self.v_max = v_max
        self.slew = slew                  # m/s² tavanı (None = sınırsız)
        self.antiwindup = antiwindup
        self.asimetrik = asimetrik        # (fren_slew, gaz_slew) ya da None
        self.I = 0.0; self.v = 0.0

    def adim(self, kutu, dt):
        hata = self.denge_px - kutu
        ham = self.k_fwd * hata + self.I
        v = max(self.v_min, min(self.v_max, ham))
        # ANTI-WINDUP (koşullu integrasyon): çıkış doyumdayken ve hata
        # doyumu DERİNLEŞTİRİYORKEN integrali dondur. Yoksa integral
        # doyumda şişer, sonra boşalması saniyeler sürer -> aşım.
        doymus = (ham > self.v_max) or (ham < self.v_min)
        if not (self.antiwindup and doymus and (hata > 0) == (ham > self.v_max)):
            self.I = max(-self.i_max, min(self.i_max, self.I + 0.04 * hata * dt))
        # SLEW (değişim hızı tavanı) — "sert fren" doğrudan burada kesilir
        s_fren = s_gaz = self.slew
        if self.asimetrik:
            s_fren, s_gaz = self.asimetrik
        if s_fren is not None:
            dv = v - self.v
            tav = (s_gaz if dv > 0 else s_fren) * dt
            v = self.v + max(-tav, min(tav, dv))
        self.v = v
        return v


def kosu(reg, tohum=0, kayit=False):
    rnd = random.Random(tohum)
    R = 30.0                      # görsel faza ~30 m'de giriyoruz
    v = 20.0                      # gerçekleşen hız
    son_kutu = KUTU_C / R
    t = 0.0; son_cikarim = 0.0
    pencere = []                  # (t, dt, kilitli)
    kum = 0.0; en_iyi = 0.0; saglandi = None
    iz = []; carpma = False; frenler = 0; onceki_vk = None
    son_fren_t = -99.0
    while t < SURE:
        if t - son_cikarim >= CIKARIM_DT:
            son_cikarim = t
            _p = (FREN_TESPIT if (t - son_fren_t) < FREN_KORLUK_S
                  else TESPIT_ORANI)
            if rnd.random() < _p:
                son_kutu = KUTU_C / max(0.3, R)
                kilitli = son_kutu >= ESIK_PX
            else:
                kilitli = False           # köprü kutusu KİLİT SAYILMAZ
            dt_k = min(DT_MAX, CIKARIM_DT)
            pencere.append((t, dt_k, kilitli))
            if kilitli: kum += dt_k
            while pencere and t - pencere[0][0] > PENCERE:
                _t, _d, _k = pencere.pop(0)
                if _k: kum -= _d
            kum = max(0.0, kum)
            en_iyi = max(en_iyi, kum)
            if saglandi is None and kum >= GEREKLI:
                saglandi = t
        vk = reg.adim(son_kutu, DT)
        if onceki_vk is not None and (vk - onceki_vk) / DT < FREN_ESIK:
            frenler += 1; son_fren_t = t
        onceki_vk = vk
        a = max(-A_MAX, min(A_MAX, K_V * (vk - v) - C_DRAG * v))
        v = max(0.0, v + a * DT)
        R = max(0.15, R + (HEDEF_HIZ - v) * DT)
        if R <= 0.9:
            carpma = True; break
        if kayit and abs(t % 1.0) < DT:
            iz.append((t, R, son_kutu, vk, v, kum))
        t += DT
    return {"saglandi": saglandi, "en_iyi": en_iyi, "carpma": carpma,
            "frenler": frenler, "iz": iz, "son_R": R}


def dene(ad, **kw):
    S = [kosu(Regulator(**kw), tohum=i) for i in range(12)]
    n = len(S)
    ok = sum(1 for s in S if s["saglandi"])
    carp = sum(1 for s in S if s["carpma"])
    ei = sorted(s["en_iyi"] for s in S)[n // 2]
    tk = [s["saglandi"] for s in S if s["saglandi"]]
    fr = sorted(s["frenler"] for s in S)[n // 2]
    print("  %-34s kilit %2d/%2d   en_iyi %5.2f s   kilit@ %6s   sert_fren %4d   çarpma %d"
          % (ad, ok, n, ei,
             ("%.1fs" % (sorted(tk)[len(tk)//2])) if tk else "—", fr, carp))
    return ok, ei


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iz", action="store_true")
    a = ap.parse_args()

    TABAN = dict(denge_px=MENZIL_C / 6.0, k_fwd=0.35, i_max=8.0,
                 v_min=0.0, v_max=28.0, slew=None, antiwindup=False)
    if a.iz:
        r = kosu(Regulator(**TABAN), tohum=0, kayit=True)
        print("  t     R      kutu   v_komut  v_gerçek  kilit_s")
        for x in r["iz"][:60]:
            print("  %5.1f %6.2f %6.0f %8.2f %9.2f %8.2f" % x)
        return

    print("=" * 96)
    print("  KİLİT REGÜLATÖRÜ ÇEVRİMDIŞI TARAMA — 12 tohum/aday, eşik %5 (96 px)")
    print("  ⛔ HİPOTEZ ÜRETİR, KARAR VERMEZ (§2)")
    print("=" * 96)

    print("\n  [0] BUGÜNKÜ HAL")
    dene("v1 sert (şu an uçandaki)", **TABAN)

    print("\n  [1] TEK BAŞINA HER DEĞİŞİKLİK")
    dene("+ slew 8 m/s²", **{**TABAN, "slew": 8.0})
    dene("+ v_min 12 m/s", **{**TABAN, "v_min": 12.0})
    dene("+ anti-windup", **{**TABAN, "antiwindup": True})
    dene("+ K_FWD 0.35 -> 0.10", **{**TABAN, "k_fwd": 0.10})
    dene("+ I_MAX 8 -> 22", **{**TABAN, "i_max": 22.0})
    dene("+ V_MAX 28 -> 33", **{**TABAN, "v_max": 33.0})

    print("\n  [2] YUMUŞAK REGÜLATÖR (nazik P + integral yükü taşısın + AW)")
    for kf in (0.06, 0.10, 0.16):
        dene("yumuşak K=%.2f I=22 vmin12 vmax33" % kf,
             denge_px=MENZIL_C / 6.0, k_fwd=kf, i_max=22.0,
             v_min=12.0, v_max=33.0, slew=None, antiwindup=True)

    print("\n  [3] + SLEW (değişim hızı tavanı)")
    for sl in (6.0, 10.0, 20.0):
        dene("yumuşak K=0.10 + slew %.0f m/s²" % sl,
             denge_px=MENZIL_C / 6.0, k_fwd=0.10, i_max=22.0,
             v_min=12.0, v_max=33.0, slew=sl, antiwindup=True)

    print("\n  [4] ASİMETRİK — yavaş fren, hızlı gaz (kullanıcı gözlemi)")
    for fr, gz in ((4.0, 20.0), (6.0, 34.0), (3.0, 12.0)):
        dene("asimetrik fren %.0f / gaz %.0f" % (fr, gz),
             denge_px=MENZIL_C / 6.0, k_fwd=0.10, i_max=22.0,
             v_min=12.0, v_max=33.0, asimetrik=(fr, gz), antiwindup=True)

    print("\n  [5] ⭐ KAZANÇ TARAMASI — yumuşaklığı SLEW sağlar, kazanç YETKİ verir")
    print("      (uçuşta ölçüldü: K=0.10 ile uzaktayken komut 25.2, kapanma +0.6 m/s)")
    for kf in (0.10, 0.18, 0.25, 0.35, 0.50):
        dene("K=%.2f + I22 + vmin12 + vmax33 + slew20" % kf,
             denge_px=MENZIL_C / 7.0, k_fwd=kf, i_max=22.0,
             v_min=12.0, v_max=33.0, slew=20.0, antiwindup=True)

    print("\n  [6] SLEW × KAZANÇ ETKİLEŞİMİ (K=0.35 sabit)")
    for sl in (0.0001, 10.0, 20.0, 40.0, 80.0):
        dene("K=0.35 · slew %5.0f m/s²" % sl,
             denge_px=MENZIL_C / 7.0, k_fwd=0.35, i_max=22.0,
             v_min=12.0, v_max=33.0, slew=sl, antiwindup=True)

    print("\n  [7] DENGE MESAFESİ TARAMASI (K=0.35 · slew 20)")
    for m in (5.0, 6.0, 7.0, 8.0, 9.0):
        dene("denge %.1f m (kutu %3.0f px, gerçek ~%.1f m)"
             % (m, MENZIL_C / m, KUTU_C / (MENZIL_C / m)),
             denge_px=MENZIL_C / m, k_fwd=0.35, i_max=22.0,
             v_min=12.0, v_max=33.0, slew=20.0, antiwindup=True)


if __name__ == "__main__":
    main()
