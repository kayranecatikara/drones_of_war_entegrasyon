# -*- coding: utf-8 -*-
"""Ölçüm koşuları için güvenli uçuş yardımcıları.
DERS (2026-08-21): bir koşu zaman aşımına uğrayıp ileri-pitch komutu askıda
kalınca drone dakikalarca uçup 1731 m uzaklaştı ve koşu boşa gitti.
Buradaki her fonksiyon try/finally ile GÜVENLİ KOMUT bırakır."""
import math, time, atexit, sys
sys.path.insert(0,"dow/sdk")
import drone_sdk as d

def wrap(a): return (a+180)%360-180

def guvenli_komut():
    """Nötr + irtifa tut. Çıkışta HER ZAMAN çağrılır."""
    try: d.set_control_surfaces(0.0, 0.0, 0.0, 0.0, True)
    except Exception: pass

atexit.register(guvenli_komut)

def geo():
    tr=d.get_debug_truth(); tp=tr['target']['position']; dp=d.get_drone_location()
    dx,dy,dz=[(a-b)/100 for a,b in zip(tp,dp)]
    return tp, dx, dy, dz, math.hypot(math.hypot(dx,dy),dz)

def ofs(R):
    """Menzile ölçekli irtifa ofseti: hedefi kadraj merkezinde tutar
    (kamera 25 derece YUKARI baktığı için h = R*tan(25))."""
    return min(25.0, 0.466*R)

def dur(sn=4.0):
    """Yatay hızı sıfırla — koşu başında askıda kalmış komutu temizler."""
    t=time.time()
    while time.time()-t<sn:
        d.set_control_surfaces(0.0,0.0,0.0,0.0,True); time.sleep(0.03)

def yaklas(cev, hedef_menzil=60.0, azami_sure=180.0, pitch=0.55, log=None):
    """Hedefe hedef_menzil'e kadar yaklaş. İrtifa ofseti menzille ölçeklenir."""
    t0=time.time()
    while time.time()-t0 < azami_sure:
        tp,dx,dy,dz,R = geo()
        if R <= hedef_menzil: return True, R
        ez=(tp[2]/100-ofs(R)) - d.get_drone_altitude()/100
        hy=wrap(math.degrees(math.atan2(dy,dx)) - d.get_drone_rotation()[2])
        # burun hedefe dönmeden ileri gitme (yoksa yanlış yöne kaçarız)
        p = pitch if abs(hy) < 25 else 0.0
        d.set_control_surfaces(cev._vz_cubuk(max(-6.5,min(12.0,0.9*ez))), p, 0,
                               max(-0.7,min(0.7,hy/35)), True)
        if log and int((time.time()-t0)*2)%20==0: log(f"    yaklaşma: R={R:.0f} m hy={hy:+.0f}°")
        time.sleep(0.03)
    tp,dx,dy,dz,R = geo()
    return False, R

def istasyon(cev, pitch):
    """Tek tik: hedefe nişanlı kal, verilen pitch ile. (R, ez, hy, dz) döner."""
    tp,dx,dy,dz,R = geo()
    ez=(tp[2]/100-ofs(R)) - d.get_drone_altitude()/100
    hy=wrap(math.degrees(math.atan2(dy,dx)) - d.get_drone_rotation()[2])
    d.set_control_surfaces(cev._vz_cubuk(max(-6.5,min(12.0,0.9*ez))),
                           pitch if abs(hy)<25 else 0.0, 0,
                           max(-0.7,min(0.7,hy/35)), True)
    return R, ez, hy, dz
