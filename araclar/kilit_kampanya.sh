#!/usr/bin/env bash
# =============================================================================
# KILIT FAZI A/B KAMPANYASI — Teknofest sartnamesi 6.1.4
#   araclar/kilit_kampanya.sh <ad> <tekrar> <sure_s> [senaryolar]
#   her tekrarda 2*len(senaryo) kosu:  K,A donusumlu (S4)
#
# NEYI SINIYORUZ (tek degisken):
#   DOW_KILIT_FAZI=0 (K)  gorsel temas -> DOGRUDAN vurusa git  [BUGUNKU HAL]
#   DOW_KILIT_FAZI=1 (A)  gorsel temas -> once ~6 m mesafe tut, hedefi AV
#                         dortgeninde %6 buyuklugunde tut, 10 s pencerede
#                         5 s kilit biriktir, SONRA terminale gec
#
# BIRINCIL OLCUT : kilit_saglandi (A kolunda) — sartname isterini sagladik mi
# IKINCIL        : isabet (iki kolda) — kilit fazi vurusu BOZUYOR mu (S5.10)
#
# S5.1 MEKANIZMA KAPISI: A kolunda `kilit_faz_s` == 0 ise o kosu VERI DEGIL,
#   GECERSIZ kosudur (ozellik hic devreye girmemis demektir).
#
# ⛔ ENV SIRASI: kol degiskeni EN SONA yazilir. 2026-08-27'de tersi yapildi
#   ve sabit env kol env'ini eziyordu; iki kol AYNI kosuyordu (16 ucus bosa
#   gidecekti). Asagida ayrica UCUS ONCESI KAPI var: iki kolun gercekten
#   farkli cozuldugu dogrulanmadan kampanya baslamaz.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; TEKRAR="${2:-4}"; SURE="${3:-150}"
SENARYOLAR="${4:-duz,kademeli}"
IFS="," read -ra SEN_LISTE <<< "$SENARYOLAR"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"

# ---- UCUS ONCESI KAPI: iki kol GERCEKTEN farkli mi? ----
python3 - <<'PYEOF' || exit 1
import os, subprocess, sys
def oku(v):
    e = dict(os.environ); e["DOW_KILIT_FAZI"] = v
    c = ("import sys;sys.path.insert(0,'.');from dow.ayarlar import Ayar;"
         "print(int(Ayar.KILIT_FAZI), Ayar.KILIT_MENZIL_M, Ayar.KILIT_BOYUT_YUZDE)")
    return subprocess.check_output([sys.executable,"-c",c], env=e).decode().strip()
k, a = oku("0"), oku("1")
print("    KAPALI kol -> KILIT_FAZI=%s" % k)
print("    ACIK   kol -> KILIT_FAZI=%s" % a)
if k == a:
    print("⛔⛔ IKI KOL AYNI COZULUYOR — kampanya BASLATILMADI."); sys.exit(1)
PYEOF

echo "=== KILIT FAZI A/B — $AD ==="
echo "    kosu   : $((TEKRAR*2*${#SEN_LISTE[@]}))  (K/A donusumlu, ${SEN_LISTE[*]})"
date

_kosu_dustu() {
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
  for SEN in "${SEN_LISTE[@]}"; do
    for KOL in K A; do                 # donusumlu: sim kaymasi iki kolu esit etkilesin
      I=$((I+1))
      [ "$KOL" = "A" ] && KFZ=1 || KFZ=0
      ETIKET="$(printf '%02d' $I)_${KOL}__${SEN}"
      echo "=== [$(date +%H:%M:%S)] KOSU $I/$((TEKRAR*2*${#SEN_LISTE[@]})) — $ETIKET (KILIT_FAZI=$KFZ) ==="
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
        DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit DOW_KILIT_FAZI=$KFZ \
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
        printf("    SONUC isabet=%s enyakin=%s kilit_saglandi=%s kilit_en_iyi=%s kilit_faz_s=%s tespit%%=%s\n",
               $h["isabet"],$h["en_yakin_m"],$h["kilit_saglandi"],$h["kilit_en_iyi_s"],
               $h["kilit_faz_s"],$h["gorsel_tespit_yuzde"])}' "logs/$AD/$ETIKET/ozet.csv"
    done
  done
done
_kopru_notr
echo "=== KAMPANYA $AD BITTI ($(date +%H:%M)) ==="
