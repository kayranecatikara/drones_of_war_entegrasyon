# GÖRSEL GÜDÜM SİCİLİ — DoW

Her kampanyanın ölçülmüş sonucu. Kararlar buradan izlenir.
Ölçütler: **tespit%** = görsel fazdaki karelerin kaçında geçerli kutu var ·
**en yakın** = truth'tan ölçülen en küçük menzil (ÖLÇÜM-ONLY) ·
**isabet** = en yakın < 4 m.

---

## ⭐ TABAN — GV09 (n=6): İSABET 3/6, en yakın medyan 5.10 m

Yapılandırma: **yalnız dikey kadraj regülasyonu**. Lead, merkez freni ve
sakin kamera KAPALI.

| koşu | tespit% | en yakın | isabet |
|---|---|---|---|
| 1 | 21.3 | 15.77 | — |
| 2 | 37.8 | 2.95 | ✅ |
| 3 | 33.3 | 6.73 | — |
| 4 | 22.9 | 12.31 | — |
| 5 | 34.7 | 3.46 | ✅ |
| 6 | 37.2 | 2.65 | ✅ |

6/6 geçerli · görsel faza giren 6/6 · devir ~22.6 m (10 kare şartı)

### 🔑 EN GÜÇLÜ BULGU: korelasyon(tespit%, en_yakın) = **−0.982**

| | tespit aralığı |
|---|---|
| **isabet** olanlar | %34.7 – %37.8 |
| **ıska** olanlar | %21.3 – %33.3 |

**Eşik net: tespit %34'ün üstünde isabet, altında ıska.**

→ İsabet oranını yükseltmenin yolu **güdüm yasasından değil, GÖRME'den**
geçiyor. Görsel fazda tespit oranı yükselmeden isabet yükselmez.

---

## Denenen ve GERİ ALINAN eklemeler

Hedefi vuramayınca güdüm yasasına üst üste ekleme yaptım; **her biri işi
kötüleştirdi**. Hepsinin kararı n=3 ile verilmişti — CLAUDE.md §5.4 ihlali.

| kampanya | eklenen | en yakın medyan | isabet |
|---|---|---|---|
| GV02 | dikey kadraj reg. (taban) | 12.05 | 1/4 |
| GV03 | + lead | 13.75 | 0/3 |
| GV04 | + merkez freni | 13.00 | 0/3 |
| GV06 | + sakin kamera | 16.08 | 0/3 |
| GV07 | + tam yaw bandı | 18.12 | 0/4 |

**Sakin kamera** tespiti +5.7 puan artırdı (%26.6 → %32.3, A/B n=3/kol) ama
**%34 eşiğinin altında kaldığı için** isabete dönüşmedi. Bu, yukarıdaki
korelasyonla tutarlı. Kod duruyor, anahtar kapalı; eşiği aşabilirse
yeniden değerlendirilecek.

---

## Kök neden bulguları (ölçülmüş)

**1. Saf takip hedefin irtifasına tırmandırıyor (GV01).** Hız vektörünü
doğrudan hedefe nişanlamak, 24° yükselişte 11.4 m/s tırmanma demek; araç
hedefin hizasına çıkıyor ve kamera 26.5° YUKARI baktığı için hedefi
göremiyor. **Çare:** dikey kanal artık hız nişanlamıyor, hedefi kadrajda
sabit yükseklikte tutuyor (cy → cy_ref).

**2. Tespiti öldüren şey hız değil KONTROL EFORU** (n=416 görsel kare):

| büyüklük | tespit VAR | tespit YOK |
|---|---|---|
| \|roll\| | 0.095 | 0.200 (2.1×) |
| \|throttle\| | 0.300 | 0.669 (2.2×) |
| \|yaw\| | 0.103 | 0.194 (1.9×) |
| \|pitch\| | 0.249 | 0.258 (fark yok) |
| hız | 21.1 | 19.9 (fark yok) |

**3. Çürütülen iki hipotezim.** (a) "Hedef ufka düşüyor, arka plan arazi" —
gerçek geometri kaydedilince çürüdü: hedef üstümüzde, elev +14…+17°.
(b) "İleri uçuş alçalmayı zorlaştırıyor" — tersi çıktı, kolaylaştırıyor.

---

## SIRADAKİ: tespit oranını %34 eşiğinin üstüne çıkarmak

Adaylar — **ayrı ve dönüşümlü A/B, n≥4/kol**:

1. **bbox köprüsü (ölü-hesap):** kayıp karelerde bbox'ı görüntü hızıyla
   ileri taşı. Gazebo'da `VIS_KOPRU_S` ile vardı, DoW'a taşınmadı.
2. **Görsel fazda daima imgsz=1920.** Uyarlanabilir eşik (55 px) yakında
   960'a düşüyor; o ölçüm SABİT istasyonda yapılmıştı, hızlı hareketle
   960 kötü olabilir.
3. **conf eşiği 0.40 → daha düşük.** Yanlış-pozitif riski artar; geçerlilik
   kapısı (menzil 3-50 m) onu bir ölçüde emer.


---

# 2026-08-22 · ARAYÜZ UÇUŞU BOZUYORDU — ölçüldü ve düzeltildi

Kullanıcı: *"bu arayüzü bir web arayüzünde görmek istiyorum, burda çok
kasıyor gibime geliyor, gerçi oyunda biraz etkiliyor yavaşlatıyor da."*

Sezgi doğruydu ama etkisi tahmin edilenden çok daha büyüktü: arayüz uçuşu
yalnız yavaşlatmıyordu, **ölçümü geçersiz kılıyordu.**

## Kök neden
`araclar/izleyici.py` ekranı **saniyede 180-330 kez** kopyalıyor ve aynı
GPU'da YOLO'yu imgsz 1920'de tam hızda koşuyordu. Kampanya süreci de
AYRICA her kontrol tikinde tam kare kopyalıyor ve kendi YOLO'sunu
koşturuyordu — yani iki kopyalayıcı + iki çıkarım.

Ölçüldü (oyun koşarken): tam kare X11 aktarımı **13.3 ms**, BGRA→RGB
1.25 ms. Asıl bedel CPU değil — her `XGetImage` oyunun çizim boru hattını
**senkrona zorluyor.**

## Etkisi (aynı kod, aynı geometri, yalnız arayüz farkı)

| | GA04 izleyici KAPALI | GV11 izleyici AÇIK | düzeltmeden SONRA |
|---|---|---|---|
| kontrol döngüsü | 6.8 Hz | 8.8 Hz | **48.2 Hz** |
| istasyon hatası medyanı | 5.3 m | 25.3 m | **5.2 m** |
| ≤15 m'de geçen oran | %88 | %2 | %90+ |
| `v_istek` | 24.0 m/s | **33.0 = doyumda** | 21.8 m/s |
| hedefin ufuk üstünde oranı | %100 | %65 | %100 |
| GERÇEK tespit | %52 | **%7** | **%62** |

Kullanıcının "detection modeli çok kötü" izlenimi **%7'lik uçuşlardan**
geliyordu; aynı model, istasyon düzgün tutulduğunda %62 yapıyor.

## Düzeltme
* Yakalama ve çıkarım TAVANLI: `PANEL_YAKALA_HZ=15`, `PANEL_DET_HZ=5`.
* TEK süreç, TEK kopyalayıcı, TEK YOLO (`kosu.py` içindeki görüş iş
  parçacığı). `izleyici.py` yalnız kampanya koşmuyorken kullanılır.
