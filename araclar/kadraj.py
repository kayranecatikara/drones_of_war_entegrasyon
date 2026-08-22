# -*- coding: utf-8 -*-
"""Oyun kadrajını güvenle yakalar. Yanlış pencereyi ölçmeye karşı KAPI."""
import subprocess, numpy as np, mss

BOLGE = {'left':0,'top':0,'width':1920,'height':1080}

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
    subprocess.run(["xdotool","key","--window",w,"e"], timeout=5)
    time.sleep(bekle)
    return True

def hazirla(sct, dene=4):
    """Ölçüm öncesi: pencereyi öne al, gerekiyorsa drone'u yeniden doğur,
    kadraj HUD'lı (uçuşta) olana kadar dener. (ok, img)"""
    import time
    for i in range(dene):
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
