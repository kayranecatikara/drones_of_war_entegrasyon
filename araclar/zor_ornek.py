# -*- coding: utf-8 -*-
"""
================================================================================
ZOR ÖRNEK MADENCİLİĞİ — dedektörün ıskaladığı kareleri bul, ETİKETİYLE çıkar
================================================================================
FİKİR (kullanıcı, 2026-08-25): "hedef aracın ve bizim aracın her an konum ve
rotasyon verisini bildiğimiz için her karede hedefin kadrajda nerede olması
gerektiğini çıkartabiliriz. Hangi anlarda Talon kadrajda olmasına rağmen
detection modeli onu tespit edemiyorsa o kareleri çekelim ve onlardan bir
veri seti oluşturup modeli fine-tune edelim."

Literatürdeki adı HARD NEGATIVE / HARD EXAMPLE MINING. Etiket elle
çizilmiyor; geometriden (`KAM.beklenen_kadraj`) türetiliyor.

⛔⛔ ETİKET KALİTESİ KAPISI — BU ARACIN EN ÖNEMLİ PARÇASI
   Yanlış etikete eğitmek modeli İYİLEŞTİRMEZ, BOZAR. Geometrik kutunun
   doğruluğu menzille birlikte düşüyor (ÖLÇÜLDÜ 2026-08-25, n=1051 başarılı
   tespitte geometrik kutu vs modelin kutusu):

       menzil    kutu px   IoU medyan   IoU p10
       0-5 m       240        0.84        0.68
       5-10 m      120        0.86        0.62
       10-20 m      72        0.74        0.46
       20-40 m      35        0.57        0.35
       40-80 m      21        0.55        0.00

   ⚠ Bu bir ALT SINIRDIR: kıyas, geometriyi MODELİN kutusuyla yapıyor ve
     uzak menzilde modelin kutusu da özensiz. Yine de eğitim etiketi için
     kanıt yükü BİZDE — o yüzden varsayılan `--maks-menzil 20`.

   ⚠ Ve asıl acı nokta: ıskalar 30-80 m'de yoğunlaşıyor (tespit %23 / %2.9),
     yani etiketin en zayıf olduğu yerde. Bu aracın çıkardığı kare sayısı
     menzil bandına göre AYRI raporlanır ki bu ödünleşim gizlenmesin.

KADRAJ İÇİ SAYILMA: beklenen merkez kadrajda VE kutunun tamamı kenardan
   `--kenar-pay` piksel içeride (kırpık hedef kötü etikettir).

ÇIKTI: YOLO biçimi — `<cikti>/images/*.jpg` + `<cikti>/labels/*.txt`
   (sınıf 0, normalize cx cy w h) + `manifest.csv` (menzil, aspekt, kaynak).

Kullanım:
    python3 araclar/zor_ornek.py logs/KAMERA10 logs/OA_TERMINAL --cikti veri/zor1
    python3 araclar/zor_ornek.py logs/* --maks-menzil 20 --kontak
================================================================================
"""
import argparse
import csv
import glob
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def kosu_tara(kdizin, a):
    """Bir koşu dizinini tara. Döner: aday listesi.

    ⛔⛔ KARE-TELEMETRİ EŞLEŞTİRMESİ — BU ARACIN EN KIRILGAN YERİ
    İlk sürüm kareyi `meta.csv` ile eşleştiriyordu ve ETİKETLER BOZUKTU:
    kontak sayfasında "5 m" yazan kutular BOMBOŞ göğe düşüyordu. Sebep
    ölçüldü (n=321): meta.csv 1 Hz, cikarim.csv ~9 Hz; aynı ana ait iki
    kaydın `bek_*` farkı medyan 10 px ama **p90 808 px, maks 48386 px**.
    Zaman farkı yalnız 0.035 s — yani sorun gecikme DEĞİL, YANSITMA
    TEKİLLİĞİ: hedef görüş konisinin kenarına gelince tan() patlıyor ve
    minik bir dönüş farkı kutuyu ışınlıyor.

    ÇARE (üçü birden):
      1. Eşleştirme `cikarim.csv` üzerinden, karenin YAKALANDIĞI an
         (`kare_t`) ile yapılır — aynı satırdaki bek_* aynı ana aittir.
      2. TEKİLLİK KAPISI: bek_* kadrajın makul bir katından taşıyorsa
         (|cx-960| > 3*W gibi) o kare ATILIR.
      3. ZAMANSAL TUTARLILIK: komşu çıkarımların bek_* değerleri birbirine
         yakın olmalı; kutu bir karede ışınlanıyorsa o an güvenilmez.
    """
    kare_d = os.path.join(kdizin, "kareler")
    cik = os.path.join(kdizin, "cikarim.csv")
    if not (os.path.isdir(kare_d) and os.path.exists(cik)):
        return []
    R = list(csv.DictReader(open(cik)))
    # kare_t -> satır (aynı an). kare_t yoksa t kullanılır.
    kayit = []
    for i, r in enumerate(R):
        kt = _f(r, "kare_t") or _f(r, "t")
        if kt is None:
            continue
        kayit.append((kt, i, r))
    kayit.sort()
    if not kayit:
        return []

    def _tekil(r):
        """Yansıtma patlamış mı?"""
        bx, by, bw = _f(r, "bek_cx"), _f(r, "bek_cy"), _f(r, "bek_w")
        if None in (bx, by, bw):
            return True
        if abs(bx - 960.0) > 3 * 1920 or abs(by - 540.0) > 3 * 1080:
            return True
        if not (0.5 <= bw <= 1500.0):
            return True
        return False

    def _tutarli(i):
        """Komşu çıkarımlarla tutarlı mı (ışınlanma var mı)?"""
        b = [_f(R[j], "bek_cx") for j in (i - 1, i, i + 1) if 0 <= j < len(R)]
        b = [x for x in b if x is not None]
        if len(b) < 2:
            return False
        return (max(b) - min(b)) <= a.tutarlilik_px

    # kareler: f%04d.jpg -> meta.csv'deki t ile zaman damgası
    meta = os.path.join(kdizin, "meta.csv")
    kare_t = {}
    if os.path.exists(meta):
        for r in csv.DictReader(open(meta)):
            k, t = r.get("kare"), _f(r, "t")
            if k and t is not None:
                kare_t[int(float(k))] = t

    adaylar = []
    atilan = {"tekil": 0, "tutarsiz": 0, "uzak_es": 0}
    for k, t in sorted(kare_t.items()):
        jpg = os.path.join(kare_d, "f%04d.jpg" % k)
        if not os.path.exists(jpg):
            continue
        kt, i, r = min(kayit, key=lambda x: abs(x[0] - t))
        if abs(kt - t) > a.tolerans:
            atilan["uzak_es"] += 1; continue
        if r.get("basarili") == "1":
            continue                       # yalnız ISKALANAN kareler
        if _tekil(r):
            atilan["tekil"] += 1; continue
        if not _tutarli(i):
            atilan["tutarsiz"] += 1; continue
        bx, by, bw = _f(r, "bek_cx"), _f(r, "bek_cy"), _f(r, "bek_w")
        Rm = _f(r, "menzil_m")
        if bw < a.min_kutu or Rm is None or Rm > a.maks_menzil:
            continue
        bh = bw * 0.8
        p = a.kenar_pay
        if not (p <= bx - bw / 2 and bx + bw / 2 < 1920 - p
                and p <= by - bh / 2 and by + bh / 2 < 1080 - p):
            continue
        adaylar.append({"jpg": jpg, "cx": bx, "cy": by, "w": bw, "h": bh,
                        "menzil": Rm, "aspekt": _f(r, "aspekt_deg"),
                        "kosu": kdizin, "kare": k, "atilan": atilan})
    if adaylar:
        adaylar[0]["atilan"] = atilan
    return adaylar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizinler", nargs="+")
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--maks-menzil", type=float, default=20.0)
    ap.add_argument("--min-kutu", type=float, default=12.0)
    ap.add_argument("--kenar-pay", type=float, default=8.0)
    ap.add_argument("--tolerans", type=float, default=0.15)  # s
    ap.add_argument("--tutarlilik-px", type=float, default=200.0)
    ap.add_argument("--kontak", action="store_true")
    a = ap.parse_args()

    kosular = []
    for d in a.dizinler:
        for k in sorted(glob.glob(os.path.join(KOK, d, "*/"))):
            if os.path.isdir(os.path.join(k, "kareler")):
                kosular.append(k.rstrip("/"))
    hepsi = []
    for k in kosular:
        hepsi += kosu_tara(k, a)

    print("\n" + "=" * 70)
    print("  ZOR ÖRNEK MADENCİLİĞİ — ıskalanan ama KADRAJDA olan kareler")
    print("=" * 70)
    print("  taranan koşu: %d | aday kare: %d" % (len(kosular), len(hepsi)))
    if not hepsi:
        print("\n  ⛔ aday yok. Kaydedilmiş kare 1-2 Hz; çıkarım ~9 Hz —")
        print("     ıskalanan anların çoğunun karesi DİSKTE YOK. Veri seti")
        print("     için ayrı bir 'her kareyi kaydet' koşusu gerekir.\n")
        return

    BANT = [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80)]
    print("\n  MENZİL DAĞILIMI (etiket kalitesi menzille düşüyor — gizlenmiyor)")
    print("  %-10s %6s %10s" % ("menzil", "kare", "etiket"))
    print("  " + "-" * 30)
    for b in BANT:
        n = sum(1 for x in hepsi if b[0] <= x["menzil"] < b[1])
        if not n:
            continue
        kal = ("✅ iyi" if b[1] <= 10 else
               "⚠ sınırda" if b[1] <= 40 else "⛔ zayıf")
        print("  %-10s %6d %10s" % ("%d-%d m" % b, n, kal))

    if a.kontak or a.cikti:
        import cv2
        import numpy as np
    if a.kontak:
        n = min(12, len(hepsi))
        sec = hepsi[:: max(1, len(hepsi) // n)][:n]
        kucuk = []
        for x in sec:
            im = cv2.imread(x["jpg"])
            if im is None:
                continue
            x1, y1 = int(x["cx"] - x["w"] / 2), int(x["cy"] - x["h"] / 2)
            x2, y2 = int(x["cx"] + x["w"] / 2), int(x["cy"] + x["h"] / 2)
            cv2.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(im, "%.0fm" % x["menzil"], (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            kucuk.append(cv2.resize(im, (640, 360)))
        if kucuk:
            while len(kucuk) % 3:
                kucuk.append(np.zeros_like(kucuk[0]))
            sat = [np.hstack(kucuk[i:i + 3]) for i in range(0, len(kucuk), 3)]
            yol = os.path.join(KOK, "logs", "zor_ornek_kontak.jpg")
            cv2.imwrite(yol, np.vstack(sat))
            print("\n  ✔ kontak sayfası: logs/zor_ornek_kontak.jpg (%d kare)"
                  % len(kucuk))
            print("    KIRMIZI kutu = geometrinin dediği yer. Hedef içinde mi?")

    if a.cikti:
        import cv2
        kd = os.path.join(KOK, a.cikti)
        os.makedirs(os.path.join(kd, "images"), exist_ok=True)
        os.makedirs(os.path.join(kd, "labels"), exist_ok=True)
        man = []
        for i, x in enumerate(hepsi):
            ad = "zor_%05d" % i
            im = cv2.imread(x["jpg"])
            if im is None:
                continue
            cv2.imwrite(os.path.join(kd, "images", ad + ".jpg"), im)
            with open(os.path.join(kd, "labels", ad + ".txt"), "w") as f:
                f.write("0 %.6f %.6f %.6f %.6f\n"
                        % (x["cx"] / 1920.0, x["cy"] / 1080.0,
                           x["w"] / 1920.0, x["h"] / 1080.0))
            man.append({"ad": ad, "menzil": round(x["menzil"], 1),
                        "aspekt": x["aspekt"], "kutu_px": round(x["w"], 1),
                        "kaynak": x["jpg"]})
        with open(os.path.join(kd, "manifest.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(man[0].keys()))
            w.writeheader(); w.writerows(man)
        print("\n  ✔ veri seti: %s  (%d kare)" % (a.cikti, len(man)))
    print()


if __name__ == "__main__":
    main()
