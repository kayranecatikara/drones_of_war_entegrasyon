# KAMPANYA Ö-F — lead, tetiklenmiş `yatay` kaçamakta · **ELENDİ, SİLİNDİ**

**Tarih:** 2026-08-26 · **n = 4/kol** · 8/8 geçerli · mekanizma 8/8

## 0 · NEDEN BU KAMPANYA

Ö-E (kare) lead'i **nötr** bulmuştu ama iki ikincil ölçüt deney lehineydi
(salınım cx 1.13 → 0.66, kaçırma 41 → 26). Karede birincil ölçüt tavandaydı
(imha 0/4) — yani kazanım **ölçülemiyordu**. Kaçamak senaryosunda ise
oynayacak yer var (KC1: 4 koşuda 4 kaçırma).

## 1 · SONUÇ — HER ÖLÇÜTTE KÖTÜLEŞTİ

| ölçüt | KONTROL | DENEY |
|---|---|---|
| imha | 4/4 | 4/4 |
| ⭐ **kaçırma** | **3** (2,0,0,1) | **5** (1,1,1,2) |
| ⭐ **ilk denemede** | **2/4** | **0/4** |
| süre | 20.4 s | 24.9 s |
| en yakın | 0.68 m | 0.66 m |
| görsel tespit | **%65.5** | %51.1 |
| \|roll\| p90 | **15.0°** | 25.6° |
| cx dönüş /s | **0.58** | 1.23 |

## 2 · ⚠ ÖNCEKİ OKUMAM YANLIŞTI

Ö-E'de *"lead aracı sakinleştirdi"* demiştim (cx 1.13 → 0.66). Ö-F tersini
gösterdi (0.58 → **1.23**, iki kat). O düşüş lead'in etkisi değil **koşu
değişkenliğiydi** — ve §5.2 tam bu tuzağı uyarıyordu (salınım, hedefi daha
çok kaybeden koşuda da düşer). Ben yine de olumlu yönde okumuşum.

Bu, §5.6'nın ("kendi lehine yorum yasağı") neden var olduğunun örneği.

## 3 · KARAR — SİLİNDİ (§5.12)

İki bağımsız kampanya, doğru zarfta, n=4/kol: Ö-E nötr, Ö-F açıkça aleyhte.
**GV03'ün (2026-08-22, n=3) hükmü DOĞRUYMUŞ** — yöntemi zayıftı ama sonucu
tuttu.

Silme listesi: `IbvsCfg.K_LEAD`, `LEAD_MAX_DEG`, `komut()` içindeki lead
bloğu ve `los_hiz` parametresi, `Beyin._son_azimut/_son_azimut_t/_los_hiz`,
`ibvs_los_hiz`/`ibvs_lead` tanı anahtarları, `los_hiz`/`lead` log sütunları,
`denklik.py` kurulumu, bekçi B59.

**DOĞRULAMA (ikisi de zorunlu):**
- sıfır referans taraması → temiz
- **bit bit denklik**: silmeden önceki hâlle 400 tikte güdüm çıktısı,
  faz ve sayaçlar **birebir aynı**

Bekçi B20 `K_LEAD` ve `LEAD_MAX_DEG` adlarını yeniden yasaklı listeye aldı.
