# -*- coding: utf-8 -*-
"""
================================================================================
ISP 2×2 — mimari mi, tavan mı?
================================================================================
Kampanya ISP kurulurken TASARIM HATASI yapıldı: deney kolunda mimari VE tavan
birlikte değişti (§4 "TEK DEĞİŞKEN" ihlali). Bu araç, dört hücreyi yan yana
koyup etkiyi ayırır:

                 tavan 15/10          tavan 20/20
  tek döngü      K  (bugünkü)         H  (HZ4 deneyi)
  iş parçacığı   M  (ISPM)            I  (ISP3)

  MİMARİ etkisi  = M − K   (tavan sabit)
  TAVAN  etkisi  = H − K   (mimari sabit)
  BİRLİKTE       = I − K

Ölçütler `docs/kampanya/ISP_GORUS_IS_PARCACIGI.md`'de KOŞMADAN ÖNCE ilan
edildi; bu araç yalnız onları hesaplar (§5.6 — sonuca bakıp ölçüt seçmek yasak).

Kullanım:
  python3 araclar/isp_2x2.py
================================================================================
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from araclar.hz_kiyas import kol_ozet          # noqa: E402

HUCRELER = [
    ("K", "tek döngü  15/10", "logs/ISP3_K_*"),
    ("M", "iş parç.   15/10", "logs/ISP5_M_*"),
    ("H", "tek döngü  20/20", "logs/HZ4_H"),
    ("I", "iş parç.   20/20", "logs/ISP5_I_*"),
]

SATIRLAR = [
    ("⚙ MEKANİZMA (§5.1)", None, None),
    ("kontrol döngüsü Hz", "tik_hz", ""),
    ("çıkarım Hz", "cikarim_hz", ""),
    ("çıkarım ORT", "det_ms", "ms"),
    ("  yavaş kol med", "det_ms_yavas", "ms"),
    ("  yavaş kolun payı", "yavas_kol_yuzde", "%"),
    ("⭐ BİRİNCİL", None, None),
    ("KÖR SÜRE ORANI", "kor_oran", "%"),
    ("kutu yaşı p90", "yas_p90", "s"),
    ("🔒 GEÇERLİLİK EŞİ (§5.2)", None, None),
    ("görsel temas", "temas_oran", "%"),
    ("tespit oranı", "tespit_oran", "%"),
    ("⭐GERÇEK tespit", "gercek_tespit", "%"),
    ("⛔ REGRESYON (§5.10)", None, None),
    ("ISTASYON hata", "ist_hata_med", "m"),
    ("ISTASYON ≤15 m", "ist_15m_oran", "%"),
    ("◎ İKİNCİL", None, None),
    ("isabet", "isabet", ""),
    ("en yakın", "en_yakin_m", "m"),
    ("〰 SALINIM (§4)", None, None),
    ("roll işaret dgş", "roll_donus_hz", "/s"),
    ("|roll| p90", "roll_p90", "°"),
]


def med(kol, anah):
    v = [x[anah] for x in kol if np.isfinite(x.get(anah, np.nan))]
    return float(np.median(v)) if v else float("nan")


def main():
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(kok)
    veri, n = {}, {}
    for kod, _ad, desen in HUCRELER:
        try:
            k = kol_ozet(desen)
        except Exception:
            k = []
        veri[kod] = k
        n[kod] = len(k)

    print("\n" + "=" * 78)
    print("  ISP 2×2 — MİMARİ Mİ, TAVAN MI?")
    print("=" * 78)
    for kod, ad, _d in HUCRELER:
        print("    %s = %-20s n=%d" % (kod, ad, n[kod]))
    print("  " + "-" * 74)
    print("  %-24s %9s %9s %9s %9s" % ("", "K", "M", "H", "I"))
    print("  %-24s %9s %9s %9s %9s" % ("", "15/10", "15/10", "20/20", "20/20"))
    print("  %-24s %9s %9s %9s %9s" % ("", "döngü", "İŞ PRÇ", "döngü", "İŞ PRÇ"))
    print("  " + "-" * 74)
    for et, anah, birim in SATIRLAR:
        if anah is None:
            print("\n  %s" % et)
            continue
        d = [med(veri[k], anah) for k, _, _ in HUCRELER]
        hucre = []
        for v in d:
            hucre.append("%9s" % ("—" if not np.isfinite(v) else
                                  ("%.2f%s" % (v, birim))[:9]))
        print("  %-24s %s" % (et, " ".join(hucre)))

    print("\n  " + "-" * 74)
    print("  ETKİ AYRIŞTIRMASI (medyan farkı, K tabanına göre)")
    for et, anah, birim in SATIRLAR:
        if anah is None or anah not in ("kor_oran", "tespit_oran",
                                        "ist_hata_med", "en_yakin_m",
                                        "tik_hz", "cikarim_hz"):
            continue
        bk = med(veri["K"], anah)
        if not np.isfinite(bk):
            continue
        def fark(kod):
            v = med(veri[kod], anah)
            return "—" if not np.isfinite(v) else "%+.2f" % (v - bk)
        print("  %-24s MİMARİ(M−K) %8s   TAVAN(H−K) %8s   BİRLİKTE(I−K) %8s"
              % (et, fark("M"), fark("H"), fark("I")))
    az = [k for k in n if n[k] < 4]
    if az:
        print("\n  ⚠ n<4 olan hücreler: %s — bunlar ARA VERİ, KARAR DEĞİL (§5.4)"
              % ", ".join(sorted(az)))
    print()


if __name__ == "__main__":
    main()
