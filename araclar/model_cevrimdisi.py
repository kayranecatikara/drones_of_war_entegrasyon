# -*- coding: utf-8 -*-
"""
================================================================================
ÇEVRİMDIŞI MODEL KIYASI — uçmadan ÖNCE akıl sağlığı kontrolü
================================================================================
⛔ BU KANIT DEĞİLDİR (CLAUDE.md §2): "Eski uçuş loglarını yeniden oynatmak.
   Çevrimdışı replay yalnız HİPOTEZ üretir. Kabul kararını sadece taze uçuş
   + video verir." Bu araç YALNIZCA şunun için var:

     1. Model bozuk mu / ölçeği kaymış mı (uçuşu boşa harcamamak için)
     2. İki model FARKLI davranıyor mu — aynı kutuları üretiyorlarsa
        uçuş kampanyası anlamsızdır (§5.1 mekanizma kapısının ön kontrolü)

⚠ EŞLEŞTİRİLMİŞ ÖLÇÜM: iki model AYNI karelerde koşulur, aynı sırayla.
   Böylece kare zorluğu iki kolu eşit etkiler.

⚠ "tespit oranı" tek başına YANILTIR: yanlış-pozitif de tespit sayılır.
   Bu yüzden kutu KONUMU da kıyaslanır — iki model aynı yere mi bakıyor.

Menzil, kareye eşlik eden meta.csv'den alınır (ÖLÇÜM-ONLY).

Kullanım: python3 araclar/model_cevrimdisi.py talon_v3 talon_v3h
================================================================================
"""
import csv
import glob
import json
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Alt süreçte koşar: bir model, bir kare listesi -> JSON
COCUK = r'''
import os, sys, json, warnings, logging
warnings.filterwarnings("ignore"); logging.disable(logging.WARNING)
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[1])
os.environ["DOW_MODEL"] = sys.argv[2]
import cv2
from dow.gorus.dedektor import Dedektor
d = Dedektor(uyarlanabilir=False)
kareler = json.load(open(sys.argv[3]))
ilk = cv2.imread(kareler[0][0])
if ilk is not None: d.isit(ilk)
import time
print("[%s] model yuklendi, %d kare" % (sys.argv[2], len(kareler)),
      file=sys.stderr, flush=True)
cikti = []
t0 = time.time()
for i, (yol, menzil, _bx, _by) in enumerate(kareler):
    im = cv2.imread(yol)          # cv2 BGR okur; dedektor BGR bekler (KANAL)
    if im is None: continue
    b = d.bul(im)
    cikti.append({"yol": yol, "menzil": menzil, "bx": _bx, "by": _by,
                  "kutu": None if b is None else [round(float(x), 1) for x in b]})
    if (i + 1) % 25 == 0:
        gec = time.time() - t0
        print("[%s] %d/%d  %.0f ms/kare  kalan ~%.0f sn"
              % (sys.argv[2], i + 1, len(kareler), 1000 * gec / (i + 1),
                 gec / (i + 1) * (len(kareler) - i - 1)),
              file=sys.stderr, flush=True)
print("JSON:" + json.dumps(cikti))
'''


# ⛔⛔ YALNIZ KANAL DÜZELTMESİ SONRASI KAMPANYALAR.
#   `araclar/kayit.py` 2026-08-25'e kadar kareleri `[:, :, ::-1]` ile, yani
#   TERS KANALLA diske yazıyordu. O karelerde kırmızı/mavi takas edilmiştir
#   ve dedektöre verilince ölçüm ZEHİRLENİR (kanal hatası tam da buydu:
#   gerçek tespit %68.6 -> %32.1). Bu yüzden liste ELLE sınırlıdır.
# ⚠ Yeni kampanya eklerken buraya da eklenmeli.
KAMPANYALAR = ["KAMERA10", "OA_TERMINAL"]


