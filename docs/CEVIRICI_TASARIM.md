# HIZ → KUMANDA ÇUBUĞU ÇEVİRİCİSİ — tasarım notu

## Neden gerekli

Gazebo'da güdüm yasamız **hız setpoint'i** üretiyordu: `(vx, vy, vz, yaw_rate)`.
ArduPilot'un `AC_PosControl` katmanı bunu alıp gövde yatış açısına çeviriyordu.
DoW'da bu katman **yok** — SDK yalnız kumanda çubuğu kabul ediyor.

Bu dosya, o eksik katmanın matematiğini tanımlar. **Güdüm yasasına dokunmaz.**

## Terimler

- **Hız setpoint'i**: "şu hızla git" komutu. Birim m/s.
- **Kumanda çubuğu (stick)**: −1..+1 arası birimsiz sayı. DoW'da bu bir
  **hedef yatış açısı**dır (Angle Mode), dönüş hızı değil.
- **İç döngü**: ölçülen hızı istenen hıza yaklaştıran kontrolcü.
- **Kararlı-hâl kazancı**: sabit bir çubuk komutunun uzun vadede ürettiği hız.

## Yapı — üç kademe

    güdüm yasası          çevirici (YENİ)                    SDK
    ────────────          ────────────────                   ───
    (vx,vy,vz,yaw_rate) → [1] dünya→gövde dönüşümü        → set_control_
       m/s, NED           [2] hız hatası → istenen ivme      surfaces(
                          [3] ivme → çubuk (ters model)       thr,pitch,
                                                              roll,yaw,arm)

### [1] Eksen dönüşümü — NED → Unreal gövde

Gazebo NED kullanıyordu: X kuzey, Y doğu, **Z AŞAĞI**. `vz > 0` = alçal.
Unreal: X ileri, Y sağ, **Z YUKARI**. `throttle > 0` = tırman.

    v_ileri  =  vx·cos(yaw) + vy·sin(yaw)
    v_sag    = -vx·sin(yaw) + vy·cos(yaw)
    v_yukari = -vz                          ← İŞARET DÖNÜYOR

⚠ `yaw` SDK'dan DERECE gelir; radyana çevrilecek.
⚠ Konum/hız cm biriminde gelir; m'ye bölünecek (÷100).

### [2] Hız hatası → istenen ivme

    a_istenen = K_V · (v_hedef − v_ölçülen)     [m/s²]

`K_V` = hız izleme kazancı, birimi 1/s. Zaman sabiti τ = 1/K_V.
Yatış zaman sabiti 0.20 s olduğuna göre, iç döngü ondan **yavaş** olmalı
(aksi halde iki döngü birbirini kovalar → salınım). Başlangıç: K_V = 1.5
(τ = 0.67 s ≈ yatış zaman sabitinin 3.3 katı).

### [3] İvme → çubuk (ters model)

Burada ÖLÇÜM şart. İki aday model:

**Model A — açı tabanlı (klasik):** çubuk açıyı belirler, açı ivmeyi:
    stick = atan(a / g) / 60°
Bu model, 60° yatışta a = g·tan60° = 17.0 m/s² öngörür.

**Model B — doğrudan orantı:** oyun ivmeyi açıdan türetmiyor olabilir:
    stick = a / a_max

⚠ ÖLÇÜM ÇELİŞKİSİ: zarf paketi 60° yatışta 34–39 m/s² ölçmüş — Model A'nın
öngördüğünün **2.3 katı**. Bu, Model A'nın DoW'da geçersiz olduğuna işaret
eder. G2 basamak-tepki kampanyası hangisinin doğru olduğunu belirleyecek:
çubuk 0.25/0.50/0.75/1.00 verilip kararlı-hâl ivmesi ölçülür.
  - ivme çubukla DOĞRUSAL artıyorsa  → Model B
  - tan() eğrisine oturuyorsa        → Model A

### Dikey kanal — AYRI, çünkü throttle zaten bir hız komutu

README: throttle bir dikey HIZ komutu (+1 = max tırmanma). Yani dikeyde
ivme kademesine gerek YOK, doğrudan:

    throttle = v_yukari_hedef / VZ_MAX_TIRMAN      (v_yukari > 0)
    throttle = v_yukari_hedef / VZ_MAX_ALCAL       (v_yukari < 0)

⚠ İKİ TAVAN AYRI: ölçüm tırmanma +33.98 m/s, alçalma −5.65 m/s verdi
(6 kat asimetrik). Tek `VZ_MAX` kullanmak alçalmada komutu 6 kat abartır.
⚠ Belge "−1 = serbest düşüş" diyor ama ölçüm −5.65 m/s buldu. G1 çözecek.

### Yaw kanalı

Gazebo'da `yaw_rate` (°/s) üretiyorduk. DoW'da yaw çubuğu da normalize:
    yaw_stick = yaw_rate_hedef / YAW_RATE_MAX
Ölçülen tavan 214 °/s; ama hızlı yaw görüntüyü bulandırıp dedektörü kırar.
Güdüm tarafındaki 120 °/s sınırı KORUNUYOR.

## Doğrulama — çeviricinin kendi testi (hedefsiz)

Çevirici, güdümden BAĞIMSIZ sınanır (§5.1 mekanizma kapısı):
1. Basamak: 0 → 20 m/s ileri. Kararlı-hâl hatası < %5, aşım < %20,
   oturma < 1.5 s, salınım yok.
2. Rampa: 0 → 30 m/s, 10 s. İzleme hatası ölçülür.
3. Dikey basamak: 0 → +5 m/s ve 0 → −3 m/s (asimetri kanıtı).
Geçmezse güdüm bağlanmaz.

## Yapısal garanti (§5.10)

Çevirici, güdüm yasasının ÇIKTISINI okur; yasanın içine girmez. Yani
güdüm kodunda tek satır değişmeden çevirici değiştirilebilir ve tersi.
Bu, regresyon testinden daha güçlü bir ayrımdır.
