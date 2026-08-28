# -*- coding: utf-8 -*-
"""
================================================================================
ZOR ÖRNEK KAYDEDİCİ — çıkarım anında, kareyi ETİKETİYLE birlikte diske yaz
================================================================================
FİKİR (kullanıcı, 2026-08-25): "hedef aracın ve bizim aracın her an konum ve
rotasyon verisini bildiğimiz için her karede hedefin kadrajda nerede olması
gerektiğini çıkartabiliriz. Hangi anlarda Talon kadrajda olmasına rağmen
detection modeli onu tespit edemiyorsa o kareleri çekelim ve onlardan bir
veri seti oluşturup modeli fine-tune edelim."

⛔⛔ NEDEN SONRADAN MADENCİLİK YAPILAMIYOR (denendi, 2026-08-25)
   Kaydedilmiş kareyi sonradan telemetriyle eşleştirmek DENENDİ ve etiketler
   BOZUK çıktı — kontak sayfasında "7 m" yazan kutu bomboş göğe düştü.
   İki ayrı sebep vardı:
     1. `meta.csv` 1 Hz; kare 0.5 s'de bir yazılıyor. Aynı ana ait iki
        kaydın `bek_*` farkı ölçüldü: medyan 10 px ama p90 808 px,
        maks 48386 px (yansıtma tekilliği).
     2. `meta.csv`'deki `bek_*` YALNIZ tespit varken yazılıyor ve son
        TESPİTİN anına göre hesaplanıyor (`t - tespit_yas`), karenin
        anına göre DEĞİL. Iskalanan karede bu bir saniye öncesinin
        geometrisidir.
   Bu dosya, kaydı ÇIKARIM ANINA taşıyarak iki sebebi de ortadan kaldırır:
   etiket, dedektörün gördüğü karenin KENDİSİNDEN ve AYNI ANIN
   geometrisinden çıkar. Eşleştirme hatası yapısal olarak imkânsız.

⛔ GÜDÜME DOKUNMAZ. Yalnız diske yazar. Hedefin GPS'i burada VERİ SETİ
   ETİKETİ için okunur; güdüm yoluna girmez (§10).

⚠ ETİKET KALİTESİ MENZİLLE DÜŞÜYOR — ölçüldü (n=1051 başarılı tespitte
   geometrik kutu vs modelin kutusu):
       menzil    kutu px   IoU medyan   IoU p10   karar
       0-5 m       240        0.84        0.68    ✅ iyi
       5-10 m      120        0.86        0.62    ✅ iyi
       10-20 m      72        0.74        0.46    ⚠ sınırda
       20-40 m      35        0.57        0.35    ⚠ sınırda
       40-80 m      21        0.55        0.00    ⛔ zayıf
   Varsayılan üst sınır bu yüzden 40 m. Yanlış etikete eğitmek modeli
   İYİLEŞTİRMEZ, BOZAR.

ÇIKTI: YOLO biçimi
    <dizin>/images/<ad>.jpg
    <dizin>/labels/<ad>.txt      "0 cx cy w h" (normalize)
    <dizin>/manifest.csv         menzil, aspekt, kutu_px, conf_esigi...

Env:
    DOW_ZOR_KAYIT=1              aç
    DOW_ZOR_DIZIN=veri/zor       çıktı dizini
    DOW_ZOR_MAKS_MENZIL=40       bu menzilin ötesi kaydedilmez
    DOW_ZOR_MIN_KUTU=14          bundan küçük kutu kaydedilmez (px)
    DOW_ZOR_KENAR=10             kutu kenardan bu kadar içeride olmalı
    DOW_ZOR_MAKS=400             koşu başına üst sınır (disk koruması)
================================================================================
"""
import csv
import os

IMG_W, IMG_H = 1920.0, 1080.0


def _f(ad, v):
    try:
        return float(os.environ.get(ad, v))
    except Exception:
        return float(v)


