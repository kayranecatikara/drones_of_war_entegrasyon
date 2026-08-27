# -*- coding: utf-8 -*-
"""
================================================================================
VURUŞ KALİTESİ — her vuruş "kontrollü vuruş" değildir (§4)
================================================================================
KURAL (CLAUDE.md §4): *"Temas anı ve ÖNCESİNDEKİ kareler tek tek incelenir
ve vuruş sınıflandırılır. Şans vuruşu isabet sayılır ama İYİLEŞME KANITI
SAYILMAZ."*

Dengesizce savrulup şans eseri çarpan bir araç, isabet sayısını yükseltir
ama sistemi iyileştirmez. Bir kolun kazandığını söylemeden önce vuruşların
NİTELİĞİ ayrılmalıdır.

ÖLÇÜTLER — vuruş anından geriye `--pencere` saniye (varsayılan 2.0 s):

  1. SÜREKLİLİK   : karelerin >= %70'inde taze kutu var
  2. MERKEZDE     : |cx-960| medyanı <= 250 px
  3. SAKİN NİŞAN  : cx işaret değişimi <= 2 (savrulmuyor)
  4. DÜZGÜN BÜYÜME: kutu boyutu monoton artıyor (son >= ilk × 1.3)
  5. SAKİN ARAÇ   : |drone yatış| p90 <= 35°

Beşinin HEPSİ sağlanırsa KONTROLLÜ, değilse ŞANS.

⛔ EŞİK KATILIĞI UYARISI (§5.6): bu eşikler bir kolun LEHİNE
   ayarlanmamalıdır. Daha önce yaşandı: bir vuruş altı ölçütten BEŞİNİ
   geçmişti ve tek takıldığı 1 kopuk kareydi; eşik fazla katı diye
   raporlandı, sonucu çevirmek için değiştirilMEDİ. Aynı disiplin geçerli:
   sınıflandırıcı bir sonucu senin önerdiğin özelliğin lehine çeviriyorsa
   ÖNCE sınıflandırıcıyı sorgula.

⚠ Arka kareler (hedefin üstünden geçtikten sonrası) payda dışıdır.

Kullanım: python3 araclar/vurus_kalitesi.py logs/KN1
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)
from araclar.arka import ArkaBekci


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def _isabet_var(d):
    """`ozet.csv`'deki yerleşik iki imzalı ölçüt. Yok/okunamıyorsa None."""
    y = os.path.join(d, "ozet.csv")
    if not os.path.exists(y):
        return None
    try:
        r = list(csv.DictReader(open(y)))[0]
        return int(r.get("isabet") or 0) == 1
    except Exception:
        return None