def kare_listesi():
    """Kayıtlı kareleri menzilleriyle eşle (meta.csv, ÖLÇÜM-ONLY)."""
    liste = []
    desen = os.environ.get("MC_KAMPANYA", ",".join(KAMPANYALAR)).split(",")
    kd_hepsi = []
    for k in desen:
        kd_hepsi += glob.glob(os.path.join(KOK, "logs", k.strip(), "*", "kareler"))
    for kd in sorted(kd_hepsi):
        meta = os.path.join(os.path.dirname(kd), "meta.csv")
        menziller = {}
        if os.path.exists(meta):
            for r in csv.DictReader(open(meta)):
                try:
                    menziller[int(float(r["kare"]))] = float(
                        r.get("gercek_menzil") or r.get("hedef_menzil_m") or "nan")
                except Exception:
                    pass
        bek = {}
        if os.path.exists(meta):
            for r in csv.DictReader(open(meta)):
                try:
                    bek[int(float(r["kare"]))] = (float(r["bek_cx"]),
                                                  float(r["bek_cy"]))
                except Exception:
                    pass
        for f in sorted(glob.glob(os.path.join(kd, "*.jpg"))):
            n = os.path.basename(f)
            try:
                i = int(n[1:5])
            except Exception:
                continue
            bx, by = bek.get(i, (float("nan"), float("nan")))
            liste.append([f, menziller.get(i, float("nan")), bx, by])
    return liste


