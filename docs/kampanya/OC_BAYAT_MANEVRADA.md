# KAMPANYA Ö-C — bayat kutuyu bırak, MANEVRA altında

**Tarih:** 2026-08-26 · **kaçamak:** `yatay` sabit · dönüşümlü A/B
**Durum:** ⚠ **HÜKÜM KURULAMADI** — deney kolu n=2 (eşik 4)

---

## 0 · SORU NEREDEN GELDİ

`ibvs.py` içindeki `BAYAT_BIRAK` notu, önceki bir oturumdan açık soru
bırakmış:

> *"⚠ Karşılaştırmanın tamamı hedef DÜZ uçarken yapıldı; hayalete uçmanın
> bedeli manevrada çıkabilir. Anahtar KAPALI, gerekçesi yazılı, **manevra
> açılınca yeniden sınanacak**."*

Manevra düzeneği (`araclar/kacamak.py`) artık var. Sınanan tam bu.

**Mekanizma:** köprü `KOPRU_S`=1.0 s dolunca güdüm sessizce ESKİ HAM KUTUYA
düşüyor. Hedef düz uçarken zararsız (C1'de berabere). Hedef 50° kırılırken
o kutu **hayalet** demek.

---

## 1 · ⛔ §5.1 MEKANİZMA KAPISI — DENEY KOLUNUN YARISI ELENDİ

| koşu | `bayat_birak` | GORSEL'de en uzun kör | hüküm |
|---|---|---|---|
| `1__t1` | 166 | 2.25 s | ✅ |
| `1__t2` | **0** | **0.00 s** | ⛔ GEÇERSİZ |
| `1__t3` | **0** | 0.54 s | ⛔ GEÇERSİZ |
| `1__t4` | 54 | 2.23 s | ✅ |

Kontrol kolu 4/4 geçerli (`bayat_birak`=0, sızıntı yok), ihlal yok.

**Sebep mekanizmanın kendi doğasında:** `BAYAT_BIRAK` yalnız köprü DOLUNCA
ateşler. Kör boşluk 1 saniyeyi geçmediyse bırakılacak bayat kutu yoktur ve
o koşu fiilen KONTROL koşusudur. Kıyasa girerse tablo sahte olur (Ö6 dersi).

⚠ Bu, özelliğin **ölçülebilirlik maliyeti**: koşuların ancak yarısında
devreye giriyor, yani n=4 geçerli için ~8 çift koşmak gerekiyor.

---

## 2 · ELDEKİ SAYILAR — ⚠ ARA VERİ, KARAR DEĞİL

| ölçüt | KONTROL (n=4) | DENEY (n=2) |
|---|---|---|
| ⭐ kaçırma | 3 (1,1,0,1) | 2 (1,1) |
| ilk denemede vuruş | 1/4 | 0/2 |
| imha | 4/4 | 2/2 |
| süre | 22.0 s | 29.6 s |
| en yakın | 0.55 m | 0.82 m |
| görsel tespit | %51.5 | %47.1 |
| kutu yaşı p90 | 1.51 s | 1.58 s |
| \|roll\| p90 | 12.4° | 12.6° |

Deney kolu **hiçbir ölçütte önde değil**, birkaçında geride.

---

## 3 · DEĞERLENDİRME

Deponun öngörüsü (*"hayalete uçmanın bedeli manevrada çıkar"*) bu veriyle
**desteklenmiyor**. İki bağımsız ölçüm aynı yöne bakıyor:
- **C1** (düz uçuş, n=4/kol): berabere, girmedi
- **Ö-C** (manevra, n=4/2): deney önde değil

Ama n=2 ile hüküm YOK. Anahtar **KAPALI kalır** (zaten varsayılan).

⚠ **DAHA ÖNEMLİ BAĞLAM — KC1'in kök neden bulgusu:**
Kaçırmaların asıl sebebi dedektörün yan aspektte kutu ÜRETMEMESİ
(kuyrukta %56-74, yanda %6-46, kafada %4-19). Köprü/bayat kutu
davranışını ayarlamak, güdümün ulaşamadığı bir sorunu güdümle çözmeye
çalışmaktır. Asıl çare kuyruk dışı görüntüyle eğitilmiş model.

## 4 · AÇIK

n=4 geçerliye çıkarmak için ~4 çift daha (~20 dk). Kullanıcı kararı.
