# -*- coding: utf-8 -*-
"""Oyun kadrajını güvenle yakalar. Yanlış pencereyi ölçmeye karşı KAPI."""
import os
import subprocess, numpy as np, mss
import cv2

BOLGE = {'left':0,'top':0,'width':1920,'height':1080}


def bolge_tazele(sessiz=False):
    """Oyun penceresini X'e SORARAK bul ve BOLGE'yi ona göre ayarla.

    ⛔ NEDEN GEREKLİ (2026-08-28, yaşandı ve bir kampanyayı çöpe atacaktı):
      BOLGE sabit 0,0 idi. Ekran düzeni değişince oyun `0,27` konumuna,
      GNOME üst çubuğunun ALTINA açıldı. Yakalanan karenin ilk 27 satırı
      çubuk oldu ve oyun içeriği 27 px kaydı -> `CY=540` varsayımında
      **2.9° dikey sapma**, `hud_parlak` şeridi yanlış yerden okundu.
      Kod hata vermedi; yalnız sayısal kontrol yakaladı.

    ⭐ ÇARE: kadraj artık tahmin etmiyor, SORUYOR. Pencere nereye açılırsa
      açılsın kadraj oraya oturur; ikisi yapısal olarak uyumsuz kalamaz.

    ⚠ GEÇERLİLİK KAPISI: bulunan bölge 1920x1080 DEĞİLSE kabul edilmez ve
      varsayılan korunur. Sebep: kamera kalibrasyonunun tamamı (F_PX=540.4,
      CX/CY=960/540, MENZIL_C=997) bu çözünürlüğe bağlı. Farklı boyutta bir
      pencereyi sessizce yakalamak, tüm geometriyi bozmak demektir.

    Dönüş: (bulundu_mu, açıklama)
    """
    global BOLGE
    try:
        w = subprocess.check_output(
            ["xdotool", "search", "--name", "^DronesOfWar"],
            text=True, timeout=5).split()
        if not w:
            return False, "oyun penceresi yok - varsayilan kullaniliyor"
        g = subprocess.check_output(
            ["xdotool", "getwindowgeometry", "--shell", w[0]],
            text=True, timeout=5)
        d = dict(satir.split("=", 1) for satir in g.strip().splitlines()
                 if "=" in satir)
        x, y = int(d["X"]), int(d["Y"])
        gw, gh = int(d["WIDTH"]), int(d["HEIGHT"])
    except Exception as e:
        return False, "pencere okunamadi (%r) - varsayilan" % (e,)

    if (gw, gh) != (1920, 1080):
        return False, ("pencere %dx%d (1920x1080 DEGIL) -> REDDEDILDI; "
                       "kamera kalibrasyonu 1920x1080'e bagli" % (gw, gh))

    BOLGE.update({"left": x, "top": y, "width": gw, "height": gh})
    if not sessiz:
        print("[KADRAJ] oyun penceresi: +%d+%d %dx%d" % (x, y, gw, gh), flush=True)
    return True, "+%d+%d %dx%d" % (x, y, gw, gh)

# ⚡ HAFİF KAPI BÖLGESİ — sol alttaki akım/batarya bloğu (oyun_mu'nun ayırıcı
#   imzası zaten YALNIZ burada). Tam kare 1920x1080 = 2.07 M piksel; bu şerit
#   240x210 = 50 400 piksel, yani 41 KAT az. Kontrol döngüsü her tikte
#   "drone hâlâ var mı" diye baktığı için bu fark oyunun GPU/X payını
#   doğrudan geri verir (bkz. Ayar.PANEL_YAKALA_HZ notu).
BOLGE_HUD = {'left':80,'top':850,'width':240,'height':210}


