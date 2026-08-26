# -*- coding: utf-8 -*-
"""
================================================================================
MODEL KİMLİK KONTROLÜ — canlıya çıkmadan önce "bu model ne?" sorusu
================================================================================
    .venv/bin/python araclar/model_kimlik_bak.py modeller/yeni.pt
    .venv/bin/python araclar/model_kimlik_bak.py modeller/yolo26s.pt

NEDEN VAR: yeni eğitilmiş bir modeli doğrudan drona doğrultup "algılamıyor"
demek en pahalı hata. Algılamamasının sebebi çoğu zaman modelin kendisi
değil, kimliğidir:
  * sınıf listesi beklediğinden başka (ör. {0:'drone'} yerine COCO'nun 80
    sınıfı gelmiş — o zaman `tayarti` diye bir şey ARAMIYOR demektir)
  * görev 'detect' değil ('classify'/'segment' ise kutu üretmez)
  * eğitim imgsz'si çok küçük/büyük — canlıda hangi imgsz'yi vereceğini
    bu belirler
Bu araç dosyayı AÇMADAN önce hiçbir şey varsaymaz; hepsini checkpoint'in
kendi içinden okur.

⚠ `.pt` DOSYASI ZATEN BİR ZIP'TİR (içinde data.pkl + data/N ham tensörler).
  Bu yüzden `.zip` uzantısıyla gelen bir ağırlık dosyası UNZIP EDİLMEZ —
  sadece adı değiştirilir. Bu araç ikisini de doğrudan kabul eder.

İsteğe bağlı ikinci argüman: üzerinde deneme çıkarımı yapılacak kare dizini
(ör. logs/dogrulama_y26). Hız ve kaç karede kutu çıktığı ölçülür.
================================================================================
"""
import os, sys, glob, time


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[3])
    yol = os.path.expanduser(sys.argv[1])
    if not os.path.exists(yol):
        sys.exit("HATA: %s yok." % yol)

    import torch
    from ultralytics import YOLO

    print("DOSYA : %s" % yol)
    print("BOYUT : %.1f MB" % (os.path.getsize(yol) / 1e6))

    ck = torch.load(yol, map_location="cpu", weights_only=False)
    ta = ck.get("train_args", {}) or {}
    print("TARİH : %s" % ck.get("date", "-"))
    print("EĞİTİM: mimari=%s  imgsz=%s  epochs=%s  veri=%s"
          % (ta.get("model", "-"), ta.get("imgsz", "-"),
             ta.get("epochs", "-"), ta.get("data", "-")))
    print("EPOCH : %s (best_fitness=%s)" % (ck.get("epoch", "-"),
                                            ck.get("best_fitness", "-")))

    m = YOLO(yol)
    par = sum(p.numel() for p in m.model.parameters())
    print("GÖREV : %s" % m.task)
    print("SINIF : %s" % m.names)
    print("PARAM : %.2f M" % (par / 1e6))
    if m.task != "detect":
        print("⛔ UYARI: görev 'detect' DEĞİL — bu model kutu üretmez, "
              "model_test_etme_kodlari.py ile kullanılamaz.")

    mt = ck.get("train_metrics", {}) or {}
    if mt:
        print("EĞİTİM ÖLÇÜTLERİ (kendi doğrulama kümesinde, SAHA DEĞİL):")
        for k in ("metrics/precision(B)", "metrics/recall(B)",
                  "metrics/mAP50(B)", "metrics/mAP50-95(B)"):
            if k in mt:
                print("   %-22s %.3f" % (k.split("/")[-1], mt[k]))
        print("   ⚠ Bu sayılar modelin KENDİ veri kümesinden; senin dron")
        print("     kameranın görüntüsünde ne yapacağını SÖYLEMEZ.")

    if len(sys.argv) > 2:
        dz = sys.argv[2]
        fs = sorted(glob.glob(os.path.join(dz, "*.jpg")))[:80]
        if not fs:
            print("\n(%s içinde .jpg yok, deneme çıkarımı atlandı)" % dz)
            return
        import cv2
        ims = [cv2.imread(f) for f in fs]
        print("\nDENEME ÇIKARIMI — %d kare, %s" % (len(ims), dz))
        for imgsz in (640, 960, 1280):
            for _ in range(4):
                m.predict(ims[0], imgsz=imgsz, conf=0.4, verbose=False)
            t = time.perf_counter(); kutulu = 0; nkutu = 0
            for im in ims:
                r = m.predict(im, imgsz=imgsz, conf=0.4, verbose=False)[0]
                k = 0 if r.boxes is None else len(r.boxes)
                nkutu += k; kutulu += (k > 0)
            dt = (time.perf_counter() - t) / len(ims) * 1000
            print("   imgsz=%-5d %5.1f ms/kare (~%3.0f FPS)  kutulu kare %2d/%d  "
                  "toplam kutu %d" % (imgsz, dt, 1000 / dt, kutulu, len(ims), nkutu))


if __name__ == "__main__":
    main()
