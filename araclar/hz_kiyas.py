# -*- coding: utf-8 -*-
"""
================================================================================
HZ KIYAS — görüş zinciri hızı A/B çözümleyicisi
================================================================================
KAMPANYA HZ4 için; ölçütler `docs/kampanya/HZ4_GORUS_HIZI.md`'de KOŞMADAN
ÖNCE ilan edildi. Bu araç yalnız onları hesaplar — sonuca bakıp ölçüt
seçmek yasak (§5.6).

BİRİNCİL   : kör süre oranı = kutu yaşı > 0.3 s olan zamanın payı
GEÇERLİLİK : görsel temas oranı + tespit%   (§5.2 — kör süre KÖTÜ sebeple de düşer)
MEKANİZMA  : ulaşılan çıkarım Hz            (§5.1 — deney kolunda <12 Hz = GEÇERSİZ)
REGRESYON  : ISTASYON fazı ist_hata_m       (§5.10 — 22 Ağu'da 5.3 -> 25.3 m bozulmuştu)
SALINIM    : cx işaret değişimi/s, roll işaret değişimi/s, |roll| p90   (§4)

Kullanım:  python3 araclar/hz_kiyas.py logs/HZ4_K logs/HZ4_H
================================================================================
"""
import csv
import os
import sys

import numpy as np

KOR_ESIK_S = 0.3        # kutu bu yaştan büyükse o an "kör" sayılır


def _f(v, d=float("nan")):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _isaret_donus(dizi):
    """İşaret değişimi sayısı (salınım vekili)."""
    s = [x for x in dizi if np.isfinite(x) and abs(x) > 1e-9]
    if len(s) < 2:
        return 0
    return int(sum(1 for a, b in zip(s, s[1:]) if a * b < 0))


