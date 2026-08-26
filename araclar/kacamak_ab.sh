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
    echo "    bitti"
  done
done
echo "=== KAMPANYA $AD BİTTİ ($(date +%H:%M)) ==="
