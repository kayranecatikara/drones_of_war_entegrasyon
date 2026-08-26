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
    # ⭐ EMNİYET: sağ kalan kaçamak süreci bir sonraki koşuya SIZMASIN.
    #   (Bu betikte alt kabuk yok, `$!` python'un kendisi -> kill çalışır.
    #    Kardeş betik kacamak_ab.sh'de alt kabuğa sarılmıştı ve 5 süreç
    #    aynı anda köprüye yazıp kampanyayı geçersiz kıldı — OC_BAYAT.)
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
