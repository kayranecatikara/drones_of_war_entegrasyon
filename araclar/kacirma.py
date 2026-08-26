# -*- coding: utf-8 -*-
"""
================================================================================
KAÇIRMA TESPİTİ — "kaç denemede vurduk?"  (BİRİNCİL ÖLÇÜT)
================================================================================
⛔ NEDEN `imha` BİRİNCİL ÖLÇÜT DEĞİL (kullanıcı kuralı 2026-08-26):

    "sen ana değerlendirme kriterini vuruş sayıyorsun ama bu yanlış bir
     kriter, koşuların yüzde 99'unda vuruyoruz aracı; ama bazen ilk
     denemede vuruyoruz bazen birkaç denemede."

  Ölçüm bunu doğruluyor: KAMERA10 5/5, OA_TERMINAL 4/4 ve 4/4, MODELH 5/5
  ve 5/5 — `imha` HER KOLDA TAVANA dayanmış, hiçbir şeyi ayırt etmiyor.
  Ayırt eden değişken KOŞU SÜRESİNDE saklıydı: koşular ya ~11 s (tek
  geçişte vuruş) ya ~31 s (birkaç deneme). Bu araç o gizli değişkeni
  DOĞRUDAN ölçer.

  ⭐ ASIL AMAÇ: hiç kaçırma olmadan İLK DENEMEDE vurmak.

--------------------------------------------------------------------------------
KAÇIRMA NASIL SAYILIR — kullanıcının tarifi birebir

    "bbox büyürken iki araç arasındaki mesafe azalıyorsa ve birden bbox'tan
     hedef çıkarsa ve drone hedef aracı geçer ise (bunu araçların gps
     verisinden çıkartabiliriz) kaçırma sayabiliriz"

  Üç şart, üçü de AYRI kaynaktan — biri yanılırsa diğerleri yakalar:

    1. YAKLAŞMA    menzil düşüyor (GPS truth) VE kutu büyüyor (kamera)
    2. GEÇİŞ       menzil yerel MİNİMUMdan sonra tekrar açılıyor (GPS truth)
                   -> drone hedefi geçti
    3. ISKA        o yerel minimum İSABET EŞİĞİNDEN uzak

  Üçü birden sağlanıyorsa: **KAÇIRMA**.
  Yerel minimum isabet eşiğinin içindeyse: **VURUŞ**.

  ⚠ Kullanıcının "birden bbox'tan hedef çıkarsa" şartı SINIFLANDIRMAYA değil
    TEŞHİSE giriyor: her kaçırma için "geçiş anında görsel temas var mıydı"
    ayrıca raporlanır. Sebebini o ayırır:
      temas VARDI  -> güdüm hatası (hedefi gördü ama vuramadı)
      temas YOKTU  -> görüş hatası (kör geçti)
    Şarta dahil edilseydi "gördüğü halde ıskalayan" koşular sayılmazdı.

--------------------------------------------------------------------------------
⚠ 3B MENZİL ŞART. `menzil_m` sütunu YATAYDIR (dz yok). Hedefin tam
  üstünden/altından geçen drone yatayda yakın görünür ve kaçırma
  KAÇIRILIR. Bu yüzden `menzil3_m` tercih edilir; yoksa 2B'ye düşülür ve
  raporda AÇIKÇA söylenir (eski koşularda o sütun yok).

⚠ ÖRNEKLEME (§5.3): çıkarım logu ~9 Hz. Buluşmada kapanma ~10 m/s ->
  örnekler arası ~1.1 m. İsabet eşiği 2 m olduğu için yerel minimum
  1 örnek kaçırılırsa ıska sayılabilir. Bu yüzden minimum, komşu örneklere
  PARABOL oturtularak inceltilir.

Kullanım:
    python3 araclar/kacirma.py logs/KAMERA10
    python3 araclar/kacirma.py logs/OA_TERMINAL --esik 2.0
================================================================================
"""
import argparse
import csv
import glob
import os
import statistics as st
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _f(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "nan") else None
    except Exception:
        return None


