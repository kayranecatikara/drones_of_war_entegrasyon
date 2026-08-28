# -*- coding: utf-8 -*-
"""
================================================================================
KİLİT ÖLÇER — şartname 6.1.4'ü MEVCUT loglara uygular (ÇEVRİMDIŞI)
================================================================================
⛔ BU BİR KANIT ARACI DEĞİLDİR (CLAUDE.md §2): çevrimdışı replay yalnız
   HİPOTEZ üretir. Amacı tek: "şartnamenin kilit isteri bizim kameramızla
   FİZİKSEL OLARAK sağlanabilir mi" sorusunu, kod yazmadan ÖNCE cevaplamak.

ŞARTNAME TANIMLARI (Teknofest 6.1.4, Şekil 2) — hepsi piksel, GPS YOK:
  AK  Kamera Görüş Alanı   : tam kadraj (1920x1080)
  AV  Hedef Vuruş Alanı    : kadrajın SOLDAN/SAĞDAN %25, ÜSTTEN/ALTTAN %10
                             kırpılmış hâli -> x:[480,1440]  y:[108,972]
  AH  Kilitlenme Dörtgeni  : bizim çizdiğimiz kutu (= dedektör bbox'u)
  HH  Hedef Hava Aracı     : rakip İHA

BİR KARENİN "KİLİTLİ" SAYILMASI İÇİN (şartname maddeleri):
  1. Tespit VAR (kutu üretildi).
  2. HH merkezi AV içinde.
  3. HH görüntüsü, ekranın yatay VEYA dikey ekseninin en az %5'ini kapsar
     ("...yatay ve dikey eksenlerinden en az birinde, en az %5'ini
     kapsamalıdır") -> w >= 96 px  VEYA  h >= 54 px.
     ⚠ Şartname %5'i SINIRDA kullanmayı ÖNERMİYOR: "paket gönderme
       limitinin %6 veya daha üstü olması tavsiye edilir." -> --pay ile.
  4. AH merkezi ile HH merkezi arası yatayda HH genişliğinin, dikeyde HH
     yüksekliğinin YARISINDAN fazla olamaz. Bizde AH = HH kutusudur, yani
     bu şart YAPISAL OLARAK sağlanır (fark 0).

ZAMAN İSTERİ:
  10 saniyelik kayan pencere içinde KÜMÜLATİF kilit süresi >= 5 s.
  Kilit kesik kesik olabilir; aralıkların TOPLAMI sayılır.

ÖRNEKLEME (§5.3): satırlar ÇIKARIM hızındadır (~9-10 Hz, 100 ms). Ölçtüğümüz
şey 5 saniyelik bir toplam; 100 ms çözünürlük 50 kat -> kural sağlanıyor.
Her satır, BİR SONRAKİ satıra kadar geçen süre boyunca kendi kilit durumunu
taşır (sıfırıncı derece tutucu).

Kullanım:
    python3 araclar/kilit_olcu.py logs/TABAN32 logs/KADEM24
    python3 araclar/kilit_olcu.py logs/TABAN32 --pay 6.0
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

# ⛔ ÖLÇÜTÜN TEK KAYNAĞI: dow/gudum/kilit.py — GÜDÜMÜN kullandığı modülün
#   TA KENDİSİ. Burada ikinci bir kopya tutmak, çevrimdışı sayının uçuşta
#   ölçülenden sessizce ayrılması demektir (§5.12 sürüklenmesi).
from dow.ayarlar import Ayar                    # noqa: E402
from dow.gudum.kilit import KilitDurumu         # noqa: E402
from dow.gorus import kamera as KAM             # noqa: E402

IMG_W, IMG_H = KAM.IMG_W, KAM.IMG_H
PENCERE_S = Ayar.KILIT_PENCERE_S
GEREKLI_S = Ayar.KILIT_GEREKLI_S


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def kare_kilitli(cx, cy, w, h, pay_yuzde):
    """Şartname 6.1.4 -> bu kare kilitli mi. Döner: (kilit, sebep).
    Karar GÜDÜMÜN modülüne devredilir; burada yalnız eşik geçici olarak
    kurulur (çevrimdışı taramada farklı %'ler denenebilsin diye)."""
    eski = Ayar.KILIT_BOYUT_YUZDE
    try:
        Ayar.KILIT_BOYUT_YUZDE = pay_yuzde
        return KilitDurumu(Ayar).kare_kilitli(
            None if None in (cx, cy, w, h) else (cx, cy, w, h, 1.0))
    finally:
        Ayar.KILIT_BOYUT_YUZDE = eski


def kosu_coz(dizin, pay=5.0):
    y = os.path.join(dizin, "k01", "cikarim.csv")
    if not os.path.exists(y):
        return None
    S = []
    for r in csv.DictReader(open(y)):
        t = _f(r, "t")
        if t is None:
            continue
        k, sb = kare_kilitli(_f(r, "vis_cx"), _f(r, "vis_cy"),
                             _f(r, "vis_w"), _f(r, "vis_h"), pay)
        S.append({"t": t, "k": k, "sb": sb, "durum": r.get("durum", ""),
                  "R": _f(r, "menzil3_m") or _f(r, "menzil_m"),
                  "w": _f(r, "vis_w"), "h": _f(r, "vis_h")})
    if len(S) < 20:
        return None
    # ⚠ SÜRE YÖNÜ, ÇEVRİMİÇİYLE AYNI OLMALI. Güdüm geleceği bilemez, o
    #   yüzden her çıkarım KENDİNDEN ÖNCEKİ boşluğu temsil eder:
    #       dt = min(KILIT_DT_MAX_S, t_i - t_{i-1})
    #   Kredi tavanı şartnamenin kendi toleransıdır (200 ms); saniyelerce
    #   süren tespit boşluğu kilit süresi SAYILAMAZ.
    S[0]["dt"] = 0.0
    for i in range(1, len(S)):
        S[i]["dt"] = max(0.0, min(Ayar.KILIT_DT_MAX_S, S[i]["t"] - S[i - 1]["t"]))

    # ---- kayan 10 s pencerede kümülatif kilit ----
    # Her satırı pencere SONU kabul edip geriye 10 s bak. O(n^2) değil,
    # iki işaretçiyle O(n).
    en_iyi = 0.0; ilk_t = None; ilk_R = None; i0 = 0; birikim = 0.0
    for i in range(len(S)):
        birikim += S[i]["dt"] if S[i]["k"] else 0.0
        while S[i]["t"] - S[i0]["t"] > PENCERE_S:
            birikim -= S[i0]["dt"] if S[i0]["k"] else 0.0
            i0 += 1
        if birikim > en_iyi:
            en_iyi = birikim
        if ilk_t is None and birikim >= GEREKLI_S:
            ilk_t = S[i]["t"]; ilk_R = S[i]["R"]
    kilitli = [x for x in S if x["k"]]
    Rk = [x["R"] for x in kilitli if x["R"] is not None]
    # en uzun KESİNTİSİZ kilit
    en_uzun = cur = 0.0
    for x in S:
        cur = cur + x["dt"] if x["k"] else 0.0
        en_uzun = max(en_uzun, cur)
    sebep = {}
    for x in S:
        if not x["k"]:
            sebep[x["sb"]] = sebep.get(x["sb"], 0) + 1
    # ozet.csv'den isabet
    isabet = None
    oz = os.path.join(dizin, "ozet.csv")
    if os.path.exists(oz):
        try:
            isabet = int(list(csv.DictReader(open(oz)))[0].get("isabet") or 0)
        except Exception:
            pass
    return {"ad": os.path.basename(dizin), "n": len(S),
            "kilit_kare": len(kilitli), "en_iyi_10s": en_iyi,
            "ilk_t": ilk_t, "ilk_R": ilk_R, "en_uzun": en_uzun,
            "R_kilit_med": st.median(Rk) if Rk else None,
            "R_kilit_max": max(Rk) if Rk else None,
            "sebep": sebep, "isabet": isabet,
            "sure": S[-1]["t"] - S[0]["t"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizinler", nargs="+")
    ap.add_argument("--pay", type=float, default=5.0,
                    help="boyut eşiği yüzde (şartname %%5; tavsiye %%6)")
    a = ap.parse_args()

    print("=" * 88)
    print("  KİLİT ÖLÇER (ÇEVRİMDIŞI — HİPOTEZ, KANIT DEĞİL) · boyut eşiği %%%.1f"
          % a.pay)
    print("  AV: x[%.0f,%.0f] y[%.0f,%.0f]   boyut: w>=%.0f px VEYA h>=%.0f px"
          % (Ayar.KILIT_KIRP_X * IMG_W, (1 - Ayar.KILIT_KIRP_X) * IMG_W,
             Ayar.KILIT_KIRP_Y * IMG_H, (1 - Ayar.KILIT_KIRP_Y) * IMG_H,
             a.pay / 100 * IMG_W, a.pay / 100 * IMG_H))
    print("  isteri: 10 s pencerede kümülatif >= 5.0 s")
    print("=" * 88)

    hepsi = []
    for kok in a.dizinler:
        kd = os.path.join(KOK, kok) if not os.path.isabs(kok) else kok
        kosular = sorted(d for d in glob.glob(os.path.join(kd, "*"))
                         if os.path.isdir(d))
        R = [x for x in (kosu_coz(d, a.pay) for d in kosular) if x]
        if not R:
            print("\n  ⛔ koşu yok: %s" % kok); continue
        print("\n  %s   (n=%d)" % (kok, len(R)))
        print("  %-20s %6s %7s %8s %9s %8s %8s %6s"
              % ("koşu", "kare", "kilitli", "en_uzun", "en_iyi10s", "KİLİT@",
                 "R@kilit", "isbt"))
        print("  " + "-" * 82)
        for x in R:
            print("  %-20s %6d %6d%% %7.1fs %8.1fs %8s %8s %6s"
                  % (x["ad"], x["n"], round(100.0 * x["kilit_kare"] / x["n"]),
                     x["en_uzun"], x["en_iyi_10s"],
                     ("%.1fs" % x["ilk_t"]) if x["ilk_t"] else "—",
                     ("%.1fm" % x["ilk_R"]) if x["ilk_R"] else "—",
                     "✓" if x["isabet"] else "·"))
        hepsi += R

    if not hepsi:
        return
    n = len(hepsi)
    basari = [x for x in hepsi if x["ilk_t"] is not None]
    print("\n" + "=" * 88)
    print("  TOPLAM n=%d" % n)
    print("  KİLİT İSTERİNİ SAĞLAYAN: %d/%d  (%%%.0f)"
          % (len(basari), n, 100.0 * len(basari) / n))
    print("  en iyi 10 s penceredeki kümülatif kilit — medyan %.2f s  (isteri 5.0 s)"
          % st.median([x["en_iyi_10s"] for x in hepsi]))
    print("  en uzun KESİNTİSİZ kilit — medyan %.2f s"
          % st.median([x["en_uzun"] for x in hepsi]))
    Rk = [x["R_kilit_max"] for x in hepsi if x["R_kilit_max"]]
    if Rk:
        print("  kilit sağlanan EN UZAK menzil — medyan %.1f m, en büyük %.1f m"
              % (st.median(Rk), max(Rk)))
    sb = {}
    for x in hepsi:
        for k, v in x["sebep"].items():
            sb[k] = sb.get(k, 0) + v
    tp = sum(sb.values()) or 1
    print("\n  KİLİTSİZ KARELERİN SEBEBİ:")
    for k, v in sorted(sb.items(), key=lambda z: -z[1]):
        print("    %-12s %7d  (%%%.1f)" % (k, v, 100.0 * v / tp))
    print("=" * 88)


if __name__ == "__main__":
    main()