def kosu_olc(kdir):
    """Tek koşu -> ölçüt sözlüğü."""
    meta_y = os.path.join(kdir, "meta.csv")
    cik_y = os.path.join(kdir, "cikarim.csv")
    if not os.path.exists(meta_y):
        return None
    meta = list(csv.DictReader(open(meta_y)))
    if not meta:
        return None
    o = {"ad": os.path.basename(kdir)}

    # --- MEKANİZMA (§5.1): ulaşılan çıkarım hızı
    o["cikarim_hz"] = float("nan")
    o["det_ms"] = float("nan")
    if os.path.exists(cik_y):
        cik = list(csv.DictReader(open(cik_y)))
        if len(cik) > 1:
            t = [_f(r["t"]) for r in cik]
            sure = t[-1] - t[0]
            if sure > 1e-6:
                o["cikarim_hz"] = (len(cik) - 1) / sure
            dm = [_f(r.get("det_ms")) for r in cik]
            dm = [x for x in dm if np.isfinite(x) and x > 0]
            if dm:
                # ⛔ MEDYAN KULLANMA — dagilim IKI TEPELI (uyarlanabilir imgsz:
                #   960 ~20 ms, 1920 ~52 ms). Yavas kolun payi %46'dan %53'e
                #   ciktiginda medyan tepe DEGISTIRIYOR ve 24 -> 50 ms sicriyor;
                #   oysa kol ICINDE fark yalnizca %5-10.
                #   (2026-08-24: tam bu artefakti "is parcacigi cikarimi
                #    yavaslatiyor" diye yanlis yorumladim. ORTALAMA ve KOL
                #    MEDYANLARI birlikte raporlanir.)
                a = np.array(dm)
                o["det_ms"] = float(a.mean())
                o["det_ms_hizli"] = float(np.median(a[a < 35])) if (a < 35).any() else float("nan")
                o["det_ms_yavas"] = float(np.median(a[a >= 35])) if (a >= 35).any() else float("nan")
                o["yavas_kol_yuzde"] = 100.0 * float((a >= 35).mean())
            o["cikarim_basari"] = 100.0 * sum(1 for r in cik
                                              if r.get("basarili") == "1") / len(cik)
            # ⭐ GERÇEK TESPİT — kutu HEDEFİN ÜSTÜNDE mi (truth doğrulamalı).
            #   ZORUNLU GEÇERLİLİK EŞİ (§5.2) özellikle TAKİPÇİ için:
            #   takipçi, çıkarım ıskaladığında Kalman ÖNGÖRÜSÜYLE kutu
            #   üretir. "Kutu var mı" diye saymak, YANLIŞ YERE öngörülmüş
            #   kutuyu ÖDÜLLENDİRİR ve kör süreyi sahte düşürür.
            #   Tanım `araclar/tespit_olcu.py` ile BİREBİR: merkez
            #   max(60, 1.5·bek_w) px içinde VE genişlik 0.5-2.0 katı.
            iyi = top = 0
            for r in cik:
                bx, by, bw = (_f(r.get("bek_cx")), _f(r.get("bek_cy")),
                              _f(r.get("bek_w")))
                if not np.isfinite(bx) or not np.isfinite(bw) or bw <= 0:
                    continue                      # hedef kadraj dışı/öngörü yok
                top += 1
                cx, cy, cw = (_f(r.get("vis_cx")), _f(r.get("vis_cy")),
                              _f(r.get("vis_w")))
                if not np.isfinite(cx) or not np.isfinite(cw) or cw <= 0:
                    continue                      # kutu yok -> gerçek tespit değil
                if (np.hypot(cx - bx, cy - by) <= max(60.0, 1.5 * bw)
                        and 0.5 <= cw / bw <= 2.0):
                    iyi += 1
            o["gercek_tespit"] = 100.0 * iyi / top if top > 4 else float("nan")
            o["truth_kare"] = top

            # --- TAKİPÇİ MEKANİZMA SÜTUNLARI (§5.1) ---
            #   takip_aktif : kaç çıkarımda EN AZ BİR aktif iz vardı
            #   takip_tahmin: dönen kutuların kaçı KALMAN ÖNGÖRÜSÜ (ölçüm YOK)
            #   takip_kimlik: kilitli kimlik kaç kez DEĞİŞTİ (yeniden kilit)
            #   ⚠ takip_aktif = 0 olan DENEY koşusu veri noktası DEĞİL,
            #     GEÇERSİZ koşudur. takip_tahmin = 0 ise takipçi köprüleme
            #     YAPMIYOR demektir; kazanç varsa başka yerden geliyordur.
            n_akt = sum(1 for r in cik if _f(r.get("takip_n"), 0) > 0)
            o["takip_aktif"] = 100.0 * n_akt / len(cik)
            kayn = [r.get("takip_kaynak", "") for r in cik]
            dolu = [k for k in kayn if k in ("eslesme", "tahmin")]
            o["takip_tahmin"] = (100.0 * sum(1 for k in dolu if k == "tahmin")
                                 / len(dolu)) if dolu else float("nan")
            idler = [int(_f(r.get("takip_id"), -1)) for r in cik]
            idler = [x for x in idler if x >= 0]
            o["takip_kimlik"] = float(sum(1 for a, b in zip(idler, idler[1:])
                                          if a != b))

    # --- BİRİNCİL: kör süre oranı (SÜRE ağırlıklı, kare değil)
    t = np.array([_f(r["t"]) for r in meta])
    yas = np.array([_f(r.get("vis_yas"), np.nan) for r in meta])
    durum = [r.get("durum", "") for r in meta]
    gorsel = np.array([d == "GORSEL" for d in durum])
    dt = np.diff(t, prepend=t[0] if len(t) else 0.0)
    dt[0] = 0.0
    # yalnız GÖRSEL fazda anlamlı: istasyondayken kutu zaten aranmıyor
    m = gorsel & np.isfinite(yas)
    if m.sum() > 1:
        kor = m & (yas > KOR_ESIK_S)
        o["kor_oran"] = 100.0 * dt[kor].sum() / max(dt[m].sum(), 1e-9)
        o["yas_med"] = float(np.median(yas[m]))
        o["yas_p90"] = float(np.percentile(yas[m], 90))
    else:
        o["kor_oran"] = o["yas_med"] = o["yas_p90"] = float("nan")

    # --- GEÇERLİLİK EŞİ (§5.2)
    o["temas_oran"] = 100.0 * dt[gorsel].sum() / max(dt.sum(), 1e-9)
    conf = np.array([_f(r.get("vis_conf"), np.nan) for r in meta])
    o["tespit_oran"] = 100.0 * float(np.isfinite(conf[gorsel]).mean()) if gorsel.sum() else float("nan")

    # --- REGRESYON (§5.10): ISTASYON fazı istasyon tutma
    ist = np.array([d == "ISTASYON" for d in durum])
    ih = np.array([_f(r.get("ist_hata_m"), np.nan) for r in meta])
    mi = ist & np.isfinite(ih)
    o["ist_hata_med"] = float(np.median(ih[mi])) if mi.sum() else float("nan")
    o["ist_15m_oran"] = 100.0 * float((ih[mi] <= 15.0).mean()) if mi.sum() else float("nan")

    # --- SALINIM (§4)
    sure_g = max(dt[gorsel].sum(), 1e-9)
    cx = np.array([_f(r.get("vis_cx"), np.nan) for r in meta])
    cxg = cx[gorsel] - 960.0                      # kadraj merkezine göre
    o["cx_donus_hz"] = _isaret_donus(cxg) / sure_g
    roll = np.array([_f(r.get("drone_roll"), np.nan) for r in meta])
    o["roll_donus_hz"] = _isaret_donus(roll[gorsel]) / sure_g
    rg = roll[gorsel][np.isfinite(roll[gorsel])]
    o["roll_p90"] = float(np.percentile(np.abs(rg), 90)) if len(rg) else float("nan")
    return o


