#!/usr/bin/env bash
# =============================================================================
# MANEVRA A/B — manevra senaryosu SABİT, kol farkı TEK ENV değişkeni
#   araclar/manevra_ab.sh <ad> <manevra> <ENV_ADI> <kapali_deger> <acik_deger> \
#                         <tekrar> <sure_s>
# Örn: araclar/manevra_ab.sh KI1 kademeli DOW_TERM_CONF 0.40 0.25 4 150
#
# NEDEN AYRI SCRIPT: `manevra_kampanya.sh` kolu MANEVRA TÜRÜ yapar; burada
#   manevra sabit tutulur ve kol GÜDÜM AYARI olur (§4 tek değişken).
# DÖNÜŞÜMLÜ (§4): her turda kapalı, açık — sim kayması iki kolu eşit etkilesin.
# HER KOŞUDAN ÖNCE OYUN KOMPLE YENİDEN BAŞLAR (isDead kirliliği görev
#   restart'ıyla temizlenmiyor — ölçüldü: sade koşuda en_yakin 1803 m).
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; MAN="${2:?manevra}"; ENVAD="${3:?env adi}"
V_KAPALI="${4:?kapali deger}"; V_ACIK="${5:?acik deger}"
TEKRAR="${6:-4}"; SURE="${7:-150}"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"
echo "=== MANEVRA A/B $AD ==="
echo "    manevra  : $MAN"
echo "    kol      : $ENVAD = $V_KAPALI (kapali) / $V_ACIK (acik)"
echo "    tekrar   : $TEKRAR  ->  toplam $(( 2 * TEKRAR )) koşu"
date

for ((i=1; i<=TEKRAR; i++)); do
  for KOL in kapali acik; do
    if [ "$KOL" = kapali ]; then DEG="$V_KAPALI"; else DEG="$V_ACIK"; fi
    ETIKET="${KOL}__t${i}"
    echo "=== [$(date +%H:%M:%S)] KOŞU $ETIKET  ($ENVAD=$DEG) ==="

    pkill -f "araclar/manevra.py" 2>/dev/null
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

    env "$ENVAD=$DEG" DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
      timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
      >> "logs/$AD.log" 2>&1 &
    KOSU_PID=$!
    python3 araclar/manevra.py "$MAN" --ad "$AD/$ETIKET" \
      >> "logs/$AD.manevra.log" 2>&1 &
    DES_PID=$!
    wait $KOSU_PID
    kill "$DES_PID" 2>/dev/null; wait "$DES_PID" 2>/dev/null
    pkill -f "araclar/manevra.py" 2>/dev/null

    SON="logs/$AD/$ETIKET/k01/cikarim.csv"
    if [ -f "$SON" ]; then
      T=$(awk -F, 'NR>1 && $3==1' "$SON" | wc -l)
      if [ "$T" -eq 0 ]; then
        echo "⛔⛔ KÖR KOŞU: $ETIKET içinde HİÇ TESPİT YOK — 'press E' olabilir."
        echo "=== KAMPANYA $AD DURDURULDU ==="; exit 1
      fi
    fi
    echo "    bitti"
  done
done
echo "=== KAMPANYA $AD BİTTİ ($(date +%H:%M)) ==="
