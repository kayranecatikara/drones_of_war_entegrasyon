# -*- coding: utf-8 -*-
"""
================================================================================
KOL KIYASI — iki kampanya kolunu CLAUDE.md disipliniyle karşılaştır
================================================================================
⛔ §5.1 MEKANİZMA KAPISI önce sorulur. Genel kapı: koşu GÖRSEL faza girdi
   mi (`gorsel_tik > 0`) ve uçuş bandı ihlali var mı (`ihlal`). Sınadığın
   özelliğin KENDİ mekanizma sütunu varsa `--mek <sutun>` ile ver; o sütunu
   sıfır olan DENEY koşusu veri noktası değil, GEÇERSİZ koşudur.

⚠ 2026-08-25: bu araç `devir_kiyas.py` adıyla iki devir kapısını
   kıyaslamak için yazılmıştı. İstasyon kapısı §5.12 ile silinince o kıyas
   imkânsızlaştı; araç genelleştirilip yeniden adlandırıldı (yanıltıcı ad
   bırakmak §5.12 ihlalidir).

⛔ §5.2 GEÇERLİLİK EŞİ: hiçbir ölçüt tek başına raporlanmaz.
     en_yakin_m      <- eşi: imha (savrulup şans eseri yaklaşma)
     roll_p90        <- eşi: gorsel_tespit_yuzde (hedefi kaybeden araç sakin
                        görünür; %60 altı GÜVENİLMEZ)
     gorsel_s        <- eşi: kutu_yasi_p90 (uzun görsel faz, kör geçmişse
                        iyi değil)

⚠ §5.14 GEÇERLİLİK FİLTRESİ YENİDEN GEREKÇELENDİRİLDİ:
   "süre < 20 s -> geçersiz" filtresi BURADA KULLANILMAZ. Bu kampanyada
   KISA KOŞU = HIZLI İMHA'dır (KANAL_D medyanı 18.2 s). O filtre en iyi
   koşuları elerdi. Tek geçerlilik filtresi `ihlal` sütunudur (uçuş bandı).

`faz_gecis_n` ozet.csv'de YOK; cikarim.csv'deki `durum` sütunundan
sayılır (çıkarım başına, yani kapının kendi çözünürlüğünde).

Kullanım: python3 araclar/kol_kiyas.py <DENEY> <KONTROL> [--mek <sutun>]
================================================================================
"""
import csv
import glob
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k, vars=float("nan")):
    try:
        v = r.get(k)
        return float(v) if v not in (None, "", "nan") else vars
    except Exception:
        return vars


def faz_gecisleri(kdizin):
    """GORSEL <-> ISTASYON geçişlerini cikarim.csv'den say."""
    yol = os.path.join(kdizin, "cikarim.csv")
    if not os.path.exists(yol):
        return -1, -1
    onceki, ileri, geri = None, 0, 0
    for r in csv.DictReader(open(yol)):
        g = str(r.get("durum", "")).startswith("GORSEL")
        if onceki is not None and g != onceki:
            (ileri := ileri + 1) if g else (geri := geri + 1)
        onceki = g
    return ileri, geri


def kol_yukle(desen):
    """logs/<desen>*/ozet.csv -> geçerli koşu satırları."""
    sat = []
    for oz in sorted(glob.glob(os.path.join(KOK, "logs", desen + "*", "ozet.csv"))):
        kok = os.path.dirname(oz)
        for r in csv.DictReader(open(oz)):
            # ⛔ TEK geçerlilik filtresi: uçuş bandı ihlali (§5.14 gereği
            #    süre filtresi YOK — kısa koşu burada HIZLI İMHA demek).
            if str(r.get("ihlal", "-")) not in ("-", "", "nan"):
                r["_gecersiz"] = "ihlal:%s" % r["ihlal"]
            kd = os.path.join(kok, "k%02d" % int(float(r.get("kosu", 0) or 0)))
            r["_ileri"], r["_geri"] = faz_gecisleri(kd)
            r["_ad"] = "%s/k%02d" % (os.path.basename(kok),
                                     int(float(r.get("kosu", 0) or 0)))
            sat.append(r)
    return sat


def mekanizma_kapisi(sat, mek_sutun=None):
    """§5.1 — özellik gerçekten çalıştı mı?

    `mek_sutun` verilirse o sütunu SIFIR olan koşu GEÇERSİZ sayılır: deney
    kolunda mekanizma hiç devreye girmediyse o koşu fiilen KONTROL
    koşusudur ve kıyasa girerse tablo SAHTE olur (Ö6 dersi)."""
    gecerli, gecersiz = [], []
    for r in sat:
        if r.get("_gecersiz"):
            gecersiz.append((r["_ad"], r["_gecersiz"]))
        elif float(r.get("gorsel_tik", 0) or 0) <= 0:
            gecersiz.append((r["_ad"], "görsel faza HİÇ girmedi"))
        elif mek_sutun and float(r.get(mek_sutun, 0) or 0) == 0.0:
            gecersiz.append((r["_ad"], "mekanizma sütunu %s = 0" % mek_sutun))
        else:
            gecerli.append(r)
    return gecerli, gecersiz


