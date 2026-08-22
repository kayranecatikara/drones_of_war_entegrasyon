# -*- coding: utf-8 -*-
"""İLK UÇTAN UCA DENEME: GPS yaklaşma -> görsel devir -> hücum.
Truth YALNIZ ölçüm/log için okunur; güdüme GİRMEZ."""
import sys, time, math, csv, numpy as np, mss
sys.path.insert(0,".")
# ⛔ DERS: burada `sys.path.insert(0,"dow/sdk"); import drone_sdk` yapıyordum.
#   Bu, dow.sdk.drone_sdk ile AYNI DOSYAYI farklı bir modül nesnesi olarak
#   yükler -> İKİ ayrı _DroneInternal örneği. Güdüm birine bağlanır, ölçüm
#   ölü olan diğerini okur ve her sütun 0 çıkar (bir koşu böyle boşa gitti).
#   Ayrıca oyun aynı anda TEK istemci kabul ediyor; ikinci bağlantı denemesi
#   reddedilir. Çözüm: HER YERDE aynı modül nesnesi.
from dow.sdk import drone_sdk as _sdk
from dow.ana import Beyin, Cfg
from dow.gorus import kamera as KAM
from araclar.kadraj import hazirla, BOLGE, ucusta_mi, oyunu_one_al, yeniden_dogur
from araclar import ucus

sct=mss.MSS(); ok,img0 = hazirla(sct)
print("hazırlık:", "UÇUŞTA" if ok else "BAŞARISIZ", flush=True); assert ok
B = Beyin()
assert B.b.baglan(), "SDK bağlanamadı"
time.sleep(1)
B.det.isit(img0)
print("dedektör ısındı", flush=True)

f=open("logs/uctan_uca.csv","w",newline=""); w=csv.writer(f)
w.writerow(["t","durum","gercek_menzil","ibvs_menzil","ibvs_azimut","ibvs_yukselis",
            "ibvs_v","vis_conf","vis_imgsz","thr","pitch","roll","yaw",
            "irtifa","hiz","own_pitch","gps_tz","gps_zhedef","gps_ez","gps_R"])
try:
    ucus.dur(4.0)
    t0=time.time(); son=t0; n=0; en_yakin=1e9; gorsel_kare=0; uc_dis=0
    while time.time()-t0 < 240:
        t=time.time(); dt=max(1e-3, t-son); son=t
        img=np.array(sct.grab(BOLGE))[:,:,:3]
        if not ucusta_mi(img):
            # DERS: burada yalnız pencereyi öne alıyordum; drone DESPAWN
            # olduysa (batarya ~12 dk) HUD hiç dönmez ve döngü boşa dönerdi.
            # Bir koşu tamamen böyle geçti (35 tik, sahte "0.0 m temas").
            uc_dis += 1
            if uc_dis == 1: oyunu_one_al()
            elif uc_dis % 12 == 0:
                print("  drone despawn -> yeniden doğuruluyor", flush=True)
                yeniden_dogur()
                try: B.b.kapat()
                except Exception: pass
                if B.b.baglan(): print("  yeniden bağlanıldı", flush=True)
                B.spawn_sifirla()
            time.sleep(0.4); continue
        uc_dis = 0
        B.gorsel_tik(img[:,:,::-1], t)
        sonuc = B.adim(t, dt)
        if sonuc is None:                 # bağlantı öldü -> yeniden doğur+bağlan
            print("  bağlantı öldü -> yeniden doğur + bağlan", flush=True)
            yeniden_dogur()
            if B.b.yeniden_bagla():
                print("  yeniden bağlanıldı", flush=True)
                B.spawn_sifirla()      # GERÇEK respawn -> zemin yeniden alınır
            time.sleep(0.5); continue
        thr,pitch,roll,yaw = sonuc
        # ---- YALNIZ ÖLÇÜM: truth (güdüme girmez) ----
        tr=_sdk.get_debug_truth(); tp=tr['target']['position']; dp=_sdk.get_drone_location()
        dx,dy,dz=[(a-b)/100 for a,b in zip(tp,dp)]
        Rg=math.hypot(math.hypot(dx,dy),dz)
        if Rg > 0.05: en_yakin=min(en_yakin,Rg)   # 0 = bozuk truth
        if B.durum=="GORSEL": gorsel_kare+=1
        ti=B.tani
        w.writerow([f"{t-t0:.2f}",B.durum,f"{Rg:.2f}",
                    f"{ti.get('ibvs_menzil_m',-1):.2f}",f"{ti.get('ibvs_azimut',0):.2f}",
                    f"{ti.get('ibvs_yukselis',0):.2f}",f"{ti.get('ibvs_v',0):.2f}",
                    f"{ti.get('vis_conf',0):.2f}",ti.get('vis_imgsz',0),
                    f"{thr:.3f}",f"{pitch:.3f}",f"{roll:.3f}",f"{yaw:.3f}",
                    f"{_sdk.get_drone_altitude()/100:.1f}",f"{_sdk.get_drone_speed()/100:.1f}",
                    f"{math.degrees(B.b.yonelim()[1]):.1f}",
                    f"{ti.get('gps_tz',0):.1f}",f"{ti.get('gps_zhedef',0):.1f}",
                    f"{ti.get('gps_ez',0):.1f}",f"{ti.get('gps_menzil',-1):.1f}"])
        n+=1
        if n%50==0:
            print(f"  t={t-t0:5.0f}s {B.durum:7s} gerçek={Rg:6.1f}m "
                  f"ibvs={ti.get('ibvs_menzil_m',-1):6.1f}m conf={ti.get('vis_conf',0):.2f} "
                  f"en_yakin={en_yakin:.1f}m", flush=True)
        if 0.05 < Rg < 3.0:      # tam 0 = bozuk truth (bağlantı ölü)
            print(f"  🎯 {Rg:.2f} m — TEMAS BÖLGESİ", flush=True)
        if n % 25 == 0: f.flush()
    print(f"\nBİTTİ: {n} tik | görsel fazda %{100*gorsel_kare/max(n,1):.0f} | "
          f"EN YAKIN {en_yakin:.1f} m", flush=True)
finally:
    f.close(); ucus.guvenli_komut()
    try: B.b.kapat()
    except Exception: pass
