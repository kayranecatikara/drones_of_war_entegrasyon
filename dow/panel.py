# -*- coding: utf-8 -*-
"""
================================================================================
DoW PANELİ — YÜKSEK FPS, ANALİZ ODAKLI
================================================================================
Kullanıcı isteği (2026-08-22):
  "panel çok düşük FPS ile çalışıyor... detection modelinin tam performansını
   görmek istiyorum... o slidebarları kaldır, ayarları değiştirme işi sende...
   arayüzü benim uçuşu analiz edebileceğim hale getir."

TASARIM
  * Kaydırıcı YOK. Ayar paneli YOK. Ayarları yapay zekâ değiştirir.
  * Kamera ve dedektör KENDİ hızlarında basılır; UI onları yavaşlatmaz.
  * Üç ayrı FPS sayacı: YAKALAMA / DEDEKTÖR / EKRAN — hangisinin darboğaz
    olduğu tek bakışta görünsün.
  * TESPİT ŞERİDİ: son ~20 s'nin kare kare tespit/kayıp haritası. Dedektörün
    sürekliliğini (asıl mesele bu) gözle değerlendirmek için.
  * Takip (HybridSORT) kutusu ayrı renkte: yeşil = bu karede TESPİT,
    turuncu = takipçinin ÖNGÖRÜSÜ (coast), yani dedektör bulamadı ama iz sürüyor.

HIZ MİMARİSİ
  Üretici (yakalama+çıkarım) döngüsü panele YALNIZ son kareyi bırakır
  (latest-wins). MJPEG akışı yeni kare geldikçe basar; bekleme yok.
================================================================================
"""
import json
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

_K = {"jpg": None, "zoom": None, "telem": {}, "sayac": 0}
_kilit = threading.Lock()
_serit = deque(maxlen=400)      # (t, durum) 0=kayıp 1=tespit 2=takip öngörüsü
_fps = {"yakala": deque(maxlen=40), "dedektor": deque(maxlen=40),
        "ekran": deque(maxlen=40)}


def _hz(d):
    if len(d) < 2:
        return 0.0
    dt = d[-1] - d[0]
    return (len(d) - 1) / dt if dt > 1e-6 else 0.0


def fps_isaretle(ad):
    _fps[ad].append(time.time())