def _ozet_oku(kok):
    """ozet.csv -> kosu adina gore satir sozlugu (k01, k02 ...).
    tik_hz (KONTROL DONGUSU HIZI) mekanizma kapisinin ikinci yarisidir:
    HZ4'te cikarim hizlandi ama kontrol 40.3 -> 22.3 Hz'e DUSTU."""
    y = os.path.join(kok, "ozet.csv")
    if not os.path.exists(y):
        return []
    return list(csv.DictReader(open(y)))


def kol_ozet(kok):
    """kok bir kosu dizini (logs/AD) ya da GLOB deseni olabilir
    (logs/AD_*). Desen, her kosunun AYRI dizine yazildigi kampanyalar
    icindir -- ayni ada birden cok kez yazmak oncekini EZIYOR (§5.7'de
    yasandi: ISP2'de 8 gecerli kosunun 6'si kayboldu)."""
    if any(c in kok for c in "*?["):
        import glob
        out = []
        for d in sorted(glob.glob(kok)):
            out.extend(kol_ozet(d))
        return out
    kosular = sorted(d for d in os.listdir(kok) if d.startswith("k") and
                     os.path.isdir(os.path.join(kok, d)))
    out = [x for x in (kosu_olc(os.path.join(kok, k)) for k in kosular) if x]
    oz = _ozet_oku(kok)
    for i, x in enumerate(out):                    # ozet satirlari kosu sirasinda
        if i < len(oz):
            r = oz[i]
            for anah, ad in (("tik_hz", "tik_hz"), ("isabet", "isabet"),
                             ("en_yakin_m", "en_yakin_m"),
                             ("devir_menzil", "devir_menzil"),
                             ("gorsel_s", "gorsel_s")):
                x[ad] = _f(r.get(anah))
            x["ihlal"] = (r.get("ihlal") or "-").strip()
            x["sure"] = _f(r.get("sure"))
    # ⛔ GEÇERSİZ KOŞULAR ATILIR (CLAUDE.md §4: "koşu SAYILMAZ").
    #   `ihlal` boş değilse uçuş iptal olmuştur (drone_yok, baglanti_yok,
    #   bant dışı...). 2026-08-24'te ölçüldü: 0.8 saniyede iptal olan bir
    #   koşu, kontrol kolunun istasyon hatası medyanını 6.7 m yerine
    #   96.3 m gösteriyordu — kıyası tamamen anlamsız kılıyordu.
    gecerli = [x for x in out
               if x.get("ihlal", "-") in ("-", "") and _f(x.get("sure"), 0) > 20.0]
    atilan = len(out) - len(gecerli)
    if atilan:
        print("  ⚠ %s: %d GEÇERSİZ koşu atıldı (ihlal/kısa) — §4"
              % (os.path.basename(kok.rstrip("*_")), atilan))
    return gecerli