def seri_oku(kdizin):
    """(t, menzil, kutu_w, tespit) serisi + hangi menzil sütunu kullanıldı."""
    yol = os.path.join(kdizin, "cikarim.csv")
    if not os.path.exists(yol):
        return None, None
    R = list(csv.DictReader(open(yol)))
    if not R:
        return None, None
    sutun = "menzil3_m" if any(_f(r, "menzil3_m") is not None for r in R) \
        else "menzil_m"
    seri = []
    t0 = _f(R[0], "t") or 0.0
    for r in R:
        m = _f(r, sutun)
        t = _f(r, "t")
        if m is None or t is None:
            continue
        seri.append({"t": t - t0, "R": m, "w": _f(r, "vis_w") or 0.0,
                     "tespit": r.get("basarili") == "1",
                     "durum": r.get("durum", "")})
    return seri, sutun


def _parabol_min(a, b, c):
    """Üç eşit aralıklı örnekten gerçek minimumu kestir (§5.3 inceltme).
    Dönüş: (kayma -1..1, minimum değeri)."""
    payda = a - 2.0 * b + c
    if abs(payda) < 1e-9:
        return 0.0, b
    d = 0.5 * (a - c) / payda
    if abs(d) > 1.0:
        return 0.0, b
    return d, b - 0.25 * (a - c) * d


def gecisleri_bul(seri, acilma_m=6.0, en_az_yaklasma_m=5.0):
    """Menzil serisindeki GEÇİŞLERİ bul — ALTERNATİF UÇ NOKTA + BELİRGİNLİK.

    ⭐ ÜÇÜNCÜ HAL. Önceki iki hal de veriyle çürütüldü, ikisi de burada
    kayıtlı ki tekrarlanmasın:

      1. "monoton yürü" — minimumdan iki yana monoton yürüyordu. ÇİFT DİP'te
         çöküyordu: OA_TERMINAL/0__t1 @23.2 s serisi
             1.0 -> 2.2 -> 2.6 -> 1.4 -> 1.7 -> 4.5 -> ... -> 14.0
         TEK geçiştir, ama monoton yürüyüş ikiye bölüp iki yarıyı da
         eşiğin altında bırakıp ELİYORDU. (Elle sayımla çelişti.)

      2. "koşan minimum + sıfırla" — geçiş yayınlayınca sıfırlıyordu.
         UZAKLAŞMA fazında (kalkış tırmanışı, ıska sonrası dönüş) menzil
         sürekli yükseldiği için HER ADIMDA yeniden tetikleniyor ve
         79 m'lik sahte 'kaçırma'lar üretiyordu.

    Doğrusu: uç noktalar SIRAYLA aranır — bir minimum onaylandıktan sonra
    yeni minimum aranmadan ÖNCE bir maksimum onaylanmalıdır. Böylece tek
    yönlü uzaklaşma yeni geçiş üretemez. Onaylanan her minimumun
    BELİRGİNLİĞİ (iki yanındaki tepelerin küçüğü eksi minimum) ayrıca
    `en_az_yaklasma_m` eşiğini geçmelidir — "gerçekten yaklaştı mı".
    """
    n = len(seri)
    if n < 5:
        return []
    R = [x["R"] for x in seri]

    # --- alternatif uç noktalar (histerezis) ---
    uclar = []                       # [(tur, indeks)] tur: "min" | "max"
    durum = "min"                    # önce bir minimum arıyoruz
    uc = R[0]
    uc_i = 0
    for i in range(1, n):
        if durum == "min":
            if R[i] < uc:
                uc, uc_i = R[i], i
            elif R[i] - uc >= acilma_m:
                uclar.append(("min", uc_i))
                durum, uc, uc_i = "max", R[i], i
        else:
            if R[i] > uc:
                uc, uc_i = R[i], i
            elif uc - R[i] >= acilma_m:
                uclar.append(("max", uc_i))
                durum, uc, uc_i = "min", R[i], i

    gecisler = []
    for sira, (tur, i) in enumerate(uclar):
        if tur != "min":
            continue
        # iki yandaki tepeler
        sol = max(R[:i + 1]) if i > 0 else R[0]
        for t2, i2 in uclar[sira + 1:]:
            if t2 == "max":
                sag = R[i2]
                break
        else:
            sag = max(R[i:]) if i < n - 1 else R[-1]
        belirginlik = min(sol, sag) - R[i]
        if belirginlik < en_az_yaklasma_m:
            continue
        _, Rmin = _parabol_min(R[max(0, i - 1)], R[i], R[min(n - 1, i + 1)])
        pencere = [x for x in seri[max(0, i - 20):i + 1] if x["tespit"]]
        yakin = seri[max(0, i - 3):i + 4]
        temas = sum(1 for x in yakin if x["tespit"])
        gecisler.append({
            "t": seri[i]["t"], "Rmin": max(0.0, Rmin),
            "kapanma": sol - R[i], "acilma": sag - R[i],
            "kutu_buyudu": (len(pencere) >= 3 and
                            pencere[-1]["w"] > pencere[0]["w"]),
            "temas_orani": temas / max(1, len(yakin)),
            "kutu_px": seri[i]["w"], "gecti": True,
            "durum": seri[i]["durum"],
        })
    return gecisler


