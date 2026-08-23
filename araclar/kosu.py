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
from araclar.kadraj import (BOLGE, grab_rgb, hud_parlak, ucusta_mi,
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
          "tespit_t": 0.0, "hud": 0.0}


def _gorus_isi(det):
    """Ekranı sabit hızda kopyala, dedektörü sabit hızda koştur, panele bas."""
    sct = mss.mss()
    son_det = 0.0
    dt_yak = 1.0 / max(1.0, Ayar.PANEL_YAKALA_HZ)
    while not _gorus_dur.is_set():
        t = time.time()
        img = grab_rgb(sct)                     # sürekli RGB
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
        with _gorus_kilit:
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
        return _gorus["img"], _gorus["hud"]


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
    """Drone'u yeniden doğur; olmazsa GÖREVİ baştan kur."""
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
    cx, cy, w = _KAM.beklenen_kadraj(menzil, elev, az, yon[1], yon[0])
    _, ufuk, _ = _KAM.beklenen_kadraj(menzil, 0.0, az, yon[1], yon[0])
    return cx, cy, w, ufuk


def kosu_yap(beyin, sct, dizin, sure, det=None, panel_ac=True):
    """Tek koşu. Döner: özet sözlüğü."""
    os.makedirs(dizin, exist_ok=True)
    kayit = Kayit(dizin, Ayar.KAYIT_ARALIK) if Ayar.KAYIT_AKTIF else None
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
    en_yakin = 1e9; isabet = 0; gorsel_tik_say = 0; tespit_say = 0
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
    dt_hedef = 1.0 / Ayar.LOOP_HZ

    while time.time() - t0 < sure:
        t = time.time(); dt = max(1e-3, t - son); son = t

        # ---- KARE: görüş iş parçacığından AL (kopyalama YOK) ----
        # Uçuş kapısı da oradan gelen HUD parlaklığıdır (sol alt batarya
        # bloğu; ölçüldü: yerde 0.151 | uçuşta 0.155 | spawn-bekler 0.000).
        img, hud_pk = _son_kare()
        if img is None:
            time.sleep(0.005); continue
        if hud_pk <= 0.05:
            ihlal = "drone_yok"; break
        if Ayar.GORSEL_AKTIF:
            # ⛔ ÇIKARIM TAVANLI (bkz. Ayar.GORSEL_DET_HZ). Aradaki tiklerde
            #   güdüm son kutuyu kullanır (Beyin._son_tespit zaten öyle
            #   çalışıyor) ve kontrol döngüsü tam hızda döner.
            if (t - son_gt) >= 1.0 / max(0.1, Ayar.GORSEL_DET_HZ):
                son_gt = t
                tespit = beyin.gorsel_tik(img, t)
                beyin._cikarim_yapildi = True
                tespit_yas = 0.0 if tespit else -1.0
                _tespit_yaz(tespit)
                PANEL.tespit_isaretle(tespit is not None)
                PANEL.fps_isaretle("dedektor")
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
                if _R < en_yakin: en_yakin = _R
                if _R < 4.0: isabet = 1
            _halka.append((t, dp, (math.degrees(_yon[0]), math.degrees(_yon[1]),
                                   math.degrees(_yon[2])), _hp))
        if beyin.durum == "GORSEL":
            gorsel_tik_say += 1
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
                      "kopru_kare", "yerel_aday", "yerel_uygun"):
                if k in ti: sat[k] = round(ti[k], 2) if isinstance(ti[k], float) else ti[k]
            if tespit:
                sat.update({"vis_cx": round(tespit[0], 1), "vis_cy": round(tespit[1], 1),
                            "vis_w": round(tespit[2], 1), "vis_h": round(tespit[3], 1),
                            "vis_conf": round(tespit[4], 3),
                            "vis_yas": round(tespit_yas, 3)})
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
    if isabet and ihlal in ("drone_yok", "baglanti_yok", "telemetri_dondu"):
        ihlal = None
    _sure_ger = max(1e-6, time.time() - t0)
    _tik_hz = n / _sure_ger          # ⚠ GERÇEK döngü hızı: görsel fazda YOLO
                                     #   yüzünden ~19 Hz, nominal 50 DEĞİL.
    if kayit: kayit.kapat()
    beyin.b.komut(beyin.cev._vz_cubuk(0.0), 0.0, 0.0, 0.0, True)
    a = np.array(ist_hatalar) if ist_hatalar else np.array([np.nan])
    return {
        "sure": round(_sure_ger, 1), "tik": n, "tik_hz": round(_tik_hz, 1),
        "ihlal": ihlal or "-",
        "en_yakin_m": round(en_yakin, 2) if en_yakin < 1e8 else -1,
        "isabet": isabet,
        "devir_s": round(devir_t, 1) if devir_t else -1,
        "devir_menzil": round(devir_menzil, 1) if devir_menzil else -1,
        "gorsel_tik": gorsel_tik_say,
        "gorsel_s": round(gorsel_tik_say / max(1e-6, _tik_hz), 1),
        "gorsel_tespit_yuzde": round(100.0 * tespit_say / max(1, gorsel_tik_say), 1),
        "devir_sebep": beyin._devir_sebep or "-",
        # --- SALINIM (§4) ---
        "cx_donus_s": round(_g_cx_don / max(1e-6, _g_cx_n / _tik_hz), 2)
                      if _g_cx_n > 5 else float("nan"),
        "roll_donus_s": round(_g_roll_don / max(1e-6, gorsel_tik_say / _tik_hz), 2)
                        if gorsel_tik_say > 5 else float("nan"),
        "roll_p90": round(float(np.percentile(_g_roll, 90)), 1) if len(_g_roll) > 5
                    else float("nan"),
        "yaw_dev_s": round(float(np.median(_g_yaw_dev)), 3) if len(_g_yaw_dev) > 5
                     else float("nan"),
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
    if not beyin.b.baglan():
        print("SDK bağlanamadı"); sys.exit(1)

    print(f"\n{adet} koşu x {sure:.0f} s | GPS={Ayar.GPS_KAYNAK} | "
          f"görsel={'AÇIK' if Ayar.GORSEL_AKTIF else 'KAPALI'}", flush=True)
    print(f"{'#':>3} {'tik':>5} {'ihlal':>13} {'ist_hata':>9} {'devir@':>7} "
          f"{'görsel tik':>10} {'tespit%':>8} {'EN YAKIN':>9} {'isabet':>7}", flush=True)
    ozetler = []
    for i in range(1, adet + 1):
        if not _yeni_gorev(beyin):
            print(f"{i:3d}  görev başlatılamadı"); continue
        if not beyin.b.canli(): beyin.b.yeniden_bagla()
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