def grab_bgr(sct, bolge=None):
    """Ekranı SÜREKLİ (contiguous) **BGR** dizisi olarak al.

    ⛔⛔ 2026-08-25 — BU FONKSİYON ESKİDEN RGB DÖNDÜRÜYORDU VE BU BİR HATAYDI.

    `ultralytics`, kendisine verilen numpy dizisini **BGR** varsayar (PIL
    Image verilirse RGB kabul eder). Biz RGB ndarray veriyorduk; model
    baştan beri KIRMIZI ile MAVİ kanalları TERS görmüş.

    ÖLÇÜLDÜ (talon_v3, 156 kare, truth doğrulamalı):

        kanal sırası          GERÇEK tespit   yanlış-poz   boş kare
        BGR (doğrusu)             %68.6          %7.1       %24.4
        RGB (eski hâl)            %32.1          %2.6       %65.4

    Yani dedektör kapasitesinin YARISINDAN AZINI kullanıyorduk. "Tespit
    kesik kesik" şikâyetinin, angajman bandında %68-88'de takılmanın ve
    büyük ihtimalle v3/v5 farkının büyüklüğünün altında bu yatıyor.

    ⚠ ADI DA DEĞİŞTİ (`grab_rgb` -> `grab_bgr`). Eski adı bırakmak, bir
    sonraki değişikliği yapanı yanıltırdı (CLAUDE.md §5.12: ölü/yanıltıcı
    ad bırakma). Kanal sırasına duyarlı TÜM tüketiciler birlikte güncellendi:
      * dow/panel.py   — RGB2BGR çevrimi KALDIRILDI (artık zaten BGR)
      * araclar/kayit.py — imwrite'taki [:, :, ::-1] KALDIRILDI
      * araclar/esik_tarama.py — imread sonrası BGR2RGB KALDIRILDI
    `hud_parlak`, `ucusta_mi`, `gorev_bitti_mi` kanal sırasından BAĞIMSIZDIR
    (hepsi kanal ortalaması/std kullanır) — dokunulmadı.

    ⚠ NEDEN cvtColor: `np.array(sct.grab())[:,:,:3][:,:,::-1]` bir GÖRÜNÜM
      döner — sürekli değildir. YOLO, cv2.resize ve cv2.imwrite sürekli dizi
      ister, dolayısıyla her biri İÇERDE kopya çıkarır. Ölçüldü (1920x1080):
          np.ascontiguousarray(görünüm)      12.37 ms
          cv2.cvtColor(BGRA -> RGB)           1.25 ms   <- 10 KAT ucuz
      X11 aktarımının kendisi zaten 13.3 ms; üstüne 12 ms bindirmenin anlamı
      yok. (Aynı ölçümde HUD şeridi 1.90 ms — tam kareden 7.9 kat ucuz.)
    """
    sh = sct.grab(bolge or BOLGE)
    buf = np.frombuffer(sh.raw, np.uint8).reshape(sh.height, sh.width, 4)
    # ⚠ KILL-SWITCH: A/B kiyasi icin ESKI (hatali) kanal sirasi geri
    #   uretilebilir. Yalniz OLCUM icindir; varsayilan KAPALI.
    if os.environ.get("DOW_KANAL_ESKI", "0").strip() not in ("0", "", "false"):
        return cv2.cvtColor(buf, cv2.COLOR_BGRA2RGB)
    return cv2.cvtColor(buf, cv2.COLOR_BGRA2BGR)

def oyunu_one_al():
    try:
        w = subprocess.check_output(["xdotool","search","--name","^DronesOfWar"],
                                    text=True).split()[0]
        subprocess.run(["xdotool","windowactivate","--sync",w], timeout=5)
        subprocess.run(["xdotool","windowraise",w], timeout=5)
        return w
    except Exception:
        return None

