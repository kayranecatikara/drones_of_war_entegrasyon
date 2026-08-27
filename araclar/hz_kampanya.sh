#!/usr/bin/env bash
# =============================================================================
# HZ KAMPANYASI — GÖRÜŞ HATTI HIZI A/B, senaryo SABİT tutularak
#   araclar/hz_kampanya.sh <ad> <kol@senaryo,kol@senaryo,...> <sure_s>
#
# KOLLAR:
#   taban  -> PANEL_YAKALA_HZ=15  GORSEL_DET_HZ=10   (bugünkü varsayılan)
#   hizli  -> PANEL_YAKALA_HZ=30  GORSEL_DET_HZ=25
#
# ⛔⛔ NİYE İKİ DÜĞME BİRLİKTE OYNUYOR — ÖLÇÜLDÜ, TASARIM GEREĞİ:
#   Görüş iş parçacığının döngü periyodu `dt_yak = 1/PANEL_YAKALA_HZ` ve
#   çıkarım DÖNGÜ BAŞINA EN FAZLA BİR KEZ koşuyor. Yani:
#         gerçek çıkarım hızı = min(GORSEL_DET_HZ, PANEL_YAKALA_HZ)
#   Yakalama 15'te sabitken GORSEL_DET_HZ=25 yapmak 15'i AŞAMAZ. İki düğmeyi
#   ayrı ayrı sınamak "tek değişken" gibi görünür ama aslında yarım bir
#   mekanizma ölçer. Bu yüzden tek değişken = GÖRÜŞ HATTI HIZI.
#
#   ⚠ `dt_yak` döngüden ÖNCE bir kez hesaplanıyor -> PANEL_YAKALA_HZ panelden
#     CANLI DEĞİŞMEZ. Env + tam restart şart; bu betik zaten öyle yapıyor.
#
# ⛔ SENARYO KOL İÇİNDE SABİT (§5.9): kollar aynı senaryo karışımını almazsa
#    kaba medyan kolları değil karışım oranını ölçer. Sıra dönüşümlü verilir
#    ve her kol AYNI senaryo dağılımını alır.
#
# ⛔ MEKANİZMA KAPISI (§5.1): `hizli` kolunda `det_hz` yükselmezse özellik
#    ÇALIŞMAMIŞ demektir; o koşular veri noktası değil GEÇERSİZ koşudur.
#    İlk A/B çiftinden sonra `araclar/karma_ozet.py` ile kontrol edilir.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; SIRA="${2:?kol@senaryo listesi}"; SURE="${3:-150}"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"
IFS=',' read -ra LISTE <<< "$SIRA"

echo "=== HZ KAMPANYASI $AD ==="
echo "    sira      : ${LISTE[*]}"
echo "    kosu      : ${#LISTE[@]}  x ${SURE}s"
echo "    taban kolu: YAKALA=15 DET=10   |   hizli kolu: YAKALA=30 DET=25"
echo "    O-M       : ACIK (iki kolda da) | model talon_v3"
date

I=0
for E in "${LISTE[@]}"; do
  I=$((I+1))
  KOL="${E%%@*}"; SEN="${E##*@}"
  ETIKET="$(printf '%02d' $I)_${KOL}__${SEN}"
  echo "=== [$(date +%H:%M:%S)] KOSU $I/${#LISTE[@]} — $ETIKET ==="

  case "$KOL" in
    taban) YHZ=15; DHZ=10 ;;
    hizli) YHZ=30; DHZ=25 ;;
    *) echo "⛔ BILINMEYEN KOL: $KOL"; exit 1 ;;
  esac

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
    echo "⛔ SIM HAZIRLANAMADI — kampanya durduruldu"; exit 1
  fi

  DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit DOW_GORUS_ISP=1 \
  DOW_PANEL_YAKALA_HZ="$YHZ" DOW_GORSEL_DET_HZ="$DHZ" \
    timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
    >> "logs/$AD.log" 2>&1 &
  KOSU_PID=$!

  HEDEF_PID=""
  case "$SEN" in
    kademeli) python3 araclar/manevra.py kademeli --ad "$AD/$ETIKET" \
                >> "logs/$AD.hedef.log" 2>&1 &
              HEDEF_PID=$! ;;
    taban)    : ;;              # devralma YOK — hedef kendi rotasında
    *) echo "⛔ BILINMEYEN SENARYO: $SEN"; kill $KOSU_PID 2>/dev/null; exit 1 ;;
  esac

  wait $KOSU_PID
  [ -n "$HEDEF_PID" ] && { kill "$HEDEF_PID" 2>/dev/null; wait "$HEDEF_PID" 2>/dev/null; }
  pkill -f "araclar/manevra.py" 2>/dev/null

  SON="logs/$AD/$ETIKET/k01/cikarim.csv"
  if [ -f "$SON" ]; then
    T=$(awk -F, 'NR>1 && $3==1' "$SON" | wc -l)
    if [ "$T" -eq 0 ]; then
      echo "⛔⛔ KOR KOSU: $ETIKET icinde HIC TESPIT YOK"
      echo "=== KAMPANYA $AD DURDURULDU ==="; exit 1
    fi
  fi
  # mekanizma kapisi teshisi — her kosuda basilir, S5.1
  if [ -f "logs/$AD/$ETIKET/ozet.csv" ]; then
    awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR==2{
      printf("    det_hz=%s  det_ms=%s  tespit%%=%s  tik_hz=%s\n",
             $h["det_hz"],$h["det_ms"],$h["gorsel_tespit_yuzde"],$h["tik_hz"])}' \
      "logs/$AD/$ETIKET/ozet.csv"
  fi
  echo "    bitti  ($(date +%H:%M:%S))"
done

echo "=== KAMPANYA $AD BITTI ($(date +%H:%M)) ==="
