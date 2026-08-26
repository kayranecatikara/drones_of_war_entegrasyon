#!/usr/bin/env bash
# =============================================================================
# BİR A/B BLOĞU KOŞ — sim hazırlığı dahil, tek komut.
#   araclar/blok.sh <ad> <ALAN> <deger1,deger2> <tekrar> <sure_s>
# Örn: araclar/blok.sh B2_KOPRU IBVS.KOPRU_S 0,0.5 4 120
# Dönüşümlü A/B'yi tarama.py yapar (CLAUDE.md §4).
# =============================================================================
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
export DISPLAY="${DISPLAY:-:0}"
python3 araclar/sim.py || { echo "SİM HAZIRLANAMADI"; exit 1; }
echo -n "hibrit" > .gudum_kipi
DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
  timeout 5400 python3 araclar/tarama.py "$1" "$2" "$3" "$4" "$5" \
  > "logs/$1.log" 2>&1
echo "BLOK $1 BITTI ($(date +%H:%M))"