def oyun_mu(img):
    """DoW FPV kadrajı mı VE drone SPAWN OLMUŞ mu?

    İMZA: sol altta akım/batarya göstergeleri ("11.50A / 4.20v / 25.2v").
    Bunlar drone VAR olduğu sürece görünür — havada da, yerde de.

    ⛔ ÖNCEKİ SÜRÜM SAĞ ÜSTTEKİ 'fly/ALT/SPD' BLOĞUNA BAKIYORDU ve YANILDI:
      uçarken "12:22 / 173m / 49kmh" bol beyaz piksel verirken, yerde
      "00:00 / 0m / 0kmh" çok az verir ve eşiğin altında kalır. Bir uçtan
      uca koşu tamamen bu yüzden boşa gitti (döngü "despawn" sanıp durdu).
      ÖLÇÜLDÜ (parlak piksel oranı, >190):
        sağ üst : yerde 0.057 | uçuşta 0.072 | spawn-bekler 0.000
        SOL ALT : yerde 0.151 | uçuşta 0.155 | spawn-bekler 0.000  <- AYIRICI
      Sol alt, drone'un varlığını durumdan BAĞIMSIZ ayırıyor."""
    b = img[850:1060, 80:320].mean(axis=2)
    parlak = float((b > 190).mean())
    # ⚡ ALT-ÖRNEKLEME: tam kare std'si 6.2 milyon piksel = ~90 ms ve panel
    #   FPS'ini 10'a düşürüyordu. 1/64 örnek aynı kararı verir, ~1.4 ms.
    renk_std = float(img[::8, ::8].reshape(-1, 3).std(axis=0).mean())
    return (parlak > 0.05) and (renk_std > 15), parlak, renk_std

def hud_parlak(img_hud):
    """BOLGE_HUD ile alınmış şeritten parlak piksel oranı.
    ÖLÇÜLDÜ (bkz. oyun_mu): yerde 0.151 | uçuşta 0.155 | spawn-bekler 0.000."""
    return float((img_hud.mean(axis=2) > 190).mean())


def ucusta_mi_hud(img_hud):
    """Tam kare gerektirmeyen HIZLI uçuş kapısı.

    ⚠ Tam karedeki `renk_std` kapısı BURADA YOK; o kapı 'yanlış pencereyi
      ölçüyor muyum' sorusuna bakıyordu ve `hazirla()` koşu başında zaten
      tam kareyle doğruluyor. Döngü içinde tam kare doğrulaması 2 s'de bir
      ayrıca yapılır (kosu.py), yani kapı kaybolmuyor — SEYRELİYOR."""
    return hud_parlak(img_hud) > 0.05


def kapi(sct, dene=3):
    """Oyun kadrajı doğrulanana kadar pencereyi öne alır. (ok, img, tani)"""
    for i in range(dene):
        img = np.array(sct.grab(BOLGE))[:,:,:3]
        ok, p, s = oyun_mu(img)
        if ok:
            return True, img[:,:,::-1], (p, s)
        oyunu_one_al()
        import time; time.sleep(1.5)
    return False, img[:,:,::-1], (p, s)

def ucusta_mi(img):
    """HUD var mı = drone spawn olmuş ve uçuyor mu."""
    return oyun_mu(img)[0]

def yeniden_dogur(bekle=6.0):
    """Drone despawn olduysa (batarya bitti/düştü) 'E' ile yeniden çıkarır."""
    import time
    w = oyunu_one_al()
    if not w: return False
    time.sleep(1.0)
    # ⛔ `--window` ile gönderilen tuş UE oyununa ULAŞMIYOR (2026-08-28;
    #    gorev_yeniden_oyna ve goreve_gir.sh'te de aynı hata) -> odakla,
    #    sonra GERÇEK tuş gönder.
    subprocess.run(["xdotool", "windowactivate", "--sync", w], timeout=5)
    time.sleep(0.5)
    subprocess.run(["xdotool", "key", "e"], timeout=5)
    time.sleep(bekle)
    return True

