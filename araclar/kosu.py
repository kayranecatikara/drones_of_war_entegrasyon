# -*- coding: utf-8 -*-
"""
================================================================================
KOŞU ARACI — bekçili, kayıtlı, OTOMATİK YENİDEN BAŞLATAN test koşumu
================================================================================
DoW'un Gazebo'ya göre ASIL AVANTAJI: bir koşu bitince (çarpma/ıska) `E` ile
saniyeler içinde yenisi başlar. Gazebo'da bir koşu ~5 dk kurulum istiyordu.
Bu araç o avantajı kullanır: N koşuyu arka arkaya, insan müdahalesi olmadan.

Kullanım:
    python3 araclar/kosu.py <ad> [koşu_sayısı] [koşu_süresi_s]

Her koşu için:
    logs/<ad>/k01/meta.csv + kareler/     (0.5 s'de bir kare + telemetri)
    logs/<ad>/ozet.csv                    (koşu başına özet satırı)

BEKÇİ: irtifa tavanı / hedeften uzaklaşma / spawn'dan uzaklaşma / donmuş
telemetri / kopuk bağlantı -> koşu ANINDA iptal, sebebiyle kaydedilir ve
yenisi başlar. "Sapıtmış uçuştan analiz yapmaya çalışmak" biter.
================================================================================
"""
import csv
import math
import os
import subprocess
import sys
import threading
import time

import numpy as np
import mss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import deque

from dow.ayarlar import Ayar


def _b(anahtar, varsayilan=False):
    """env bayrağı oku (kosu.py yerel yardımcısı)."""
    return os.environ.get(anahtar, "1" if varsayilan else "0").strip() \
        not in ("0", "", "false")
from dow.ana import Beyin
from dow import panel as PANEL
from dow.gorus import kamera as _KAM


def _telem_gonder(tel, port=8801):
    """Güdüm telemetrisini panele yaz.

    ⚡ ARTIK SÜREÇ İÇİ. Eskiden her 5 tikte bir localhost'a HTTP POST
    atılıyordu (bağlantı kurma + 0.25 s zaman aşımı riski, kontrol
    döngüsünün İÇİNDE). Panel aynı süreçte koştuğu için doğrudan yazıyoruz."""
    PANEL.telem_yaz(tel)
from araclar.bekci import Bekci
from araclar.kayit import Kayit
from araclar.kadraj import (BOLGE, grab_bgr, hud_parlak, ucusta_mi,
                            gorev_bitti_mi, gorev_yeniden_oyna,
                            oyunu_one_al, yeniden_dogur, hazirla)


# ==============================================================================
# GÖRÜŞ İŞ PARÇACIĞI — TEK ekran kopyalayıcı, TEK dedektör (ikisi de tavanlı)
# ==============================================================================
# ⛔ NEDEN (ölçüldü 2026-08-22, GA04 vs GV11):
#   Eskiden ekranı İKİ süreç birden kopyalıyordu (izleyici.py sınırsız hızda,
#   kontrol döngüsü her tikte) ve YOLO da iki yerde koşuyordu. Oyun aynı GPU
#   ve aynı X sunucusunda olduğu için istasyon tutma 5.3 m -> 25.3 m'ye
#   BOZULDU, istenen hız 120 s boyunca 33 m/s tavanında doyumda kaldı.
#   Artık: yakalama Ayar.PANEL_YAKALA_HZ (30), dedektör Ayar.PANEL_DET_HZ (5).
#   Kontrol döngüsü ARTIK HİÇ tam kare kopyalamaz — bu iş parçacığının
#   bıraktığı son kareyi kullanır ("latest-wins", bekleme yok).
_gorus_dur = threading.Event()
_gorus_isp = [None]              # iş parçacığı tutamağı (temiz kapanış için)
_gorus_kilit = threading.Lock()
_gorus = {"img": None, "t": 0.0, "n": 0, "tespit": None,
          "tespit_t": 0.0, "hud": 0.0,
          # ⭐ Ayar.GORUS_ISP için: beyin tutamacı (iş parçacığı beyinden ÖNCE
          #   başlıyor, bu yüzden sonradan konur) ve kontrol döngüsünün
          #   boşaltacağı çıkarım kuyruğu. CSV'yi TEK iş parçacığı yazsın diye
          #   satır burada KURULMAZ, yalnız ham sonuç biriktirilir.
          "beyin": None, "bekleyen": []}


def _gorus_isi(det):
    """Ekranı sabit hızda kopyala, dedektörü koştur, panele bas.

    ⭐ Ayar.GORUS_ISP AÇIKKEN görsel güdüm çıkarımı da BURADA koşar
    (yer-kontrol `model-fps` mimarisi: `dedektor_dongusu` ayrı iş parçacığı).
    Kontrol döngüsü artık YOLO'yu beklemez, son kutuyu okur.
    ÖLÇÜLDÜ (HZ4): çıkarım kontrol döngüsünün içindeyken 16 Hz'e çıkarmak
    kontrolü 40.3 -> 22.3 Hz'e düşürüyor ve araç istasyonu tutamıyor."""
    sct = mss.mss()
    son_det = 0.0
    son_gt = 0.0                       # görsel güdüm çıkarımı zamanlayıcısı
    dt_yak = 1.0 / max(1.0, Ayar.PANEL_YAKALA_HZ)
    while not _gorus_dur.is_set():
        t = time.time()
        img = grab_bgr(sct)                     # sürekli BGR (ultralytics BGR bekler)
        pk = hud_parlak(img[850:1060, 80:320])   # kanal sırasından bağımsız
        # Görsel güdüm AÇIKKEN dedektörü BURADA koşturmayız — kontrol döngüsü
        # zaten koşturuyor; iki YOLO = oyunu aç bırakan hatanın ta kendisi.
        det_kostu = (det is not None and Ayar.DEDEKTOR_GOSTER
                     and not Ayar.GORSEL_AKTIF
                     and (t - son_det) >= 1.0 / max(0.1, Ayar.PANEL_DET_HZ))
        if det_kostu:
            son_det = t
            tespit = det.bul(img)
            PANEL.fps_isaretle("dedektor")
            PANEL.tespit_isaretle(tespit is not None)   # şerit YALNIZ burada
        # ⭐ GÖRSEL GÜDÜM ÇIKARIMI — GORUS_ISP açıkken kontrol döngüsü yerine
        #   BURADA. GORSEL_DET_HZ üst sınır olarak kalır (sınırsız değil).
        _beyin = _gorus["beyin"]
        _g_kostu = (Ayar.GORUS_ISP and Ayar.GORSEL_AKTIF and _beyin is not None
                    and (t - son_gt) >= 1.0 / max(0.1, Ayar.GORSEL_DET_HZ))
        _g_tespit = None
        if _g_kostu:
            son_gt = t
            _g_tespit = _beyin.gorsel_tik(img, t, t)
            PANEL.fps_isaretle("dedektor")
            PANEL.tespit_isaretle(_g_tespit is not None)
        with _gorus_kilit:
            if _g_kostu and _g_tespit is not None:
                # ⛔ YALNIZ BAŞARILI çıkarımda güncelle — `beyin._son_tespit`
                #   ile AYNI anlam. Iskada silmek paneli titretiyor ve
                #   ölçütü bozuyordu (bkz. kontrol döngüsündeki not).
                _gorus["tespit"] = _g_tespit
                _gorus["tespit_t"] = t
            if _g_kostu:
                # tani ANLIK GÖRÜNTÜSÜ — kontrol döngüsü CSV satırını kurar
                _gorus["bekleyen"].append((t, _g_tespit, dict(_beyin.tani)))
            _gorus["img"] = img; _gorus["t"] = t; _gorus["n"] += 1
            _gorus["hud"] = pk
            # ⛔ TESPİT YAŞAR: yakalama 15 Hz, çıkarım 5 Hz. Çıkarımın
            #   koşmadığı karelerde kutuyu SİLMEK, kayıt karelerinin 2/3'ünü
            #   sahte "tespit yok" yapıyordu (duman testi: ham %70 yerine
            #   %13.5). Kutu, bir sonraki çıkarıma kadar geçerlidir.
            if det_kostu:
                _gorus["tespit"] = tespit
                _gorus["tespit_t"] = t
            son_tespit = _gorus["tespit"]
        PANEL.fps_isaretle("yakala")
        # ⛔ KAYNAK KAPISI (2026-08-25): yakalama TÜM EKRANA bakıyor; oyunun
        #   üstüne pencere gelirse panel oyunu değil ONU yayınlar ve operatör
        #   fark etmez. HUD imzası yoksa kareyi YAYINLAMA — son iyi kare
        #   ekranda kalsın, arayüz de uyarı bassın. Eşik `ucusta_mi_hud` ile
        #   AYNI (0.05); ölçüldü: oyun 0.126, üstü kapalıyken 0.001.
        #   ⚠ Güdüm bundan ETKİLENMEZ: kontrol döngüsü kareyi `_gorus["img"]`
        #     üzerinden ayrıca okur, `kare_koy` yalnız paneli besler.
        _kare_oyun = pk > 0.05
        PANEL.kaynak_isaretle(_kare_oyun, pk)
        if _kare_oyun:
            PANEL.kare_koy(img, son_tespit, olcek=Ayar.PANEL_OLCEK)
        kalan = dt_yak - (time.time() - t)
        if kalan > 0:
            time.sleep(kalan)


