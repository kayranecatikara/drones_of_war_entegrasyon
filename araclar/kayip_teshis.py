# -*- coding: utf-8 -*-
"""
================================================================================
KAYIP TEŞHİSİ — "hedefi neden kaybediyoruz?" sorusunu ÜÇE ayırır
================================================================================
Bir çıkarımda tespit BAŞARISIZ olduğunda üç ayrı sebep olabilir ve üçünün
ÇARESİ BAMBAŞKADIR. Hepsini "tespit kötü" diye tek torbaya atmak, yanlış
şeyi düzeltmeye çalışmak demektir.

  A) KADRAJ DIŞI  — hedef o an kameranın göremeyeceği yerde.
     Sebep GÜDÜM/GEOMETRİ: yanlış yere nişan aldık, ya da hedef manevrayla
     görüş konisinden çıktı. Çare: güdüm yasası / nişan noktası / FOV.

  B) DEDEKTÖR KÖR — hedef kadrajda AMA model hiç kutu üretmedi
     (`yerel_aday == 0`). Sebep MODEL: menzil, açı, kontrast, çözünürlük.
     Çare: model / imgsz / eşik.

  C) KAPI ELEDİ    — model kutu ÜRETTİ ama süzgeç attı
     (`yerel_aday > 0` ama `yerel_uygun == 0`). Sebep BİZİM KODUMUZ.
     Çare: yerellik kapısı / güven eşiği / menzil tavanı.

`bek_cx, bek_cy` = hedefin kadrajda BEKLENEN piksel yeri (GPS geometrisinden,
ÖLÇÜM-ONLY — güdüme girmez, §10 temiz). Kadraj içi/dışı ayrımı buradan gelir.

⚠ SINIRI: `bek_*` yalnız hedefin GPS'i okunabildiğinde dolar. GORSEL fazda
  `hedef_konumu()` çağrılmadığı için (bekçi B18) bu sütunlar GORSEL fazda
  BOŞ kalabilir. O yüzden teşhis, sütunun DOLU olduğu karelerle sınırlıdır
  ve kaç karenin dışarıda kaldığı ayrıca basılır — gizlenmez.

Ayrıca MANEVRA bağı: `hedef_roll` (hedefin yatışı) hedefin manevra yaptığının
göstergesidir. Kayıpların manevrayla ilişkisi ölçülür.

Kullanım: python3 araclar/kayip_teshis.py logs/KAMERA10
================================================================================
"""
import csv
import glob
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)
from araclar.arka import ArkaBekci
IMG_W, IMG_H = 1920.0, 1080.0


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def teshis(kdizin):
    yol = os.path.join(kdizin, "cikarim.csv")
    if not os.path.exists(yol):
        return None
    R = list(csv.DictReader(open(yol)))
    if not R:
        return None
    t0 = _f(R[0], "t") or 0.0
    d = {"ad": os.path.basename(os.path.dirname(kdizin)) + "/" +
         os.path.basename(kdizin), "n": len(R),
         "A": 0, "B": 0, "C": 0, "ARK": 0, "bilinmiyor": 0, "basarili": 0,
         "manevra_kayip": 0, "manevra_kare": 0, "sakin_kayip": 0,
         "sakin_kare": 0, "seriler": []}
    _ab = ArkaBekci(kdizin)
    seri = 0
    for r in R:
        hr = _f(r, "hedef_roll")
        manevra = hr is not None and abs(hr) > 10.0
        if manevra:
            d["manevra_kare"] += 1
        else:
            d["sakin_kare"] += 1
        if r.get("basarili") == "1":
            d["basarili"] += 1
            if seri:
                d["seriler"].append(seri); seri = 0
            continue
        seri += 1
        if manevra:
            d["manevra_kayip"] += 1
        else:
            d["sakin_kayip"] += 1
        bx, by = _f(r, "bek_cx"), _f(r, "bek_cy")
        ad_ = _f(r, "yerel_aday")
        # ⭐ ARK: hedef ARKAMIZDA — üstünden geçtik, bu KAYIP DEĞİL.
        #   Ayrılmazsa geçiş geometrisi güdüm kusuru sanılır (bkz. arka.py).
        if _ab is not None and _ab.var and _ab.arkada(_f(r, "t")):
            d["ARK"] += 1
        elif bx is None or by is None:
            d["bilinmiyor"] += 1
        elif not (0 <= bx < IMG_W and 0 <= by < IMG_H):
            d["A"] += 1
        elif ad_ is not None and ad_ > 0:
            d["C"] += 1
        else:
            d["B"] += 1
    if seri:
        d["seriler"].append(seri)
    return d