class ZorKayit:
    def __init__(self, dizin=None):
        self.dizin = dizin or os.environ.get("DOW_ZOR_DIZIN", "veri/zor")
        self.maks_menzil = _f("DOW_ZOR_MAKS_MENZIL", 40.0)
        self.min_kutu = _f("DOW_ZOR_MIN_KUTU", 14.0)
        self.kenar = _f("DOW_ZOR_KENAR", 10.0)
        self.maks = int(_f("DOW_ZOR_MAKS", 400))
        # ⛔ KOŞULAR BİRBİRİNİN ÜSTÜNE YAZMASIN (2026-08-25'te YAŞANDI).
        #   `kosu_yap` her koşuda YENİ bir kaydedici kuruyor. Sayaç sıfırdan
        #   başlayınca 3 koşunun 43 karesi 16'ya düştü — dosya adları
        #   çakıştı ve görüntüler üzerine yazıldı. Manifest 43 satırdı ama
        #   15 ad tekrar ediyordu; sayı doğru, VERİ YOKTU.
        #   Çare: numaralandırma diskteki EN BÜYÜK indisten devam eder.
        self.n = self._sonraki_indis()
        self.yazilan = 0          # bu KOŞUDA yazılan (üst sınır bunu sayar)
        self.atilan = {"tespit_var": 0, "menzil": 0, "kutu": 0,
                       "kadraj": 0, "tekil": 0, "dolu": 0}
        os.makedirs(os.path.join(self.dizin, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.dizin, "labels"), exist_ok=True)
        self._man = open(os.path.join(self.dizin, "manifest.csv"), "a",
                         newline="")
        self._w = csv.DictWriter(self._man, fieldnames=[
            "ad", "t", "menzil_m", "aspekt_deg", "kutu_px", "cx", "cy"])
        if self._man.tell() == 0:
            self._w.writeheader()

    def _sonraki_indis(self):
        """Dizindeki en büyük zor_*_NNNNN indisinden bir sonrası."""
        d = os.path.join(self.dizin, "images")
        en = -1
        if os.path.isdir(d):
            for f in os.listdir(d):
                if not f.endswith(".jpg"):
                    continue
                try:
                    en = max(en, int(f[:-4].rsplit("_", 1)[1]))
                except Exception:
                    pass
        return en + 1

    def belki_kaydet(self, img, csat):
        """Bir çıkarım satırı ver; ZOR ÖRNEKSE kareyi etiketiyle yaz.

        ZOR ÖRNEK = dedektör ıskaladı AMA geometri hedefin kadrajda,
        tamamen içeride ve makul boyutta olduğunu söylüyor."""
        if self.yazilan >= self.maks:
            self.atilan["dolu"] += 1
            return False
        if csat.get("basarili"):
            self.atilan["tespit_var"] += 1
            return False
        bx, by = csat.get("bek_cx"), csat.get("bek_cy")
        bw, R = csat.get("bek_w"), csat.get("menzil_m")
        if None in (bx, by, bw) or bw is None:
            self.atilan["tekil"] += 1
            return False
        # TEKİLLİK KAPISI — yansıtma patladıysa (tan() sonsuza giderse)
        if (abs(bx - 960.0) > 3 * IMG_W or abs(by - 540.0) > 3 * IMG_H
                or not (0.5 <= bw <= 1500.0)):
            self.atilan["tekil"] += 1
            return False
        if R is None or R > self.maks_menzil:
            self.atilan["menzil"] += 1
            return False
        if bw < self.min_kutu:
            self.atilan["kutu"] += 1
            return False
        bh = bw * 0.8
        p = self.kenar
        # kutunun TAMAMI kadrajda ve kenardan içeride (kırpık hedef = kötü etiket)
        if not (p <= bx - bw / 2 and bx + bw / 2 < IMG_W - p
                and p <= by - bh / 2 and by + bh / 2 < IMG_H - p):
            self.atilan["kadraj"] += 1
            return False

        import cv2
        ad = "zor_%s_%05d" % (os.environ.get("DOW_ZOR_ETIKET", "k"), self.n)
        # üzerine yazma paranoyası: ad çakışıyorsa boşta olana kadar ilerle
        while os.path.exists(os.path.join(self.dizin, "images", ad + ".jpg")):
            self.n += 1
            ad = "zor_%s_%05d" % (os.environ.get("DOW_ZOR_ETIKET", "k"), self.n)
        cv2.imwrite(os.path.join(self.dizin, "images", ad + ".jpg"), img,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        with open(os.path.join(self.dizin, "labels", ad + ".txt"), "w") as f:
            f.write("0 %.6f %.6f %.6f %.6f\n"
                    % (bx / IMG_W, by / IMG_H, bw / IMG_W, bh / IMG_H))
        self._w.writerow({"ad": ad, "t": csat.get("t"), "menzil_m": R,
                          "aspekt_deg": csat.get("aspekt_deg"),
                          "kutu_px": round(bw, 1), "cx": round(bx, 1),
                          "cy": round(by, 1)})
        self._man.flush()
        self.n += 1
        self.yazilan += 1
        return True

    def kapat(self):
        try:
            self._man.close()
        except Exception:
            pass
        return self.yazilan, self.atilan


def kur():
    """Env açıksa kaydediciyi kur, değilse None."""
    v = os.environ.get("DOW_ZOR_KAYIT", "0").strip().lower()
    if v in ("0", "", "false", "hayir"):
        return None
    return ZorKayit()