def gorev_bitti_mi(img):
    """Ekranda 'MISSION COMPLETED' görev-sonu ekranı var mı?

    NEDEN GEREKLİ (2026-08-24): sistem hedefi VURUNCA görev tamamlanıyor,
    oyun bu ekrana düşüyor ve **SDK 12345 portunu dinlemeyi bırakıyor**.
    'E' burada işe yaramaz; PLAY AGAIN gerekir. Kampanyada her koşu AYRI
    SÜREÇ olduğu için sonraki süreç `hazirla()`da takılır ve
    "hazırlık: BAŞARISIZ" der — ISP kampanyasının ilk denemesinde 4 koşu
    üst üste böyle düştü.

    ⛔⛔⛔ ÜÇ KEZ YANLIŞ YAZDIM. Hepsi öğretici, o yüzden duruyorlar:
      1. "ortada parlak yazı bandı" — MISSION COMPLETED yazısı kum rengi
         arazi üstünde DÜŞÜK kontrastlı. Hiç yakalamadı.
      2. "üst pusula bandında koyu piksel oranı" — SAHNEYE bağlı: bir
         karede üst bant gökyüzüydü (0.000 geçti), diğerinde koyu tepeler
         (0.193 kaldı). Kamera nereye bakarsa değişiyor.
      3. "PLAY AGAIN bölgesinde >195 parlak piksel" — doğru ÖĞEYE bakıyordu
         ama EŞİK YANLIŞTI: ham piksellerde düğme yazısı en fazla **191**.
         Kaydedilmiş JPEG'de sıkıştırma artefaktı 195'i aşırıyor, canlı ham
         karede aşmıyordu. Yani test GEÇİYOR, canlı DÜŞÜYORDU.

    ⭐ DOĞRUSU — FARK TABANLI, arayüz öğesine bakan kural:
    PLAY AGAIN düğmesinin bölgesi ile AYNI YÜKSEKLİKTEKİ boş şerit kıyaslanır.
    Ölçüldü (3 görev-sonu + 5 negatif kare, eşik 170):

        ekran        sag_btn   bos_serit   fark    alt_std
        GÖREV-SONU 1  0.091      0.000    +0.091     15.4
        GÖREV-SONU 2  0.091      0.000    +0.091     16.0
        GÖREV-SONU 3  0.091      0.000    +0.091     16.6
        PRESS-E       0.000      0.005    -0.004     11.6
        FPV 1         0.011      0.324    -0.313     38.2
        FPV 2         0.402      0.807    -0.404     40.4
        FPV 3         0.000      0.021    -0.021     35.8
        FPV 4         0.114      0.266    -0.152     42.9

    Fark tabanlı olması ŞART: FPV'de düğme bölgesi de parlak olabiliyor
    (0.40), ama o zaman YANINDAKİ ŞERİT DE parlak. Görev-sonunda ise
    yalnız düğmenin olduğu yer parlak. Sahne parlaklığı ikisini eşit
    etkiler, fark sabit kalır.

    KURAL: uçuşta DEĞİLİZ (alt_std < 25) VE düğme bölgesi komşusundan
    belirgin parlak (fark > 0.03).
    """
    import numpy as _np
    if img is None:
        return False
    h, w = img.shape[:2]
    g = _np.asarray(img, dtype=_np.float32).mean(axis=2)
    alt = g[int(0.78 * h):, :int(0.20 * w)]          # sol alt HUD bloğu
    btn = g[int(0.845 * h):int(0.895 * h), int(0.71 * w):int(0.89 * w)]
    bos = g[int(0.845 * h):int(0.895 * h), int(0.40 * w):int(0.62 * w)]
    if alt.size == 0 or btn.size == 0 or bos.size == 0:
        return False
    fark = float((btn > 170).mean()) - float((bos > 170).mean())
    return float(alt.std()) < 25.0 and fark > 0.03


