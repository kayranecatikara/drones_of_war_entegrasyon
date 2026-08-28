# -*- coding: utf-8 -*-
"""ADIM 4 — SONUCU HESAPLA.

Kullanim:   python3 04_gecikme_oku.py
Cikti   :   logs/gecikme/SONUC.txt  + ekrana karar tablosu

NE YAPAR: logs/gecikme/*/olcum.csv dosyalarini okur, doldurulmus
'karede_yazan' sutunlarindan gecikmeyi hesaplar, kol kol MEDYAN alir
ve karari yazar.

⚠ MEDYAN kullanilir, ortalama DEGIL: tek bir takilma ortalamayi bozar,
  medyani bozmaz.
"""
import csv
import glob
import os
import statistics as st

KOK = os.path.join("logs", "gecikme")
satirlar = []


def yaz(s):
    print(s, flush=True)
    satirlar.append(s)


kollar = {}      # kol harfi -> [gecikme_ms, ...]
kosular = []     # (etiket, kol, n, medyan)

for yol in sorted(glob.glob(os.path.join(KOK, "*", "olcum.csv"))):
    dizin = os.path.dirname(yol)
    etiket = os.path.basename(dizin)

    kol = "?"
    not_yolu = os.path.join(dizin, "not.txt")
    if os.path.exists(not_yolu):
        for satir in open(not_yolu, encoding="utf-8"):
            if satir.startswith("kol:"):
                kol = satir.split(":", 1)[1].strip()

    degerler = []
    with open(yol, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ham = (r.get("karede_yazan") or "").strip().replace(",", ".")
            if not ham:
                continue
            try:
                karede = float(ham)
                varis = float(r["varis"])
            except ValueError:
                continue
            g = (varis - karede) * 1000.0
            # sss.mmm bicimi 1000 s'de bir basa sarar
            if g < -500000:
                g += 1000000.0
            if 0.0 < g < 2000.0:
                degerler.append(g)

    if not degerler:
        yaz("ATLANDI  %-8s  (karede_yazan sutunu bos)" % etiket)
        continue

    m = st.median(degerler)
    kosular.append((etiket, kol, len(degerler), m))
    kollar.setdefault(kol, []).extend(degerler)

if not kosular:
    yaz("")
    yaz("HIC VERI YOK. olcum.csv dosyalarindaki 'karede_yazan'")
    yaz("sutununu doldurmayi unutmayin (ADIM 4).")
    raise SystemExit(1)

yaz("")
yaz("KOSU KOSU")
yaz("-" * 46)
yaz("%-10s %-5s %5s %12s" % ("etiket", "kol", "n", "medyan ms"))
for etiket, kol, n, m in kosular:
    yaz("%-10s %-5s %5d %12.1f" % (etiket, kol, n, m))

yaz("")
yaz("KOL KOL (tum kosular birlestirilmis)")
yaz("-" * 46)
yaz("%-5s %5s %12s %12s" % ("kol", "n", "medyan ms", "en iyi ms"))
ozet = {}
for kol in sorted(kollar):
    v = kollar[kol]
    ozet[kol] = st.median(v)
    yaz("%-5s %5d %12.1f %12.1f" % (kol, len(v), st.median(v), min(v)))

yaz("")
yaz("=" * 60)
yaz("KARAR")
yaz("=" * 60)

A = ozet.get("A")
if A is None:
    yaz("Kol A (taban) olculmemis - kiyas yapilamaz.")
else:
    yaz("Taban (Kol A)          : %.0f ms" % A)
    for kol, ad in (("B", "BUFFERSIZE=1"), ("C", "BOSALTMA (drain)")):
        if kol in ozet:
            kazanc = A - ozet[kol]
            yaz("%-22s : %.0f ms   (kazanc %+.0f ms)"
                % (ad, ozet[kol], kazanc))

    en_iyi = min(ozet, key=lambda k: ozet[k])
    kazanc = A - ozet[en_iyi]
    yaz("")
    if en_iyi == "A" or kazanc < 20:
        yaz(">>> YAZILIM TAMPONU SUCLU DEGIL.")
        yaz(">>> Gecikme kartin kendi donaniminda. GStreamer denenir,")
        yaz("    sonucu degistirmezse BASKA KART konusulur.")
    else:
        yaz(">>> KOL %s KAZANDI: %.0f ms bedava kazanc." % (en_iyi, kazanc))
        yaz(">>> Bu yontem sistemde KALICI hale getirilmeli.")

    yaz("")
    yaz("Not: bu sayilar MONITORUN kendi gecikmesini de icerir (~16-40 ms).")
    yaz("     Kollar arasi FARK temizdir - monitor payi ikisinde de ayni.")
    yaz("     Gudum monitoru kullanmaz; gercek gudum gecikmesi bu")
    yaz("     sayilardan ~20-25 ms DAHA AZDIR.")

with open(os.path.join(KOK, "SONUC.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(satirlar) + "\n")
print("\nyazildi: %s/SONUC.txt" % KOK)
