# -*- coding: utf-8 -*-
"""
================================================================================
DoW PANELİ — canlı kamera + tespit kutusu + telemetri + CANLI AYAR
================================================================================
Gazebo'daki gcs_server panelinin DoW karşılığı (CLAUDE.md §6).
Bağımlılık YOK: stdlib http.server. Tarayıcıdan  http://127.0.0.1:8800

  /                 arayüz
  /video            MJPEG akışı (dedektör kutusu ÇİZİLİ)
  /telem            JSON telemetri
  /ayar   (POST)    canlı ayar değişikliği  {"ad": "...", "deger": ...}

⚠ Panel güdüm döngüsünü BLOKLAMAZ: son kareyi ve son telemetriyi paylaşımlı
  bir kutudan okur (latest-wins). Kare üretmek panelin işi değildir.
================================================================================
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

from dow.ayarlar import Ayar, CANLI

_kutu = {"jpg": None, "zoom": None, "telem": {}, "t": 0.0}
_kilit = threading.Lock()
# Son tespiti KISA SÜRE saklarız: dedektör 2 Hz koşuyor ve tespit oranı
# ~%45, yani kutu sürekli kaybolup görünüyor. Kullanıcı "hedefi algıladığını
# göremedim" dedi — kalıcılık olmadan göz yakalayamıyor.
_son_det = {"d": None, "t": 0.0}
DET_OMUR_S = 1.5


def kare_koy(img_rgb, tespit=None, telem=None, kalite=70, olcek=0.5):
    """Güdüm döngüsü her karede çağırır. tespit: (cx,cy,w,h,conf) ya da None."""
    try:
        simdi = time.time()
        if tespit:
            _son_det["d"] = tespit; _son_det["t"] = simdi
        d = _son_det["d"]
        yas = simdi - _son_det["t"]
        taze = d is not None and yas <= DET_OMUR_S

        im = img_rgb[:, :, ::-1].copy()          # RGB -> BGR
        hh, ww = im.shape[:2]
        zoom = None
        if taze:
            cx, cy, w, h, conf = d
            x1, y1 = int(cx - w / 2), int(cy - h / 2)
            x2, y2 = int(cx + w / 2), int(cy + h / 2)
            canli = tespit is not None
            renk = (0, 255, 0) if canli else (0, 190, 255)   # taze / bayat
            cv2.rectangle(im, (x1, y1), (x2, y2), renk, 3)
            # KILAVUZ ÇEMBER: kutu 20 px olunca gözle bulunamıyor; etrafına
            # büyük bir halka çizip bakışı oraya çekiyoruz.
            cv2.circle(im, (int(cx), int(cy)), max(45, int(1.9*max(w, h))), renk, 2)
            et = f"talon {conf:.2f}  {max(w,h):.0f}px"
            if not canli: et += f"  ({yas:.1f}s)"
            cv2.putText(im, et, (max(5, x1 - 40), max(24, y1 - 26)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, renk, 2)
            # YAKINLAŞTIRILMIŞ KESİT — 21 px'lik hedef yarı ölçekli panelde
            # nokta kadar; ayrı bir pencerede 5x büyütülür.
            k = 110
            zx1, zy1 = max(0, int(cx) - k), max(0, int(cy) - k)
            zx2, zy2 = min(ww, int(cx) + k), min(hh, int(cy) + k)
            if zx2 - zx1 > 20 and zy2 - zy1 > 20:
                z = im[zy1:zy2, zx1:zx2]
                z = cv2.resize(z, (440, 440), interpolation=cv2.INTER_NEAREST)
                cv2.rectangle(z, (0, 0), (439, 439), renk, 3)
                ok2, zb = cv2.imencode(".jpg", z,
                                       [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if ok2: zoom = zb.tobytes()
        cv2.drawMarker(im, (ww // 2, hh // 2), (255, 160, 0),
                       cv2.MARKER_CROSS, 30, 1)
        if olcek != 1.0:
            im = cv2.resize(im, None, fx=olcek, fy=olcek,
                            interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", im, [int(cv2.IMWRITE_JPEG_QUALITY), kalite])
        if not ok:
            return
        with _kilit:
            _kutu["jpg"] = buf.tobytes()
            if zoom is not None: _kutu["zoom"] = zoom
            if telem is not None:
                telem = dict(telem)
                telem["tespit"] = "VAR" if tespit else ("bayat %.1fs" % yas
                                                        if taze else "yok")
                if taze:
                    telem["vis_conf"] = round(d[4], 2)
                    telem["vis_kutu_px"] = round(max(d[2], d[3]), 1)
                _kutu["telem"] = telem
            _kutu["t"] = time.time()
    except Exception:
        pass


def telem_koy(telem):
    with _kilit:
        _kutu["telem"] = telem
        _kutu["t"] = time.time()


_HTML = """<!doctype html><meta charset=utf-8><title>DoW Panel</title>
<style>
 body{background:#0d0f12;color:#dfe3e8;font:14px system-ui,sans-serif;margin:0}
 .w{display:flex;gap:14px;padding:14px;flex-wrap:wrap}
 .k{background:#161a1f;border:1px solid #262c34;border-radius:10px;padding:12px}
 img{width:min(900px,60vw);border-radius:8px;display:block;background:#000}
 table{border-collapse:collapse;font-variant-numeric:tabular-nums}
 td{padding:2px 10px 2px 0;white-space:nowrap}
 td.v{color:#7fd1ff;text-align:right;font-weight:600}
 h3{margin:0 0 8px;font-size:13px;letter-spacing:.06em;color:#8b96a3;text-transform:uppercase}
 .faz{display:inline-block;padding:3px 10px;border-radius:6px;background:#1d4ed8;font-weight:700}
 .kotu{background:#b91c1c}.iyi{background:#15803d}
 input[type=range]{width:190px;vertical-align:middle}
 .a{margin:7px 0}.a label{display:inline-block;width:190px;color:#a8b3c0}
 .n{color:#7fd1ff;display:inline-block;width:64px;text-align:right}
 button{background:#1f2937;color:#dfe3e8;border:1px solid #374151;border-radius:6px;
        padding:4px 10px;cursor:pointer}
</style>
<div class=w>
 <div class=k><h3>FPV + tespit</h3><img id=v src="/video"></div>
 <div class=k><h3>Hedef — 5× yakın</h3>
   <img id=z src="/zoom" style="width:340px;image-rendering:pixelated"></div>
 <div class=k style="min-width:330px">
   <h3>Durum</h3><div id=faz class=faz>—</div>
   <table id=t></table>
 </div>
 <div class=k style="min-width:430px"><h3>Canlı ayar</h3><div id=a></div></div>
</div>
<script>
const AL=["durum","tespit","vis_conf","vis_kutu_px","ist_hata_m","ist_hata_yatay","ist_hata_dikey","hedef_menzil_m",
 "hedef_hiz","hedef_yon","yaw_hata","v_istek","yukseklik","drone_hiz",
 "vis_conf","vis_menzil","bekci"];
async function tik(){
 try{const r=await fetch('/telem'),d=await r.json();
  const f=document.getElementById('faz');
  f.textContent=d.durum||'—';
  f.className='faz'+(d.durum==='ISTASYON'?' iyi':(d.bekci&&d.bekci!=='sağlıklı'?' kotu':''));
  let h='';
  for(const k of AL){ if(d[k]===undefined||k==='durum')continue;
    let v=d[k]; if(typeof v==='number')v=v.toFixed(2);
    h+=`<tr><td>${k}</td><td class=v>${v}</td></tr>`;}
  document.getElementById('t').innerHTML=h;
 }catch(e){}
}
async function ayarlar(){
 const r=await fetch('/ayar'),d=await r.json();let h='';
 for(const [ad,o] of Object.entries(d)){
  if(o.tip==='b'){h+=`<div class=a><label>${o.etiket}</label>
    <button onclick="set('${ad}',${o.deger?0:1})">${o.deger?'AÇIK':'kapalı'}</button></div>`;}
  else if(o.tip==='f'){h+=`<div class=a><label>${o.etiket}</label>
    <input type=range min=${o.min} max=${o.max} step=0.01 value=${o.deger}
     oninput="document.getElementById('n_${ad}').textContent=this.value"
     onchange="set('${ad}',parseFloat(this.value))">
    <span class=n id=n_${ad}>${o.deger}</span></div>`;}
  else {h+=`<div class=a><label>${o.etiket}</label><span class=n>${o.deger}</span></div>`;}
 }
 document.getElementById('a').innerHTML=h;
}
async function set(ad,deger){
 await fetch('/ayar',{method:'POST',body:JSON.stringify({ad,deger})});
 ayarlar();
}
ayarlar();setInterval(tik,300);
setInterval(()=>{document.getElementById('z').src='/zoom?'+Date.now()},400);
</script>"""


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):  pass

    def _json(self, obj, kod=200):
        b = json.dumps(obj).encode()
        self.send_response(kod)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path == "/":
            b = _HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b); return
        if self.path == "/zoom":
            with _kilit: z = _kutu["zoom"]
            if not z:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(z)))
            self.end_headers(); self.wfile.write(z); return
        if self.path == "/telem":
            with _kilit: t = dict(_kutu["telem"])
            self._json(t); return
        if self.path == "/ayar":
            d = {}
            for ad, (tip, etiket, mn, mx) in CANLI.items():
                d[ad] = {"tip": tip, "etiket": etiket, "min": mn, "max": mx,
                         "deger": getattr(Ayar, ad)}
            self._json(d); return
        if self.path == "/video":
            self.send_response(200)
            self.send_header("Content-Type",
                             "multipart/x-mixed-replace; boundary=k")
            self.end_headers()
            son = 0.0
            try:
                while True:
                    with _kilit:
                        jpg, t = _kutu["jpg"], _kutu["t"]
                    if jpg and t != son:
                        son = t
                        self.wfile.write(b"--k\r\nContent-Type: image/jpeg\r\n"
                                         b"Content-Length: " +
                                         str(len(jpg)).encode() + b"\r\n\r\n" +
                                         jpg + b"\r\n")
                    else:
                        time.sleep(0.02)
            except Exception:
                return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/telem":
            # Kampanya süreci güdüm telemetrisini BURAYA basar; böylece
            # izleyici (kamera+tespit) ile güdüm sayıları TEK panelde birleşir.
            n = int(self.headers.get("Content-Length", 0))
            try:
                d = json.loads(self.rfile.read(n) or b"{}")
                with _kilit:
                    t = dict(_kutu["telem"]); t.update(d); _kutu["telem"] = t
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "hata": str(e)}, 400)
            return
        if self.path != "/ayar":
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0))
        try:
            d = json.loads(self.rfile.read(n) or b"{}")
            ad = d["ad"]
            if ad not in CANLI:
                raise KeyError(ad)
            tip = CANLI[ad][0]
            v = d["deger"]
            setattr(Ayar, ad, bool(v) if tip == "b" else
                    (float(v) if tip == "f" else str(v)))
            self._json({"ok": True, ad: getattr(Ayar, ad)})
        except Exception as e:
            self._json({"ok": False, "hata": str(e)}, 400)


def baslat(port=8800):
    s = ThreadingHTTPServer(("127.0.0.1", port), _H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    print(f"[panel] http://127.0.0.1:{port}", flush=True)
    return s
