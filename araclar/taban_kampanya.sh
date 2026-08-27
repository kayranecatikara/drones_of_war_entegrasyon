#!/usr/bin/env bash
# =============================================================================
# TABAN KAMPANYASI — A/B YOK, sistemin BUGUNKU VARSAYILAN hali olculur
#   araclar/taban_kampanya.sh <ad> <tekrar> <sure_s>
#   her tekrarda 2 kosu: duz, kademeli  ->  tekrar=16 ise 32 kosu
#
# AMAC (2026-08-28 gecesi): terminal teshisi 5 iskayla kurulamadi. Bu kampanya
# tek bir seyi hedefler: YETERLI ISKA ORNEKLEMI (>=10) ve n=32'de gercek
# isabet orani. A/B yok, cunku soru "hangi ayar daha iyi" degil, "bu sistem
# neyi, ne siklikta kaciriyor".
#
# ⭐ AYARLAR: HICBIR env override YOK — kodun varsayilani ne ise o kosar.
#   K1 (HZ2): yakala 15 / det 10 kazandi  -> varsayilan zaten bu
#   K2 (ISP1): O-M kapali kazandi/berabere -> varsayilan zaten kapali
#   talon_v3                               -> varsayilan zaten bu
#   Yani bu kampanya, gecenin sonunda "en iyi" diye onerilecek halin ta kendisi.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; TEKRAR="${2:-16}"; SURE="${3:-150}"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"

echo "=== TABAN KAMPANYASI $AD ==="
echo "    kosu   : $((TEKRAR*2))  (duz + kademeli, donusumlu)"
echo "    ayar   : KODUN VARSAYILANI (env override YOK)"
python3 -c "
import sys; sys.path.insert(0,'.')
from dow.ayarlar import Ayar
print('    -> GORUS_ISP=%s  YAKALA=%s  DET_HZ=%s' % (Ayar.GORUS_ISP, Ayar.PANEL_YAKALA_HZ, Ayar.GORSEL_DET_HZ))
from dow.gorus.dedektor import MODEL_YOLU
print('    -> model %s' % MODEL_YOLU)"
date

# ⛔⛔ DUSEN KOSUYU TELAFI ET — 2026-08-28'de yasandi ve genellememi curuttu.
#   RESTART4 olcumu "TEK kosu.py sureci icinde 4 kosu, oyun restart'i yok"
#   demisti; orada kosular arasi gorev gecisini kosu.py'nin kendisi yapiyor.
#   Bu betik ise HER KOSU ICIN AYRI SUREC aciyor ve aralarinda yalniz sim.py
#   kosuyor — o da her zaman ucabilir bir arac birakmiyor. TABAN32'nin 7.
#   kosusu `ihlal=drone_yok` ile dustu (2 tik, 0.0 s).
#   Cozum: kosu dustuyse (drone_yok / tespit yok) OYUNU KOMPLE yeniden kur ve
#   AYNI etiketi bir kez daha kos. Ikinci denemede de duserse kampanyayi
#   durdur — sessizce eksik n ile devam etmek kollari bozar (S5.9).
_kosu_dustu() {   # $1 = kosu dizini
  local oz="$1/ozet.csv" cik="$1/k01/cikarim.csv"
  [ -f "$oz" ] || return 0
  awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR==2{
    if ($h["ihlal"] ~ /drone_yok/ || $h["sure"]+0 < 1.0) exit 0; else exit 1}' "$oz" && return 0
  [ -f "$cik" ] || return 0
  [ "$(awk -F, 'NR>1 && $3==1' "$cik" | wc -l)" -eq 0 ] && return 0
  return 1
}

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
    I=$((I+1))
    ETIKET="$(printf '%02d' $I)_T__${SEN}"
    echo "=== [$(date +%H:%M:%S)] KOSU $I/$((TEKRAR*2)) — $ETIKET ==="
    pkill -f "araclar/manevra.py" 2>/dev/null
    _kopru_notr
    if [ "$SEN" = "kademeli" ]; then
      pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null
      sleep 4
    fi
    for DENEME in 1 2; do
      if [ "$DENEME" = "2" ]; then
        echo "    ⚠ kosu dustu — OYUN KOMPLE yeniden kuruluyor, tekrar deneniyor"
        rm -rf "logs/$AD/$ETIKET"
        pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null
        sleep 4
      fi
      if ! python3 araclar/sim.py >> "logs/$AD.sim.log" 2>&1; then
        echo "⛔ SIM HAZIRLANAMADI — durduruldu"; exit 1
      fi
      DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit \
        timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
        >> "logs/$AD.log" 2>&1 &
      KOSU_PID=$!
      HEDEF_PID=""
      if [ "$SEN" = "kademeli" ]; then
        python3 araclar/manevra.py kademeli --ad "$AD/$ETIKET" >> "logs/$AD.hedef.log" 2>&1 &
        HEDEF_PID=$!
      fi
      wait $KOSU_PID
      [ -n "$HEDEF_PID" ] && { kill "$HEDEF_PID" 2>/dev/null; wait "$HEDEF_PID" 2>/dev/null; }
      pkill -f "araclar/manevra.py" 2>/dev/null
      _kosu_dustu "logs/$AD/$ETIKET" || break
      [ "$DENEME" = "2" ] && { echo "⛔⛔ $ETIKET IKI KEZ DUSTU — durduruldu"; exit 1; }
    done
    [ -f "logs/$AD/$ETIKET/ozet.csv" ] && awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR==2{
      printf("    SONUC isabet=%s enyakin=%s sure=%s tespit%%=%s\n",
             $h["isabet"],$h["en_yakin_m"],$h["sure"],$h["gorsel_tespit_yuzde"])}' "logs/$AD/$ETIKET/ozet.csv"
  done
done
_kopru_notr
echo "=== KAMPANYA $AD BITTI ($(date +%H:%M)) ==="
