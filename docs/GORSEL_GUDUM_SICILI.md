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
