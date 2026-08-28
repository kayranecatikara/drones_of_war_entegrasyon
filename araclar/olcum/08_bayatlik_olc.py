# -*- coding: utf-8 -*-
"""AŞAMA 1 — mevcut loglardan BAYATLIK bedelini ölç (uçuş YOK).

Soru: "kareyi 145 ms geç işlersek, hedef kadrajda ne kadar kaymış olur?"

⭐ YÖNTEM — MODEL DEĞİL, DOĞRUDAN ÖLÇÜM:
   Ardışık iki tespit arasında kutunun kadrajda kaç piksel kaydığına bakarız.
   Bu, "N ms önceki piksel konumunu kullanırsam kaç piksel yanılırım"
   sorusunun ta kendisidir. Kamera modeli, duruş, hiçbiri gerekmez.

⚠ GEÇERLİLİK EŞİ (§5.2): Δcx yalnız kutu İKİ karede de varken hesaplanır.
   Tespitin koptuğu kareler elenir — ve onlar büyük ihtimalle en hareketli
   anlardır. Yani çıkan sayı bir ALT SINIRDIR, gerçeği hafife alır.

⚠ ÖRNEKLEME (§5.3): cikarim.csv 9.2 Hz (108 ms). Ölçmek istediğimiz pencere
   145 ms. Oran 1.3 — §5.3'ün istediği 5 kat DEĞİL. Bu yüzden hızlı
   geçişler görünmez. Sayı yine ALT SINIR olarak okunur.
"""
import csv
import glob
import math
import os
import statistics as st

D_MS = 145.0                 # telafi edilecek gecikme

