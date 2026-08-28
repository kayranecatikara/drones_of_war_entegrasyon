# GECİKME ÖLÇÜMÜ — yönerge

**Süre:** ~10 dakika (kurulum dahil). Ölçümün kendisi **1 dakika**.
**Gereken:** drone (pervaneler **SÖKÜLÜ**), batarya, VTX açık, yakalama
kartı, bir bilgisayar, bir monitör. Ekstra donanım yok.

⭐ **Elle sayı okuma YOK, iki terminal YOK, tek komut.**

---

## 0 · NEYİ, NEDEN ÖLÇÜYORUZ

Elle ölçüldü: **kamera görüntüsü ekrana ~200 ms'de düşüyor.**

Drone hedefe 25 m/s ile yaklaşırken:

```
25 m/s × 0.20 s = 5 metre
```

Nişan aldığımız görüntü **5 metre eski**. Vuruş menzilimiz ~10 m olduğu
için bu, menzilin yarısı kadar hata demek.

**Cevaplanacak tek soru:**

> 200 ms'nin ne kadarı **yazılım tamponundan** (bedava düzelir),
> ne kadarı **kartın kendi donanımından** (kart değişmeli)?

### Tamponlama nedir

Yakalama kartı ve sürücü kareleri tek tek vermez, bir **kuyrukta**
biriktirir. Uygulama kare istediğinde kuyruktaki **EN ESKİ** kare gelir,
en yenisi değil. Kuyrukta 4 kare varsa, saniyede 30 kare geliyorsa:

```
4 × 33 ms = 133 ms — hiçbir işe yaramayan gecikme
```

---

## 1 · ⭐ TEK KOMUT

```bash
.venv/bin/python araclar/olcum/07_otomatik.py /dev/video2 HDMI-0
```