def main(kdir, hdir, baslik="A/B", et_k="KONTROL", et_h="DENEY",
         tik_esik=35.0, cik_esik=10.0):
    tik_esik = float(tik_esik); cik_esik = float(cik_esik)   # argv -> str gelir
    K, H = kol_ozet(kdir), kol_ozet(hdir)
    if not K or not H:
        print("veri yok"); return
    ad = lambda p: os.path.basename(p)

    def sat(etiket, anah, birim="", ters=False):
        a = [x[anah] for x in K if np.isfinite(x.get(anah, np.nan))]
        b = [x[anah] for x in H if np.isfinite(x.get(anah, np.nan))]
        if not a or not b:
            print("  %-26s   veri yok" % etiket); return
        ma, mb = float(np.median(a)), float(np.median(b))
        iyi = (mb < ma) if not ters else (mb > ma)
        print("  %-26s %8.2f%-3s %8.2f%-3s   %s" %
              (etiket, ma, birim, mb, birim, "H ↑" if iyi else ("=" if abs(ma-mb) < 1e-9 else "K ↑")))

    print("\n" + "=" * 74)
    print("  %s      n(K)=%d  n(H)=%d" % (baslik, len(K), len(H)))
    print("=" * 74)
    print("  %-26s %11s %11s   kazanan" % ("", "KONTROL", "DENEY"))
    print("  %-26s %11s %11s" % ("", et_k, et_h))
    print("  " + "-" * 70)
    print("  ⚙ MEKANİZMA KAPISI (§5.1)")
    sat("KONTROL DÖNGÜSÜ Hz", "tik_hz", "", ters=True)
    sat("ulaşılan çıkarım Hz", "cikarim_hz", "", ters=True)
    sat("çıkarım süresi ORT", "det_ms", "ms")
    sat("  imgsz960 kolu med", "det_ms_hizli", "ms")
    sat("  imgsz1920 kolu med", "det_ms_yavas", "ms")
    sat("  yavaş kolun payı", "yavas_kol_yuzde", "%")
    _tk = [x["tik_hz"] for x in H if np.isfinite(x.get("tik_hz", np.nan))]
    if _tk:
        _kotu = [x for x in _tk if x < tik_esik]
        print("     -> kontrol döngüsü: %d/%d koşu >= %.0f Hz   %s"
              % (len(_tk) - len(_kotu), len(_tk), tik_esik,
                 "✔" if not _kotu else "⛔ %d KOŞU GEÇERSİZ" % len(_kotu)))
    gecti = [x["cikarim_hz"] for x in H if np.isfinite(x.get("cikarim_hz", np.nan))]
    if gecti:
        kotu = [x for x in gecti if x < cik_esik]
        print("     -> çıkarım hızı: %d/%d koşu >= %.0f Hz   %s"
              % (len(gecti) - len(kotu), len(gecti), cik_esik,
                 "✔ KAPI GEÇİLDİ" if not kotu else "⛔ %d KOŞU GEÇERSİZ" % len(kotu)))
    print("\n  ⭐ BİRİNCİL ÖLÇÜT")
    sat("KÖR SÜRE ORANI", "kor_oran", "%")
    sat("kutu yaşı medyan", "yas_med", "s")
    sat("kutu yaşı p90", "yas_p90", "s")
    print("\n  🔒 GEÇERLİLİK EŞİ (§5.2)")
    sat("görsel temas oranı", "temas_oran", "%", ters=True)
    sat("tespit oranı", "tespit_oran", "%", ters=True)
    sat("çıkarım başarı", "cikarim_basari", "%", ters=True)
    sat("⭐GERÇEK tespit", "gercek_tespit", "%", ters=True)
    print("\n  🎯 TAKİPÇİ MEKANİZMASI (§5.1)")
    sat("aktif iz olan çıkarım", "takip_aktif", "%", ters=True)
    sat("kimlik değişimi", "takip_kimlik", "")
    # ⚠ `öngörü oranı` YALNIZ deney kolunda tanımlıdır (kontrol kolunda
    #   takipçi yok -> NaN). İki kollu `sat()` ile basılırsa "veri yok"
    #   der ve MEKANİZMA SÜTUNU görünmez olur (§5.1 kapısı okunamaz).
    for ad, kol in (("kapalı kol", K), ("AÇIK kol", H)):
        v = [x["takip_tahmin"] for x in kol
             if np.isfinite(x.get("takip_tahmin", np.nan))]
        if v:
            print("    öngörü ile dönen kutu (%s): %.1f%%  [koşular: %s]"
                  % (ad, float(np.median(v)),
                     ", ".join("%.0f" % z for z in v)))
    print("\n  ⛔ REGRESYON (§5.10)")
    sat("ISTASYON hata medyan", "ist_hata_med", "m")
    sat("ISTASYON <=15 m oranı", "ist_15m_oran", "%", ters=True)
    print("\n  ◎ İKİNCİL (önceden ilan edildi)")
    sat("isabet", "isabet", "", ters=True)
    sat("en yakın menzil", "en_yakin_m", "m")
    sat("görsel devir menzili", "devir_menzil", "m", ters=True)
    sat("görsel fazda süre", "gorsel_s", "s", ters=True)
    print("\n  〰 SALINIM (§4)")
    sat("cx işaret değişimi", "cx_donus_hz", "/s")
    sat("roll işaret değişimi", "roll_donus_hz", "/s")
    sat("|roll| p90", "roll_p90", "°")
    print("=" * 74)
    if len(K) < 4 or len(H) < 4:
        print("  ⚠ n < 4/kol — bunlar ARA VERİ, KARAR DEĞİL (§5.4)")
    print()


if __name__ == "__main__":
    main(*sys.argv[1:])