# ⛔⛔ §5.14 TUZAĞI — İLK YAZIMDA BUNA DÜŞTÜM, DÜZELTİLDİ (2026-08-27).
#   Loglar SİMÜLATÖRDEN geliyor: 1920x1080, f=540.4 px, C=997 px·m.
#   İlk sürümde GERÇEK kameranın sabitlerini (f=171.3, C=314) bu loglara
#   uygulamıştım -> menzil bandı tablosu tamamen yanlış çıktı
#   ("hepsi 0-8 m" dedi, çünkü C 3.2 kat küçüktü).
#
#   DOĞRUSU: her şeyi ÖNCE AÇIYA çevir (çözünürlükten bağımsız), SONRA
#   gerçek kameranın pikseline dön. Ölçüm sim'de yapılıyor, hüküm gerçek
#   donanım için kuruluyor.
SIM_F_PX    = 540.4          # sim, 1920 genişlik
SIM_MENZIL_C = 997.0         # sim, px·m
GER_F_PX    = 171.3          # gerçek kamera, 640 genişlik (ölçüldü)
GER_MENZIL_C = 314.0         # gerçek, px·m
KANAT_M = 1.718


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sayi(r, k):
    v = (r.get(k) or "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def main():
    dosyalar = sorted(glob.glob("logs/*/*/cikarim.csv"))
    if not dosyalar:
        print("cikarim.csv bulunamadi.")
        return

    kaymalar = []        # (dt_ms, dcx_px, dcy_px, menzil_m, kosu)
    roll_hiz = []        # deg/s
    toplam, kutulu = 0, 0

    for yol in dosyalar:
        kosu = "/".join(yol.split("/")[-3:-1])
        satirlar = oku(yol)
        onceki = None
        for r in satirlar:
            toplam += 1
            t = sayi(r, "t")
            cx, cy = sayi(r, "vis_cx"), sayi(r, "vis_cy")
            w = sayi(r, "vis_w")
            roll = sayi(r, "drone_roll")
            if t is None:
                continue
            if cx is not None and cy is not None:
                kutulu += 1
            if onceki is not None:
                t0, cx0, cy0, roll0 = onceki
                dt = (t - t0) * 1000.0
                if 40.0 < dt < 250.0:               # ardışık tik
                    if None not in (cx, cy, cx0, cy0):
                        menzil = SIM_MENZIL_C / w if w else None
                        kaymalar.append((dt, abs(cx - cx0), abs(cy - cy0),
                                         menzil, kosu))
                    if None not in (roll, roll0):
                        roll_hiz.append(abs(roll - roll0) / (dt / 1000.0))
            onceki = (t, cx, cy, roll)

    print("=" * 66)
    print("AŞAMA 1 — BAYATLIK BEDELİ (mevcut loglardan, uçuş yok)")
    print("=" * 66)
    print("koşu sayısı        : %d" % len(dosyalar))
    print("toplam görsel tik  : %d" % toplam)
    print("kutulu tik         : %d  (%%%.0f)" % (kutulu, 100.0 * kutulu / max(toplam, 1)))
    print("ardışık kutu çifti : %d   <- ölçüm bunlardan" % len(kaymalar))
    print()

    if len(kaymalar) < 30:
        print("⛔ YETERSİZ VERİ (n=%d). Hüküm kurulmaz." % len(kaymalar))
        return

    # 145 ms'e ölçekle: kayma dt boyunca oldu, D_MS boyunca ne olurdu
    olcek = [(k[1] * D_MS / k[0], k[2] * D_MS / k[0], k[3]) for k in kaymalar]
    dcx = sorted(x[0] for x in olcek)
    dcy = sorted(x[1] for x in olcek)

    def p(v, q):
        return v[min(int(len(v) * q), len(v) - 1)]

    def der(px_sim):
        """sim pikseli -> AÇI (derece). Çözünürlükten bağımsız birim."""
        return math.degrees(math.atan(px_sim / SIM_F_PX))

    def ger_px(px_sim):
        """sim pikseli -> GERÇEK kameranın pikseli (açı üzerinden)."""
        return GER_F_PX * math.tan(math.radians(der(px_sim)))

    print("%.0f ms'de hedefin kadrajda kayması — AÇI olarak" % D_MS)
    print("(çözünürlükten bağımsız; sim ve gerçek için aynı):")
    print("            medyan      %75      %90      %95   en kötü")
    print("  yatay  %9.2f° %8.2f° %8.2f° %8.2f° %8.2f°"
          % (der(st.median(dcx)), der(p(dcx, .75)), der(p(dcx, .90)),
             der(p(dcx, .95)), der(dcx[-1])))
    print("  dikey  %9.2f° %8.2f° %8.2f° %8.2f° %8.2f°"
          % (der(st.median(dcy)), der(p(dcy, .75)), der(p(dcy, .90)),
             der(p(dcy, .95)), der(dcy[-1])))
    print()
    print("GERÇEK kamerada (640x480, fx=%.1f px) kaç piksel eder:" % GER_F_PX)
    print("  yatay  medyan %5.1f px   %%90 %5.1f px   en kötü %5.1f px"
          % (ger_px(st.median(dcx)), ger_px(p(dcx, .90)), ger_px(dcx[-1])))
    print("  dikey  medyan %5.1f px   %%90 %5.1f px   en kötü %5.1f px"
          % (ger_px(st.median(dcy)), ger_px(p(dcy, .90)), ger_px(dcy[-1])))
    print()

    # menzile göre: yakınlaştıkça kayma büyür mü
    bantlar = [(0, 5), (5, 8), (8, 15), (15, 25), (25, 60), (60, 1e9)]
    print("MENZİL BANDINA GÖRE — yatay kayma ve hedefin KENDİ boyutu")
    print("(gerçek kamera pikselinde; 'kayma/kutu' 1'e yaklaşırsa")
    print(" bayat kutu hedefin tamamen DIŞINI gösteriyor demektir):")
    print("  %-10s %6s %9s %9s %9s %9s"
          % ("bant", "n", "medyan", "%90", "kutu px", "%90/kutu"))
    for a, b in bantlar:
        v = sorted(x[0] for x in olcek if x[2] is not None and a <= x[2] < b)
        if len(v) >= 10:
            ad = "%d-%d m" % (a, b) if b < 1e9 else ">%d m" % a
            orta = (a + b) / 2.0 if b < 1e9 else 80.0
            kutu = GER_MENZIL_C / orta
            print("  %-10s %6d %9.1f %9.1f %9.1f %9.2f"
                  % (ad, len(v), ger_px(st.median(v)), ger_px(p(v, .90)),
                     kutu, ger_px(p(v, .90)) / kutu))
    print()

    if roll_hiz:
        rh = sorted(roll_hiz)
        print("Kendi yatış hızımız (|Δroll|/s, 9.2 Hz'den — ALT SINIR):")
        print("  medyan %.0f °/s   %%90 %.0f °/s   en kötü %.0f °/s"
              % (st.median(rh), p(rh, .90), rh[-1]))
        print("  -> %.0f ms'de yatış değişimi: medyan %.1f°  %%90 %.1f°"
              % (D_MS, st.median(rh) * D_MS / 1000.0, p(rh, .90) * D_MS / 1000.0))


if __name__ == "__main__":
    main()