- 1. argüman: **cihaz** (Windows'ta indeks, ör. `1`)
- 2. argüman: **hangi monitörde** desen gösterilecek (ör. `HDMI-0`)

Monitör argümanını yazmazsan bağlı ekranları listeler ve sorar:

```
BAGLI MONITORLER
  [0] DP-2       1920x1080  konum +0+0      ~15 inc
  [1] HDMI-0     1920x1080  konum +1920+0   ~22 inc
Hangi monitorde gosterelim? (numara) >
```

⚠ **Çok ekranlı kurulumda bu şart.** Betik tam ekran kullanmıyor; pencereyi
seçtiğin monitöre elle konumlandırıyor. Sebep: tam ekran modunda hangi
ekrana açılacağına pencere yöneticisi karar veriyor ve genellikle
**birincil** ekranı seçiyor — yani kameranın baktığı ekran olmayabilir.

### Nasıl çalışıyor

Ekranda insan için sayı değil, **makine için bir işaret** gösteriyoruz:
**ArUco işareti** (siyah-beyaz kare desen). Deseni her **25 ms**'de bir
değiştiriyoruz ve hangi deseni saat kaçta gösterdiğimizi not alıyoruz.

Kamera ekrana bakıyor. Yakalanan her karede OpenCV deseni **tanıyor** ve
numarasını söylüyor. O numaranın ne zaman gösterildiğini bildiğimiz için:

```
gecikme = (karenin bize ulaştığı an) − (o desenin gösterildiği an)
```

**İnsan hiçbir şey okumuyor, hiçbir şey yazmıyor.**

### Ne yapar, sırayla

1. Kurulum kontrol listesini gösterir, **ENTER'a basmanı bekler**
2. 10 saniye deneme yapar — deseni görebiliyor mu diye **kendisi kontrol
   eder**. Göremezse durur ve ne düzelteceğini söyler.
3. Görüyorsa altı koşuyu **dönüşümlü** yapar: `A B C A B C` (~45 sn)
4. Pencere **kendiliğinden kapanır**, sonuç ekrana yazılır
5. `logs/gecikme/SONUC.txt` ve `ham_olcumler.csv` kaydedilir

### Üç kol ne demek

| kol | ne yapıyor | not |
|---|---|---|
| **A** | **TABAN** — düz `read()` | kıyas çizgisi |
| **B** | `BUFFERSIZE=1` — sürücüye "tek tampon" der | ⚠ yalnız Linux/V4L2; Windows'ta yok sayılır, betik söyler |
| **C** | **BOŞALTMA** — kuyruktaki bayat kareleri atar | her platformda çalışır; kalıcı çözüm muhtemelen bu |

⛔ Sıra **dönüşümlüdür** (A,A,B,B,C,C değil). Sebep: sinyal kalitesi veya
bilgisayar yükü zamanla değişirse üç kolu da eşit etkilesin.

---

## 2 · KURULUM — tek gerçek zahmet

- ⚠ **PERVANELERİ SÖK.**
- ⭐ **DRONE'U ELİNDE TUTMA.** Kitap yığınına, sehpaya, kutuya koy;
  gerekirse banta al. Kamerası monitöre baksın.
  *Ölçüm 1 dakika sürüyor ama elde tutmak gereksiz — sabitlemek hem
  kolun ağrımaz hem ölçüm daha temiz olur.*
- Monitör ile kamera arası **40-60 cm**.
- Ekrandaki kare desen, kamera görüntüsünde **kadrajın en az üçte birini**
  doldursun.
- Oda ışığını kıs; ekran parlamasın.
- **Başladıktan sonra drone'a ve monitöre dokunma.**

📝 Cihaz adresini bilmiyorsan önce:
```bash
.venv/bin/python araclar/olcum/00_cihaz_bul.py
```
`logs/gecikme/` içine düşen PNG'lerden hangisinde FPV görüntüsü varsa o.
⚠ `/dev/video0` genelde dizüstünün **kendi kamerasıdır**.

---

## 3 · SONUÇ NASIL OKUNUR

```
KOL KOL (kosular birlestirilmis)
kol       n     medyan     en iyi
A       300        198        189
B       300        195        184
C       300        142        131

KARAR
Taban (A, duz read)        :    198 ms
BUFFERSIZE=1               :    195 ms   (kazanc +3 ms)
BOSALTMA (drain)           :    142 ms   (kazanc +56 ms)
>>> KOL C KAZANDI: 56 ms bedava kazanc.
```
*(örnek — gerçek sayılar ölçümden gelecek)*

| sonuç | anlamı | sıradaki iş |
|---|---|---|
| B veya C, A'dan **belirgin düşük** | yazılım tamponu suçluydu | o yöntem sisteme kalıcı konur — **bedava kazanç** |
| üçü de birbirine yakın | kartın kendi donanımı | GStreamer denenir, olmazsa başka kart |

---

## 4 · ÖLÇÜMÜN DOĞRULUĞU (doğrulandı)

Betik, donanımsız bir **öz-testten** geçirildi: sahte bir kameraya bilinen
bir gecikme enjekte edildi, ölçüm onu bulabildi mi diye bakıldı.

| enjekte edilen | ölçülen | hata |
|---|---|---|
| 80 ms | 81 ms | +1.3 ms |
| 180 ms | 180 ms | +0.2 ms |
| 300 ms | 301 ms | +1.3 ms |

Desen tanıma da bozulmaya karşı sınandı: ±6° eğim, bulanıklık, gürültü
(σ=15) ve 150 piksele kadar küçülme altında **34/34 ve 20/20 doğru**.

⚠ **Yarım tik düzeltmesi:** ham eşleşme, desen 25 ms'de bir değiştiği için
sistematik olarak ~12.5 ms fazla ölçüyordu (180 → 194 ms). Bu sapma
koddan çıkarıldı; öz-test yukarıdaki hâliyle geçiyor.

---

## 5 · ÖLÇÜMÜN SINIRI (dürüst not)

Yöntem kameranın **ekrana bakması** üzerine kurulu. Ölçülen sayı
monitörün kendi gecikmesini de içerir (~16-40 ms).

**Karar buna bağlı değil:** monitör payı A, B ve C kollarında **aynıdır**,
dolayısıyla **kollar arası farkta tamamen sadeleşir.** Mutlak sayı kirli,
fark temiz — ve biz farka bakıyoruz.

Gerçek güdüm döngüsü monitör kullanmaz; oradaki gecikme bu sayılardan
~20-25 ms daha azdır.

---

## 6 · TESLİM EDİLECEKLER

- [ ] `logs/gecikme/SONUC.txt`
- [ ] `logs/gecikme/ham_olcumler.csv`
- [ ] `logs/gecikme/01_varis.txt` (varsa — kare varış düzeni ön teşhisi)
- [ ] Not: `BUFFERSIZE=1 kabul: False` yazdı mı?

---

## 7 · SIK ÇIKAN SORUNLAR

| sorun | çözüm |
|---|---|
| `DESEN TANINAMIYOR` | Kamerayı monitöre daha iyi doğrult, desen kadrajı doldursun. Mesafeyi 40-60 cm yap. Oda ışığını kıs. Kamera çok yakınsa netleyemez — biraz uzaklaştır. |
| `cihaz acilamadi` | `00_cihaz_bul.py` ile doğru adresi bul. Başka program (OBS, gözlük yazılımı) kartı tutuyorsa kapat. |
| Kare siyah / gürültü | VTX açık mı, kanal doğru mu (`C8 / 5945`), anten takılı mı? |
| `BUFFERSIZE=1 kabul: False` | Normal, Windows'ta beklenen. **Kol C** zaten her yerde çalışır. Raporla yeter. |
| Fullscreen pencere kapanmıyor | Ölçüm bitince kendiliğinden kapanır. Acil durumda `Ctrl+C`. |

---

## 8 · ELLE YÖNTEM (yedek)

Otomatik betik çalışmazsa (ör. `cv2.aruco` yoksa) eski elle yol duruyor:

```
02_saat.py        ekrana ms'li saat basar (AYRI terminalde)
06_hepsini_kos.py altı koşuyu yapar, PNG kaydeder
05_kare_oku.py    kareleri gösterir, sayıyı sen girersin
04_gecikme_oku.py sonucu hesaplar
```

Bu yol ~45 dakika ve elle 48 sayı girmeyi gerektirir. **Otomatik betik
çalışıyorsa buna gerek yok.**

---

## 9 · İLGİLİ BELGELER

- `docs/GERCEK_SISTEM.md` — donanım zinciri, ölçülen sayılar, §5 gecikme
- `logs/olcum_kamera/` — kamera/FOV ölçümü
