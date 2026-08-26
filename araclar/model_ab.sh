#!/usr/bin/env bash
# =============================================================================
# MODEL A/B — iki modeli DÖNÜŞÜMLÜ koş, her koşu AYRI SÜREÇ + kendi env'i
#   araclar/model_ab.sh <kampanya_adi> <modelA> <modelB> <tekrar> <sure_s>
#
# NEDEN AYRI SÜREÇ: `dedektor.MODEL_YOLU` içe aktarma anında okunuyor ve
#   `Dedektor.__init__(yol=MODEL_YOLU)` varsayılan argümanı da öyle. Tek
#   süreçte modeli değiştirmek MÜMKÜN DEĞİL. Ayrıca CLAUDE.md §6:
#   "Otomatik A/B kampanyalarında hâlâ env + tam restart kullan: koşu
#   boyunca anahtarın değişmediğinden emin olmak deney disiplininin parçası."
#
# DÖNÜŞÜMLÜ (§4): A,B,A,B,... — sim kayması iki kolu eşit etkilesin.
# Bir kolun hepsini arka arkaya koşmak YASAK.
#
# ⚠ Sim ZATEN AYAKTA olmalı (araclar/sim.py ile). Bu script simi kurmaz;
#   her koşu `kosu.py` içindeki `_yeni_gorev()` ile görevi baştan alır.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; A="${2:?model A}"; B="${3:?model B}"
TEKRAR="${4:-5}"; SURE="${5:-150}"

echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"

for ((i=1; i<=TEKRAR; i++)); do
  for M in "$A" "$B"; do
    ETIKET="${M}__t${i}"
    echo "=== [$(date +%H:%M:%S)] KOŞU $ETIKET ==="
    DOW_MODEL="$M" DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
      timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
      >> "logs/$AD.log" 2>&1
    echo "    bitti (çıkış $?)"
  done
done
echo "=== KAMPANYA $AD BİTTİ ($(date +%H:%M)) ==="