def vurus_indeksi(seri, sicrama_m=10.0):
    """VURUŞ ANI = menzilin ANİDEN SIÇRADIĞI yer (hedef yok oldu).

    ⭐ BU, ÖLÇÜTÜN EN ÖNEMLİ PARÇASI (2026-08-26'da veri gösterdi).
    Önce "Rmin <= 2 m ise vuruş" diye bir EŞİK TAHMİNİ kullanıyordum ve
    YANLIŞTI: ham seride 1.4 m ve 0.9 m'ye kadar giren geçişler var ve
    hedef ÖLMÜYOR, menzil tekrar 12-14 m'ye açılıyor. Yani yakınlık
    vuruşun kanıtı değil.

    Gerçek vuruş imzası tartışmasız: hedef ölünce yeniden doğuyor ve
    menzil TEK ÖRNEKTE sıçrıyor —
        0__t1:  1.0 m -> 22.8 m
        1__t2:  0.4 m -> 29.5 m
    Bu sıçramadan ÖNCEKİ her geçiş, tanımı gereği KAÇIRMADIR. Böylece
    isabet yarıçapı TAHMİN ETMEK GEREKMİYOR.
    """
    for i in range(len(seri) - 1):
        if seri[i + 1]["R"] - seri[i]["R"] >= sicrama_m:
            return i
    return None


