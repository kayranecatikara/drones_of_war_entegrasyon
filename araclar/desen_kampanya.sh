#!/usr/bin/env bash
# =============================================================================
# DESEN KAMPANYASI — hedef KARE/DAİRE çizerken güdümü sına
#   araclar/desen_kampanya.sh <ad> <desen1,desen2,...> <tekrar> <sure_s>
# Örn: araclar/desen_kampanya.sh KD1 taban,kare,daire 4 150
#
# ⛔ `taban` kolu HER KAMPANYADA koşulur: desensiz isabet oranını bilmeden
#    desenli sonuç yorumlanamaz (§3.3'ün `yok` kolunun karşılığı).
# DÖNÜŞÜMLÜ (§4): her turda tüm desenler sırayla.
# HER KOŞUDAN ÖNCE OYUN KOMPLE YENİDEN BAŞLAR — UE4SS modu hedefi spline
#   rotasından koparınca kirlilik birikiyor ve görev restart'ı temizlemiyor
#   (ölçüldü: sade koşuda bile en_yakin 1803 m). Bedeli ~2.5 dk/koşu.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; DESENLER="${2:?desenler}"
TEKRAR="${3:-4}"; SURE="${4:-150}"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"
IFS=',' read -ra LISTE <<< "$DESENLER"
echo "=== DESEN KAMPANYASI $AD ==="
echo "    desenler : ${LISTE[*]}"
echo "    tekrar   : $TEKRAR  ->  toplam $(( ${#LISTE[@]} * TEKRAR )) koşu"
date

for ((i=1; i<=TEKRAR; i++)); do
  for D in "${LISTE[@]}"; do
    ETIKET="${D}__t${i}"
    echo "=== [$(date +%H:%M:%S)] KOŞU $ETIKET ==="

    pkill -f "araclar/desen.py" 2>/dev/null
    python3 - <<'PYEOF' 2>/dev/null
import os
p = "/tmp/talon_kopru.txt"
with open(p + ".tmp", "w") as f:
    f.write("0 0.000 0.000 0.000 0.000 999999 0\n")
os.replace(p + ".tmp", p)
PYEOF
    pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null
    sleep 4
    if ! python3 araclar/sim.py >> "logs/$AD.sim.log" 2>&1; then
      echo "⛔ SİM HAZIRLANAMADI — kampanya durduruldu"; exit 1
    fi

    DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
      timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
      >> "logs/$AD.log" 2>&1 &
    KOSU_PID=$!
    python3 araclar/desen.py "$D" --ad "$AD/$ETIKET" \
      >> "logs/$AD.desen.log" 2>&1 &
    DES_PID=$!
    wait $KOSU_PID
    kill "$DES_PID" 2>/dev/null; wait "$DES_PID" 2>/dev/null
    pkill -f "araclar/desen.py" 2>/dev/null

    # ⛔ KÖR KOŞU KAPISI — hiç tespit yoksa kampanyayı ORADA durdur
    SON="logs/$AD/$ETIKET/k01/cikarim.csv"
    if [ -f "$SON" ]; then
      T=$(awk -F, 'NR>1 && $3==1' "$SON" | wc -l)
      if [ "$T" -eq 0 ]; then
        echo "⛔⛔ KÖR KOŞU: $ETIKET içinde HİÇ TESPİT YOK — oyun 'press E' durumunda olabilir."
        echo "=== KAMPANYA $AD DURDURULDU ==="; exit 1
      fi
    fi
    echo "    bitti"
  done
done
echo "=== KAMPANYA $AD BİTTİ ($(date +%H:%M)) ==="