def gorev_yeniden_oyna(sct=None, bekle=8.0):
    """Görev-sonu ekranından HIZLI kurtarma: PLAY AGAIN -> E.

    ÖLÇÜLDÜ 2026-08-24: bu yol ~15 s sürüyor; alternatifi olan tam oyun
    yeniden başlatma (`calistirma_betikleri/goreve_gir.sh`) ~2 dakika.
    PLAY AGAIN düğmesi oyun kadrajında (1530, 940) — ekran görüntüsüyle
    doğrulandı, tıklama sonrası 'Press E' ekranı geldi ve E ile SDK portu
    açıldı."""
    import time
    w = oyunu_one_al()
    if not w: return False
    # ⛔ İKİ HATA BİRDEN YAŞANDI (2026-08-28) — bir koşu bu yüzden düştü
    #    ("görev-sonu ekranı" üç kez denendi, üçü de ıskaladı,
    #     "hazırlık: BAŞARISIZ"):
    #  1) Tıklama sabit (1530, 940) idi, yani oyunun 0,0'da olduğunu
    #     varsayıyordu. Oyun AOC monitörüne (+1920+0) taşınınca boşa gitti.
    #     Çare: BOLGE ofseti eklenir; BOLGE pencereyi X'e sorarak bulunur.
    #  2) `xdotool key --window w e` UE oyununa ULAŞMIYOR (goreve_gir.sh'te
    #     de aynı hata vardı). Çare: odakla, sonra GERÇEK tuş gönder.
    bolge_tazele(sessiz=True)              # pencere taşınmış olabilir
    time.sleep(1.0)
    _x = BOLGE.get("left", 0) + 1530
    _y = BOLGE.get("top", 0) + 940
    subprocess.run(["xdotool", "mousemove", str(_x), str(_y), "click", "1"],
                   timeout=5)
    time.sleep(bekle)
    oyunu_one_al(); time.sleep(1.0)
    subprocess.run(["xdotool", "windowactivate", "--sync", w], timeout=5)
    time.sleep(0.5)
    subprocess.run(["xdotool", "key", "e"], timeout=5)
    time.sleep(6.0)
    return True


def hazirla(sct, dene=4):
    """Ölçüm öncesi: pencereyi öne al, gerekiyorsa drone'u yeniden doğur,
    kadraj HUD'lı (uçuşta) olana kadar dener. (ok, img)

    ⭐ GÖREV-SONU EKRANI BURADA DA SINANIR (2026-08-24).
    Kampanyada HER KOŞU AYRI SÜREÇTİR; `kosu.py::_yeni_gorev` yalnız tek
    sürecin İÇİNDEKİ koşular arası çalışır. Sistem hedefi vurup görev
    bitince sonraki SÜREÇ burada, `hazirla()`da takılır ve
    "hazırlık: BAŞARISIZ" der. ISP kampanyasının ilk denemesinde 4 koşu
    üst üste böyle düştü ve kurtarma hiç tetiklenmedi — çünkü yanlış yere
    bağlanmıştı. 'E' bu ekranda işe yaramaz; PLAY AGAIN gerekir."""
    import time
    # ⭐ KADRAJ PENCEREYE OTURTULUR (2026-08-28). Sabit 0,0 varsaymak, oyun
    #   GNOME çubuğunun altına açılınca 27 px kaymaya ve 2.9° dikey sapmaya
    #   yol açıyordu. Bkz. bolge_tazele().
    bolge_tazele()
    for i in range(dene):
        img = np.array(sct.grab(BOLGE))[:,:,:3]
        if ucusta_mi(img):
            return True, img[:,:,::-1]
        if gorev_bitti_mi(img):
            print("  [görev-sonu ekranı — PLAY AGAIN ile yeniden oynanıyor]",
                  flush=True)
            gorev_yeniden_oyna()
            img = np.array(sct.grab(BOLGE))[:,:,:3]
            if ucusta_mi(img):
                return True, img[:,:,::-1]
        oyunu_one_al(); time.sleep(1.0)
        img = np.array(sct.grab(BOLGE))[:,:,:3]
        if ucusta_mi(img):
            return True, img[:,:,::-1]
        yeniden_dogur()
    img = np.array(sct.grab(BOLGE))[:,:,:3]
    return ucusta_mi(img), img[:,:,::-1]
