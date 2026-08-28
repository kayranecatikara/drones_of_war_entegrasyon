# KAMPANYA Ö-E — lead (kestirim payı), kare senaryosunda · **GİRMEDİ**

**Tarih:** 2026-08-26 · **n = 4 kontrol / 3 deney** · dönüşümlü

## 0 · NEDEN DENENDİ

KD1 kare senaryosu (n=4): 20→10 m arası **78 kapanma denemesinin 76'sı
(%97)** 6 m'nin altına inemeden kesiliyor. Kesilme sebebi:
- **45** "GÖRDÜ ama menzil açıldı" → GÜDÜM
- 31 "kör kesildi" → görüş

Kesilme anında hedef kadraj merkezinden **medyan 8.8° (p90 22.2°)** sapmış,
olayların %46'sında 200 px'ten fazla. Yani araç hedefi görüyor ama nişanı
üzerinde tutamıyor.

**GV03'teki red iki yönden geçersizdi:** (a) n=3 ile karar verilmiş —
dosyanın kendi notu *"HATAM: her kararı n=3 koşuyla verdim"*; (b) DÜZ uçan
hedefte sınanmış, oysa lead'in tasarım zarfı DÖNEN hedef (§5.13).

## 1 · MEKANİZMA KAPISI — 7/8

`lead > 0.5°` olan kare: DENEY 102/331/195/**16** · KONTROL 0/0/0/0.
`0.4__t4` yalnız 23 çıkarımda kalmış (görsel faza neredeyse girmemiş) →
§5.1 gereği ELENDİ. Deney kolu n=3.

## 2 · SONUÇ

| ölçüt | KONTROL | DENEY |
|---|---|---|
| ⭐ imha | 0/4 | 0/3 |
| süre | 150 s | 150 s |
| en yakın | **7.67 m** | 7.98 m |
| görsel tespit | %23.4 | %24.4 |
| kutu yaşı p90 | 1.89 s | 1.93 s |
| \|roll\| p90 | 39.1° | **29.0°** |
| cx dönüş /s | 1.13 | **0.66** |
| kaçırma | 41 | **26** |

Koşu koşu en yakın: KONTROL 6.59 / 7.63 / 8.20 / 7.72 · DENEY 7.98 / 9.60 / 6.76
→ **aralıklar tamamen örtüşüyor.**

## 3 · KARAR — GİRMEDİ

İlan edilen kural: *"birincil ölçüt (imha / en yakın) belirgin iyileşirse
girer"*. İyileşmedi. `DOW_LEAD` varsayılan **0** kalır.

⚠ **DÜRÜST NOT:** iki ikincil ölçüt deney lehine ve §4'ün özellikle önem
verdiği ölçütler bunlar — salınım (cx işaret değişimi 1.13 → 0.66, yatış
p90 39.1° → 29.0°) ve kaçırma (41 → 26). Lead aracı SAKİNLEŞTİRMİŞ.
Kazanım diye sunulmuyor çünkü:
- birincil ölçüt sıfır,
- n=3 (§5.4 eşiği 4),
- §5.2: salınım, hedefi daha çok kaybeden koşuda da düşer. Burada görsel
  tespit oranları yakın (%23.4 vs %24.4) olduğu için tuzak zayıf ama
  ortadan kalkmış değil.

## 4 · KOD KALIYOR — AÇIK BORÇ

`K_LEAD` kill-switch arkasında, varsayılanı 0, bit bit denkliği kanıtlı
(bekçi B59: 324 kombinasyon × 4 `los_hiz` → 0 fark). §5.12 anlamında
çıkarılacak bir şey yok: özellik hiç girmedi.

**Yeniden sınanacağı yer:** salınım azalması gerçekse, tetiklenmiş `yatay`
kaçamakta (KC1'de kaçırmanın yoğunlaştığı kol) ölçülmeli. Orada birincil
ölçüt tavanda değil, yani oynayacak yer var.
