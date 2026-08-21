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
    """HUD imzası: DoW kadrajında sağ üstte 'fly/ALT/SPD' beyaz metin bloğu,
    sol altta batarya göstergeleri var. Tarayıcı/terminalde bu desen yoktur.
    Ölçüt: sağ-üst 300x140 kutuda parlak piksel oranı %1-25 arası VE
    kadrajın genel renk çeşitliliği yüksek (düz arayüz değil)."""
    su = img[60:200, 1600:1900]
    parlak = float((su.mean(axis=2) > 200).mean())
    renk_std = float(img.reshape(-1,3).std(axis=0).mean())
    return (0.01 < parlak < 0.25) and (renk_std > 18), parlak, renk_std

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
