#!/usr/bin/env bash
# =============================================================================
# GECE KAMPANYASI — tek degiskenli A/B, iki senaryo, DONUSUMLU
#   araclar/gece_kampanya.sh <ad> <A_env> <B_env> <tekrar> <sure_s>
#   ornek: araclar/gece_kampanya.sh HZ2 "DOW_PANEL_YAKALA_HZ=15 DOW_GORSEL_DET_HZ=10" \
#                                       "DOW_PANEL_YAKALA_HZ=30 DOW_GORSEL_DET_HZ=25" 4 150
#
# HER TEKRARDA 4 KOSU: A@duz, B@duz, A@kademeli, B@kademeli  (donusumlu, §4)
#   -> tekrar=4 ise 16 kosu, her hucrede n=4 (§5.4)
#   -> iki kol AYNI senaryo karisimini alir (§5.9)
#
# ⭐ OYUN RESTART'I SADECE `kademeli` KOSULARINDA — 2026-08-27'de OLCULDU
#   (RESTART4, n=4): devralma YOKKEN oyunu ayakta birakmak hicbir sey
#   bozmuyor. 4 kosu ust uste, restart'siz: isabet 4/4, en yakin 0.91 /
#   0.48 / 0.52 / 0.92 m, ihlal 0, tik_hz 49.1. Korkulan imza (en_yakin
#   1803 m) hic gorunmedi ve kopru dosyasi koşu boyunca aktif=0 kaldi,
#   yani mod hic devreye girmedi. Kirliligin kaynagi DEVRALMAYMIS.
#   `kademeli`de mod hedefi rotasindan koparıyor -> orada restart DURUYOR.
#   Kazanc: duz kosu ~105 s yerine ~35 s.
#
# ⚠ SUREC RESTART'I HER KOSUDA VAR (oyun degil): env kola gore degisiyor ve
#   PANEL_YAKALA_HZ dongu disinda bir kez okunuyor, canli degismez.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; A_ENV="${2:?A kolu env}"; B_ENV="${3:?B kolu env}"
TEKRAR="${4:-4}"; SURE="${5:-150}"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"

echo "=== GECE KAMPANYASI $AD ==="
echo "    A kolu : ${A_ENV:-<varsayilan>}"
echo "    B kolu : ${B_ENV:-<varsayilan>}"
echo "    tekrar : $TEKRAR  ->  $((TEKRAR*4)) kosu (n=$TEKRAR/hucre)"
date

_kopru_notr() {
  python3 - <<'PYEOF' 2>/dev/null
import os
p="/tmp/talon_kopru.txt"
open(p+".tmp","w").write("0 0.000 0.000 0.000 0.000 999999\n"); os.replace(p+".tmp",p)
PYEOF
}

I=0
for ((t=1; t<=TEKRAR; t++)); do
  for SEN in duz kademeli; do
    for KOL in A B; do
      I=$((I+1))
      ETIKET="$(printf '%02d' $I)_${KOL}__${SEN}"
      [ "$KOL" = "A" ] && ENVK="$A_ENV" || ENVK="$B_ENV"
      echo "=== [$(date +%H:%M:%S)] KOSU $I/$((TEKRAR*4)) — $ETIKET ==="

      pkill -f "araclar/manevra.py" 2>/dev/null
      _kopru_notr

      # oyun restart'i YALNIZ kademeli'de (yukaridaki nota bak)
      if [ "$SEN" = "kademeli" ]; then
        pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null
        sleep 4
      fi
      if ! python3 araclar/sim.py >> "logs/$AD.sim.log" 2>&1; then
        echo "⛔ SIM HAZIRLANAMADI — kampanya durduruldu"; exit 1
      fi

      env $ENVK DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit DOW_GORUS_ISP=1 \
        timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
        >> "logs/$AD.log" 2>&1 &
      KOSU_PID=$!

      HEDEF_PID=""
      if [ "$SEN" = "kademeli" ]; then
        python3 araclar/manevra.py kademeli --ad "$AD/$ETIKET" \
          >> "logs/$AD.hedef.log" 2>&1 &
        HEDEF_PID=$!
      fi

      wait $KOSU_PID
      [ -n "$HEDEF_PID" ] && { kill "$HEDEF_PID" 2>/dev/null; wait "$HEDEF_PID" 2>/dev/null; }
      pkill -f "araclar/manevra.py" 2>/dev/null

      SON="logs/$AD/$ETIKET/k01/cikarim.csv"
      if [ -f "$SON" ]; then
        T=$(awk -F, 'NR>1 && $3==1' "$SON" | wc -l)
        [ "$T" -eq 0 ] && { echo "⛔⛔ KOR KOSU: $ETIKET — HIC TESPIT YOK"; echo "=== $AD DURDURULDU ==="; exit 1; }
      fi
      if [ -f "logs/$AD/$ETIKET/ozet.csv" ]; then
        awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR==2{
          printf("    SONUC isabet=%s enyakin=%s sure=%s tespit%%=%s tik_hz=%s\n",
                 $h["isabet"],$h["en_yakin_m"],$h["sure"],$h["gorsel_tespit_yuzde"],$h["tik_hz"])}' \
          "logs/$AD/$ETIKET/ozet.csv"
      fi
    done
  done
done
_kopru_notr
echo "=== KAMPANYA $AD BITTI ($(date +%H:%M)) ==="
