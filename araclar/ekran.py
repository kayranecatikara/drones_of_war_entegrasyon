# -*- coding: utf-8 -*-
"""EKRAN SEÇİMİ — oyun HANGİ monitörde açılacak, kadraj NEREDEN alınacak.

⛔ NEDEN VAR (2026-08-28, yaşandı):
  `goreve_gir.sh` oyunu sabit `0,0`'a koyuyordu ve yorumu "2. ekrana
  (HDMI-0, 0,0)" diyordu — yani yazıldığında AOC monitörü 0,0'daydı.
  Ekran düzeni sonradan değişti: AOC +1920+0'a gitti, `0,0` dizüstü
  paneli oldu ve orada **GNOME üst çubuğu** var. Oyun çubuğun altına,
  `0,27` konumuna açıldı; yakalanan karenin ilk 27 satırı GNOME çubuğu
  oldu ve oyun 27 px kaydı -> `CY=540` varsayımında **2.9° dikey sapma**.
  Bir kampanya bu yüzden çöpe gidecekti; sayısal kontrol yakaladı.

⭐ ÇÖZÜM İKİ PARÇA:
  1. Oyun, GNOME çubuğunun OLMADIĞI monitöre açılır (birincil olmayan).
     Tercih sırası: adında AOC/2262 geçen -> birincil olmayan -> birincil.
  2. Kadraj, o pencereyi X'e SORARAK bulur (`kadraj.bolge_tazele`).
     Böylece ikisi yapısal olarak uyumsuz kalamaz.

⚠ GNOME üst çubuğu YALNIZ birincil monitördedir. Bu yüzden oyunu
  birincil olmayan monitöre koymak çubuk sorununu kökünden çözer.
"""
import re
import subprocess

TERCIH = ("aoc", "2262")          # bu dizgeleri içeren monitör önceliklidir


def monitorler():
    """xrandr çıktısını ayrıştır -> [(ad, w, h, x, y, birincil_mi, urun_adi)]"""
    try:
        ham = subprocess.check_output(["xrandr", "--listmonitors"],
                                      text=True, timeout=5)
    except Exception:
        return []
    out = []
    for satir in ham.splitlines()[1:]:
        m = re.search(r"\+(\*?)(\S+)\s+(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)", satir)
        if not m:
            continue
        yildiz, ad, w, h, x, y = m.groups()
        out.append((ad, int(w), int(h), int(x), int(y), yildiz == "*", ""))
    return out


def _urun_adlari():
    """mss'ten monitör ÜRÜN adlarını al (AOC2262 gibi). Yoksa boş sözlük."""
    try:
        import mss
        with mss.MSS() as s:
            return {m.get("output"): "%s %s" % (m.get("name", ""),
                                                m.get("unique_id", ""))
                    for m in s.monitors[1:] if m.get("output")}
    except Exception:
        return {}


def hedef_ekran():
    """Oyunun açılacağı monitör. Dönüş: (ad, x, y, w, h, sebep)."""
    mons = monitorler()
    if not mons:
        return ("?", 0, 0, 1920, 1080, "xrandr okunamadi - varsayilan 0,0")
    urun = _urun_adlari()

    # 1) adı/ürünü TERCIH listesinde geçen
    for ad, w, h, x, y, birincil, _ in mons:
        etiket = (ad + " " + urun.get(ad, "")).lower()
        if any(t in etiket for t in TERCIH):
            return (ad, x, y, w, h, "tercih edilen monitor (AOC)")

    # 2) birincil OLMAYAN (GNOME cubugu birincilde durur)
    for ad, w, h, x, y, birincil, _ in mons:
        if not birincil:
            return (ad, x, y, w, h, "birincil olmayan (ust cubuk yok)")

    # 3) tek monitor
    ad, w, h, x, y, _b, _ = mons[0]
    return (ad, x, y, w, h, "tek monitor - ust cubuk KADRAJDA OLABILIR")


if __name__ == "__main__":
    ad, x, y, w, h, sebep = hedef_ekran()
    print("HEDEF EKRAN: %s  +%d+%d  %dx%d" % (ad, x, y, w, h))
    print("SEBEP      : %s" % sebep)
    print()
    print("Bagli monitorler:")
    urun = _urun_adlari()
    for a, W, H, X, Y, b, _ in monitorler():
        print("  %-10s %dx%d +%d+%d %-10s %s"
              % (a, W, H, X, Y, "BIRINCIL" if b else "", urun.get(a, "")))
