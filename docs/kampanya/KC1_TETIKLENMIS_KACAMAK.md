# KAMPANYA KC1 — tetiklenmiş kaçamak · güdüm manevra altında

**Tarih:** 2026-08-26 · **n = 4/kol** · 12 uçuş · dönüşümlü · **12/12 geçerli**

---

## 0 · NEDEN BU KAMPANYA

Kullanıcı (2026-08-26): *"BUNUN İÇİN FARKLI FARKLI SENARYOLARDA HEDEF ARACI
UÇUR, DRONE HEDEF ARACA YAKLAŞIRKEN MANEVRALAR YAPTIR VE DRONE'UN BU
MANEVRALARA KARŞI REAKSİYONUNU ÖLÇ."*

Ayrıca birincil ölçüt değişti (§ kullanıcı kuralı): `imha` her kolda tavanda
(4/4, 5/5) ve hiçbir şeyi ayırt etmiyordu. Yeni ölçüt **KAÇIRMA** —
`araclar/kacirma.py`.

## 1 · DÜZENEK

`araclar/kacamak.py`: mesafe 25 m'ye inince hedef devralınır ve BELİRLİ bir
manevra 4 s uygulanır. Devralma TETİKTE olur (öncesinde hedef kendi spline
rotasında uçar) — ilk tasarım koşu başından devralıyordu ve senaryoyu
bozuyordu (KC1 ilk denemesi bu yüzden iptal edildi).

## 2 · §5.1 MEKANİZMA KAPISI — 12/12 GEÇTİ

| kol | Δyön (tetik+5 s) | Δirtifa |
|---|---|---|
| `yok` ×4 | +0.0 … +2.4° | ~0 |
| `yatay` ×4 | **+48.2 … +50.4°** | ~0 |
| `dikey_yukari` ×4 | ~0 | **+9.8 … +14.8 m** |

Her kol yalnız kendi eksenini hareket ettiriyor — kalibrasyonda ölçülen
kanal bağımsızlığıyla tutarlı.

⚠ İki `dikey_yukari` koşusu önce "doğrulanamadı" diye GEÇERSİZ sayıldı;
yanlıştı. `meta.csv` 1 Hz ve `hedef_z` görsel fazda BOŞ kalıyor — bu kanıt
YOKLUĞU, manevranın olmadığının kanıtı değil. Truth kanalından (`dz_m`,
9 Hz) bakınca ikisi de manevra yapmış.

---

## 3 · SONUÇ — BİRİNCİL ÖLÇÜT

| kaçamak | kaçırma (koşu koşu) | **ilk denemede vuruş** |
|---|---|---|
| **`yok` (TABAN)** | **0** (0,0,0,0) | **4/4** |
| `yatay` | 4 (1,2,1,0) | 1/4 |
| `dikey_yukari` | 3 (2,1,0,0) | 2/4 |

**Taban kusursuz.** Manevra girince ilk-denemede oranı %100 → %25-50.
Kullanıcının gözlemi ("manevrada kaçırıyoruz") ölçümle doğrulandı.

### İkincil

| kaçamak | imha | süre | en yakın | görsel tespit | kutu yaşı p90 |
|---|---|---|---|---|---|
| `yok` | 4/4 | 13.7 s | 0.53 m | **%71.0** | 0.56 s |
| `yatay` | 4/4 | 19.9 s | 0.70 m | %62.2 | 1.34 s |
| `dikey_yukari` | 3/4 | 17.5 s | 0.65 m | **%44.8** | 1.56 s |

---

## 4 · ⭐ KÖK NEDEN — GÜDÜM DEĞİL, GÖRÜŞ

**7 kaçırmanın 7'sinde de geçiş anında görsel temas YOK.** Bir tane bile
"gördü ama dönemedi" yok. Ve ıska medyanı **1.2 m** — araç hedefe 1.2 metre
yaklaşıp ıskalıyor. Bu bir güdüm kabiliyeti sorunu değil.

### 4.1 · ⛔ Ö-B'NİN GEREKÇESİ ÇÜRÜDÜ

Ö-B "hedefi kadrajda tut" fikriydi; dayanağı eski kampanyalardaki
"çıkışların 48'i üstten, 13'ü alttan" sayısıydı. KC1'de temasın kesildiği
an ölçüldü:

| kaçırma | bek_cx | bek_cy | nerede |
|---|---|---|---|
| 7 kaçırmanın 7'si | 725-1058 | **14-589** | **KADRAJ İÇİ** |

**Hiçbiri kadrajdan çıkmamış.** Hedef kadrajda duruyor, dedektör göremiyor.
Ö-B bu koşularda çözeceği bir problem bulamaz — ELENDİ (kod yazılmadı).

### 4.2 · GERÇEK SEBEP: ASPEKT

Tespit oranı, hedefin bize gösterdiği yüze göre (yalnız <40 m):

| aspekt | 0-20° kuyruk | 20-40° | 40-60° | 60-90° yan | 90°+ kafa |
|---|---|---|---|---|---|
| `yok` | %72 | %21 | %29 | %46 | — |
| `yatay` | %74 | %45 | %18 | **%6** | %19 |
| `dikey_yukari` | %56 | %15 | %17 | **%7** | **%4** |

Kuyruktan ~%70 gören dedektör, hedef yana dönünce **%10'un altına** iniyor.
Depo bunu 2026-08-24'te zaten ölçmüş: *"tespit kuyrukta %95, yandan %35;
aspekt tespiti belirleyen EN GÜÇLÜ etken (r = -0.45)"* — model kuyruk
görüntüsüyle eğitilmiş.

**Kaçamak tam da bunu yapıyor:** `yatay` karelerin %41'ini kuyruk dışına
itiyor (`yok`'ta %25). `dikey_yukari` azimut aspektini değiştirmiyor ama
kuyruk aspektindeki tespiti bile %72 → %56'ya düşürüyor (yükseliş aspekti
`aspekt_deg`'in ölçmediği bir eksen).

---

## 5 · ⛔ DONANIM KISITI (kullanıcı, 2026-08-26)

*"kamera açısı sabit onu azaltamayız. yarışma komitesi belirledi onu,
donanımda değişiklik yapamıyoruz."*

Kamera 26.5° aşağı eğik, VFOV 90° — kadraj ufkun 18.5° üstü .. 71.5° altı.
**Bu bir VERİ, tasarım değişkeni DEĞİL.** Çözümler bu geometriyi veri kabul
edip üstüne kurulacak.

---

## 6 · SIRADAKİ

Kök neden "hedef kadrajda ama görülmüyor" olduğuna göre:

1. **Ö-C · köprü süresi** — hedef kaybolunca güdüm `KOPRU_S`=1.0 s köprüleyip
   bırakıyor; kaçamak 4 s sürüyor. Kör dönemi taşıyacak kadar uzun mu?
   Tek parametre, kill-switch hazır (`DOW_KOPRU_S`).
2. **Model** — aspekt körlüğünün ASIL çaresi kuyruk dışı görüntüyle eğitim.
   Bu güdüm tarafının işi değil.