* Kontrol döngüsü artık hiç ekran kopyalamıyor; görüş parçacığının son
  karesini kullanıyor. Uçuş kapısı için 41 kat küçük HUD şeridi yeter.
* `np.array(grab)[:,:,:3][:,:,::-1]` yerine `cv2.cvtColor(BGRA→RGB)`:
  sürekli dizi, ardıl kopyalar kayboldu (12.37 ms → 1.25 ms).
* Bekçiler: **B24** (tavanlar + kontrol döngüsü kopyalamaz).

## Ölçüm dersi (CLAUDE.md §5'e aday)
**Ölçüm aracının kendisi ölçtüğü şeyi bozabilir.** GV11'in 20 uçuşluk
sonucu güdüm yasası hakkında hiçbir şey söylemiyordu; ölçüm düzeneğinin
yükünü ölçüyordu. Bir kampanya öncesi "bu koşuda makinede başka ne
koşuyor?" sorusu artık kontrol listesinde.

---

# 2026-08-22 · HybridSORT ÇIKARILDI

Kullanıcı: *"şu an hybridsort tracking algoritmasını komple denklemden
çıkart; detection kötü olduğu için tracking bir işe yaramıyor ve rastgele
yerlere track atabiliyor. Düzgün detection modeli gelince tekrar entegre
ederiz."*

Gerekçe teknik olarak da doğru: takipçi, dedektörün **yanlış-pozitifini**
de bir iz olarak benimseyip Kalman ile 20 kare boyunca ileri taşıyordu —
hatayı silmiyor, **uzatıyordu.**

§5.12 silme listesi tamamlandı: `Ayar.TAKIP_AKTIF` + `DOW_TAKIP`,
`TakipliDedektor`, `dow/gorus/tracker.py`, izleyici/kosu/panel kullanımları,
`iz_id`/`iz_coast`/`_oran_iz`. `grep` sıfır sonuç (yalnız tarihsel yorum).
**Bit bit denklik:** 1665 satırlık güdüm çıktı imzası silme öncesi ve
sonrası aynı (`d9f7daaf…`). Bekçi **B23** nüksü engelliyor.
Kod `b435f08` commit'inde duruyor; gerektiğinde oradan alınır.


---

# 2026-08-22 · İSTASYON GEOMETRİSİ: 15 m/0.45 → **8 m/0.75** (24 uçuş)

Kullanıcı: *"gps güdümün o istasyon konumunu hedef araca daha da
yaklaştıralım, daha yakınken detection modeli daha iyi algılayabilir. Bir de
istasyonu hedef aracın biraz gerisine ve ALTINA alalım ki hedef araç droneun
kadrajına girdiğinde arka planı gökyüzü olsun."*

## İki düğme BAĞIMSIZ
`MENZİL` yalnız kutu boyutunu, `ORAN` yalnız gök payını değiştirir — çünkü
yükseliş açısı `atan(oran)`, menzilden bağımsız. Bu yüzden ikisi tek deneyde
ayrı ayrı okunabildi.

## BİRİNCİL ÖLÇÜT: "gerçek tespit oranı"
Ham "kutu var mı" oranı KULLANILMADI — kullanıcının şikâyeti tam olarak
yanlış-pozitifti (*"OSD'yi falan tespit edip 0.50 conf atıyor"*). Bir kare
gerçek tespit sayılır ancak: kutu merkezi, kalibre kamera modelinin truth
geometriden öngördüğü yere `max(60 px, 1.5·kutu)` içinde düşerse VE kutu
genişliği öngörülenin 0.5-2.0 katıysa.

### ⚠ Ölçütte yakalanan yanlılık (ve düzeltmesi)
Kutu kontrol döngüsüne **0.075-0.28 s gecikmeyle** ulaşıyor (ekran kopyalama
15 ms + YOLO 60 ms; dedektör 5 Hz). Karşılaştırmayı KAYIT anının duruşuyla
kurmak, kutuyu hedefin gerisinde gösterip yanlış-pozitif saydırıyordu — ve
bedeli kollara EŞİT DEĞİLDİ: dik bakan (0.75) kollarda sapma medyanı 93 px,
0.45'te 51 px. Yani ölçüt kolları tespit kalitesinden BAĞIMSIZ bir sebeple
ayırıyordu.
İlk deneme ("kaydı taze kutuya hizala") BAŞARISIZ oldu: kutu boru hattı
gecikmesinden daha taze OLAMAZ. Çözüm: kontrol döngüsü 48 Hz'de son 2 s'nin
duruşunu bir halkada tutuyor; kayıt, kutunun ÜRETİLDİĞİ anın duruşundan
`bek_cx/bek_cy/bek_w/bek_ufuk_cy` hesaplayıp yazıyor.
Sonuç: sapma medyanı kollar arası **51-93 px → 12-19 px**; kutu-boyut oranı
0.92-0.99 (kamera modeli doğrulandı).
⛔ `bek_*` sütunu OLMAYAN eski koşular bu yanlılığı taşır; yeni ve eski
kampanyalar birbiriyle KIYASLANMAZ.

## SONUÇ — GK2, 3 kol × 4 koşu × 90 s, dönüşümlü

| kol | ist_hata | ih/R | kutu px | kadraj% | gök% | HAM% | **GERÇEK%** | yanlış% |
|---|---|---|---|---|---|---|---|---|
| 15/0.45 taban | 5.16 | 0.34 | 47.7 | 100 | 100 | 78.9 | **66.9** | 11.4 |
| 8/0.45 | 5.06 | 0.63 | 73.5 | 100 | 100 | 79.7 | **76.0** | 4.0 |
| **8/0.75** | 5.04 | 0.63 | 69.3 | 100 | 100 | 92.8 | **88.8** | 3.7 |

Koşu koşu: taban 66.7/66.9/66.9/70.7 · 8/0.45 79.4/75.4/76.0/76.0 ·
8/0.75 90.2/82.9/88.6/89.1. **Kol aralıkları hiç örtüşmüyor.**