def kosuyu_coz(kdizin, sicrama=10.0, acilma=6.0, en_az_yaklasma=5.0):
    seri, sutun = seri_oku(kdizin)
    if not seri:
        return None
    vi = vurus_indeksi(seri, sicrama)
    # ⛔ SIÇRAMADAN SONRASI ATILIR: hedef yeniden doğdu, o menziller
    #   bu buluşmaya ait değil. (Eskiden dahil ediliyordu ve "en yakın
    #   0.00" gibi sahte sayılar üretiyordu.)
    calisma = seri[:vi + 1] if vi is not None else seri
    gec = gecisleri_bul(calisma, acilma_m=acilma,
                        en_az_yaklasma_m=en_az_yaklasma)
    # ⛔ GERÇEKTEN GEÇMİŞ OLMALI. `gecti` bayrağı, minimumdan sonra menzilin
    #   `acilma` kadar AÇILDIĞINI söyler. Bu filtre olmadan sürekli bir
    #   yaklaşmanın içindeki 0.1-0.3 m'lik gürültü kıpırtıları ayrı deneme
    #   sayılıyordu (0__t1'de 17.1/16.8/16.4 üçlüsü — elle sayımla çeliştiği
    #   için yakalandı).
    gec = [g for g in gec if g["gecti"]]
    # vuruş anındaki son yaklaşma geçiş sayılmaz -> kalan HEPSİ kaçırma
    if vi is not None and gec and gec[-1]["t"] >= calisma[-1]["t"] - 1.0:
        gec = gec[:-1]
    son_R = min((s["R"] for s in calisma[-4:]), default=float("nan"))
    return {
        "ad": os.path.basename(os.path.dirname(kdizin)) + "/" +
              os.path.basename(kdizin),
        "sutun": sutun, "sure": calisma[-1]["t"],
        "vurdu": vi is not None,
        "gecis": gec, "kacirma": gec, "n_kacirma": len(gec),
        "son_R": son_R,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin", nargs="?", default="logs/KAMERA10")
    ap.add_argument("--sicrama", type=float, default=10.0,
                    help="menzil bu kadar sıçrarsa VURUŞ (hedef yok oldu)")
    ap.add_argument("--acilma", type=float, default=6.0,
                    help="minimumdan sonra bu kadar açılırsa GEÇTİ sayılır")
    ap.add_argument("--detay", action="store_true", help="her geçişi listele")
    a = ap.parse_args()

    dizinler = sorted(glob.glob(os.path.join(KOK, a.dizin, "*", "cikarim.csv")))
    dizinler = [os.path.dirname(x) for x in dizinler]
    if not dizinler:
        dizinler = sorted(glob.glob(os.path.join(KOK, a.dizin + "*", "*",
                                                 "cikarim.csv")))
        dizinler = [os.path.dirname(x) for x in dizinler]
    if not dizinler:
        print("⛔ cikarim.csv bulunamadı: %s" % a.dizin)
        return

    sonuc = [x for x in (kosuyu_coz(d, a.sicrama, a.acilma) for d in dizinler) if x]
    if not sonuc:
        print("⛔ çözümlenebilir koşu yok")
        return

    sutunlar = set(s["sutun"] for s in sonuc)
    print("\n" + "=" * 78)
    print("  KAÇIRMA TESPİTİ — %s" % a.dizin)
    print("  vuruş = menzil sıçraması >=%.0f m · geçiş açılması >=%.0f m"
          % (a.sicrama, a.acilma))
    print("  menzil sütunu: %s" % ", ".join(sorted(sutunlar)))
    if "menzil_m" in sutunlar:
        print("  ⚠ 2B MENZİL kullanıldı (menzil3_m yok) — hedefin tam")
        print("    üstünden/altından geçen drone YAKIN görünür, kaçırma")
        print("    SAYILAMAYABİLİR. Yeni koşularda 3B sütun var.")
    print("=" * 78)
    print("\n  %-18s %7s %10s %10s %10s   %s"
          % ("koşu", "süre", "⭐KAÇIRMA", "sonuç", "son R", "ıska mesafeleri (m)"))
    print("  " + "-" * 74)
    top_k = 0
    ilk_denemede = 0
    for s in sonuc:
        gec_m = " ".join("%.1f" % g["Rmin"] for g in s["gecis"]) or "-"
        print("  %-18s %6.1fs %10d %10s %10s   %s"
              % (s["ad"], s["sure"], s["n_kacirma"],
                 "VURDU" if s["vurdu"] else "vuramadı",
                 "%.2f" % s["son_R"], gec_m))
        top_k += s["n_kacirma"]
        if s["n_kacirma"] == 0:
            ilk_denemede += 1
    print("  " + "-" * 74)
    n = len(sonuc)
    print("  %-18s %6s %10d %10s" % ("TOPLAM", "", top_k, ""))
    print("\n  ⭐ İLK DENEMEDE VURUŞ : %d/%d  (%%%.0f)"
          % (ilk_denemede, n, 100.0 * ilk_denemede / n))
    print("     koşu başına kaçırma: medyan %.1f  ortalama %.2f"
          % (st.median([s["n_kacirma"] for s in sonuc]),
             sum(s["n_kacirma"] for s in sonuc) / n))

    # ---- TEŞHİS: kaçırmaların sebebi ----
    tum_k = [g for s in sonuc for g in s["kacirma"]]
    if tum_k:
        korr = sum(1 for g in tum_k if g["temas_orani"] < 0.5)
        print("\n  KAÇIRMALARIN SEBEBİ (geçiş anında görsel temas)")
        print("     temas YOKTU (kör geçti)  : %2d/%d  -> GÖRÜŞ hatası"
              % (korr, len(tum_k)))
        print("     temas VARDI (gördü, ıskaladı): %2d/%d  -> GÜDÜM hatası"
              % (len(tum_k) - korr, len(tum_k)))
        rr = [g["Rmin"] for g in tum_k]
        print("     ıska mesafesi: medyan %.1f m  en iyi %.1f m  en kötü %.1f m"
              % (st.median(rr), min(rr), max(rr)))
        kb = sum(1 for g in tum_k if g["kutu_buyudu"])
        print("     kutu büyüyordu (yaklaşma kamerada da görünür): %d/%d"
              % (kb, len(tum_k)))

    if a.detay:
        print("\n  --- GEÇİŞ DETAYI ---")
        for s in sonuc:
            print("\n  %s" % s["ad"])
            for g in s["gecis"]:
                etiket = "KAÇIRMA"
                print("     %6.1fs  Rmin %6.2f m  kapanma %5.1f  açılma %5.1f"
                      "  kutu %4.0f px  temas %%%3.0f  %s"
                      % (g["t"], g["Rmin"], g["kapanma"], g["acilma"],
                         g["kutu_px"], 100 * g["temas_orani"], etiket))
    print()


if __name__ == "__main__":
    main()