def kare_koy(img_rgb, tespit=None, iz=None, telem=None, kalite=62, olcek=0.5):
    """iz: (cx,cy,w,h,id,coast) — HybridSORT izi (tespit yoksa da gelir)."""
    try:
        # ⚡ ÖNCE küçült, SONRA çevir+çiz: tüm çizim 1/4 piksel üzerinde
        #   olur, JPEG kodlama da ucuzlar. Ölçülen:
        #     img[:,:,::-1].copy() 8.62 ms  vs  cvtColor 0.15 ms (57 kat)
        #     resize+cvtColor birlikte 0.20 ms
        #   Çizim koordinatları TAM ÇÖZÜNÜRLÜKTEN gelir -> `o` ile ölçeklenir.
        o = olcek
        kck = cv2.resize(img_rgb, None, fx=o, fy=o,
                         interpolation=cv2.INTER_LINEAR) if o != 1.0 else img_rgb
        im = cv2.cvtColor(kck, cv2.COLOR_RGB2BGR)
        hh, ww = im.shape[:2]
        zoom = None
        odak = None

        # --- TAKİP kutusu (öngörü dahil) ---
        if iz is not None:
            cx, cy, w, h, tid, coast = iz
            cx, cy, w, h = cx*o, cy*o, w*o, h*o
            canli = coast == 0
            renk = (60, 255, 60) if canli else (0, 170, 255)
            x1, y1 = int(cx - w / 2), int(cy - h / 2)
            x2, y2 = int(cx + w / 2), int(cy + h / 2)
            cv2.rectangle(im, (x1, y1), (x2, y2), renk, 2)
            # köşe işaretleri (küçük kutuyu gözle bulmayı kolaylaştırır)
            L = max(10, int(0.6 * max(w, h)))
            for (px, py, dx, dy) in ((x1, y1, 1, 1), (x2, y1, -1, 1),
                                     (x1, y2, 1, -1), (x2, y2, -1, -1)):
                cv2.line(im, (px, py), (px + dx * L, py), renk, 3)
                cv2.line(im, (px, py), (px, py + dy * L), renk, 3)
            et = f"#{int(tid)}"
            if not canli:
                et += f"  ONGORU +{int(coast)}"
            cv2.putText(im, et, (x1, max(18, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, renk, 2)
            odak = (cx, cy, renk)
            _serit.append((time.time(), 1 if canli else 2))
        else:
            _serit.append((time.time(), 0))

        # --- ham TESPİT (takipten farklıysa ayrı göster) ---
        if tespit is not None:
            cx, cy, w, h = [v*o for v in tespit[:4]]; conf = tespit[4]
            cv2.putText(im, f"{conf:.2f}", (int(cx + w / 2) + 6, int(cy)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 255, 60), 2)
            if odak is None:
                odak = (cx, cy, (60, 255, 60))

        # --- kadraj merkezi ---
        cv2.line(im, (ww // 2 - 14, hh // 2), (ww // 2 + 14, hh // 2), (255, 170, 0), 1)
        cv2.line(im, (ww // 2, hh // 2 - 14), (ww // 2, hh // 2 + 14), (255, 170, 0), 1)

        # --- yakın kesit ---
        if odak is not None and (_K["sayac"] % 2 == 0):
            cx, cy, renk = odak
            k = int(100 * o)
            zx1, zy1 = max(0, int(cx) - k), max(0, int(cy) - k)
            zx2, zy2 = min(ww, int(cx) + k), min(hh, int(cy) + k)
            if zx2 - zx1 > 24 and zy2 - zy1 > 24:
                z = cv2.resize(im[zy1:zy2, zx1:zx2], (400, 400),
                               interpolation=cv2.INTER_NEAREST)
                cv2.rectangle(z, (0, 0), (399, 399), renk, 2)
                ok2, zb = cv2.imencode(".jpg", z, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
                if ok2:
                    zoom = zb.tobytes()

        # ⚡ INTER_LINEAR: INTER_AREA 3.07 ms, LINEAR 0.47 ms (6 kat hızlı;
        #   yalnız gösterim için, ölçüm buradan yapılmıyor)
        ok, buf = cv2.imencode(".jpg", im, [int(cv2.IMWRITE_JPEG_QUALITY), kalite])
        if not ok:
            return
        with _kilit:
            _K["jpg"] = buf.tobytes()
            if zoom is not None:
                _K["zoom"] = zoom
            if telem is not None:
                _K["telem"] = telem
            _K["sayac"] += 1
    except Exception:
        pass


def _serit_ozet(pencere=20.0):
    simdi = time.time()
    son = [(t, d) for t, d in _serit if simdi - t <= pencere]
    if not son:
        return [], 0.0, 0.0
    n = len(son)
    tesp = sum(1 for _, d in son if d == 1)
    izli = sum(1 for _, d in son if d >= 1)
    return [d for _, d in son][-140:], 100.0 * tesp / n, 100.0 * izli / n


_HTML = """<!doctype html><meta charset=utf-8><title>DoW — Görüş Analizi</title>
<style>
:root{--bg:#0a0c10;--k:#141922;--ç:#222c3a;--y:#e6edf5;--s:#8b98a8;--v:#4ade80;--t:#fb923c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--y);
     font:13px/1.45 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.üst{display:flex;align-items:center;gap:18px;padding:10px 16px;
     background:var(--k);border-bottom:1px solid var(--ç)}
.üst h1{margin:0;font-size:14px;letter-spacing:.14em;text-transform:uppercase;color:var(--s)}
.fps{display:flex;gap:16px;margin-left:auto}
.fps div{text-align:right}
.fps b{display:block;font-size:19px;font-variant-numeric:tabular-nums;color:var(--v)}
.fps span{font-size:10px;letter-spacing:.1em;color:var(--s);text-transform:uppercase}
.gövde{display:grid;grid-template-columns:1fr 330px;gap:14px;padding:14px}
.kart{background:var(--k);border:1px solid var(--ç);border-radius:10px;overflow:hidden}
.kart h2{margin:0;padding:8px 12px;font-size:11px;letter-spacing:.12em;color:var(--s);
         text-transform:uppercase;border-bottom:1px solid var(--ç)}
#v{display:block;width:100%;background:#000}
#z{display:block;width:100%;image-rendering:pixelated;background:#000}
.satır{display:flex;justify-content:space-between;padding:5px 12px;
       border-bottom:1px solid #1a212c;font-variant-numeric:tabular-nums}
.satır:last-child{border:0}
.satır i{font-style:normal;color:var(--s)}
.satır b{font-weight:600}
#şerit{display:flex;gap:1px;height:34px;padding:8px 12px;align-items:stretch}
#şerit i{flex:1;border-radius:1px;background:#25303f}
#şerit i.d{background:var(--v)}
#şerit i.t{background:var(--t)}
.açk{display:flex;gap:14px;padding:6px 12px 10px;font-size:11px;color:var(--s)}
.açk s{text-decoration:none;display:inline-block;width:10px;height:10px;
       border-radius:2px;margin-right:5px;vertical-align:-1px}
.büyük{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums;
       padding:6px 12px 12px}
</style>
<div class=üst>
  <h1>DoW · Görüş Analizi</h1>
  <div class=fps>
    <div><b id=f1>—</b><span>yakalama</span></div>
    <div><b id=f2>—</b><span>dedektör</span></div>
    <div><b id=f3>—</b><span>ekran</span></div>
  </div>
</div>
<div class=gövde>
  <div>
    <div class=kart><h2>FPV — tespit + HybridSORT izi</h2><img id=v src="/video"></div>
    <div class=kart style="margin-top:14px">
      <h2>Tespit sürekliliği — son 20 saniye</h2>
      <div id=şerit></div>
      <div class=açk>
        <span><s style="background:#4ade80"></s>dedektör buldu</span>
        <span><s style="background:#fb923c"></s>takip öngörüsü (dedektör bulamadı)</span>
        <span><s style="background:#25303f"></s>iz yok</span>
      </div>
      <div class=büyük><span id=or1 style="color:#4ade80">—</span>
        <span style="font-size:13px;color:#8b98a8"> ham tespit</span>
        &nbsp; <span id=or2 style="color:#fb923c">—</span>
        <span style="font-size:13px;color:#8b98a8"> takiple birlikte</span></div>
    </div>
  </div>
  <div>
    <div class=kart><h2>Hedef — 4× yakın</h2><img id=z src="/zoom"></div>
    <div class=kart style="margin-top:14px"><h2>Durum</h2><div id=t></div></div>
  </div>
</div>
<script>
const AL=[["durum","faz"],["iz_id","iz #"],["iz_coast","öngörü kare"],
  ["vis_conf","güven"],["vis_kutu_px","kutu px"],["vis_menzil","menzil (kutu)"],
  ["imgsz","çıkarım boyu"],["gercek_menzil","GERÇEK menzil"],
  ["ist_hata_m","istasyon hata"],["drone_hiz","hız m/s"],["bekci","bekçi"]];
let son=0;
async function tik(){
 try{
  const d=await (await fetch('/telem')).json();
  document.getElementById('f1').textContent=(d._fps_yakala||0).toFixed(1);
  document.getElementById('f2').textContent=(d._fps_dedektor||0).toFixed(1);
  document.getElementById('f3').textContent=(d._fps_ekran||0).toFixed(1);
  let h='';
  for(const [k,ad] of AL){ if(d[k]===undefined)continue;
    let v=d[k]; if(typeof v==='number')v=Math.abs(v)<1000?v.toFixed(2):v.toFixed(0);
    h+=`<div class=satır><i>${ad}</i><b>${v}</b></div>`;}
  document.getElementById('t').innerHTML=h;
  const s=d._serit||[];
  document.getElementById('şerit').innerHTML=
    s.map(x=>`<i class="${x===1?'d':(x===2?'t':'')}"></i>`).join('');
  document.getElementById('or1').textContent='%'+(d._oran_tespit||0).toFixed(0);
  document.getElementById('or2').textContent='%'+(d._oran_iz||0).toFixed(0);
 }catch(e){}
}
setInterval(tik,220);
setInterval(()=>{document.getElementById('z').src='/zoom?'+(son++)},120);
</script>"""


class _H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _gonder(self, gövde, tip, kod=200):
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(gövde)))
        self.end_headers()
        self.wfile.write(gövde)

    def do_GET(self):
        yol = self.path.split("?")[0]
        if yol == "/":
            return self._gonder(_HTML.encode(), "text/html; charset=utf-8")
        if yol == "/telem":
            serit, o1, o2 = _serit_ozet()
            with _kilit:
                t = dict(_K["telem"])
            t.update({"_serit": serit, "_oran_tespit": o1, "_oran_iz": o2,
                      "_fps_yakala": _hz(_fps["yakala"]),
                      "_fps_dedektor": _hz(_fps["dedektor"]),
                      "_fps_ekran": _hz(_fps["ekran"])})
            return self._gonder(json.dumps(t).encode(), "application/json")
        if yol == "/zoom":
            with _kilit:
                z = _K["zoom"]
            if not z:
                self.send_response(404); self.send_header("Content-Length","0")
                self.end_headers(); return
            return self._gonder(z, "image/jpeg")
        if yol == "/video":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=k")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            son = -1
            try:
                while True:
                    with _kilit:
                        jpg, c = _K["jpg"], _K["sayac"]
                    if jpg is not None and c != son:
                        son = c
                        fps_isaretle("ekran")
                        self.wfile.write(b"--k\r\nContent-Type: image/jpeg\r\n"
                                         b"Content-Length: " + str(len(jpg)).encode() +
                                         b"\r\n\r\n" + jpg + b"\r\n")
                    else:
                        time.sleep(0.004)      # yeni kareyi HIZLI yakala
            except Exception:
                return
        self.send_response(404); self.send_header("Content-Length","0"); self.end_headers()

    def do_POST(self):
        if self.path != "/telem":
            self.send_response(404); self.send_header("Content-Length","0")
            self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0))
        try:
            d = json.loads(self.rfile.read(n) or b"{}")
            with _kilit:
                t = dict(_K["telem"]); t.update(d); _K["telem"] = t
            self._gonder(b'{"ok":true}', "application/json")
        except Exception as e:
            self._gonder(json.dumps({"ok": False, "hata": str(e)}).encode(),
                         "application/json", 400)


def baslat(port=8801):
    s = ThreadingHTTPServer(("127.0.0.1", port), _H)
    s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    print(f"[panel] http://127.0.0.1:{port}", flush=True)
    return s
