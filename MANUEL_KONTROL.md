# Hedef İHA'yı (Talon) Elle Sürme

Bu dal **tek bir şey** ekler: yer kontrol arayüzünden hedef İHA'yı klavye ve
sanal joystick ile sürebilme. Uçuş/güdüm/dedektör tarafına dokunmaz.

---

## 1. Neden dosya köprüsü? (önce bunu oku)

**Resmî SDK Talon'a komut VEREMEZ.** `sdk/drone_sdk.py` içinde hedefle ilgili
yalnızca okuma fonksiyonları var:

```
get_target_location()   get_target_rotation()   get_target_speed()
```

Bütün `set_*` çağrıları (`set_throttle`, `set_pitch`, `set_roll`, `set_yaw`,
`set_arm`) **avcı drone'a** aittir. Yani TCP 12345 kanalından hedefi sürmek
mümkün değil. Bu yüzden komutlar oyunun içindeki bir UE4SS moduna dosya
üzerinden aktarılıyor:

```
tarayıcı → /api/talon → /tmp/talon_kopru.txt → (Z: sürücüsü) → UE4SS modu → Talon
```

Proton önekinin `Z:` sürücüsü tüm Linux dosya sistemini gördüğü için oyun
tarafı aynı dosyayı `Z:\tmp\talon_kopru.txt` olarak okur. Yazma **atomik**
(önce `.tmp`, sonra `os.replace`) — yoksa oyun yarım satır okuyor.

### Köprü biçimi

Tek satır, boşlukla ayrılmış:

```
<aktif> <throttle> <yaw> <pitch> <roll> <sayaç> <kip>
```

| alan | aralık | anlam |
|---|---|---|
| `aktif` | 0/1 | serbest uçuş açık mı |
| `throttle` | 0..1 | ileri hız — oyun tarafı 300..4000 cm/s'ye eşler |
| `yaw` | -1..1 | burun sola/sağa (arayüzde KAPALI, hep 0 gider) |
| `pitch` | -1..1 | alçal / tırman |
| `roll` | -1..1 | sola/sağa yatış — koordineli dönüş de üretir |
| `sayaç` | tamsayı | her yazmada artar |
| `kip` | 0/1/2 | 0 = elle, 1 = **kare**, 2 = **daire** (isteğe bağlı 7. alan) |

`sayaç` tazelik içindir: ilerlemezse (arayüz kapandı/dondu) mod kumanda
eksenlerini sıfırlar ama **throttle'ı korur** — uçak düz uçmaya devam eder,
aniden durmaz.

---

## 2. Talon'u rotasından nasıl kopardık

Talon bir **spline rotası** üzerinde uçuyor ve konumu **her tikte spline'dan
yeniden hesaplanıyor**. Bu yüzden aktörü doğrudan taşıyan yöntemlerin hiçbiri
tutmuyor. Oyun içinde ölçüldü — her yöntem üç noktada (hareket öncesi, hemen
sonrası, +1.5 sn), hedef 500 cm yer değiştirme:

| yöntem | sonuç |
|---|---|
| `K2_SetActorLocation` (konsol komutları) | ✗ uygulanıyor ama drone kendi uçuşuna devam ediyor, 17.7 m uzaklaşıyor |
| Dondur (`CustomTimeDilation=0`) + taşı | ✗ **0.0 cm** — çapa döngüsü geri çekiyor |
| Dondur + çapayı hedefe güncelle | ✗ **0.0 cm** |
| Özyinelemeli "nuclear freeze" (`SetMovementMode(0)` dahil) | ✗ **0.0 cm** |
| `Speed = 0` sonra taşı | ✗ **0.0 cm** |
| `SetActorTickEnabled(false)` | ✗ 27.2 m — hiç durmuyor |
| `BPC_AIMove.DistanceAlongSpline`'a yaz | ✓ rota **üzerinde** taşır |
| **`BPC_AIMove.isDead = true`** | ✓ **500 cm hedef → 500.0 cm sonuç** |

**Kazanan: `isDead = true`.** Bu bayrak spline takibini tamamen kapatıyor ve
aktörün konumu tamamen bize kalıyor. Sonrasında uçuş modelini mod hesaplıyor.

Kontrol değişkenleri `BPP_AIDroneTalon_C` içindeki `BPC_AIMove` bileşeninde:
`DistanceAlongSpline`, `Speed` (varsayılan 1800 cm/s), `isLoop`, `isDead`.

> ⚠ `bIsActive = false` görüntüsüne aldanmayın — bileşen öyle görünmesine
> rağmen gerçekten ilerliyor (1.5 sn'de `DistanceAlongSpline` +2710 ölçüldü,
> tam olarak `Speed × süre`).