Karar kuralı (koşmadan önce ilan edildi: ≥8 puan + iki geçerlilik eşi):
8/0.45 **+9.1**, 8/0.75 **+21.9** puan. İkisi de geçti; 8/0.75 seçildi
(8/0.45'i de +12.8 geçiyor).

Geçerlilik eşleri: hedef kadrajda %100 (eşik %90), `ist_hata/R` = 0.63
(eşik 1.5). Güvenlik: 12 koşuda **0 kaza**, en yakın 12.6 m (isabet
yarıçapı 4 m). Oturma 5.9 s (tabanla aynı), döngü 47.4-48.2 Hz (tekdüze).

## ⚠ NE ÖLÇÜLMEDİ (§5.13)
Bu kampanya **görsel güdüm KAPALIYKEN** yapıldı; ölçülen şey "istasyonda
dururken dedektör hedefi buluyor mu". Yeni geometri 36.9° yukarı bakıyor
(eskisi 24.2°); görsel faz açıldığında terminal yaklaşma bundan etkilenir
ve AYRICA sınanmalıdır. Bu koşudan görsel güdüm hakkında hüküm çıkmaz.

## Sıradaki aday
6 m / 0.75 (eğik menzil 7.5 m, kutu 133 px). ⚠ İstasyon hatası ~5 m
olduğu için GPS fazında kaza riski doğar; yarışma kuralı gereği GPS fazında
temas OLMAMALI. Kullanıcı kararı gerektirir.


---

# 2026-08-22 · KAYIT TAMAMLANDI (hedef rotasyonu) → kazanımın MEKANİZMASI

Kullanıcı denetimi: *"hedef aracın ve droneun konum ve rotasyon bilgilerini
anlık olarak kaydedip ... bu verilerin hepsini analiz ederek uçuşu değerlendir
demiştim, sen bunu yaptın mı?"*

**Eksik vardı:** hedefin ROTASYONU kaydedilmiyordu. SDK'da
`get_target_rotation()` (indeks 14-16) var, hiç okunmamıştı. Kayıttaki
`hedef_yon`, konum farkından türetilmiş EMA'lı ROTA'dır — gerçek yönelim
değil; hedefin YATIŞI ve PITCH'i hiç yoktu. Ayrıca 3846 kare kaydedilmiş
ama videoya çevrilip sıralı incelenmemişti (§2 adım 3-4).
Kapatıldı: `baglanti.hedef_yonelim()`, `hedef_roll/pitch/yaw` sütunları,
`araclar/video.py` (telemetri yakılı koşu videosu).

## Ölçüldü: SDK hedef yaw'ı bozuk DEĞİL
truth konumlarından türetilen rotayla medyan fark **1.46°** (|fark| p90 7.94°).
⚠ Bizim EMA'lı `hedef_yon`'umuz aynı referansa 0.29° medyanla daha yakın —
ama bu KIYAS YANLI: referans da konumlardan türetiliyor, yani EMA'nın lehine.
Bu veriyle "hangisi güdüm için daha iyi" SORUSU CEVAPLANMAZ.

## Yeni bilgi: Talon virajda 45°'ye kadar YATIYOR
`hedef_roll` bandı 3.2-45.0°. Gözle baktığım "ince profil kaçırılıyor"
hipotezimi sınadım ve **ÇÜRÜDÜ**: 0-8° yatışta tespit %77.6, 30-50° yatışta
%87.8; korelasyon(|roll|, tespit) = **+0.13**. Yatış tespiti bozmuyor.

## ⭐ Kazanımın mekanizması (GK2, n=2097 istasyon karesi)
"Bakış açısı" = hedefin burun yönü ile drone→hedef kerterizi arasındaki açı
(0° = tam kuyrukta).

| kol | kuyrukta (<10°) tespit | açılı (≥10°) tespit | **açılı kare oranı** |
|---|---|---|---|
| 15/0.45 | %83.0 | %72.1 | **%36.0** |
| 8/0.45 | %83.6 | %40.7 | **%7.7** |
| 8/0.75 | **%96.6** | %39.0 | %8.4 |

İki düğme **farklı mekanizmalardan** kazandırıyor:
* **YAKLAŞMAK** kuyrukta kalmayı sağlıyor: açılı kare oranı %36 → %8.
  Sebep geometrik — istasyon noktası hedeften R kadar uzaktaysa, hedef ω ile
  dönerken istasyon ω·R hızıyla süpürür. R 15→8 m dönüş süpürmesini yarıya
  indiriyor, araç virajda kuyruktan düşmüyor. (Dönüş ileri beslemesi
  `ISTASYON_DONUS_ILERI` hâlâ KAPALI ve doğrulanmadı — bu kazanç onun
  yaptığı işi geometriyle yapıyor.)
* **ALTINA ALMAK** kuyruktayken tespit kalitesini artırıyor: %83.6 → %96.6.

⚠ ≥20° kovalarındaki düşüş MENZİLLE KARIŞIK (o kareler yaklaşma fazı:
menzil 40-70 m, istasyon hatası 33-65 m). "Açı mı menzil mi" bu veriyle
AYRILAMAZ; yalnız 0-10 vs 10-20 kovası anlamlı ve orada da menzil
14.3 vs 20.2 m ile farklı. Ayrıştırmak için ayrı deney gerekir.

---

# 2026-08-27 · ARKA YARIKÜRE HATASI ve TERMİNAL GECİKME

## ⛔ ÖNCE BİR ÖLÇÜM HATASI: "kadraj içinde" yalanı

`§2` adımı 4 (kareye GÖZLE bak) bir analiz hatası yakaladı.
`KM2/kademeli__t2` kare 21: log "menzil 6.58 m, hedef kadrajda (1338,477)"
diyordu; **kareye bakınca hedef YOKTU** (uçuş süresi 00:10, irtifa 43 m).
Hedef ARKADA kalmıştı — üstünden geçmiştik.

**Kök neden.** Kadraj izdüşümü ışının kamera ekseni bileşenine (`ileri`)
BÖLER. Hedef arkadayken `ileri` negatif olur, bölme işareti çevirir ve
KADRAJIN İÇİNDE bir piksel üretir. `tan()` de aynısını yapar:
`tan(170°) = −0.176` → `cx = 960 − 0.176·F`, yani "kadrajın ortası".

**Ne kadarını kirletmiş** (menzil < 12 m kayıpları):

| kol | "kayıp" | aslında ARKADA |
|---|---|---|
| KM2 `yok` (manevrasız) | 42 | **0 (%0)** |
| KM2 `kademeli` (manevralı) | 139 | **65 (%47)** |
| KI1 `kapali` | 222 | 88 (%40) |

Manevrasız kolda %0 — orada hedefi ıskalayıp geçmiyoruz.

**ÇÜRÜYEN İKİ HÜKMÜM:**
1. *"Araç son 10 metrede 1.7 kat uzun oyalanıyor (136 → 234 kare)"* —
   arka kareler çıkınca **136 vs 134**. ARTEFAKTMIŞ.
2. *"Sert manevra tespiti %85 → %48 bozuyor"* — evrelere ayırıp arka
   kareleri çıkarınca:

| evre | kare* | tespit% | ARKADA |
|---|---|---|---|
| `yok` (taban) | 190 | %77.9 | 0 |
| `kademeli` boş | 79 | %63.3 | 0 |
| `kademeli` HAFİF (= görsel temas YOK, yeniden yaklaşma) | 56 | %46.4 | 64 |
| `kademeli` SERT (görsel güdüm fazı) | 83 | **%73.5** | 7 |

Görsel güdüm fazındaki sert manevrada tespit %73.5, tabanda %77.9 —
**4 puan**, 33 puan değil.

**Düzeltme YALNIZ ölçüm yolunda** (`araclar/arka.py` → `ArkaBekci`;
`kosu.py` ve `kamera.beklenen_kadraj` |açı| ≥ 85° → None; bekçi B62).
⚠ Güdümdeki `seviye_piksel` AYNI kusuru taşıyor (T5 köprüsü onu
kullanır) — DOKUNULMADI, ayrı karar.

## TERMİNAL GECİKME — ıskanın gerçek sebebi

**1. Iskalar 0.9-1.5 m'de**, bazı vuruşlar 1.8 m'de → ölümcül yarıçap
metre altı. (`vurus_indeksi` belgesi de kayıtlıydı: 0.9 m'den geçilen
kareler var ve hedef ölmüyor.)

**2. Bayat kutu DEĞİL:** son 2 s'de kutu yaşı ~0 s, kapanma 4.2 m/s.

**3. Nişan hatası, METRE cinsinden** (`yanal = R·(cx−CX)/F_PX`,
seviye çerçevesinde):

| kol | yanal | dikey | son 1 s tespit |
|---|---|---|---|
| `yok` | **0.26 m** | 0.60 m | %90-100 |
| `kademeli` | **1.37 m** | 1.45 m | %50-70 |

**4. Salınım DEĞİL:** son 1.5 s'de işaret değişimi **SIFIR**; işaret
hedefin yatış yönüyle birebir aynı (+32° → sağda, −27° → solda).

**5. Kendi yatışımızın artefaktı DEĞİL:** seviye çerçevesine döndürünce
`yok` 20 px, `kademeli` 108 px. Kendi yatışımız hatanın ~%25'i
(156 → 114 px).

**6. Yalnız 12 m'nin İÇİNDE kuruluyor:** 12-25 m'de 10 px ve işaret
karışık; 5-12 m'de 80 px; 0-5 m'de 120 px; işaret değişimi 0.10/s.
Sebep fizik: gereken açısal hız 1/R ile büyüyor.

**7. Gecikme NEREDE — ölçüldü:** burun yönü ile gerçek hız vektörü
arasındaki fark yalnız **2.0-3.9°** ve işaret karışık. Yani hız vektörü
burnu takip ediyor; gecikme `cevirici.K_V`'de DEĞİL. Gecikme burnun
LOS'u takibinde: `ana.py` başlık döngüsü `yaw_rate = 3.0·eps` →
kalıcı hata `eps_ss = ω_LOS/3`. Terminal LOS p90 24-31°/s → 8-10°;
ölçülen yanlılık 10-19°.
⚠ Bu, önce "K_V = 1.5, τ = 0.67 s" diye yaptığım atfın DÜZELTMESİDİR.

## ELENEN ADAYLAR (kampanya harcanmadan, ölçümle)

* **Yerellik kapısını gevşetmek** — <10 m'de kapı reddi yalnız 12 kare.
* **Dönüş tavanı (YAW_RATE_MAX 120)** — ölçülen LOS medyan 6-9°/s,
  tavanı aşan %2. Bağlayıcı değil.
* **Piksel hızına dayalı lead** — "hata = τ·kutu hızı" modeli ÇÜRÜDÜ:
  τ koşular arası −2.22 … +5.75 s, bir koşuda hata ile kutu hızı TERS
  işaretli. Ö-F'nin batma sebebi budur.
* **İntegrali hız döngüsüne koymak** — madde 7 çürüttü.

## Ö-I · TERMİNAL GÜVEN İSTİSNASI — **ELENDİ**

Terminal fazda güven eşiğini düşürmek (0.40 → 0.25/0.20).
Gerekçe: manevralı kolda kabul edilen kutuların p10 güveni 0.54,
%13'ü 0.40-0.55 bandında.

| kampanya | n/kol | kaçırma (ort) | <20m tespit | aktiflik |
|---|---|---|---|---|
| Kİ1 (0.25, 12 m) | 4 | — | — | %0.78, 2 koşu SIFIR |
| Kİ2 (0.20, 20 m) | 6 | **1.67 vs 1.67** | %76.4 vs %76.3 | %1.08, 6/6 geçerli |

Fırsat tavanı ölçüldü (kutu var + kapıyı geçti + `gecerli()` eledi):
%7.9-8.0. Kural "kaçırmada eşit/iyi VE tespitte ≥8 puan önde" idi;
tespit farkı SIFIR. **Girmedi, §5.12 ile tamamen silindi**
(grep sıfır + bit bit denklik).

## Ö-J · TERMİNAL KERTERİZ İNTEGRALİ — **ELENDİ**

`R < 12 m` iken `yaw_hedef += yaw_I`, `yaw_I += 0.8·eps·dt` (±20°).
Yalnız taze kutuyla beslenir, köprüde donar, terminal dışında sıfırlanır.

| ölçüt | KJ1 `kademeli` (tasarım zarfı, n=6) | KJ2 `yok` (regresyon, n=4) |
|---|---|---|
| kaçırma kapalı | 0.83 (0,0,0,2,2,1) | 1.00 (1,2,0,1) |
| **kaçırma açık** | **1.33** (4,1,0,1,1,1) | **3.25** (1,**8**,0,4) |
| terminal yanal kapalı | 1.04 m | 0.35 m |
| terminal yanal açık | 0.76 m | 0.24 m |
| ölçülemeyen koşu | 0/6 vs **2/6** | 0/4 vs 0/4 |
| mekanizma | 5/6 geçerli | 4/4 geçerli |

Manevrasız TABANDA kaçırma **1.0 → 3.25**; en kötü koşu (8 kaçırma)
integralin en çok biriktiği koşuydu (9.3°). §5.10 regresyonu yakaladı.

**MEKANİZMA ÇALIŞTI, TASARIM YANLIŞTI.** `yaw_hedef` yalnız burnu değil
HIZ VEKTÖRÜNÜ de çeviriyor (`vx,vy = v·cos/sin(yaw_hedef)`), yani hedefin
ÖNÜNE uçuyoruz. Hedef dönüşünü sürdürmeyince diğer taraftan ıskalıyoruz.

## ⛔ METODOLOJİK DERS: "terminal nişan hatası" GEÇERSİZ ÖLÇÜT

Yanal hata **her iki kampanyada da iyileşti**, sonuç **her ikisinde de
kötüleşti**. Sebep: "en yakın andaki nişan hatası", hedefin önünden daha
yakın geçen ama DEĞMEYEN yörüngeyi ödüllendirir — §5.2'nin tarif ettiği
tuzağın ta kendisi. Kendi kurduğum ikincil ölçüt bu tuzağa düştü ve
önceden ilan edilmiş birincil ölçüt (kaçırma) yakaladı.
Uyarı `araclar/terminal_nisan.py` başlığına ve çıktısına gömüldü.

## ⛔ İKİNCİ METODOLOJİK DERS: SESSİZ DÜŞÜRME

`terminal_nisan` ilk hâlinde, son saniyede 3'ten az kutu olan koşuyu
`None` döndürüp medyandan SESSİZCE düşürüyordu. KJ1'de deney kolunun
6 koşusundan 2'si böyle düştü, kontrol kolunun 0'ı — ölçüt "terminalde
kör kalmayı" ödüllendiriyordu. Artık "ÖLÇÜLEMEDİ" diye raporlanıyor.

## Ö-K · HÜCUM HIZI TAVANI — **ELENDİ** (kampanya erken kesildi)

Kırpma tavanı 28 → 40 m/s. **Mekanizma mükemmel çalıştı:**

| kol | KOMUT | GERÇEKLEŞEN | açık |
|---|---|---|---|
| kapali | 28.0 | **22.0** | 5.9 |
| acik | 40.0 | **30.6** | 9.4 |

⭐ **Yeni bilgi:** aracın 22 m/s'de oturması SÜRÜKLEME SINIRI DEĞİLMİŞ —
tamamen hız döngüsünün oransal kalıcı hatasıymış. Araç 30.6 m/s yapabiliyor.

**Ama sonuç felaket** (n=3/kol, mekanizma 3/3 geçerli):

| kol | kaçırma | ortalama |
|---|---|---|
| kapali | 1, 3, 0 | **1.33** |
| acik | **18**, 2, 6 | **8.67** |

`acik__t1`: 110 s'de **18 kez** üstünden geçti, en yakını 2.8 m. Kapanma
12.6 m/s olunca son metrelerde düzeltmeye vakit kalmıyor, içinden geçiyor.
Kampanya §1.1 uyarınca erken kesildi, KK2 regresyonu hiç koşulmadı.

## ⛔ ÜÇÜNCÜ METODOLOJİK DERS: KORELASYONU KALDIRAÇ SANMAK

40 koşuluk havuzda "kapanma hızı" iyi/kötü koşuyu ayıran en güçlü
değişkendi (2.1 vs 0.5 m/s) ve ben bunu **kaldıraç** sandım. Deney
tersini gösterdi: kapanmayı ZORLA artırmak sonucu 6.5 kat kötüleştirdi.

Doğrusu: kötü koşular yavaş kapanıyor ÇÜNKÜ geometrileri bozuk — yavaş
kapandıkları için kötü değiller. Ok yönünü ters kurmuşum. Bu, gözlemsel
bir ayrımın nedensel sanılmasının bedeli; ancak taze uçuş A/B'si
ayırt edebilirdi (§2: replay/istatistik hipotez üretir, KARAR VERMEZ).

## ⭐ GÖZLE İNCELEME — ıskanın anatomisi (KJ1/kapali__t5, §2 adım 4)

Aynı kol, aynı senaryo, aynı ayar; `kapali__t1` 0 kaçırma, `kapali__t5` 2.
`t5` menzil profili: 1.04 m'ye ve 2.16 m'ye kadar giriyor, ikisinde de
VURAMIYOR ve hedefin arkasına düşüp yeniden yaklaşıyor.

Kareler (f0018 ≈ 4 m, f0019 ≈ 1 m): hedef NET görünüyor, sert yatık,
**kadraj merkezinin belirgin ÜSTÜNDE** (~250 px). 4 m'de bu
`4 × 250/540 ≈ 1.85 m` demek — hedefin altından geçiyoruz.

## ÇÜRÜTÜLEN ÜÇ HİPOTEZ (bu turda, kod yazılmadan)

**1. "Dikey kanal boğaz noktası"** — ÇÜRÜDÜ. 20 Hz'te komut ile
gerçekleşen dikey hız neredeyse birebir:

| menzil | e_cy med | KOMUT vz | GERÇEK vz | doyum% |
|---|---|---|---|---|
| 0-5 m | −174 px | 2.44 m/s | **2.45** | %30 |
| 5-12 m | −156 px | 2.18 m/s | **2.11** | %26 |
| 12-25 m | −114 px | 1.60 m/s | 1.10 | %9 |

Araç dikey komutu uyguluyor. ⚠ Bu, "araç dikey komutu 4 s'de uyguluyor"
notunu bu araç için GEÇERSİZ kılar. Ayrıca e_cy sabit PİKSEL kalıyor,
yani fiziksel yükseklik farkı menzille ORANTILI küçülüyor: 1 m'de
0.32 m'ye iniyor. Dikey ofset temas anında ölümcül yarıçapın içinde.

**2. "Kuyruk konisine girmeliyiz"** — ÇÜRÜDÜ, hem de TERS yönde
(159 geçiş):

| aspekt | geçiş | vuruş | oran |
|---|---|---|---|
| 0-10° (tam kuyruk) | 42 | 6 | **%14** |
| 10-20° | 12 | 6 | %50 |
| 20-35° | 73 | 33 | %45 |
| 35-90° | 22 | 5 | %23 |
| 90-180° | 10 | 0 | %0 |

Tam kuyruktan yaklaşmak EN KÖTÜSÜ. Muhtemel sebep: kuyrukta kapanma
yalnız 4 m/s, araç sürünerek yaklaşıyor ve sapmaya bol vakit oluyor.
⚠ HİPOTEZ, sonuç değil — gözlemsel, karıştırıcılar ayrılmadı.

**3. "Hız döngüsüne integral"** — ÇÜRÜDÜ: burun ile gerçek hız vektörü
arasındaki fark yalnız 2.0-3.9°, gecikme orada değil.

## AÇIK KALAN — bir sonraki oturum için

Iskaların ortak paydası: `Rmin` vuruşlarda 1.30 m, ıskalarda 2.80 m.
Yani ölümcül yarıçap ~1.3-2 m ve soru "neden her seferinde 1.3 m'nin
içine giremiyoruz". Aşağıdakiler ÖLÇÜLDÜ ve SEBEP DEĞİL:
kutu bayatlığı (terminalde ~0 s), dönüş tavanı (%2 aşım), yerellik
kapısı (<10 m'de 12 kare), dikey kanal, hız döngüsü, hedef manevrası
(LOS dönüşü iyi/kötü koşuda AYNI), aracın hızı (artırmak 6.5 kat
kötüleştirdi), nişan yanlılığı (düzeltmek regresyon üretti).

## ⛔ GERİ ÇEKİLDİ — "görsel menzil 2 kat sapıyor" İDDİAM YANLIŞTI

Bu bölümde önce şunu yazmıştım: *"kutu tabanlı menzil 3-6 m bandında
2.04 kat uzak görüyor"*. **BU BİR ANALİZ ARTEFAKTIYDI.**

**HATA:** `cikarim.csv`'de `vis_h` sütunu YOK. Analizde
`boyut = max(w, h or 0)` yazmıştım; `h` None olduğu için bu yalnız
GENİŞLİĞE indi. Güdüm ise `max(w, h)` kullanıyor. Yatık hedefte
yükseklik genişliği aşabildiği için yalnız genişlik kullanmak boyutu
küçük gösterip menzili şişiriyor — ölçtüğüm 2.04, benim ölçütümün
sapmasıydı, sistemin değil.

**DOĞRUSU** (`meta.csv`, `vis_h` var, taze kutu, n=2674):
`C = boyut × gerçek menzil` bantlar arasında ÇOK KARARLI:

| bant | C = max(w,h)·R | C = köşegen·R |
|---|---|---|
| 0-3 m | 848 | 932 |
| 3-6 m | 853 | 937 |
| 6-12 m | 852 | 936 |
| 12-25 m | 880 | 951 |
| 25-40 m | 828 | 888 |

Yani **bant bağımlı çarpıklık YOK** (±%3). Tek gerçek sorun tekdüze:
kodda `MENZIL_C = 997`, ölçülen **866** — menzil her yerde **%15 uzak**
okunuyor.

**YATIŞ BAĞIMLILIĞI VAR AMA KÜÇÜK** (0-10° bandından kalibre, oran):

| ölçüt | 0-10° | 10-25° | 25-40° | 40°+ | yayılım |
|---|---|---|---|---|---|
| `max(w,h)` (mevcut) | 1.00 | 1.08 | 1.19 | 1.13 | **0.19** |
| **köşegen √(w²+h²)** | 1.00 | 1.04 | 1.11 | 1.00 | **0.11** |
| √(w·h) | 1.00 | 0.95 | 0.98 | 0.83 | 0.17 |

Köşegen daha düz çünkü düzlem içi dönmeye karşı (ince cisim için tam)
değişmezdir. Kazanç mütevazı: yayılım 0.19 → 0.11.

**Ö-L freninin ateşlememesi de %15 ile açıklanıyor:** gerçek 5.7 m'de
`R ≈ 6.5 m` okunuyor ve 6 m kapısının HEMEN DIŞINDA kalıyor.

⚠ AÇIK ÖNERİ (kullanıcı onayı bekliyor): `MENZIL_C` 997 → 866 ve
   ölçüt `max(w,h)` → köşegen (C = 944). İkisi de menzile bağlı HER
   kapıyı ve hız PI'sının sıfır noktasını kaydırır — her fazda davranış
   değişir, ayrı regresyon ister (§5.10, §8).

## ⭐⭐⭐ EN BÜYÜK KALDIRAÇ: dedektör YATIK hedefte 25 puan kaybediyor

11.265 kare, sekiz kampanya, arka kareler çıkarılmış, hedef kadraj içinde:

| hedef \|yatış\| | kare | **tespit** | C = max(w,h)·R |
|---|---|---|---|
| 0-10° (düz) | 827 | **%86** | 928 |
| 10-25° | 6539 | **%64** | 862 |
| 25-40° | 3552 | **%63** | 779 |
| 40°+ | 347 | **%57** | 820 |

⚠ Tespit yüzdeleri BAĞIMSIZ kaynakla doğrulandı (`meta.csv`, 1 Hz):
%84 / %67 / %61 / %77 — aynı şekil. Kutu boyutundan bağımsız oldukları
için `vis_h` eksikliği bunları ETKİLEMEDİ.
`C` sütunu ise doğru ölçütle (`max(w,h)`) yeniden hesaplandı: düz uçuşta
928, 25-40° yatışta 779 — yani yatış menzili **%16 şişiriyor**, daha
önce yazdığım gibi iki kat DEĞİL.

**Angajmanın %93'ü yatık bantlarda geçiyor** (10.438 / 11.265 kare).
Yani sistem neredeyse HER ZAMAN bozulmuş rejimde çalışıyor.

**Tek kök neden, iki ayrı hasar:**
1. Tespit %86 → %57-64 (25 puan)
2. Kutu daralıyor → `R = 997/kutu` **%16 şişiyor** (C 928 → 779) →
   menzile bağlı kapılar kayıyor. Buna koddaki `MENZIL_C = 997`'nin
   düz-uçuş değerine kalibre olması eklenince toplam sapma ~%15-30.

**Ve bu, 2 m'nin içinde vuranı ıskalayandan ayıran TEK ölçülebilir
farkla birebir örtüşüyor:** son 0.7 s tespiti vuruşlarda %80,
ıskalarda %67.

⭐ **REÇETE (güdüm tarafında değil, MODEL tarafında):** eğitim setine
YATIK hedef kareleri eklenmeli. Yatık tespiti %63'ten %86'ya çıkarsa
son saniye sürekliliği %67 → ~%90 olur — bu, ölçülen tek ayırıcı
değişkendir.

## Ö-L · TERMİNAL FREN — **ELENDİ** (en sert regresyon)

Son 12 görsel metrede hız tavanı 28 → 24 m/s (gerçekleşen ~19.5).

**Mekanizma tam öngörüldüğü gibi çalıştı:** komut 24 → gerçekleşen
19.5 m/s (doğrusal modelin öngörüsü 19.3). Fren KL1'de 19/22, KL2'de
30/32 geçişte aktifti.

| ölçüt | KL1 `kademeli` (n=6) | KL2 `yok` = TABAN (n=4) |
|---|---|---|
| kaçırma kapalı | 1,4,3,1,0,2 → **1.83** | 0,0,2,3 → **1.25** |
| kaçırma açık | 1,1,4,0,3,7 → **2.67** | 8,7,9,11 → **8.75** |
| geçiş / vuruş (açık) | 22 / 5 | **32 / 0** |
| Rmin p50 kapalı → açık | 1.30 → 1.60 m | 1.10 → 1.95 m |

Manevrasız tabanda fren açıkken **32 geçişte SIFIR vuruş**.

**MEKANİZMA ÇALIŞTI, ÖNGÖRÜ YANLIŞTI.** "Donmuş düzeltme hatası"
modeli doğruydu ama baskın etki değildi: yavaşlayınca terminal bölgede
**3 kat uzun** kalıyoruz (8 m içinde koşu başına 1.5 s → 4.8 s) ve
hedefe sıyrılma vakti veriyoruz.

## ⭐ SONUÇ: TERMİNAL HIZ İKİ YÖNDE DE KALDIRAÇ DEĞİL

| deneme | gerçekleşen hız | kaçırma (tasarım zarfı) |
|---|---|---|
| Ö-K hızlandır | 22.0 → 30.6 m/s | 1.33 → **8.67** |
| **mevcut** | **22.0 m/s** | **~1.2-1.8** |
| Ö-L yavaşlat | 22.0 → 19.5 m/s | 1.25 → **8.75** (tabanda) |

Mevcut hız YEREL OPTİMUM ve iki yanı da diktir. Bu kapı kapandı.

---

## ⭐ Ö-M · GÖRÜŞ İŞ PARÇACIĞI (`GORUS_ISP`) — **İLK POZİTİF SONUÇ**

Kod zaten vardı, `VARSAYILAN KAPALI` ve *"açılması ölçümle kararlaşır"*
diye bırakılmıştı. Hiç ölçülmemişti. **Kod değişikliği yapılmadı**;
yalnız panel düğmesi bağlandı ve A/B koşuldu.

**NEDEN ADAY:** çıkarım kontrol döngüsünün İÇİNDE koşuyor ve döngünün
~%26'sını yiyor (9.1 Hz × 29 ms). Kodun kendi notu, çıkarımı 16 Hz'e
çıkarmanın `tik_hz`'i 40.3 → 22.3'e düşürüp isabeti 1 → 0 yaptığını
kaydediyor — yani `GORSEL_DET_HZ = 10` tavanı bir çözüm değil SEMPTOM.

**HAVUZLANMIŞ (KN1 `kademeli` n=6 + KN2 `yok` n=4, mekanizma 10/10):**

| ölçüt | kapalı | **AÇIK** |
|---|---|---|
| kaçırma ortalama | 1.90 | **0.70** |
| kaçırma dağılımı | 1,0,2,4,1,4,1,3,1,2 | 3,0,0,0,0,1,1,1,1,0 |
| **sıfır kaçırma (ilk denemede vuruş)** | **1/10** | **5/10** |
| isabet | 8/10 | **10/10** |
| `tik_hz` (kontrol döngüsü) | 44.0 | **49.2** |
| `det_hz` (çıkarım) | 9.1 | **11.0** |

**§4 ZORUNLU GEÇERLİLİK ÖLÇÜTLERİ — hepsi aynı yönde:**

| | KN1 manevralı | KN2 taban |
|---|---|---|
| yatış salınımı /s | 0.42 → **0.15** | 0.55 → 0.59 |
| \|yatış\| p90 | 17° → 15° | 21° → **9°** |
| görsel tespit | %60 → **%64** | %75 → **%82** |
| toplam körlük | 5.2 s → **1.2 s** | 3.7 s → **0.6 s** |
| vuruş kalitesi | 3K/1Ş → 3K/3Ş | 4K/0Ş → **4K/0Ş** |

Salınım düşerken tespit ARTMIŞ → §5.2 geçerlilik eşi tuttu.

### Dürüst kalması gereken üç nokta

1. **HİPOTEZİM YANLIŞTI, SONUÇ DOĞRU ÇIKTI.** Kazanımın terminal görsel
   süreklilikten geleceğini öngörmüştüm; terminal tespit neredeyse
   DEĞİŞMEDİ (%65 → %62). Kazanç kontrol döngüsünün hızlanmasından
   (44 → 49 Hz) ve toplam körlüğün 4-6 kat kısalmasından geliyor.
2. **İLAN EDİLEN KURAL TAM SAĞLANMADI.** Kural "kaçırma kötüleşmez VE
   terminal tespit belirgin artarsa girer" idi; ikinci şart oluşmadı.
   Kural sonuca göre YENİDEN YAZILMADI (§5.6) — karar kullanıcıya.
3. **MANEVRALI KOLDA FAZLADAN VURUŞLAR ŞANS SINIFINDA.** Kontrollü
   vuruş sayısı eşit (3-3). ⚠ O iki ŞANS koşusu YALNIZ süreklilik
   ölçütünde takılıyor (%67 vs %70 eşiği); eşik sonucu çevirmek için
   DEĞİŞTİRİLMEDİ. Taban senaryosunda kalite 4/4 kontrollü, bozulma yok.

### ⭐ TEKRARLANDI — havuzlanmış n=20/kol (KN1+KN2+KN3+KN4)

Aynı deney iki senaryoda ikişer kez koşuldu; kollar dönüşümlü.

| ölçüt | kapalı | **AÇIK** |
|---|---|---|
| **kaçırma ortalama** | **1.60** | **0.75** |
| kaçırma medyan | 1.0 | 0.5 |
| **sıfır kaçırma (ilk denemede vuruş)** | **5/20** | **10/20** |
| isabet | 16/20 | **19/20** |
| `tik_hz` | 44.0 | **49.1** |
| `det_hz` | 9.0 | **11.0** |

kapalı: `1,0,2,4,1,4,1,3,1,2,0,0,3,2,2,0,1,0,4,1`
açık:   `3,0,0,0,0,1,1,1,1,0,1,1,0,0,0,0,3,2,1,0`

**PERMÜTASYON TESTİ** (20000 karıştırma, tek yönlü): gözlenen fark
0.85 kaçırma/koşu → **p = 0.021**. Fark, rastgele kol atamasıyla
açıklanamıyor.

**§4 SALINIM (havuzlanmış):**

| ölçüt | kapalı | açık |
|---|---|---|
| cx dönüş/s | 0.35 | 0.41 |
| yatış dönüş/s | 0.43 | **0.30** |
| \|yatış\| p90 | 17° | **14°** |
| görsel tespit | %65 | **%68** |
| **toplam körlük** | **3.3 s** | **1.1 s** |

**VURUŞ KALİTESİ (havuzlanmış):**

| kol | vuruş | KONTROLLÜ | ŞANS |
|---|---|---|---|
| kapalı | 16 | **14** | 2 |
| açık | 19 | **14** | 5 |

⚠ **KONTROLLÜ VURUŞ SAYISI EŞİT (14-14).** Fazladan üç vuruşun hepsi
ŞANS sınıfında. §4 gereği bu, "daha çok vuruyor" iddiasını
DESTEKLEMEZ. Kazanım, ilan edilen birincil ölçütte (kaçırma) ve
körlük/salınımdadır — vuruş kalitesinde DEĞİL.

**DURUM:** anahtar KAPALI bırakıldı; varsayılan yapılması kullanıcı
onayına bağlı (§8). Doğal ikinci adım: iş parçacığı ayrıldığına göre
`GORSEL_DET_HZ` tavanı artık semptom değil — 10 → 25 denenebilir
(donanım 34 Hz'e izin veriyor, çıkarım 29 ms). Ö-M kararı verilmeden
başlanmaz (§0.1).

---

# 2026-08-27 · talon_v5 ELENDİ (TAMAMEN) ve KARMA10 KARAKTERİZASYONU

## A · ÜÇ GÜN BOYUNCA YANLIŞ MODEL KOŞMUŞ — §5.12'nin tam örneği

Gecikme ölçümü yaparken ortaya çıktı: `dedektor.py` model adını **iki ayrı
yerde** tanımlıyordu ve varsayılanları FARKLIYDI.

| yer | varsayılan |
|---|---|
| `MODEL_YOLU` (satır 86) | `talon_v3` |
| `DetCfg.MODEL` (satır 173) | `talon_v5` |

`Dedektor.__init__` v3'ü yüklüyor, sonra `_tara()` içindeki
`_model_uygula()` **ilk çıkarımda** `DetCfg.MODEL` ile karşılaştırıp
sessizce **v5'e geçiyordu.** Canlı üretildi:

```
1) kuruluşta yüklenen : talon_v3 | modeller/talon_v3.pt
   DetCfg.MODEL değeri: talon_v5
2) bir çıkarım SONRASI: talon_v5 | modeller/talon_v5.pt
```

v5 **24 Ağustos'ta ölçümle elenmişti** (v3 4/4 imha / 0.43 m · v5 3/4 /
0.94 m) ama 27 Ağustos'a kadar bütün uçuşlar v5 ile koştu. Kapı MODEL20
kampanyasının dönüşümlü koşu şartı (§4) için yazılmış, kampanya bitince
kaldırılmamıştı.

⚠ **A/B kıyaslarını geçersiz KILMAZ** (iki kolda da aynı model vardı) ama
Ö-I…Ö-M kampanyalarının MUTLAK sayıları elenmiş modelin sayılarıdır.

**SİLME (§5.12 kontrol listesi):** `DetCfg.MODEL` · `_model_uygula()` ·
`self._model_yuklu` + `_tara()` çağrısı · 2 birim test satırı ·
`model_kiyas.py`, `model_kiyas20.py`, `model_cevrimdisi.py`,
`model_ab.sh` · README. Ağırlık dosyası depodan çıkarıldı.
**Doğrulama:** canlı kodda sıfır iz · 60/60 bekçi · **bit bit denklik
400 tikte BİREBİR AYNI.**

## B · KARMA10 — hedef davranışına göre karakterizasyon (10 uçuş)

Kullanıcı: *"hedef araca farklı rotalar çizdir... bazısında kare bazısında
daire. görsel güdüm ile yaklaşırken manevra yaptırıp reaksiyona bakalım."*

Model `talon_v3` (tek model), Ö-M AÇIK, `hibrit`, 150 s/koşu, dönüşümlü sıra.
**İhlal: 0/10.** Mekanizma kapıları (§5.1) üçü de kanıtlandı: kare → dört yön
90° aralıklı (%20 her biri) · daire → 8 yön kovası eşit (%12-13), kutu 35×35 m
· kademeli → SERT, GÖRSEL fazda 14.4-14.7 m'de, tiklerin %17-21'i.

| kol | n | isabet | kaçırma | en yakın | tespit | kutu p90 | kesinti |
|---|---|---|---|---|---|---|---|
| taban | 2 | **2/2** | 2.5 | 0.64 m | %49.2 | 1.78 s | 9.9 s |
| kademeli | 2 | **2/2** | **0.0** | 0.96 m | **%75.2** | **0.25 s** | 0.9 s |
| kare | 3 | 0/3 | 12.0 | 6.69 m | %18.8 | 2.42 s | 34.4 s |
| daire | 3 | 0/3 | 14.0 | 6.01 m | **%7.2** | 2.54 s | 42.1 s |

**VURUŞ KALİTESİ: 4 vuruşun DÖRDÜ DE KONTROLLÜ, sıfır ŞANS.**

**KAÇIRMALARIN SEBEBİ** (geçiş anında görsel temas var mıydı):

| kol | KÖR geçti (görüş hatası) | GÖRDÜ ıskaladı (güdüm hatası) |
|---|---|---|
| taban | 4 (%80) | 1 (%20) |
| kare | 25 (%76) | 8 (%24) |
| daire | 35 (%81) | 8 (%19) |

## C · SONUÇ — ayrım manevranın SERTLİĞİ değil SÜRESİ

Hedef görsel fazda **31.5° yatarak sert kaçarken** drone iki koşuda da
vurdu (0.83 m ve 1.09 m), üstelik kaçamak iki farklı yönde tetiklendi.
O kolda tespit EN YÜKSEK (%75.2) ve kutu yaşı EN DÜŞÜK (0.25 s).

Buna karşılık kare/daire'de **6 koşuda sıfır vuruş**. Fark, hedefin
sürekli yatık kalması: tespit %49 → %19 → %7 çöküyor, kutu yaşı p90
1.8 → 2.5 s'ye çıkıyor (18 m/s'de 45 m hedef hareketi, öldürücü yarıçapın
22 katı). Kaçırmaların **%76-81'i KÖR geçiş** — güdüm hatası değil,
GÖRÜŞ hatası.

⚠ **Salınım sayıları taban/kare/daire kollarında HÜKME GİREMEZ** (§5.2):
görsel temas %60 eşiğinin altında, salınım yalnız kutulu karelerde ölçülüyor.

⚠ **n=2-3/kol — §5.4 gereği hüküm cümlesi değil, GÜÇLÜ ARA VERİ.** Kol içi
tekrarlanabilirlik alışılmadık derecede dar (kademeli tespit %75.8/%74.7;
daire %7.2/%8.6/%7.2), bu yüzden yön güvenilir; kesin hüküm n=4 ister.

## D · ÖLÇÜLEMEYEN — kayıt eksiği

`cikarim.csv`'de **`vis_h` sütunu yok.** Kutu boyutu × gerçek menzil sabit
çıkmalı; yalnız genişlikle 950 → 350'ye düşüyor. Ama güdüm `max(w,h)`
kullanıyor ve hedef yatıkken h > w olur. Bu, 2026-08-26'da "görsel menzil
2 kat sapıyor" diye yazılıp geri alınan artefaktın AYNISI. **Sütun
eklenmeden bu ölçülemez.**

## E · SIRADAKİ — görüş hattı, güdüm hattı değil

Kaçırmaların %76-81'i kör geçiş olduğuna göre kazanım güdüm yasasında
değil GÖRÜŞTE. Sıradaki adaylar (§0.1: teker teker):
1. `GORSEL_DET_HZ` 10 → 25 (Ö-M iş parçacığı bunu mümkün kıldı)
2. `PANEL_YAKALA_HZ` 15 → 30 (ölçüldü: kopyalama 2.4 ms, 191 Hz kaldırır)
3. `vis_h` sütunu — ölçüm borcu
4. Yatık hedef için dedektör eğitimi (en büyük kaldıraç, en pahalı)

---

# 2026-08-27/28 GECESİ — 5 KAMPANYA, ~100 UÇUŞ

Kullanıcı: *"çok uzun koşular yap, farklı farklı bir sürü şey dene."*
Gece boyunca **güdüm yasasına tek satır dokunulmadı** (`git diff dow/gudum/`
boş); denenenlerin hepsi dedektör/görüş hattı ayarları ve ölçüm altyapısı.

## A · SİSTEMİN BUGÜNKÜ HALİ — n=32, hiçbir override yok

`GORUS_ISP=False · YAKALA=15 · DET_HZ=10 · talon_v3` (yani kodun varsayılanı)

| senaryo | n | İSABET | en yakın medyan | imha süresi | tespit% |
|---|---|---|---|---|---|
| `duz` | 16 | **16/16 (%100)** | 0.93 m | 16.1 s | 83 |
| `kademeli` | 16 | **12/16 (%75)** | 0.99 m | 16.0 s | 75 |
| TOPLAM | 32 | **28/32 (%88)** | | | |

**Düz uçan hedef hiç kaçırılmıyor.** Bütün ıskalar sert kaçamakta ve
**hepsi öldürücü yarıçapın İÇİNDE** (0.93 · 1.08 · 1.11 · 1.32 m).

## B · İKİ ÖZELLİK ELENDİ

**K1 · Görüş hattı hızı** (YAKALA 15→30, DET 10→25): mekanizma kusursuz
çalıştı (çıkarım/s 7.2→14.6, kutu yaşı p90 1.83→0.39 s) ama **isabet
8/8 → 5/8 düştü.** Fisher tek yönlü p≈0.10 — yön net, kesinlik yok.
Ö-K ile aynı şekil: mekanizmanın çalışması sonucun iyileşeceğini göstermez.

**K2 · Ö-M görüş iş parçacığı**: birincil ölçütte berabere (7/8 vs 7/8) ama
vuruş kalitesi **7/7 vs 5/7 KONTROLLÜ**, görüş verimi **2 kat** kapalı
lehine (4.1 vs 2.0 TESPİT/s), çıkarım 19 vs 34 ms. **Eski olumlu sonucu
(p=0.021) tekrarlanmadı** — o kampanyalar elenmiş `talon_v5` modeliyle ve
şimdi silinmiş senaryolarda koşulmuştu.

## C · ⭐ KÖK NEDEN BULUNDU: TEMAS ANINDA MENZİL ŞİŞMESİ

68 koşu (59 vuruş / 9 ıska), terminal 1 saniye:

| ölçüt | VURAN | ISKA |
|---|---|---|
| kutu **genişliği** | 260 px | **116 px** (−55%) |
| kutu **yüksekliği** | 105 px | 103 px (−2%) |
| görsel süreklilik | 0.88 | 0.62 |
| dedektör güveni | 0.87 | 0.71 |

Yükseklik sabit, genişlik yarıya iniyor. Güdüm menzili `max(w,h)`'den
okuduğu için doğrudan ölçüldü:

```
güdümün gördüğü menzil / GERÇEK menzil (son 1 s)
  VURAN     n=52  medyan 1.18
  ISKALAYAN n= 9  medyan 1.97      <-- hedefi İKİ KAT uzak sanıyor
```

**Zincir:** hedef sert yatar → kanatlar kameraya kenardan gelir → kutu
genişliği çöker → `max(w,h)` çöker → güdüm menzili 2 kat şişer → hız yasası
ve terminal davranışı TAM TEMAS ANINDA yanlış çalışır.

## D · ÇÖZÜM ADAYI VE SINIRI — 3387 kare

| kutu ölçüsü | C medyan | yayılım p90/p10 | 0-30° | 30-60° | 60-90° |
|---|---|---|---|---|---|
| `max(w,h)` (bugün) | 899 | 1.94 | +1% | −29% | +17% |
| **köşegen √(w²+h²)** | **973** | **1.68** | +0% | −22% | +25% |
| yalnız h | 386 | 1.77 | −1% | +12% | **+69%** |

⛔ **"Yükseklik dönmeye dayanıklıdır" HİPOTEZİM YANLIŞ ÇIKTI** — terminal
karşılaştırmada öyle görünüyordu, tüm aspekt bandında en kötüsü.

Köşegen en kararlısı ama kazanım **mütevazı** ve 30-60°'deki çukuru
**hiçbiri kapatmıyor**: o çukur ölçüm artefaktı değil, hedefin siluetinin
gerçekten daralması. Tek bir sabitle çözülmez.

**KULLANICIYA SUNULAN, UYGULANMAYAN ADAYLAR:**
1. `boyut = max(w,h)` → `√(w²+h²)`, `MENZIL_C` 997 → **973**
2. `MENZIL_C` 997 → **901** (yalnız sabit düzeltmesi; iki bağımsız
   kampanyada −9.7% / −9.6% ölçüldü)
3. Aspekt-farkında menzil ya da terminalde kutu boyutuna hiç güvenmemek

## E · ÖLÇÜM ALTYAPISINDA DÜZELTİLENLER

- `vis_h` sütunu eklendi → iki kez kurulamayan çaprazlama artık yapılabiliyor
- `vurus_kalitesi.py` eski boş klasörlere takılıp §4'ü sessizce atlıyordu
- `gece_kampanya.sh`'a **uçuş öncesi kapı**: iki kol gerçekten farklı mı
  (K2'de kol env'i sabitler tarafından eziliyordu — 16 uçuş kurtarıldı)
- **Kendi genellememi çürüttüm:** RESTART4 "tek süreç içinde restart
  gereksiz" demişti; gece betiği her koşuya ayrı süreç açıyor ve orada
  `drone_yok` ile koşu düşüyor. Düşen koşuyu tespit edip tekrarlayan
  telafi eklendi (gerçek ıskayı düşen koşu sanmıyor, sınandı).