def kos(model, kareler):
    tmp = os.path.join(KOK, "logs", "_kareler_%s.json" % model)
    json.dump(kareler, open(tmp, "w"))
    # -u: TAMPONSUZ. Tamponlu koşuda ilerleme dosyaya HİÇ yazılmıyordu ve
    #     dışarıdan iş "takılmış" görünüyordu (2026-08-26, 34 dk sessizlik).
    pr = subprocess.Popen([sys.executable, "-u", "-W", "ignore", "-c", COCUK,
                           KOK, model, tmp],
                          stdout=subprocess.PIPE, stderr=None, text=True)
    cikti_satir = []
    for satir in pr.stdout:
        cikti_satir.append(satir)
    pr.wait(timeout=3000)
    class _R: pass
    r = _R(); r.stdout = "".join(cikti_satir); r.stderr = ""
    os.remove(tmp)
    for s in r.stdout.splitlines():
        if s.startswith("JSON:"):
            return json.loads(s[5:])
    print((r.stderr or r.stdout)[-500:])
    return None


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "talon_v3"
    b = sys.argv[2] if len(sys.argv) > 2 else "talon_v3h"
    kareler = kare_listesi()
    if not kareler:
        print("⛔ kayıtlı kare yok"); return
    # ⚠ ÖRNEK SINIRI: tüm kareleri koşmak iki model için çok uzun sürüyor.
    #   Menzile göre TABAKALI seyreltme — her menzil bandı temsil edilsin,
    #   yoksa örnek yakın karelere kayar ve uzak menzil hiç ölçülmez.
    ust = int(os.environ.get("MC_ORNEK", "160"))
    if len(kareler) > ust:
        adim = len(kareler) / float(ust)
        kareler = [kareler[int(i * adim)] for i in range(ust)]
        print("  (tabakalı seyreltme: %d kare)" % len(kareler), flush=True)
    print("\n  %d kare, iki model AYNI karelerde koşuluyor..." % len(kareler))
    ra = kos(a, kareler)
    rb = kos(b, kareler)
    if ra is None or rb is None:
        print("⛔ bir kol koşamadı"); return

    # ⭐ TRUTH DOĞRULAMA: kutu, hedefin BEKLENEN piksel yerine yakın mı?
    #   Yakınsa GERÇEK tespit, uzaksa YANLIŞ-POZİTİF. Ham "kutu var mı"
    #   oranı yanlış-pozitifi ÖDÜLLENDİRİR (bu depoda yaşandı) — o yüzden
    #   ikisi AYRI sayılır. Tolerans kutu boyutuyla ölçeklenir.
    def _gercek(d):
        if not d["kutu"]:
            return None
        bx, by = d.get("bx"), d.get("by")
        if bx is None or by is None or bx != bx or by != by:
            return None                      # doğrulanamıyor
        cx, cy, w = d["kutu"][0], d["kutu"][1], d["kutu"][2]
        tol = max(80.0, 1.5 * w)
        return ((cx - bx) ** 2 + (cy - by) ** 2) ** 0.5 <= tol

    BANT = [(0, 5), (5, 10), (10, 20), (20, 30), (30, 50), (50, 999)]
    T = {x: {"n": 0, "a": 0, "b": 0, "ikisi": 0, "sapma": [],
             "ag": 0, "bg": 0, "ay": 0, "by": 0, "dog": 0} for x in BANT}
    for x, y in zip(ra, rb):
        R = x["menzil"]
        bant = next((z for z in BANT if R == R and z[0] <= R < z[1]), None)
        if bant is None:
            continue
        t = T[bant]; t["n"] += 1
        if x["kutu"]: t["a"] += 1
        if y["kutu"]: t["b"] += 1
        ga, gb = _gercek(x), _gercek(y)
        if ga is not None or gb is not None:
            t["dog"] += 1
        if ga is True: t["ag"] += 1
        if ga is False: t["ay"] += 1
        if gb is True: t["bg"] += 1
        if gb is False: t["by"] += 1
        if x["kutu"] and y["kutu"]:
            t["ikisi"] += 1
            t["sapma"].append(((x["kutu"][0] - y["kutu"][0]) ** 2 +
                               (x["kutu"][1] - y["kutu"][1]) ** 2) ** 0.5)

    print("\n" + "=" * 74)
    print("  ÇEVRİMDIŞI KIYAS — %s vs %s   (⛔ KANIT DEĞİL, §2)" % (a, b))
    print("=" * 74)
    print("\n  %-10s %6s %10s %10s %12s %12s" %
          ("menzil", "kare", a, b, "ikisi de", "merkez farkı"))
    print("  " + "-" * 66)
    ta = tb = tn = ti = 0
    for z in BANT:
        t = T[z]
        if not t["n"]:
            continue
        sap = (sum(t["sapma"]) / len(t["sapma"])) if t["sapma"] else float("nan")
        print("  %-10s %6d %9.1f%% %9.1f%% %11.1f%% %10.0f px" %
              ("%d-%d m" % z if z[1] < 999 else "50+ m", t["n"],
               100.0 * t["a"] / t["n"], 100.0 * t["b"] / t["n"],
               100.0 * t["ikisi"] / t["n"], sap))
        ta += t["a"]; tb += t["b"]; tn += t["n"]; ti += t["ikisi"]
    print("  " + "-" * 66)
    if tn:
        print("  %-10s %6d %9.1f%% %9.1f%% %11.1f%%" %
              ("TOPLAM", tn, 100.0 * ta / tn, 100.0 * tb / tn, 100.0 * ti / tn))
    print("\n  ⭐ TRUTH DOĞRULAMALI (kutu beklenen yere yakın mı?)")
    print("  %-10s %8s | %9s %9s | %9s %9s" %
          ("menzil", "doğrul.", a + " gerçek", "yanlış+", b + " gerçek", "yanlış+"))
    print("  " + "-" * 64)
    for z in BANT:
        t = T[z]
        if not t["dog"]:
            continue
        print("  %-10s %8d | %8.1f%% %8.1f%% | %8.1f%% %8.1f%%" %
              ("%d-%d m" % z if z[1] < 999 else "50+ m", t["dog"],
               100.0 * t["ag"] / t["dog"], 100.0 * t["ay"] / t["dog"],
               100.0 * t["bg"] / t["dog"], 100.0 * t["by"] / t["dog"]))
    _d = sum(T[z]["dog"] for z in BANT)
    if _d:
        print("  " + "-" * 64)
        print("  %-10s %8d | %8.1f%% %8.1f%% | %8.1f%% %8.1f%%" %
              ("TOPLAM", _d,
               100.0 * sum(T[z]["ag"] for z in BANT) / _d,
               100.0 * sum(T[z]["ay"] for z in BANT) / _d,
               100.0 * sum(T[z]["bg"] for z in BANT) / _d,
               100.0 * sum(T[z]["by"] for z in BANT) / _d))
    print("""
  ⚠ 'tespit oranı' YANLIŞ-POZİTİFİ de sayar — tek başına iyilik ölçütü
    değildir. 'merkez farkı' küçükse iki model aynı şeye bakıyor demektir.
  ⚠ Kabul kararı YALNIZ taze uçuşla verilir (§2). Bu tablo, uçuş
    kampanyasının anlamlı olup olmadığını söyler.""")


if __name__ == "__main__":
    main()