def main():
    kok = sys.argv[1] if len(sys.argv) > 1 else "logs/KAMERA10"
    dizinler = sorted(glob.glob(os.path.join(KOK, kok, "k*")))
    if not dizinler:
        dizinler = sorted(glob.glob(os.path.join(KOK, kok + "*", "k*")))
    hepsi = [x for x in (teshis(d) for d in dizinler) if x]
    if not hepsi:
        print("⛔ cikarim.csv bulunamadı: %s" % kok); return

    print("\n" + "=" * 78)
    print("  KAYIP TEŞHİSİ — %s" % kok)
    print("=" * 78)
    print("\n  A=kadraj dışı (GÜDÜM)  B=dedektör kör (MODEL)  C=kapı eledi (KOD)")
    print("  ⭐ ARK=hedef ARKAMIZDA (üstünden geçtik) — KAYIP DEĞİL, bkz. arka.py\n")
    print("  %-16s %5s %7s %6s %6s %6s %6s %9s" %
          ("koşu", "çık", "tespit%", "A", "B", "C", "ARK", "bilinmiyor"))
    print("  " + "-" * 68)
    T = {"n": 0, "basarili": 0, "A": 0, "B": 0, "C": 0, "ARK": 0,
         "bilinmiyor": 0}
    for d in hepsi:
        print("  %-16s %5d %7.1f %6d %6d %6d %6d %9d" %
              (d["ad"], d["n"], 100.0 * d["basarili"] / d["n"],
               d["A"], d["B"], d["C"], d["ARK"], d["bilinmiyor"]))
        for k in T:
            T[k] += d[k]
    kayip = T["n"] - T["basarili"]
    print("  " + "-" * 68)
    print("  %-16s %5d %7.1f %6d %6d %6d %6d %9d" %
          ("TOPLAM", T["n"], 100.0 * T["basarili"] / T["n"],
           T["A"], T["B"], T["C"], T["ARK"], T["bilinmiyor"]))
    if kayip:
        bilinen = T["A"] + T["B"] + T["C"]
        print("\n  ⭐ %d kare hedef ARKAMIZDAYKEN — bunlar KAYIP DEĞİL, geçiş"
              % T["ARK"])
        print("     sonrası kareler. Payda dışı bırakılır (bkz. arka.py).")
        print("\n  GERÇEK KAYIPLARIN DAĞILIMI (%d kayıptan %d'i sınıflandı)"
              % (kayip - T["ARK"], bilinen))
        if bilinen:
            for k, ad in (("A", "kadraj dışı  -> GÜDÜM/GEOMETRİ"),
                          ("B", "dedektör kör -> MODEL"),
                          ("C", "kapı eledi   -> BİZİM KOD")):
                print("     %-32s %5d  %%%.1f" %
                      (ad, T[k], 100.0 * T[k] / bilinen))
        if T["bilinmiyor"]:
            print("     ⚠ %d kare sınıflanamadı (bek_cx boş — GORSEL fazda"
                  " hedef GPS'i okunmuyor)." % T["bilinmiyor"])

    print("\n  MANEVRA BAĞI — hedef yatışı |roll| > 10° iken kayıp oranı")
    print("  %-16s %14s %14s" % ("koşu", "manevrada", "sakin"))
    print("  " + "-" * 48)
    mk = mn = sk = sn = 0
    for d in hepsi:
        a = (100.0 * d["manevra_kayip"] / d["manevra_kare"]) if d["manevra_kare"] else float("nan")
        b = (100.0 * d["sakin_kayip"] / d["sakin_kare"]) if d["sakin_kare"] else float("nan")
        print("  %-16s %13.1f%% %13.1f%%" % (d["ad"], a, b))
        mk += d["manevra_kayip"]; mn += d["manevra_kare"]
        sk += d["sakin_kayip"]; sn += d["sakin_kare"]
    print("  " + "-" * 48)
    print("  %-16s %13.1f%% %13.1f%%" %
          ("TOPLAM", 100.0 * mk / mn if mn else float("nan"),
           100.0 * sk / sn if sn else float("nan")))
    if mn and sn:
        print("\n     manevrada %d/%d kare, sakinde %d/%d kare" % (mk, mn, sk, sn))

    ser = [x for d in hepsi for x in d["seriler"]]
    if ser:
        ser.sort()
        print("\n  KAYIP SERİLERİ (ardışık tespitsiz kare)")
        print("     n=%d seri | medyan %d | p90 %d | en uzun %d"
              % (len(ser), st.median(ser), ser[int(0.9 * (len(ser) - 1))], ser[-1]))
        print("     20+ olan (geri dönüş kapısını ateşleyen): %d seri"
              % sum(1 for x in ser if x >= 20))
    print()


if __name__ == "__main__":
    main()
