#!/usr/bin/env bash
# =============================================================================
# KAÇAMAK KAMPANYASI — güdümü MANEVRA altında sına
#   araclar/kacamak_kampanya.sh <ad> <kacamak1,kacamak2,...> <tekrar> <sure_s>
#
# Örn: araclar/kacamak_kampanya.sh KC1 yok,yatay,dikey_yukari 4 150
#
# ⛔ `yok` KOLU HER KAMPANYADA KOŞULUR (CLAUDE.md §3.3): kaçamaksız isabet
#    oranını bilmeden kaçamaklı sonuç yorumlanamaz.
#
# DÖNÜŞÜMLÜ (§4): tur tur gidilir — her turda TÜM kaçamak türleri sırayla.
#    Bir türün hepsini arka arkaya koşmak YASAK (sim kayması kolları
#    eşit etkilesin).
#
# HER KOŞU AYRI SÜREÇ: kosu.py + kacamak.py birlikte kalkar, koşu bitince
#    ikisi de iner. Böylece kaçamak tetiği koşular arasında sızmaz.
#
# ⚠ ÖNKOŞUL: oyunda UE4SS + TalonWebControl modu KURULU olmalı
#   (MANUEL_KONTROL.md §4). Kurulu değilse köprüye yazılır, hedef DUYMAZ ve
#   kaçamak sessizce hiç olmaz -> koşular GEÇERSİZ olur. kacamak.py bunu
#   tetik sonrası irtifa değişimiyle DOĞRULAR ve bağırır.
#
# ⚠ Sim ZATEN AYAKTA olmalı (araclar/sim.py). Bu betik simi kurmaz.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; TURLER="${2:?kacamak turleri, virgullu}"
TEKRAR="${3:-4}"; SURE="${4:-150}"

echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"
IFS=',' read -ra LISTE <<< "$TURLER"

echo "=== KAÇAMAK KAMPANYASI $AD ==="
echo "    türler : ${LISTE[*]}"
echo "    tekrar : $TEKRAR  ->  toplam $(( ${#LISTE[@]} * TEKRAR )) koşu"
echo "    süre   : $SURE s/koşu"
date

for ((i=1; i<=TEKRAR; i++)); do
  for K in "${LISTE[@]}"; do
    ETIKET="${K}__t${i}"
    echo "=== [$(date +%H:%M:%S)] KOŞU $ETIKET ==="

    # kaçamak tetikleyicisi ÖNCE kalksın (paneli bekler)
    DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
      timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
      >> "logs/$AD.log" 2>&1 &
    KOSU_PID=$!

    sleep 2
    python3 araclar/kacamak.py "$K" --ad "$AD/$ETIKET" \
      >> "logs/$AD.kacamak.log" 2>&1 &
    KAC_PID=$!

    wait $KOSU_PID
    kill $KAC_PID 2>/dev/null
    wait $KAC_PID 2>/dev/null
    echo "    bitti"
  done
done
echo "=== KAMPANYA $AD BİTTİ ($(date +%H:%M)) ==="