def kosu_sinifla(d, pencere=2.0):
    y = os.path.join(d, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return None
    _is = _isabet_var(d)
    if _is is False:
        return {"ad": os.path.basename(d), "vurus": False}
    ab = ArkaBekci(d)
    R = []
    for r in csv.DictReader(open(y)):
        t = _f(r, "t")
        m = _f(r, "menzil3_m") or _f(r, "menzil_m")
        if None in (t, m):
            continue
        R.append((t, m, r.get("basarili") == "1", _f(r, "vis_cx"),
                  _f(r, "vis_w"), _f(r, "drone_roll")))
    if len(R) < 20:
        return None
    # ⛔ VURUŞ VAR MI SORUSUNU BU ARAÇ CEVAPLAMAZ — `ozet.csv`'deki
    #   `isabet` cevaplar. O ölçüt deponun yerleşik, İKİ İMZALI ölçütüdür
    #   (pervane sekmesi = ivme sıçraması, VEYA temas menzilinde anında
    #   imha) ve kullanıcı kararıyla kalibre edilmiştir.
    #   ⚠ YAŞANDI: burada ÜÇÜNCÜ bir vuruş tanımı uydurdum ve üç kaynak
    #   birbirini tutmadı (kapali t4/t6: ozet isabet=0 ama benim kuralım
    #   "vuruş" diyordu). Kendi tanımını uydurmak, ölçütü sessizce
    #   kaydırır. Bu araç YALNIZ `isabet=1` koşularda KALİTE sınıflar.
    #
    # VURUŞ ANI İKİ İMZALI — TEK İMZA EN TEMİZ VURUŞLARI KAÇIRIR.
    #   YAŞANDI (KN1): acik__t3 ve t6 "VURUŞ YOK" sayıldı; oysa ozet.csv
    #   ikisine de imha=1 diyordu. Sebep: koşu TAM temas anında bitiyor,
    #   dolayısıyla menzil SIÇRAMASI görünmüyor (sıçramayı görmek için
    #   vuruştan SONRA kare gerekir). `kosu.py` bu tuzağı zaten
    #   belgelemişti: "Bu imza EKSİKTİ ve en temiz vuruşları kaçırıyordu".
    #   Tek imzayla ölçmek, en temiz vuruşları elediği için kaliteyi
    #   TEMİZ KOLUN ALEYHİNE çarpıtır.
    #   İMZA 1: menzil sıçraması (hedef despawn, koşu devam ediyor)
    #   İMZA 2: koşu EN YAKIN anda bitti ve o menzil temas yarıçapında
    vur = None
    for i in range(len(R) - 1):
        if R[i + 1][1] - R[i][1] >= 10.0:
            vur = i
            break
    if vur is None and R[-1][1] <= 2.0:
        # İMZA 2 — koşu TEMAS MENZİLİNDE bitti (drone da yok oldu).
        #   ⚠ "genel minimum" DEĞİL, SON KARE: aynı menzile birden çok
        #   geçişte inilebiliyor ve min() ilkini seçip 9.6 s önceki bir
        #   geçişi işaret ediyordu (KN1/acik__t6: 0.90 m hem t=15.9'da
        #   hem koşu sonunda t=25.5'te). Vuruş, koşuyu BİTİREN geçiştir.
        vur = len(R) - 1
    if vur is None:
        return {"ad": os.path.basename(d), "vurus": False}
    t0 = R[vur][0]
    pen = [x for x in R[max(0, vur - 200):vur + 1]
           if t0 - pencere <= x[0] <= t0 and not (ab.var and ab.arkada(x[0]))]
    if len(pen) < 8:
        return {"ad": os.path.basename(d), "vurus": True, "sinif": "ÖLÇÜLEMEDİ"}
    kut = [x for x in pen if x[2] and x[3] is not None]
    sur = len(kut) / len(pen)
    cx = [abs(x[3] - 960.0) for x in kut]
    isar = [x[3] - 960.0 for x in kut]
    don = sum(1 for i in range(len(isar) - 1) if isar[i] * isar[i + 1] < 0)
    w = [x[4] for x in kut if x[4]]
    buy = (w[-1] >= w[0] * 1.3) if len(w) >= 3 else False
    rl = sorted(abs(x[5]) for x in pen if x[5] is not None)
    rp90 = rl[int(0.9 * (len(rl) - 1))] if rl else 0.0
    kos = {"süreklilik": sur >= 0.70,
           "merkezde": bool(cx) and st.median(cx) <= 250.0,
           "sakin nişan": don <= 2,
           "düzgün büyüme": buy,
           "sakin araç": rp90 <= 35.0}
    return {"ad": os.path.basename(d), "vurus": True,
            "sinif": "KONTROLLÜ" if all(kos.values()) else "ŞANS",
            "kos": kos,
            "sayi": (sur, st.median(cx) if cx else -1, don,
                     (w[-1] / w[0]) if len(w) >= 3 and w[0] else -1, rp90)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kok", nargs="?", default="logs/KN1")
    ap.add_argument("--pencere", type=float, default=2.0)
    a = ap.parse_args()
    # İKİ ADLANDIRMA DÜZENİ DESTEKLENİR:
    #   A/B kampanyaları  : "<kol>__t<N>"          (kol = "__" öncesi)
    #   gece/karma        : "<NN>_<kol>[__<senaryo>]"  (kol = ilk "_" sonrası)
    #
    # ⛔ İKİSİ DE ARANIR, "ilki bulduysa dur" YAPILMAZ — 2026-08-27'de tam bu
    #   hata oldu: `logs/HZ2` dizini ÖNCEDEN VARDI ve içinde eski bir
    #   kampanyanın BOŞ koşu klasörleri duruyordu (`0_0_0_10__t1` …).
    #   Birinci desen onlara takıldı, yeni koşular hiç görülmedi ve §4'ün
    #   zorunlu vuruş sınıflandırması SESSİZCE 0/0 rapor etti.
    # ⛔ VERİSİ OLMAYAN DİZİN ALINMAZ: k01/cikarim.csv yoksa o klasör bir
    #   koşu değildir (yarıda kesilmiş ya da başka bir şeyin kalıntısıdır).
    kollar = {}
    _adaylar = (glob.glob(os.path.join(KOK, a.kok, "*__t*"))
                + glob.glob(os.path.join(KOK, a.kok, "[0-9][0-9]_*")))
    for d in sorted(set(_adaylar)):
        if not os.path.exists(os.path.join(d, "k01", "cikarim.csv")):
            continue
        ad = os.path.basename(d)
        kol = (ad.split("__")[0] if "__t" in ad
               else (ad.split("_", 1)[1] if "_" in ad else ad))
        kollar.setdefault(kol, []).append(d)
    if not kollar:
        print("⛔ koşu yok: %s" % a.kok)
        return
    print("\n" + "=" * 76)
    print("  VURUŞ KALİTESİ — %s (vuruş anından geriye %.1f s)" % (a.kok, a.pencere))
    print("=" * 76)
    print("\n  %-14s %-12s %8s %9s %7s %8s %8s"
          % ("koşu", "sınıf", "süreklk", "|cx-960|", "dönüş", "büyüme", "yatışp90"))
    print("  " + "-" * 72)
    OZ = {}
    for kol in sorted(kollar):
        R = [x for x in (kosu_sinifla(d, a.pencere) for d in kollar[kol]) if x]
        OZ[kol] = R
        for x in R:
            if not x["vurus"]:
                print("  %-14s %-12s" % (x["ad"], "VURUŞ YOK"))
            elif x.get("sayi"):
                s = x["sayi"]
                print("  %-14s %-12s %7.0f%% %8.0f %7d %7.2fx %7.0f°"
                      % (x["ad"], x["sinif"], 100 * s[0], s[1], s[2], s[3], s[4]))
            else:
                print("  %-14s %-12s" % (x["ad"], x["sinif"]))
    print("\n  ÖZET")
    print("  %-14s %8s %12s %10s"
          % ("kol", "vuruş", "KONTROLLÜ", "ŞANS"))
    print("  " + "-" * 48)
    for kol in sorted(OZ):
        R = OZ[kol]
        v = [x for x in R if x["vurus"]]
        k = sum(1 for x in v if x.get("sinif") == "KONTROLLÜ")
        s = sum(1 for x in v if x.get("sinif") == "ŞANS")
        print("  %-14s %8d %12d %10d" % (kol, len(v), k, s))
    print("""
  ⚠ ŞANS vuruşu isabet SAYILIR ama İYİLEŞME KANITI SAYILMAZ (§4).
    Bir kol daha çok vuruyor ama vuruşları ŞANS'a kayıyorsa, kazanım
    iddiası zayıftır.
""")


if __name__ == "__main__":
    main()