Bu bulgu `TalonDatasetGenerator/main.lua` satır 63-72'deki yazar notunu da
açıklıyor: "rotasyonu motor geri alıyor" — sebebi bu spline sürücüsü.

---

## 3. Uçuş modeli

`isDead` sonrası konum bizde olduğu için uçuşu mod kendisi entegre ediyor
(30 ms tik):

```
hız  = 300 + throttle × 3700              (cm/s)
YAW += (yaw × 35 + roll × 20) × dt        (derece/s)
X   += cos(YAW) × hız × dt
Y   += sin(YAW) × hız × dt
Z   += pitch × 600 × dt                   (cm/s)
```

Roll hem gövdeyi yatırıyor hem **koordineli dönüş** üretiyor — sabit kanat bir
uçakta doğrusu bu. Görsel olarak burun `pitch × 15°`, yatış `roll × 45°`.

**Ölçülen davranış** (oyun içi, SDK telemetrisiyle):

| eksen | ölçüm |
|---|---|
| pitch | 6 m/s tırmanış (ayarla birebir) |
| irtifa kilidi | bırakınca **14 sn boyunca ±5 cm** |
| yaw | ~35°/s |
| roll | `-1` ile ~18.7°/s sola (ayar 20) |

---

## 4. Kurulum

### 4.1 Önkoşul: oyunda UE4SS çalışıyor olmalı

Üç parça birden gerekiyor; biri eksikse mod yükleyici **sessizce hiç
çalışmaz** (oyun modsuz da sorunsuz açılır, hata vermez):

1. `Binaries/Win64/dwmapi.dll` — proxy. **UE4SS `experimental-latest`**
   sürümünden (279 KB). v3.0.1'inki (58 KB) YANLIŞ: eski klasör düzenini arar.
2. `Binaries/Win64/MSVCP140_CODECVT_IDS.dll` — UE4SS.dll'in bağımlılığı,
   Proton önekinde yok. VC++ redist kurulumu önekе bir şey EKLEMİYOR; DLL'i
   `vc_redist.x64.exe` içinden `cabextract` ile `a12` cab'ından çıkarmak gerekti.
3. `WINEDLLOVERRIDES="dwmapi=n,b"` — başlatıcıda.

**Yüklendiğini anlamanın tek yolu:** `ue4ss/UE4SS.log` dosyasının zaman
damgası. Güncellenmediyse UE4SS devreye girmemiştir. Ayrıntılı teşhis:
`WINEDEBUG=+loaddll` ile çalıştırıp çıktıda `dwmapi` ve `import_dll` arayın.

### 4.2 Modu kur

```bash
bash calistirma_betikleri/talon_modu_kur.sh
```

Mod kaynağı `dow/ue4ss_modlari/TalonWebControl/` altında repoda durur; betik
onu oyunun `ue4ss/Mods` klasörüne kopyalar ve `mods.txt`'ye kaydeder. Oyun
klasörünü önce `oyun/Drones of War Teknofest`, sonra `~/Desktop/Drones of War
Teknofest` sırasıyla arar.

Kurulumdan sonra **oyunu yeniden başlatın** (UE4SS modları açılışta yükler).

### 4.3 Çakışan modları kapat

`mods.txt` içinde aynı anda **yalnızca bir** Talon kontrol modu açık olmalı.
İkisi birden açıkken konumu iki ayrı hesap yazar ve Talon titrer.
`TalonDatasetGenerator` açıksa `9` (Talon dondur) ve `F` tuşlarına dikkat —
onlar da bu kontrolle çakışır.

> `enabled.txt` dosyası `mods.txt`'yi **ezer**. Bir modu kapatırken
> `mods.txt`'de `0` yapmak yetmez, klasöründeki `enabled.txt` varsa onu da
> kaldırın.

---

## 5. Çalıştırma

```bash
# 1) oyun — TAM EKRAN olmalı
drones-of-war          # ya da kendi başlatıcınız

#    elle: PRESS FOR START (iki tık) -> FLY -> harita gelince E
#    sol altta akım/batarya göstergesi görünüyorsa hazır

# 2) arayüz (ayrı terminal)
DISPLAY=:0 python3 araclar/uzaktan.py

# 3) tarayıcı
#    http://127.0.0.1:8801
```

`araclar/uzaktan.py` yalnız **panel + ekran yakalama** çalıştırır. YOLO
yüklemez, SDK'ya bağlanmaz, güdüm koşturmaz ve **menüye tıklamaz**.