OLCUTLER = [
    ("imha", "⭐ imha", "%d"), ("temas", "temas", "%d"),
    ("sure", "süre s", "%.1f"), ("devir_s", "devir s", "%.1f"),
    ("devir_menzil", "devir menzil m", "%.1f"),
    ("en_yakin_m", "en yakın m", "%.2f"),
    ("gorsel_s", "görsel faz s", "%.1f"),
    ("gorsel_tespit_yuzde", "görsel tespit %", "%.1f"),
    ("kutu_yasi_p90", "kutu yaşı p90 s", "%.2f"),
    ("roll_p90", "|roll| p90 °", "%.2f"),
    ("cx_donus_s", "cx dönüş /s", "%.3f"),
    ("ist_hata_min", "istasyon en iyi m", "%.2f"),
    ("det_hz", "çıkarım Hz", "%.1f"), ("tik_hz", "kontrol Hz", "%.1f"),
]


def main():
    d_desen = sys.argv[1] if len(sys.argv) > 1 else "KAMERA10"
    k_desen = sys.argv[2] if len(sys.argv) > 2 else "KANAL_D"
    deney = kol_yukle(d_desen)
    kontrol = kol_yukle(k_desen)

    print("\n" + "=" * 78)
    print("  KOL KIYASI — DENEY: %s   vs   KONTROL: %s"
          % (d_desen, k_desen))
    print("=" * 78)

    mek = None
    for i, a in enumerate(sys.argv):
        if a == "--mek" and i + 1 < len(sys.argv):
            mek = sys.argv[i + 1]
    d_ok, d_red = mekanizma_kapisi(deney, mek)
    k_ok, k_red = mekanizma_kapisi(kontrol, None)

    print("\n  ⛔ §5.1 MEKANİZMA KAPISI%s"
          % ("  (mekanizma sütunu: %s)" % mek if mek else ""))
    print("     DENEY  : %d geçerli / %d koşu" % (len(d_ok), len(deney)))
    for ad, s in d_red:
        print("        ✗ %-16s %s" % (ad, s))
    print("     KONTROL: %d geçerli / %d koşu" % (len(k_ok), len(kontrol)))
    for ad, s in k_red:
        print("        ✗ %-16s %s" % (ad, s))
    if not d_ok:
        print("\n  ⛔ DENEY KOLUNDA GEÇERLİ KOŞU YOK — rapor değil, EKSİK LİSTESİ.\n")
        return

    print("  %-20s %14s %14s   %s" % ("ölçüt", "DENEY", "KONTROL",
                                      "deney kolu koşuları"))
    print("  " + "-" * 74)
    for k, ad, biç in OLCUTLER:
        dv = [_f(r, k) for r in d_ok]
        kv = [_f(r, k) for r in k_ok]
        dv = [x for x in dv if x == x]; kv = [x for x in kv if x == x]
        if not dv:
            continue
        if k in ("imha", "temas"):
            sol = "%d/%d" % (int(sum(dv)), len(dv))
            sag = "%d/%d" % (int(sum(kv)), len(kv)) if kv else "-"
        else:
            sol = biç % st.median(dv)
            sag = (biç % st.median(kv)) if kv else "-"
        print("  %-20s %14s %14s   %s"
              % (ad, sol, sag, " ".join(biç % x for x in dv)))

    il = [r["_ileri"] for r in d_ok if r["_ileri"] >= 0]
    ge = [r["_geri"] for r in d_ok if r["_geri"] >= 0]
    print("  " + "-" * 74)
    print("  %-20s %14s %14s   %s"
          % ("faz geçişi ileri", "%d" % sum(il) if il else "-", "", il))
    print("  %-20s %14s %14s   %s"
          % ("faz geçişi GERİ(yo-yo)", "%d" % sum(ge) if ge else "-", "", ge))

    print("\n  ⚠ §5.2 GEÇERLİLİK EŞLERİ")
    gt = [_f(r, "gorsel_tespit_yuzde") for r in d_ok]
    gt = [x for x in gt if x == x]
    if gt and st.median(gt) < 60.0:
        print("     ⛔ görsel tespit %%%.1f < %%60 -> salınım ölçütü GÜVENİLMEZ"
              % st.median(gt))
    else:
        print("     ✔ görsel tespit %%%.1f (>= %%60) -> salınım ölçütü geçerli"
              % (st.median(gt) if gt else -1))
    print("\n  ⚠ §5.4: n=%d tek kol, dönüşümlü A/B DEĞİL -> ARA VERİ.\n" % len(d_ok))


if __name__ == "__main__":
    main()