def gorus_durdur(sure=2.0):
    """Görüş iş parçacığını TEMİZ durdur.
    ⚠ Yoksa yorumlayıcı kapanırken parçacık hâlâ sct.grab/cv2 içindeyken
      yıkılıyor ve süreç 'terminate called without an active exception'
      ile çekirdek döküyor. Çıktı yazıldıktan sonra olduğu için zararsız
      ama kampanya kabuk betiğini hata koduyla düşürüyor."""
    _gorus_dur.set()
    if _gorus_isp[0] is not None:
        _gorus_isp[0].join(timeout=sure)


def _son_kare():
    with _gorus_kilit:
        return _gorus["img"], _gorus["hud"], _gorus["n"], _gorus["t"]


def _tespit_yaz(d):
    with _gorus_kilit:
        _gorus["tespit"] = d
        _gorus["tespit_t"] = time.time()


def _gorevi_yeniden_kur(zaman_asimi=240):
    """⛔ SON ÇARE: 'E' ile yeniden doğuş yetmediğinde GÖREVİ baştan kurar.

    NEDEN (2026-08-22): hedefi VURUNCA drone yok oluyor ve oyun bazen
    görev-sonu ekranına düşüyor; orada 'E' hiçbir şey yapmıyor. GV08'de
    ilk koşu ISABETLE bitti, kalan 5 koşu 'görev başlatılamadı' dedi ve
    kampanya boşa gitti. Kullanıcının istedigi 'sorun olursa durdur,
    yeniden başlat' mekanizmasının eksik kalan parçası buydu."""
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    betik = os.path.join(kok, "calistirma_betikleri", "goreve_gir.sh")
    print("  [görev yeniden kuruluyor — bu ~2 dk sürer]", flush=True)
    try:
        subprocess.run([betik], timeout=zaman_asimi,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  görev kurulamadı: {e}", flush=True); return False
    for _ in range(20):
        with mss.mss() as sct:
            img = np.array(sct.grab(BOLGE))[:, :, :3]
        if ucusta_mi(img): return True
        time.sleep(2.0)
    return False


def _yeni_gorev(beyin=None):
    """Drone'u yeniden doğur; olmazsa GÖREVİ baştan kur.

    ⭐ SIRA ÖNEMLİ (2026-08-24, HZ4'te yaşandı): önce GÖREV-SONU ekranı
    sınanır. Sistem hedefi VURUNCA oyun 'MISSION COMPLETED' ekranına düşüyor
    ve SDK 12345 portunu KAPATIYOR; orada 'E' hiçbir şey yapmaz. Eskiden
    4 kez boşuna 'E' denenip 2 dakikalık tam yeniden başlatmaya gidiliyordu
    ve kampanya yine de ölüyordu — HZ4'ün ilk denemesinde 8 uçuşun 7'si
    koşulamadı. PLAY AGAIN yolu ~15 s ve doğrudan çalışıyor."""
    with mss.mss() as sct:
        img0 = np.array(sct.grab(BOLGE))[:, :, :3]
    if gorev_bitti_mi(img0):
        print("  [görev-sonu ekranı — PLAY AGAIN ile yeniden oynanıyor]", flush=True)
        gorev_yeniden_oyna()
        for _ in range(3):
            with mss.mss() as sct:
                img = np.array(sct.grab(BOLGE))[:, :, :3]
            if ucusta_mi(img):
                if beyin is not None:
                    try: beyin.b.yeniden_bagla()
                    except Exception: pass
                return True
            yeniden_dogur(); time.sleep(1.0)
    for _ in range(4):
        yeniden_dogur()
        with mss.mss() as sct:
            img = np.array(sct.grab(BOLGE))[:, :, :3]
        if ucusta_mi(img):
            return True
        oyunu_one_al(); time.sleep(1.0)
    # 'E' yetmedi -> görevi baştan kur
    if not _gorevi_yeniden_kur():
        return False
    if beyin is not None:
        try: beyin.b.yeniden_bagla()
        except Exception: pass
    return True


def _truth_aspekt(beyin, dp, hp):
    """Hedefin O ANDA bize gösterdiği yüz + menzil. ÖLÇÜM-ONLY.

    aspekt: 0° = tam KUYRUK (bizden uzaklaşıyor), 90° = yandan,
            180° = kafa kafaya.
    ÖLÇÜLDÜ 2026-08-24 (2763 kare): tespit oranı kuyrukta %95, yandan %35.
    Model kuyruk görüntüsüyle eğitilmiş; aspekt tespiti belirleyen EN GÜÇLÜ
    etken (r = -0.45; hedefin yatışı -0.15, bizim yatışımız -0.23)."""
    out = {}
    if not hp or not dp: return out
    dx, dy = hp[0] - dp[0], hp[1] - dp[1]
    out["menzil_m"] = round(math.hypot(dx, dy), 1)
    # ⭐ 3B MENZİL (2026-08-26) — KAÇIRMA TESPİTİ İÇİN ZORUNLU.
    #   `menzil_m` YATAYDIR (dz yok). Kaçırma, "en yakın geçiş noktası"nın
    #   yerel minimumlarından bulunuyor; hedefin tam üstünden/altından geçen
    #   bir drone yatayda YAKIN görünür ve ıska KAÇIRILIR. 3B menzil şart.
    #   ⛔ ÖLÇÜM-ONLY: güdüm bu sütunu görmez (§10; bekçi B1/B18/B19).
    out["menzil3_m"] = round(math.dist(dp, hp), 1)
    # kapanma işareti için hedefin gidiş yönüne izdüşüm: + = biz GERİDEYİZ
    #   (henüz geçmedik), - = hedefi GEÇTİK. Yerel minimum bulmanın yanında
    #   ikinci, bağımsız bir "geçti mi" kanıtı.
    out["dz_m"] = round(hp[2] - dp[2], 1)
    try:
        out["drone_roll"] = round(math.degrees(beyin.b.yonelim()[0]), 1)
    except Exception:
        pass
    try:
        hr = beyin.b.hedef_yonelim()          # (roll, pitch, yaw) derece
        out["hedef_roll"] = round(hr[0], 1)
        los = math.degrees(math.atan2(dy, dx))          # bizden hedefe
        out["aspekt_deg"] = round(abs(((hr[2] - los + 180.0) % 360.0) - 180.0), 1)
    except Exception:
        pass
    return out


class CikarimKaydi:
    """⭐ HER ÇIKARIMI ayrı ayrı yazar (meta.csv 2 Hz; bu, çıkarım hızında).

    NEDEN GEREKTİ (2026-08-24): tespit boşluklarının süresini ölçmek
    istedim ama meta.csv 0.5 s aralıklı. 9 Hz çıkarımda %54 başarıyla
    ortalama boşluk 1.85 çıkarım ≈ 0.2 s — yani ASIL OLAY meta.csv'nin
    örnekleme aralığının ALTINDA kalıyor ve görünmüyor (§5.3: ölçütün
    örnekleme hızı, ölçtüğü şeyin en az 5 katı olmalı).

    Bu kayıt şunu cevaplayacak: kutu kaybolunca KISA boşluklarda (0.1-0.4 s)
    konumu ileri taşımak mı dondurmak mı daha isabetli? 0.5 s ve üstünde
    dondurma kazanıyordu (ölçüldü), ama gerçek boşluklar oradan kısa.

    ⚠ ÖLÇÜM-ONLY: truth sütunları (bek_*) analiz içindir, güdüme GİRMEZ.
    """
    ALANLAR = ["t", "kare_t", "basarili", "durum",
               "vis_cx", "vis_cy", "vis_w", "vis_conf",
               "bek_cx", "bek_cy", "bek_w",
               "yerel_aday", "yerel_uygun", "red_konum", "red_boyut",
               "terminal_kabul", "kesme", "ibvs_v", "olcum_hiz", "olcum_vz",
               "iz_yas", "iz_w", "det_ms", "det_pencere",
               "takip_id", "takip_kaynak", "takip_coast", "takip_n",
               "menzil_m", "menzil3_m", "dz_m",
               "aspekt_deg", "hedef_roll", "drone_roll"]

    def __init__(self, dizin):
        os.makedirs(dizin, exist_ok=True)
        self._f = open(os.path.join(dizin, "cikarim.csv"), "w", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=self.ALANLAR,
                                 extrasaction="ignore")
        self._w.writeheader()
        self.n = 0

    def yaz(self, sat):
        self._w.writerow(sat); self.n += 1
        if self.n % 40 == 0: self._f.flush()

    def kapat(self):
        try: self._f.close()
        except Exception: pass


def _gecmis_beklenen(halka, t_hedef):
    """Halkadan t_hedef anına EN YAKIN kaydı bul ve hedefin o andaki
    öngörülen kadraj konumunu döndür: (cx, cy, kutu_px, ufuk_cy).

    ⚠ ÖLÇÜM-ONLY: truth kanalı kullanılır, güdüme GİRMEZ."""
    if not halka:
        return None
    en = min(halka, key=lambda k: abs(k[0] - t_hedef))
    _t, dp, yon, hp = en
    if hp is None:
        return None
    yat = math.hypot(hp[0] - dp[0], hp[1] - dp[1])
    menzil = math.hypot(yat, hp[2] - dp[2])
    if menzil < 0.5:
        return None
    elev = math.degrees(math.atan2(hp[2] - dp[2], max(yat, 1e-6)))
    ker = math.degrees(math.atan2(hp[1] - dp[1], hp[0] - dp[0]))
    az = (ker - yon[2] + 180.0) % 360.0 - 180.0
    # ⛔ ARKA YARIKÜRE KAPISI — 2026-08-27, YAŞANMIŞ ANALİZ HATASI.
    #   İzdüşüm zinciri `ileri` bileşenine BÖLER; hedef arkadayken `ileri`
    #   NEGATİF olur ve bölme işareti çevirerek KADRAJ İÇİ bir piksel
    #   üretir. Yani "üstünden geçtiğimiz" hedef, kadrajın ortasında
    #   duruyormuş gibi loglanır.
    #   ÖLÇÜLDÜ: KM2 kademeli__t2 kare 21 (t=10.7 s, menzil 6.58 m) ->
    #   bek=(1338,477) diyordu; KAREYE BAKINCA hedef YOKTU, arkada
    #   kalmıştı. Bu, "kadraj içinde ama dedektör kör" (B) kovasını
    #   şişiriyordu ve aday tasarımım o şişkin sayıya dayanıyordu.
    #   ⚠ BU KAPI YALNIZ ÖLÇÜM YOLUNDA (CSV sütunları). Güdümdeki
    #     `seviye_piksel` AYNI kusuru taşır ama ORAYA DOKUNULMADI —
    #     güdüm davranışı değişikliği ayrı karar (§8).
    if abs(az) >= 85.0:
        return None
    # ⭐ TAM ZİNCİR (Gazebo'nun `los_seviye`inin tersi). ÖLÇÜLDÜ 2026-08-23,
    #   4146 eşleşmiş karede tespit edilen kutuya uyum:
    #     yaklaşık zincir: sapma medyan 33.1 px (p90 109.4)
    #     TAM zincir     : sapma medyan 13.6 px (p90  76.4)   <- 2.4 KAT iyi
    #   Yanlış model, gerçek tespitlerin bir kısmını "yanlış nişan"
    #   saydırıyordu -> `dogru%` olduğundan DÜŞÜK ölçülüyordu.
    cx, cy = _KAM.seviye_piksel(az, elev, yon[0], yon[1])
    w = _KAM.MENZIL_C / max(menzil, 1e-6)
    _, ufuk = _KAM.seviye_piksel(az, 0.0, yon[0], yon[1])
    return cx, cy, w, ufuk


def _saglikli(beyin, deneme=3):
    """Koşuya BAŞLAMADAN önce sim gerçekten hazır mı?

    ⛔ ÖLÇÜLDÜ 2026-08-23: oyun bir koşu ortasında tamamen KAPANDI; harness
      HUD kapısını geçmiş sayıp koşmaya devam etti ve 3 koşu `drone_yok` /
      `baglanti_yok` ile boşa gitti. HUD kapısı "ekranda oyun var mı" der,
      "SDK canlı mı" DEMEZ. Koşu saymadan önce ikisi de doğrulanır; gerekirse
      oyun baştan kurulur."""
    from araclar.sim import hazir_ol
    for i in range(deneme):
        if beyin.b.canli():
            return True
        beyin.b.yeniden_bagla()
        if beyin.b.canli():
            return True
        print(f"  [sağlık {i+1}/{deneme}] SDK ölü — sim baştan kuruluyor",
              flush=True)
        if not hazir_ol():
            continue
        beyin.b.yeniden_bagla()
    return beyin.b.canli()


def kosu_yap(beyin, sct, dizin, sure, det=None, panel_ac=True):
    """Tek koşu. Döner: özet sözlüğü."""
    os.makedirs(dizin, exist_ok=True)
    kayit = Kayit(dizin, Ayar.KAYIT_ARALIK) if Ayar.KAYIT_AKTIF else None
    ckayit = CikarimKaydi(dizin) if Ayar.KAYIT_AKTIF else None
    # ⭐ ZOR ÖRNEK KAYDEDİCİ (DOW_ZOR_KAYIT=1) — bkz. araclar/zor_kayit.py
    #   Iskalanan ama hedefin KADRAJDA olduğu kareleri etiketiyle diske yazar.
    #   VARSAYILAN KAPALI: normal koşuya disk/CPU yükü bindirmez.
    from araclar.zor_kayit import kur as _zor_kur
    _zor = _zor_kur()
    bekci = Bekci(); bekci.sifirla()
    beyin.spawn_sifirla()
    if not beyin.b.canli():
        beyin.b.yeniden_bagla()

    t0 = time.time(); son = t0; n = 0
    tespit_yas = -1.0
    son_gt = 0.0
    # ⛔ ÖLÇÜT YANLILIĞI — KESİN ÇÖZÜM (2026-08-22).
    #   Kutu, kontrol döngüsüne en erken ~75 ms sonra ulaşıyor (ekran
    #   kopyalama 15 ms + YOLO imgsz1920 60 ms) ve dedektör 5 Hz olduğu için
    #   yaşı 0.075-0.28 s arasında salınıyor. "Kaydı taze kutuya hizala"
    #   denemesi bu yüzden BAŞARISIZ oldu (ölçüldü: medyan yaş 0.21 s, hiç
    #   düşmedi). Kutuyu tazeleştirmek mümkün değil; ONUN ÜRETİLDİĞİ ANIN
    #   DURUŞUYLA karşılaştırmak mümkün. Kontrol döngüsü 48 Hz koştuğu için
    #   son 2 s'nin duruşunu tutmak 100 kayıt = bedava.
    #   Neden şart: 0.2 s'de araç 20°/s yaw ile 4° döner = 38 px kadraj
    #   kayması; ölçüt bunu YANLIŞ-POZİTİF sayıyordu ve bedeli kollara EŞİT
    #   DEĞİLDİ (dik bakan 0.75 kollarında sapma medyanı 93 px, 0.45'te 51).
    _halka = deque(maxlen=140)      # (t, dp, (roll,pitch,yaw), hedef_p)
    # ⚠ ÖLÇÜM-ONLY: truth kanalı YALNIZ isabet/menzil ölçmek için okunur.
    #   Beyin'e ASLA verilmez; yarışmada bu kanal zaten yoktur.
    en_yakin = 1e9; _en_yakin_t = 0.0; isabet = 0; gorsel_tik_say = 0; tespit_say = 0
    # ⭐ TEMAS ÖLÇÜMÜ (kullanıcı isteği 2026-08-23): "drone hedefin
    #   pervanesine çarparsa bu vuruş sayılmıyor, drone geriye itiliyor;
    #   sen bu pervaneye çarpmayı anla ve bunu vuruş say."
    #   0.5 s'lik kayıt darbeyi AYIRAMADI (her menzil bandında taban/darbe
    #   oranı 1.4-2.5x, ayrışma yok) -> ölçüm DÖNGÜ HIZINDA (~43 Hz) yapılır.
    #   Burada yalnız ADAY toplanır; eşik SONRADAN veriden seçilecek.
    #   ⚠ ÖLÇÜM-ONLY: truth + KENDİ hızımız. Güdüme girmez.
    _v_onceki = None; _ivme_tum = []
    _temas_ivme = 0.0; _temas_menzil = -1.0; _temas_t = -1.0
    _temas_geri = 0.0
    devir_t = None; devir_menzil = None
    # ⛔ CLAUDE.md §4: "SALINIM ÖLÇÜLMEDEN 'İYİLEŞTİ' DENMEZ."
    #   Yalnız isabet+menzile bakan ölçüt, dengesizce savrulup ŞANS eseri
    #   çarpan aracı ödüllendirir. Her karşılaştırmada bunlar da raporlanır:
    #     cx işaret değişimi/s   (hedef kadrajda sağa-sola atıyor mu)
    #     yatış işaret değişimi/s ve |yatış| p90
    #     yaw komutu değişim hızı
    #     görsel temas kesintisi sayısı ve toplam süresi
    #   ⚠ GEÇERLİLİK EŞİ (§5.2): salınım YALNIZ tespit olan karelerde
    #     ölçülebilir; hedefi daha çok kaybeden koşu daha "sakin" görünür.
    #     Bu yüzden tespit oranı HER ZAMAN yanında raporlanır.
    _g_cx = None; _g_cx_don = 0; _g_cx_n = 0
    _g_roll = []; _g_roll_don = 0; _g_roll_isaret = None
    _g_yaw_onceki = None; _g_yaw_dev = []
    _g_kesinti = 0; _g_kesinti_s = 0.0; _g_kesik_bas = None
    ist_hatalar = []; oturma_t = None
    ihlal = None; tespit = None
    son_kare_n = -1; det_tekrar = 0
    _g_yas = []; _g_det_ms = []; _g_det_n = 0; _g_pencere_n = 0
    dt_hedef = 1.0 / Ayar.LOOP_HZ

    while time.time() - t0 < sure:
        t = time.time(); dt = max(1e-3, t - son); son = t

        # ---- KARE: görüş iş parçacığından AL (kopyalama YOK) ----
        # Uçuş kapısı da oradan gelen HUD parlaklığıdır (sol alt batarya
        # bloğu; ölçüldü: yerde 0.151 | uçuşta 0.155 | spawn-bekler 0.000).
        img, hud_pk, kare_n, kare_t = _son_kare()
        if img is None:
            time.sleep(0.005); continue
        if hud_pk <= 0.05:
            ihlal = "drone_yok"; break
        # ---- ÇIKARIM SATIRI (ölçüm-only) — TEK yerde kurulur ----
        def _cikarim_satiri(ct, ctespit, cti, ckare_t):
            """cikarim.csv satırı. TRUTH kanalına (beyin.b) dokunduğu için
            YALNIZ kontrol iş parçacığından çağrılır — SDK soketi tek
            iş parçacığına ait kalsın (GORUS_ISP'te görüş yalnız ham sonucu
            kuyruğa koyar, satırı buradan kurarız)."""
            _c = {"t": round(ct - t0, 3),
                  "kare_t": round(ckare_t - t0, 3) if ckare_t else -1,
                  "basarili": int(ctespit is not None),
                  "durum": beyin.durum,
                  "yerel_aday": cti.get("yerel_aday"),
                  "yerel_uygun": cti.get("yerel_uygun"),
                  "red_konum": cti.get("red_konum"),
                  "red_boyut": cti.get("red_boyut"),
                  "terminal_kabul": cti.get("terminal_kabul"),
                  "kesme": cti.get("ibvs_kesme"),
                  # ⚠ ÖLÇÜM-ONLY: komut vs gerçekleşen hız, 20 Hz (§5.3)
                  "ibvs_v": cti.get("ibvs_v"),
                  "olcum_hiz": cti.get("olcum_hiz"),
                  "olcum_vz": cti.get("olcum_vz"),
                  "takip_id": cti.get("takip_id"),
                  "takip_kaynak": cti.get("takip_kaynak"),
                  "takip_coast": cti.get("takip_coast"),
                  "takip_n": cti.get("takip_n"),
                  "iz_yas": cti.get("iz_yas"),
                  "iz_w": cti.get("iz_w"),
                  "det_ms": cti.get("det_ms"),
                  "det_pencere": cti.get("det_pencere")}
            if ctespit:
                _c.update({"vis_cx": round(ctespit[0], 1),
                           "vis_cy": round(ctespit[1], 1),
                           "vis_w": round(ctespit[2], 1),
                           "vis_conf": round(ctespit[4], 3)})
            _bg = _gecmis_beklenen(_halka, ckare_t if ckare_t else ct)
            if _bg:
                _c.update({"bek_cx": round(_bg[0], 1),
                           "bek_cy": round(_bg[1], 1),
                           "bek_w": round(_bg[2], 1)})
            # ⚠ ÖLÇÜM-ONLY truth kanalı; GÜDÜME girmez, yalnız bu CSV'ye.
            try:
                _trc = beyin.b.truth()
                if _trc:
                    _c.update(_truth_aspekt(beyin, beyin.b.konum(), _trc["hedef_m"]))
            except Exception:
                pass
            return _c

        if Ayar.GORSEL_AKTIF and Ayar.GORUS_ISP:
            # ⭐ ÇIKARIM GÖRÜŞ İŞ PARÇACIĞINDA KOŞTU — burada YALNIZ OKU.
            #   Kontrol döngüsü YOLO'yu BEKLEMEZ; bu değişikliğin tamamı budur.
            #
            # ⛔ KUTU ANLAMI İKİ KOLDA AYNI OLMALI (2026-08-24, ISP3).
            #   `_gorus["tespit"]` eskiden HER çıkarımda üzerine yazılıyordu;
            #   ıskada None oluyordu. Eski yolda `beyin._son_tespit` KALICI.
            #   İki kol farklı şey ölçüyordu:
            #     kör süre  %31.5 -> %0.00 | tespit% %94.4 -> %50.0
            #   İkisi de KAZANÇ DEĞİL, ARTEFAKT. Çare görüş iş parçacığında:
            #   `_gorus["tespit"]` artık YALNIZ BAŞARILI çıkarımda güncellenir,
            #   yani `beyin._son_tespit` ile BİREBİR aynı anlam taşır.
            #
            # ⛔⛔ BURADA `beyin._kilit_g` KULLANMA. Bir ara öyle yapmıştım ve
            #   ÖZELLİĞİN TAMAMINI İPTAL ETTİ: o kilidi görüş iş parçacığı
            #   ÇIKARIM BOYUNCA (~50 ms) tutuyor; kontrol döngüsü onu
            #   beklerken yine YOLO'ya bağlanıyor. Ölçüldü: kontrol döngüsü
            #   46.0 -> 39.8 Hz. `_gorus_kilit` ise mikrosaniyeler tutulur.
            with _gorus_kilit:
                tespit = _gorus["tespit"]
                tespit_yas = (t - _gorus["tespit_t"]) if tespit else -1.0
                _bekleyen = _gorus["bekleyen"]; _gorus["bekleyen"] = []
            beyin._cikarim_yapildi = bool(_bekleyen)
            if ckayit is not None:
                for (_bt, _bd, _bti) in _bekleyen:
                    ckayit.yaz(_cikarim_satiri(_bt, _bd, _bti, _bt))
            for (_bt, _bd, _bti) in _bekleyen:      # §5.1 mekanizma sayaçları
                _g_det_n += 1
                _dm = _bti.get("det_ms")
                if _dm: _g_det_ms.append(_dm)
                if _bti.get("det_pencere"): _g_pencere_n += 1
        elif Ayar.GORSEL_AKTIF:
            # ⛔ ÇIKARIM TAVANLI (bkz. Ayar.GORSEL_DET_HZ). Aradaki tiklerde
            #   güdüm son kutuyu kullanır (Beyin._son_tespit zaten öyle
            #   çalışıyor) ve kontrol döngüsü tam hızda döner.
            # ⭐ KOL C — YENİ KARE KAPISI (DOW_DET_YENI_KARE):
            #   Yakalama 15 Hz, çıkarım tavanı 10 Hz. Zamanlayıcıyla
            #   koşturmak AYNI kareyi ikinci kez taramaya yol açar: bedava
            #   değil, bedelli hiçlik. Kapı açıkken çıkarım YALNIZ yeni bir
            #   kare geldiğinde koşar; tavan üst sınır olarak kalır.
            #   Mekanizma sütunu: det_tekrar (aynı kareyi kaç kez taradık).
            _sure_doldu = (t - son_gt) >= 1.0 / max(0.1, Ayar.GORSEL_DET_HZ)
            _yeni = (kare_n != son_kare_n)
            _kos = (_sure_doldu and _yeni) if Ayar.DET_YENI_KARE else _sure_doldu
            if _kos:
                if not _yeni: det_tekrar += 1
                son_gt = t; son_kare_n = kare_n
                tespit = beyin.gorsel_tik(img, t, kare_t)
                beyin._cikarim_yapildi = True
                tespit_yas = 0.0 if tespit else -1.0
                _tespit_yaz(tespit)
                PANEL.tespit_isaretle(tespit is not None)
                PANEL.fps_isaretle("dedektor")
                # ⭐ HER ÇIKARIMI YAZ (ölçüm-only, güdüme dokunmaz)
                if ckayit is not None:
                    _csat = _cikarim_satiri(t, tespit, beyin.tani, kare_t)
                    ckayit.yaz(_csat)
                    # ⭐⭐ ZOR ÖRNEK KAYDI (DOW_ZOR_KAYIT=1) — kullanıcı fikri
                    #   2026-08-25: "hangi anlarda Talon kadrajda olmasına
                    #   rağmen detection modeli onu tespit edemiyorsa o
                    #   kareleri çekelim ve veri seti oluşturalım."
                    #
                    #   ⛔ NEDEN TAM BURADA: etiket, dedektörün GÖRDÜĞÜ
                    #   karenin KENDİSİYLE ve AYNI ANIN geometrisiyle
                    #   eşleşmeli. Kaydedilmiş kareyi sonradan telemetriyle
                    #   eşleştirme denendi ve ETİKETLER BOZUK ÇIKTI
                    #   (kontak sayfasında "7 m" kutusu boş göğe düştü):
                    #   meta.csv 1 Hz ve oradaki bek_* son TESPİTİN anına
                    #   göre hesaplanıyor, karenin anına göre değil.
                    #   Burada eşleştirme hatası YAPISAL OLARAK imkânsız.
                    #
                    #   ⛔ GÜDÜME DOKUNMAZ: yalnız diske yazar. Hedefin
                    #   GPS'i burada VERİ SETİ ETİKETİ için okunuyor —
                    #   güdüm yoluna girmiyor (§10; bekçi B18/B19 ayrıca
                    #   görsel fazda GPS'in güdüme ulaşmadığını sınar).
                    if _zor is not None:
                        _zor.belki_kaydet(img, _csat)
            else:
                beyin._cikarim_yapildi = False
                tespit = beyin._son_tespit
                tespit_yas = t - beyin._son_tespit_t if tespit else -1.0
        else:
            with _gorus_kilit:
                tespit = _gorus["tespit"]
                tespit_yas = t - _gorus["tespit_t"] if _gorus["tespit"] else -1.0

        sonuc = beyin.adim(t, dt)
        if sonuc is None:
            ihlal = "baglanti_yok"; break
        thr, pitch, roll, yaw = sonuc
        ti = beyin.tani

        # ---- BEKÇİ ----
        dp = beyin.b.konum()
        _yon = beyin.b.yonelim()
        hp = None
        if ti.get("hedef_var"):
            hp = beyin.hedef_konumu(t)
        s = bekci.kontrol(t - t0, dp, beyin._zemin_z, hp, beyin.b.canli())
        if s:
            ihlal = s; break

        # ---- ÖLÇÜM-ONLY: gerçek menzil / isabet ----
        _tr = beyin.b.truth()
        _gdz = _gelev = float("nan"); _R = float("nan")
        if _tr:
            _hp = _tr["hedef_m"]
            _R = math.dist(dp, _hp)
            _gdz = _hp[2] - dp[2]
            _gyat = math.hypot(_hp[0]-dp[0], _hp[1]-dp[1])
            _gelev = math.degrees(math.atan2(_gdz, max(_gyat, 1e-6)))
            if _R > 0.05:
                if _R < en_yakin: en_yakin = _R; _en_yakin_t = t - t0
                if _R < 4.0: isabet = 1
            # ---- TEMAS ADAYI: kendi hızımızda ani sıçrama, YAKINDA ----
            _vv = beyin.b.hiz_vektoru()
            if _v_onceki is not None and dt > 1e-3:
                _dv = tuple(_vv[i] - _v_onceki[i] for i in range(3))
                _iv = math.sqrt(sum(c * c for c in _dv)) / dt
                _ivme_tum.append(_iv)
                # ⭐ "GERİYE doğru" bileşen (kullanıcının tarifi 2026-08-23):
                #   yaklaşma yönü = drone -> hedef birim vektörü. Darbenin bu
                #   yönün TERSİNDEKİ bileşeni = geri itilme.
                _geri = 0.0
                if _hp and _R > 1e-6:
                    _u = tuple((_hp[i] - dp[i]) / _R for i in range(3))
                    _geri = -sum(_dv[i] * _u[i] for i in range(3)) / dt
                if _R < 6.0 and _iv > _temas_ivme:
                    _temas_ivme = _iv; _temas_menzil = _R; _temas_t = t - t0
                    _temas_geri = _geri
            _v_onceki = _vv
            _halka.append((t, dp, (math.degrees(_yon[0]), math.degrees(_yon[1]),
                                   math.degrees(_yon[2])), _hp))
        if beyin.durum == "GORSEL":
            gorsel_tik_say += 1
            # ⭐ BİRİNCİL ÖLÇÜT — güdümün kullandığı kutunun GERÇEK yaşı.
            #   Karenin YAKALANDIĞI andan sayılır (çıkarımın koştuğu andan
            #   değil); aradaki fark yakalama tavanı kadardır ve yanlılıktır.
            if beyin._son_tespit and beyin._son_tespit_kare_t:
                _g_yas.append(t - beyin._son_tespit_kare_t)
            # ⚠ GORUS_ISP açıkken bu sayaçlar ÇIKARIM KUYRUĞUNDAN sayılır
            #   (yukarıda, her gerçek çıkarım için bir kez). Burada da saymak
            #   ÇİFT SAYIM olurdu — mekanizma sütunu §5.1 için kullanılıyor,
            #   şişmiş bir sayı "özellik çalıştı" yanılsaması verir.
            if beyin._cikarim_yapildi and not Ayar.GORUS_ISP:
                _g_det_n += 1
                _g_det_ms.append(beyin._det_ms)
                if beyin._det_pencere > 0: _g_pencere_n += 1
            if beyin._bu_kare_tespit:
                tespit_say += 1
                if _g_kesik_bas is not None:
                    _g_kesinti_s += t - _g_kesik_bas; _g_kesik_bas = None
                _cx = beyin._son_tespit[0] - 960.0 if beyin._son_tespit else 0.0
                if _g_cx is not None and _cx * _g_cx < 0: _g_cx_don += 1
                _g_cx = _cx; _g_cx_n += 1
            else:
                if _g_kesik_bas is None:
                    _g_kesik_bas = t; _g_kesinti += 1
            _rl = math.degrees(beyin.b.yonelim()[0])
            _g_roll.append(abs(_rl))
            _is = 1 if _rl > 1.0 else (-1 if _rl < -1.0 else 0)
            if _is and _g_roll_isaret and _is != _g_roll_isaret: _g_roll_don += 1
            if _is: _g_roll_isaret = _is
            if _g_yaw_onceki is not None:
                _g_yaw_dev.append(abs(yaw - _g_yaw_onceki) / max(1e-3, dt))
            _g_yaw_onceki = yaw
            if devir_t is None:
                devir_t = t - t0
                devir_menzil = _R if _tr else -1
        elif _g_kesik_bas is not None:
            # ⛔ GORSEL fazdan çıkıldı: açık kesintiyi KAPAT. Yoksa bir
            #   sonraki görsel faza kadar geçen TÜM İSTASYON süresi
            #   "görsel temas kesintisi" olarak sayılıyordu (ölçüldü:
            #   14 s'lik görsel fazda 70.1 s kesinti raporlandı).
            _g_kesinti_s += t - _g_kesik_bas; _g_kesik_bas = None

        # ---- ölçüt: istasyon hatası ----
        ih = ti.get("ist_hata_m")
        if ih is not None and beyin.durum == "ISTASYON":
            ist_hatalar.append(ih)
            if oturma_t is None and ih <= 15.0:
                oturma_t = t - t0

        # ---- panel ----
        # Kareyi/tespiti yukarıda kendimiz bastık; burada GÜDÜM sayıları.
        # ⚠ İKİNCİ BİR GÖRÜŞ SÜRECİ (izleyici.py) AYNI ANDA KOŞTURULMAZ —
        #   iki ekran kopyalayıcı + iki YOLO oyunu aç bırakıyor (GV11).
        if panel_ac and (n % 5 == 0):
            tel = {k: (round(v, 2) if isinstance(v, float) else v)
                   for k, v in ti.items() if isinstance(v, (int, float, str))}
            tel["drone_hiz"] = round(beyin.b.hiz(), 2)
            tel["bekci"] = bekci.rapor()
            # ⭐ YER-KONTROL ARAYÜZÜ İÇİN GENİŞ TELEMETRİ (2026-08-24).
            #   `dow/web/index.html` (arkadaşın `model-fps` branch'inden) iç içe
            #   bir şema bekliyor; `dow/panel.py::_api_telemetry` bu düz alanları
            #   o şekle çeviriyor. Buraya YALNIZ GÖSTERİM verisi konur.
            #   ⛔ §10: truth kanalı GÜDÜME girmez — meta.csv'de olduğu gibi
            #      burada da yalnız EKRANA gider (görsel güdüm `gorsel_tik`
            #      içinde bu alanların hiçbirini görmez).
            tel["d_x"], tel["d_y"], tel["d_z"] = [round(v, 2) for v in dp]
            tel["d_roll"] = round(math.degrees(_yon[0]), 2)
            tel["d_pitch"] = round(math.degrees(_yon[1]), 2)
            tel["d_yaw"] = round(math.degrees(_yon[2]), 2)
            if hp:
                tel["h_x"], tel["h_y"], tel["h_z"] = [round(v, 2) for v in hp]
                tel["mesafe_m"] = round(math.dist(dp, hp), 2)
            if np.isfinite(_R):
                tel["gercek_mesafe_m"] = round(float(_R), 2)
            # ⭐ 3B KONUM GRAFİĞİ İÇİN HEDEF KONUMU (2026-08-26, kullanıcı isteği)
            #   ⛔ §10: `h_*` YALNIZ hp varken yazılır ve GORSEL fazda hp YOKTUR
            #     (o fazda hedefin GPS'i okunmaz) -> grafik orada DONARDI.
            #     Bu yüzden truth kanalı kullanılıyor: her fazda dolu.
            #   ⛔ Statüsü `gercek_mesafe_m` ile AYNI: YALNIZ EKRANA gider.
            #     Görsel güdüm (`Beyin._gorsel_tik_kilitli`) bu alanların
            #     hiçbirini görmez — girdisi yalnız görüntüdür (B1/B18/B19).
            if _tr:
                tel["t_x"], tel["t_y"], tel["t_z"] = [round(float(v), 2)
                                                      for v in _hp]
            if tespit:
                tel["vis_cx"], tel["vis_cy"] = round(tespit[0], 1), round(tespit[1], 1)
                tel["vis_w"], tel["vis_h"] = round(tespit[2], 1), round(tespit[3], 1)
                tel["vis_conf"] = round(tespit[4], 3)
                tel["vis_yas"] = round(tespit_yas, 3)
            tel["kare_w"], tel["kare_h"] = 1920, 1080
            tel["gorsel_aktif"] = int(Ayar.GORSEL_AKTIF)
            _telem_gonder(tel)

        # ---- kayıt (0.5 s) ----
        if kayit and kayit.gerek(t - t0):
            yon = beyin.b.yonelim()
            sat = {
                "durum": beyin.durum,
                "drone_x": round(dp[0], 2), "drone_y": round(dp[1], 2),
                "drone_z": round(dp[2], 2),
                "drone_roll": round(math.degrees(yon[0]), 2),
                "drone_pitch": round(math.degrees(yon[1]), 2),
                "drone_yaw": round(math.degrees(yon[2]), 2),
                "drone_hiz": round(beyin.b.hiz(), 2),
                "yukseklik": round(ti.get("yukseklik", 0), 2),
                "thr": round(thr, 3), "pitch": round(pitch, 3),
                "roll": round(roll, 3), "yaw": round(yaw, 3),
            }
            if hp:
                sat.update({"hedef_x": round(hp[0], 2), "hedef_y": round(hp[1], 2),
                            "hedef_z": round(hp[2], 2)})
            # hedefin GERÇEK yönelimi (ölçüm/analiz; güdüme girmez)
            try:
                _hr = beyin.b.hedef_yonelim()
                sat.update({"hedef_roll": round(_hr[0], 2),
                            "hedef_pitch": round(_hr[1], 2),
                            "hedef_yaw": round(_hr[2], 2)})
            except Exception:
                pass
            # ÖLÇÜM-ONLY: gerçek geometri (analiz için; güdüme girmez)
            if _tr:
                sat.update({"gercek_menzil": round(_R, 2),
                            "gercek_dz": round(_gdz, 2),
                            "gercek_elev": round(_gelev, 2)})
            for k in ("hedef_hiz", "hedef_yon", "ist_x", "ist_y", "ist_z",
                      "ist_hata_m", "ist_hata_yatay", "ist_hata_dikey",
                      "hedef_menzil_m", "yaw_hata", "v_istek",
                      "kopru_kare", "bayat_birak", "yerel_aday", "yerel_uygun",
                      "det_ms", "det_pencere", "red_konum", "red_boyut",
                      "terminal_kabul", "yerel_kayip",
                      "iz_yas", "iz_w",
                      "takip_id", "takip_kaynak", "takip_coast", "takip_n",
                      "ibvs_nisan_elev", "ibvs_vz_kirpildi", "ibvs_e_cy",
                      "ibvs_vz_yukari", "ibvs_v", "olcum_hiz", "olcum_vz"):
                if k in ti: sat[k] = round(ti[k], 2) if isinstance(ti[k], float) else ti[k]
            if tespit:
                sat.update({"vis_cx": round(tespit[0], 1), "vis_cy": round(tespit[1], 1),
                            "vis_w": round(tespit[2], 1), "vis_h": round(tespit[3], 1),
                            "vis_conf": round(tespit[4], 3),
                            "vis_yas": round(tespit_yas, 3),
                            "vis_yas_tam": round(
                                t - beyin._son_tespit_kare_t, 3)
                            if beyin._son_tespit_kare_t else -1.0})
                # tespit ANINDAKİ duruş+truth -> öngörülen kadraj konumu
                bg = _gecmis_beklenen(_halka, t - max(0.0, tespit_yas))
                if bg:
                    sat.update({"bek_cx": round(bg[0], 1), "bek_cy": round(bg[1], 1),
                                "bek_w": round(bg[2], 1), "bek_ufuk_cy": round(bg[3], 1)})
            kayit.yaz(t - t0, img, sat)

        n += 1
        kalan = dt_hedef - (time.time() - t)
        if kalan > 0: time.sleep(kalan)

    # ⛔ ÖLÇÜM HATASI DÜZELTMESİ (2026-08-22):
    #   Hedefi VURUNCA drone da yok oluyor -> bekçi "drone_yok" diyor ve
    #   koşuyu GEÇERSİZ sayıyordu. Yani BAŞARIYI başarısızlık gibi
    #   işaretliyordum; bu, istatistiği tam da istediğimiz sonucun ALEYHİNE
    #   sistematik olarak saptırır (§5.2 "ölçüt kötü sebeple iyileşir mi"nin
    #   tersi: ölçüt İYİ sebeple KÖTÜLEŞİYORDU).
    #   İsabet varsa koşu GEÇERLİDİR; ihlal "isabet_sonrasi" diye işaretlenir.
    if _g_kesik_bas is not None:            # koşu kesinti içinde bitti
        _g_kesinti_s += time.time() - _g_kesik_bas
    # ---- TEMAS SINIFLANDIRMASI (Ayar.TEMAS_* eşikleri ÖLÇÜLDÜ) ----
    #   ⭐ KULLANICI KARARI (2026-08-23): "imha ettim demek için hedefe
    #      DEĞMEK YETERLİ. DoW pervaneye çarpmayı vuruş saymıyor ama sen say;
    #      bu bizim için BAŞARIDIR."
    #   TEMAS       : darbe var -> BAŞARI (pervane çarpması dahil)
    #   imha        : temasın alt kümesi — drone da yok oldu (yalnız teşhis)
    #   YAKIN GEÇİŞ : yakından geçtik ama HİÇ DEĞMEDİK -> başarısız
    #   İMZA 1 — SEKME (pervane): ani geri ivme, drone yaşar
    _sekme = int(_temas_ivme >= Ayar.TEMAS_IVME_ESIK
                 and 0 <= _temas_menzil <= Ayar.TEMAS_MENZIL_M)
    #   İMZA 2 — ANINDA İMHA: koşu TAM en yakınlaşma anında bitti ve o
    #   menzil temas yarıçapı içinde. Sekme YOK çünkü drone yok oldu.
    #   ⛔ Bu imza EKSİKTİ ve en temiz vuruşları kaçırıyordu (E1b: üç koşu
    #      0.67-0.81 m'de tam o anda bitmiş, darbe sıfır -> "temas yok"
    #      sayılmıştı; gerçekte 0.014/4.0 kolu 3/8 değil 8/8'di).
    _imha = int(en_yakin <= Ayar.TEMAS_MENZIL_M
                and (time.time() - t0) - _en_yakin_t <= 0.6)
    _temas = int(_sekme or _imha)
    isabet = _temas                        # kullanıcı kuralı: temas = vuruş
    # ⛔ GEÇERLİLİK KURALI — İKİ YÖNLÜ DÜZELTME (§5.2)
    #  (1) 2026-08-22: hedefi VURUNCA drone da yok oluyor ve bekçi
    #      "drone_yok" diyordu -> BAŞARI başarısızlık gibi işaretleniyordu.
    #  (2) 2026-08-23: TERSİ de yanlıştı. Temas OLMADAN düşen drone
    #      (C1_BAYAT koşu 3-4: ivme 18-19, hedefin 2.5-4.3 m'sinde despawn)
    #      GEÇERSİZ sayılıp elenıyordu — oysa o bir ISKA, yani veri.
    #      Başarısızlığı elemek iki kolu da olduğundan iyi gösterir.
    #  DOĞRU KURAL: görsel faza GİRDİYSE `drone_yok` bir SONUÇTUR (isabet ya
    #  da ıska), geçersizlik değil. Hiç giremediyse kurulum sorunudur.
    if ihlal in ("drone_yok", "baglanti_yok", "telemetri_dondu") \
            and (isabet or gorsel_tik_say > 0):
        ihlal = None
    _sure_ger = max(1e-6, time.time() - t0)
    _tik_hz = n / _sure_ger          # ⚠ GERÇEK döngü hızı: görsel fazda YOLO
    # det_hz paydasi: sayacin sayildigi pencere (bkz. det_hz notu)
    _det_pencere_s = (_sure_ger if Ayar.GORUS_ISP
                      else gorsel_tik_say / max(1e-9, _tik_hz))
                                     #   yüzünden ~19 Hz, nominal 50 DEĞİL.
    if kayit: kayit.kapat()
    if ckayit: ckayit.kapat()
    if _zor is not None:
        _n, _at = _zor.kapat()
        print("  [ZOR ÖRNEK] %d kare yazıldı -> %s" % (_n, _zor.dizin), flush=True)
        print("  [ZOR ÖRNEK] atılan: %s" % _at, flush=True)
    beyin.b.komut(beyin.cev._vz_cubuk(0.0), 0.0, 0.0, 0.0, True)
    a = np.array(ist_hatalar) if ist_hatalar else np.array([np.nan])
    return {
        "sure": round(_sure_ger, 1), "tik": n, "tik_hz": round(_tik_hz, 1),
        "ihlal": ihlal or "-",
        "en_yakin_m": round(en_yakin, 2) if en_yakin < 1e8 else -1,
        "isabet": isabet,          # = TEMAS veya İMHA (ölçüldü, mesafe değil)
        "temas": _temas,
        "sekme": _sekme,
        "imha": _imha,
        # --- TEMAS ADAYI (eşik henüz seçilmedi; ham ölçüm) ---
        "temas_ivme": round(_temas_ivme, 1),
        "temas_geri": round(_temas_geri, 1),   # darbenin GERİYE bileşeni
        "temas_menzil": round(_temas_menzil, 2),
        "temas_t": round(_temas_t, 1),
        "ivme_p99": round(float(np.percentile(_ivme_tum, 99)), 1)
                    if len(_ivme_tum) > 50 else float("nan"),
        "ivme_medyan": round(float(np.median(_ivme_tum)), 1)
                       if len(_ivme_tum) > 50 else float("nan"),
        "drone_yasadi": int(ihlal not in ("drone_yok",)),
        "devir_s": round(devir_t, 1) if devir_t else -1,
        "devir_menzil": round(devir_menzil, 1) if devir_menzil else -1,
        "gorsel_tik": gorsel_tik_say,
        "gorsel_s": round(gorsel_tik_say / max(1e-6, _tik_hz), 1),
        "gorsel_tespit_yuzde": round(100.0 * tespit_say / max(1, gorsel_tik_say), 1),
        # ⭐ §5.1 MEKANİZMA SÜTUNU (Ö-A): terminal süreklilik istisnasıyla
        #   kabul edilen kutu sayısı. DENEY kolunda 0 ise o koşu fiilen
        #   KONTROL koşusudur -> VERİ NOKTASI DEĞİL (bkz. kol_kiyas --mek).
        "terminal_kabul": int(getattr(beyin, "_terminal_kabul", 0)),
        # --- SALINIM (§4) ---
        "cx_donus_s": round(_g_cx_don / max(1e-6, _g_cx_n / _tik_hz), 2)
                      if _g_cx_n > 5 else float("nan"),
        "roll_donus_s": round(_g_roll_don / max(1e-6, gorsel_tik_say / _tik_hz), 2)
                        if gorsel_tik_say > 5 else float("nan"),
        "roll_p90": round(float(np.percentile(_g_roll, 90)), 1) if len(_g_roll) > 5
                    else float("nan"),
        "yaw_dev_s": round(float(np.median(_g_yaw_dev)), 3) if len(_g_yaw_dev) > 5
                     else float("nan"),
        # --- ⭐ GÖRÜŞ ZİNCİRİ (2026-08-23 kampanyası) ---
        # kutu_yasi_p90 BİRİNCİL; gercek tespit% GEÇERLİLİK EŞİ (§5.2):
        # yaş, kutuyu ATARAK da düşer — tespit oranı yanında okunmalı.
        "kutu_yasi_med": round(float(np.median(_g_yas)), 3) if len(_g_yas) > 5
                         else float("nan"),
        "kutu_yasi_p90": round(float(np.percentile(_g_yas, 90)), 3)
                         if len(_g_yas) > 5 else float("nan"),
        "det_ms": round(float(np.median(_g_det_ms)), 1) if len(_g_det_ms) > 3
                  else float("nan"),
        # ⚠ det_hz'nin PAYDASI KOLA GÖRE DEĞİŞİR — İKİ KEZ yanlış yazıldı:
        #   1) `_g_det_n / (gorsel_tik_say / tik_hz)`: GORUS_ISP AÇIKKEN
        #      şişiyordu (gerçek 11.2 Hz iken 80.4).
        #   2) "duvar saatine böl" düzeltmesi NORMAL yolu bozdu: `_g_det_n`
        #      YALNIZ `durum=="GORSEL"` iken sayılır ama toplam süreye
        #      bölünüyordu. Kullanıcının izlediği koşuda gerçek 9.1 Hz iken
        #      **1.3 Hz** yazdı ve "dedektör bozuldu" sanılmasına yol açtı.
        #   DOĞRUSU: sayacın SAYILDIĞI pencereye böl (_det_pencere_s).
        "det_hz": round(_g_det_n / max(1e-6, _det_pencere_s), 1)
                  if _g_det_n > 5 and _det_pencere_s > 1.0 else float("nan"),
        "pencere_yuzde": round(100.0 * _g_pencere_n / max(1, _g_det_n), 1),
        "det_tekrar": det_tekrar,
        "kesinti_n": _g_kesinti,
        "kesinti_s": round(_g_kesinti_s, 1),
        "ist_hata_medyan": round(float(np.nanmedian(a)), 2),
        "ist_hata_min": round(float(np.nanmin(a)), 2),
        "ist_hata_son5s": round(float(np.nanmedian(a[-int(5/max(1e-9,1/Ayar.LOOP_HZ)):])), 2)
                          if len(a) > 10 else float("nan"),
        "oturma_s": round(oturma_t, 1) if oturma_t else -1,
        "ist_orani_15m": round(float(np.mean(a <= 15.0)), 3) if len(a) > 1 else 0.0,
    }


def main():
    ad = sys.argv[1] if len(sys.argv) > 1 else "kosu"
    adet = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    sure = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
    kok = os.path.join("logs", ad)
    os.makedirs(kok, exist_ok=True)

    det = None
    if Ayar.GORSEL_AKTIF or Ayar.DEDEKTOR_GOSTER:
        from dow.gorus.dedektor import Dedektor
        det = Dedektor()
        print(f"dedektör: {'GÜDÜMDE' if Ayar.GORSEL_AKTIF else 'yalnız PANELDE'}"
              f" | {Ayar.DEDEKTOR_HZ:.1f} Hz", flush=True)

    sct = mss.mss()
    ok, img0 = hazirla(sct)
    print(f"hazırlık: {'UÇUŞTA' if ok else 'BAŞARISIZ'}", flush=True)
    if not ok: sys.exit(1)
    if det: det.isit(img0)

    # ---- PANEL + GÖRÜŞ (tek süreç, tek kopyalayıcı, tek YOLO) ----
    PANEL.baslat(8801)
    print(f"panel: http://127.0.0.1:8801  "
          f"(yakalama tavanı {Ayar.PANEL_YAKALA_HZ:.0f} Hz, "
          f"dedektör tavanı {Ayar.PANEL_DET_HZ:.0f} Hz)", flush=True)
    _gorus_isp[0] = threading.Thread(target=_gorus_isi, args=(det,), daemon=True)
    _gorus_isp[0].start()
    for _ in range(100):                      # ilk kare gelsin
        if _son_kare()[0] is not None: break
        time.sleep(0.05)

    beyin = Beyin(dedektor=det)
    # ⭐ GORUS_ISP: görüş iş parçacığı beyinden ÖNCE başlıyor; tutamacı şimdi ver.
    with _gorus_kilit:
        _gorus["beyin"] = beyin
    # ⭐ SDK BAĞLANTISI YENİDEN DENENİR (2026-08-24, ISP5'te ölçüldü).
    #   Görev-sonu kurtarmasından (PLAY AGAIN -> 'E') sonra drone doğuyor ve
    #   HUD görünüyor — `hazirla()` "UÇUŞTA" diyor — ama oyunun SDK dinleyicisi
    #   12345 portunu BİRKAÇ SANİYE SONRA açıyor. Süreç o aralıkta bağlanmaya
    #   çalışıp "SDK bağlanamadı" ile ölüyordu.
    #   BEDELİ ÖLÇÜLDÜ: ISP5'te 8 koşunun 2'si (%25) bu yüzden kayboldu ve
    #   kampanya n=3'te kaldı — §5.4 gereği KARAR VERİLEMEZ hale geldi.
    #   ⚠ Bu YALNIZ uçuş ÖNCESİ kurulum yoludur; güdüm davranışına dokunmaz.
    #   ⚠ 24 s YETMEDİ (MODEL20 kampanyası): görev-sonu kurtarmasından sonra
    #     port bazen daha geç açılıyor ve koşu düşüyor. Düşen koşu, kolların
    #     n'ini eşitsizleştirir ve kıyası bozar (§5.9). 60 s'ye çıkarıldı.
    #   ⚠ 24 s ve 60 s İKİSİ DE YETMEDİ (MODEL20): görev-sonu kurtarmasından
    #     sonra port bazen hiç açılmıyor ve koşu DÜŞÜYOR. Düşen koşu kolların
    #     n'ini eşitsizleştirir ve kıyası bozar (§5.9) — MODEL20'de v3 iki
    #     koşu geride kaldı. Artık son çare olarak GÖREV BAŞTAN KURULUR.
    def _sdk_bagla(sn=60):
        for _d in range(int(sn / 2)):
            if beyin.b.baglan():
                return True
            if _d == 0:
                print("  [SDK portu henüz açık değil — bekleniyor]", flush=True)
            time.sleep(2.0)
        return False

    if not _sdk_bagla(60):
        print("  [SDK 60 s'de açılmadı — GÖREV BAŞTAN KURULUYOR (~2 dk)]",
              flush=True)
        _gorevi_yeniden_kur()
        try:
            beyin.b.yeniden_bagla()
        except Exception:
            pass
        if not _sdk_bagla(90):
            print("SDK bağlanamadı (görev yeniden kurulduktan sonra da)")
            sys.exit(1)

    # ⭐ PANELDEN BAŞLATMA KAPISI (2026-08-25, kullanıcı isteği).
    #   `DOW_PANELDEN=1` iken uçuş HEMEN başlamaz: panel ayağa kalkar, kullanıcı
    #   arayüzü açıp "🚀 Görev Başlat"a basınca döngü koşar. Amaç, tek komutla
    #   kurup uçuşu gözle takip ederek tetikleyebilmek.
    #   ⚠ VARSAYILAN KAPALI: kampanya betikleri (araclar/*.sh) beklemeden
    #     koşmalı, yoksa otomatik A/B'ler asılır.
    if _b("DOW_PANELDEN", False):
        print("\n⏸  PANEL BEKLİYOR — http://127.0.0.1:8801 açıp "
              "'🚀 Görev Başlat'a bas", flush=True)
        while not PANEL.baslat_istendi():
            if not PANEL.baslat_bekle(1.0):
                continue
        print("▶  başlatıldı\n", flush=True)

    print(f"\n{adet} koşu x {sure:.0f} s | GPS={Ayar.GPS_KAYNAK} | "
          f"görsel={'AÇIK' if Ayar.GORSEL_AKTIF else 'KAPALI'}", flush=True)
    print(f"{'#':>3} {'tik':>5} {'ihlal':>13} {'ist_hata':>9} {'devir@':>7} "
          f"{'görsel tik':>10} {'tespit%':>8} {'EN YAKIN':>9} {'isabet':>7}", flush=True)
    ozetler = []
    for i in range(1, adet + 1):
        if not _saglikli(beyin):
            print(f"{i:3d}  sim hazırlanamadı — koşu ATLANDI"); continue
        if not _yeni_gorev(beyin):
            print(f"{i:3d}  görev başlatılamadı"); continue
        if not _saglikli(beyin):
            print(f"{i:3d}  spawn sonrası SDK ölü — koşu ATLANDI"); continue
        o = kosu_yap(beyin, sct, os.path.join(kok, f"k{i:02d}"), sure, det)
        o["kosu"] = i; ozetler.append(o)
        print(f"{i:3d} {o['tik']:5d} {o['ihlal']:>13} {o['ist_hata_medyan']:9.2f} "
              f"{o['devir_menzil']:7.1f} {o['gorsel_tik']:10d} "
              f"{o['gorsel_tespit_yuzde']:8.1f} {o['en_yakin_m']:9.2f} "
              f"{'EVET' if o['isabet'] else '-':>7}", flush=True)

    if ozetler:
        with open(os.path.join(kok, "ozet.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(ozetler[0].keys()))
            w.writeheader(); w.writerows(ozetler)
        gec = [o for o in ozetler if o["ihlal"] == "-"]
        print(f"\nGEÇERLİ {len(gec)}/{len(ozetler)} koşu")
        if gec:
            m = np.array([o["ist_hata_medyan"] for o in gec])
            ey = np.array([o["en_yakin_m"] for o in gec])
            isb = sum(o["isabet"] for o in gec)
            gt = np.array([o["gorsel_tik"] for o in gec])
            print(f"istasyon hatası medyanı: {np.nanmedian(m):.1f} m")
            print(f"EN YAKIN medyan {np.nanmedian(ey):.2f} m | en iyi {np.nanmin(ey):.2f} m")
            print(f"İSABET {isb}/{len(gec)}  |  görsel faza giren koşu: "
                  f"{int((gt>0).sum())}/{len(gec)}")
    gorus_durdur()
    beyin.b.kapat()


if __name__ == "__main__":
    main()