> `araclar/kosu.py` bir ÖLÇÜM koşucusudur: görev-sonu ekranından kurtulmak
> için ekrana kör tıklar. Uzaktan kontrol için bu riske girmeye gerek yok.
> Uçuş+telemetri isteniyorsa `kosu.py` kullanın (`DOW_PANELDEN=1` ile panelden
> tetiklenir), yalnız kontrol isteniyorsa `uzaktan.py` yeterli.

**Tam ekran neden şart:** yakalama sabit ekran bölgesine bakar
(`araclar/kadraj.py::BOLGE` = 1920x1080). Pencere modunda HUD beklenen yerde
olmaz ve kaynak kapısı sürekli uyarı basar.

---

## 6. Kullanım

Panelde **🎯 Talon Kontrol** düğmesi. RC verici düzeni (Mode 2):

| kol | dikey ↕ | yatay ↔ |
|---|---|---|
| **SOL** | **throttle** — YAPIŞKAN, bıraktığın yerde kalır | kilitli (yaw kaldırıldı) |
| **SAĞ** | pitch | roll (dönüş) |

Gerçek bir vericide gaz kolu geri yaylanmaz; burada da öyle — hedefe bir hız
verip elini çekebilirsin. Diğer eksenler yaylı.

**Klavye** (fiziksel tuş kodu; klavye dili fark etmez):

| tuş | işlev |
|---|---|
| `I` / `K` | gaz + / − |
| `↑` / `↓` | pitch (tırman / alçal) |
| `←` / `→` | roll (dönüş) |

Basılı tut → eksen dolu. **Bırak → 0**, yani irtifa ve yön o anki değerde
kilitlenir. Kol ve klavye toplanır, sonuç -1..1'e kısılır.

Düğmeye tekrar basınca `isDead` geri alınır ve Talon kendi rotasına döner.

---

## 7. Desenler (kare / daire)

İki desen düğmesi var:

* **⬛ Kare Deseni** — 40 m düz, 90° sağa, tekrar... (kenar 40 m)
* **◯ Daire Deseni** — sabit yarıçaplı daire (çap 35 m)

Basıldığı **andan itibaren** başlar ve sen kapatana kadar sürer. Tekrar
basınca desen kalkar; Talon kendi rotasına döner.

Desen kipinde **joystickler devre dışı** (panelde soluklaşır); yalnız **gaz**
geçerli kalır, böylece desenin hızını ayarlayabilirsin. İrtifa sabit tutulur.

### Neden geometri oyun tarafında

Desen **UE4SS modunda** sürülüyor, tarayıcıda değil. Arayüzden yalnız `kip=1`
gidiyor. Sebep: ağ gecikmesi ve tarayıcı takılması kenar uzunluğunu bozardı;
modda 30 ms'lik tikle ölçülüyor.

**Ölçüldü:** 65 kenar üst üste tamamlandı, **hepsi 40.1 m** (hedef 40 m).

### Köşe geometrisi (kare)

Uçak anlık 90° dönemez. Düz kenar tam 40 m ölçülür, köşe ise `KARE_DONUS_HIZI`
ile sürülür — yani köşe bir **yay**. Yay yarıçapı `hız / dönüş_hızı`:

```
1500 cm/s ve 90°/s  ->  15 m/s / 1.571 rad/s  =  ~9.5 m
```

Keskin köşeli kare isteniyorsa modda `KARE_DONUS_HIZI` çok büyük yapılır
(ör. 3600). Kenar uzunluğu `KARE_KENAR` (cm), köşe açısı `KARE_DONUS`.

Köşede taşma yok: dönüş 90°'yi geçecekse son adım kırpılır, tam 90°'de durur.

### ◯ Daire — çap 35 m

**Çap sabit tutulur: dönüş hızı hızdan türetilir.**

```
omega = v / r        (rad/s)        derece/s = omega x 57.2957795
```

Sabit bir dönüş hızı verseydik gaz artınca çap büyürdü. Bu yolla throttle ne
olursa olsun çap 35 m kalır; yalnız tur süresi değişir.

**Ölçüldü** (gaz 0.40 = 1780 cm/s):

| | beklenen | ölçülen |
|---|---|---|
| dönüş hızı | 58.3°/s | **58.3°/s** |
| tur süresi | 6.18 s | **6–7 s** (3 tur üst üste) |

Çap `DAIRE_CAP` (cm) ile değişir. Görsel viraj yatışı `DAIRE_YATIS_MAX` ile
sınırlıdır ve yalnız görseldir — uçuş geometrisini etkilemez.

### Doğrulama (tek oturumda, uçtan uca)

Kare → daire → kare → elle → bırak zinciri canlı olarak sınandı:

```
ARAYUZ KONTROLU ACIK - irtifa 93 m, yon -2
KARE MODU ACIK  - kenar 40 m, kose 90 derece saga      <- kare
DAIRE MODU ACIK - cap 35 m (yaricap 17.5 m)            <- daireye gecis
KARE MODU ACIK  - kenar 40 m, kose 90 derece saga      <- kareye geri
kare modu kapandi - elle kumandaya donuldu             <- elle
arayuz kontrolu kapali - Talon kendi rotasina dondu    <- birak
```

Bu koşuda **13 kenar** (kare) ve **3 tur** (daire) tamamlandı. Geçişlerde
takılma yok; her desen devralırken diğerini temiz kapatıyor.

Ayrı ölçümler: kare **65 kenar üst üste, hepsi 40.1 m**; daire **58.3°/s,
tur 6–7 s** (hesap 6.18 s).

### İki düğme birbirini dışlar

Kare açıkken daireye basarsan kare kapanır, daire açılır. Açık olana tekrar
basarsan desen kapanır; panel de kapalıysa Talon kendi rotasına döner.

---

## 8. Bilinen sınırlar

- **`isDead = true` yan etkisi:** oyunun gözünde Talon'u "düşmüş"
  saydırabilir; skor/görev mantığı etkilenebilir. Kapatınca geri düzeliyor,
  ama bu ayrıca doğrulanmadı.
- **Yaw arayüzden kaldırıldı** (kullanıcı isteği): dönüş yalnız roll ile.
  Protokolde alan duruyor, hep `0` gidiyor — köprü biçimi ve mod değişmedi.
- **Panel aniden kapanırsa** mod kontrolü bırakmaz; eksenleri sıfırlayıp Talon'u
  düz uçurmaya devam eder. Hedef İHA için ani rotaya sıçramaktan güvenli
  bulundu. Otomatik bırakma isteniyorsa modda `BAYAT_TIK` mantığı değiştirilir.
- **Tek monitörde** tarayıcıyı oyunun üstüne getirme — yakalama ekrana bakıyor.
  Bu durumda panel yayını durdurur ve uyarı basar (bkz. kaynak kapısı).

---

## 9. Dosyalar

| dosya | rol |
|---|---|
| `dow/ue4ss_modlari/TalonWebControl/Scripts/main.lua` | oyun tarafı: köprüyü okur, uçuş modelini hesaplar |
| `calistirma_betikleri/talon_modu_kur.sh` | modu oyuna kurar, `mods.txt`'ye kaydeder |
| `dow/panel.py` | `talon_kopru_yaz()` + `POST /api/talon` |
| `dow/web/index.html` | iki sanal joystick + klavye + eksen göstergeleri |
| `araclar/uzaktan.py` | yalnız uzaktan kontrol için giriş noktası |

---

## 10. Wine/UE4SS tuzakları (tuş bağlarken)

- **`Key.OEM_1` diye bir şey YOK.** UE4SS bu adları rakamla değil yazıyla
  tutar: `OEM_ONE`, `OEM_EIGHT`. Olmayan bir ada `RegisterKeyBind` çağrısı
  `No overload found` hatası verip **script'i o satırda öldürür**; sonraki tüm
  bağlamalar sessizce kaydolmaz. Belirti: mod "yüklendi" der ama tuşların bir
  kısmı çalışmaz. Her bağlamayı `pcall` ile sarın.
- **Wine, Türkçe tuşları beklenen kodlara çevirmiyor.** Ölçüldü:
  `ş → Key.OEM_EIGHT` (OEM_1 değil), `i → Key.I`, `ı → Key.I` (aynı).
  Tahmin etmeyin, ölçün.
- **`math.deg` / `math.atan` KULLANMAYIN.** Daire dalı ilk yazıldığında bu
  ikisini kullanıyordu; UE4SS Lua'sında ilk tikte **sessizce** ölüyor ve
  `LoopAsync` bir daha dönmüyordu — log'a hata da düşmüyor, mod "yüklendi"
  diyor ama hiçbir şey yapmıyor. Aynı matematik düz aritmetikle yazılınca
  (`RAD2DEG = 57.2957795`) sorun bitti. `math.rad/cos/sin/min` sorunsuz.
- **UE4SS basılı tutmayı bildirmez.** `RegisterKeyBind` tuş başına tek sefer
  tetikler (3 sn basılı tutuldu → 1 tetik). Bu yüzden "bırakınca kilitlen"
  davranışı oyun içi tuşlarla YAPILAMAZ; tarayıcıda `keyup` olduğu için
  arayüzden yapılabiliyor. Bu, kontrolü arayüze taşımanın asıl sebebi.
