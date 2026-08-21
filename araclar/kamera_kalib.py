# -*- coding: utf-8 -*-
"""
KAMERA MODELİ KALİBRASYONU — ölçümle.
Bilinmeyenler: kamera tilt açısı, fx, fy, ve kendi pitch/roll'umuzun İŞARETİ.
Girdi: logs/kamera_kalib.csv (truth geometri + kendi yönelimimiz + bbox'lar)

YÖNTEM
  1) Her karede "hedef kutusu"nu seç: beklenen boyutun 0.5-2 katı olan,
     en yüksek güvenli kutu. (Menzil truth'tan bilindiği için boyut kapısı
     GÜVENİLİR bir etikettir; bu YALNIZ kalibrasyon içindir, güdümde yok.)
  2) Hedefin gövde çerçevesindeki birim vektörünü kur:
        v_yatay = [cos(elev)cos(hy), cos(elev)sin(hy), sin(elev)]
     sonra kendi pitch/roll'umuzu GERİ AL (işaret bilinmiyor -> 4 kombinasyon denenir).
  3) Kamerayı TILT kadar yukarı çevir, delik-iğne modeliyle piksele bas:
        u = CX + fx * (y/x)          v = CY - fy * (z/x)
  4) TILT, fx, fy'yi en küçük kareler ile çöz; artığı raporla.
"""
import numpy as np, math

def _don_y(a):
    c,s=math.cos(a),math.sin(a)
    return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def _don_x(a):
    c,s=math.cos(a),math.sin(a)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]])

def yukle(yol="logs/kamera_kalib.csv"):
    d=np.genfromtxt(yol,delimiter=",",names=True)
    return d

def hedef_kutulari(d, alt=0.5, ust=2.0):
    """Kare kare: boyut kapısını geçen EN YÜKSEK güvenli kutu."""
    key=lambda r:(round(r['menzil'],2),round(r['yaw_hata'],2))
    gruplar={}
    for r in d:
        gruplar.setdefault(key(r),[]).append(r)
    out=[]
    for _,g in gruplar.items():
        aday=[r for r in g if r['sira']>=0 and alt*r['bek_px']<=r['bw']<=ust*r['bek_px']]
        if aday:
            out.append(max(aday,key=lambda r:r['conf']))
    return out

def coz(kayitlar, p_isaret=+1, r_isaret=+1):
    """TILT, fx, fy'yi çöz. Döndürür: (tilt_deg, fx, fy, artik_px, n)"""
    V=[]; U=[]; Vp=[]
    for r in kayitlar:
        e=math.radians(r['elev']); h=math.radians(r['yaw_hata'])
        v=np.array([math.cos(e)*math.cos(h), math.cos(e)*math.sin(h), math.sin(e)])
        # kendi yönelimimizi geri al
        v=_don_x(-r_isaret*math.radians(r['own_roll'])) @ \
          _don_y(-p_isaret*math.radians(r['own_pitch'])) @ v
        V.append(v); U.append(r['bcx']); Vp.append(r['bcy'])
    V=np.array(V); U=np.array(U); Vp=np.array(Vp)
    en_iyi=None
    for tilt in np.arange(0.0, 45.0, 0.25):
        Vt = (_don_y(math.radians(tilt)) @ V.T).T      # kamerayı yukarı çevir
        x,y,z = Vt[:,0],Vt[:,1],Vt[:,2]
        ok = x>0.15
        if ok.sum()<15: continue
        # u = 960 + fx*(y/x)  -> fx en küçük kareler
        ax=(y/x)[ok]; bu=(U-960)[ok]
        fx=float(ax@bu/max(ax@ax,1e-9))
        az=(z/x)[ok]; bv=(540-Vp)[ok]
        fy=float(az@bv/max(az@az,1e-9))
        ru=bu-fx*ax; rv=bv-fy*az
        art=float(np.sqrt((ru**2+rv**2).mean()))
        if en_iyi is None or art<en_iyi[3]:
            en_iyi=(tilt,fx,fy,art,int(ok.sum()))
    return en_iyi
