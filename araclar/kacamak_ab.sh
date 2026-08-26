#!/usr/bin/env bash
# =============================================================================
# KAÇAMAK ALTINDA A/B — kaçamak SABİT, bir güdüm anahtarı DÖNÜŞÜMLÜ
#   araclar/kacamak_ab.sh <ad> <kacamak> <ENV_ADI> <deger0,deger1> <tekrar> <sure>
#
# Örn: araclar/kacamak_ab.sh OC_BAYAT yatay DOW_BAYAT_BIRAK 0,1 4 150
#
# NEDEN AYRI BETİK: `kacamak_kampanya.sh` kaçamak TÜRLERİ arasında dönüyor.
# Burada kaçamak sabit tutulur (kaçırmanın yoğunlaştığı kol) ve güdüm
# anahtarı dönüşümlü koşulur -> §4 TEK DEĞİŞKEN.
#
# HER KOŞU AYRI SÜREÇ + kendi env'i (§6: otomatik A/B'de env + tam restart).
# DÖNÜŞÜMLÜ (§4): her turda iki değer sırayla; bir kolun hepsi arka arkaya YOK.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; KAC="${2:?kacamak turu}"; ENVAD="${3:?env adi}"
IFS=',' read -ra DEG <<< "${4:?degerler}"
TEKRAR="${5:-4}"; SURE="${6:-150}"

echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"
echo "=== KAÇAMAK ALTINDA A/B: $AD ==="
echo "    kaçamak sabit : $KAC"
echo "    değişken      : $ENVAD = ${DEG[*]}"
echo "    tekrar        : $TEKRAR  ->  toplam $(( ${#DEG[@]} * TEKRAR )) koşu"
date

for ((i=1; i<=TEKRAR; i++)); do
  for V in "${DEG[@]}"; do
    ETIKET="${V}__t${i}"
    echo "=== [$(date +%H:%M:%S)] KOŞU $ETIKET  ($ENVAD=$V) ==="

    # ⛔⛔ HER KOŞUDAN ÖNCE OYUNU KOMPLE YENİDEN BAŞLAT (2026-08-26).
    #   NEDEN: UE4SS modu Talon'u `isDead=true` ile spline rotasından
    #   koparınca, kontrol BIRAKILSA (aktif=0) ve GÖREV YENİDEN KURULSA BİLE
    #   hedef eski yerinde kalabiliyor. ÖLÇÜLDÜ: kaçamak aracı HİÇ
    #   çalışmadığı SADE koşuda bile en_yakin 1803 m, ihlal irtifa_tavani,
    #   0 tespit. Yani kirlilik kaçamak düzeneğinden BAĞIMSIZ olarak simde
    #   BİRİKİYOR ve görev restart'ı temizlemiyor.
    #   BEDELİ: koşu başına ~2.5 dk. Alternatifi kampanyanın tamamen
    #   çöpe gitmesi (üç kez yaşandı).
    pkill -f "araclar/kacamak.py" 2>/dev/null
    python3 - <<'PYEOF' 2>/dev/null
import os
p = "/tmp/talon_kopru.txt"
with open(p + ".tmp", "w") as f:
    f.write("0 0.000 0.000 0.000 0.000 999999\n")
os.replace(p + ".tmp", p)
PYEOF
    pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null
    sleep 4
    if ! python3 araclar/sim.py >> "logs/$AD.sim.log" 2>&1; then
      echo "⛔ SİM HAZIRLANAMADI — kampanya durduruldu"
      exit 1
    fi
    env "$ENVAD=$V" DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
      timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
      >> "logs/$AD.log" 2>&1 &
    KOSU_PID=$!
    # ⛔⛔ ALT KABUĞA SARMA — `kill $!` ALT KABUĞU öldürür, python'u SAĞ BIRAKIR.
    #   YAŞANDI (OC_BAYAT ilk denemesi): 5 kacamak.py süreci aynı anda koştu,
    #   beşi birden /tmp/talon_kopru.txt'ye yazıp hedefin kumandası için
    #   boğuştu. Koşularda spawn_cok_uzak / irtifa_tavani ihlalleri çıktı ve
    #   kampanya GEÇERSİZ oldu. Süreci DOĞRUDAN arka plana al.
    #   (kacamak.py paneli zaten 60 s bekliyor; `sleep` gerekmez.)
    python3 araclar/kacamak.py "$KAC" --ad "$AD/$ETIKET" \
      >> "logs/$AD.kacamak.log" 2>&1 &
    KAC_PID=$!
    wait $KOSU_PID
    kill "$KAC_PID" 2>/dev/null; wait "$KAC_PID" 2>/dev/null
    # ⭐ EMNİYET: yine de sağ kalan varsa temizle — bir sonraki koşuya sızmasın
    pkill -f "araclar/kacamak.py" 2>/dev/null
    # ⛔⛔ KÖR KOŞU KAPISI (2026-08-26, İKİ KAMPANYA BÖYLE YANDI).
    #   Oyun "press E to spawn" durumunda kalabiliyor; o ekranda da pusula
    #   HUD'i göründügü icin `ucusta_mi` UÇUŞTA diyor ve kosu baslıyor.
    #   Dedektör bos manzaraya bakiyor: 962 cikarim / 0 tespit, arac 14 m'de
    #   takili kaliyor, `spawn_cok_uzak` ihlali. Kampanyanin TAMAMI cope
    #   gidiyor. Bir kosuda HIC tespit yoksa kampanyayi ORADA durdur.
    SON="logs/$AD/$ETIKET/k01/cikarim.csv"
    if [ -f "$SON" ]; then
      TESPIT=$(awk -F, 'NR>1 && $3==1' "$SON" | wc -l)
      if [ "$TESPIT" -eq 0 ]; then
        echo "⛔⛔ KÖR KOŞU: $ETIKET içinde HİÇ TESPİT YOK."
        echo "    Oyun muhtemelen 'press E' durumunda — FPV görüntüsü yok."
        echo "    Düzelt: python3 araclar/sim.py  (sonra kampanyayı yeniden başlat)"
        echo "=== KAMPANYA $AD DURDURULDU ==="
        exit 1
      fi
    fi
    echo "    bitti"
  done
done
echo "=== KAMPANYA $AD BİTTİ ($(date +%H:%M)) ==="
