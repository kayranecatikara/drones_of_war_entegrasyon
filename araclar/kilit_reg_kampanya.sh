#!/usr/bin/env bash
# =============================================================================
# KILIT REGULATORU A/B — "sert fren" duzeltmesi (2026-08-28)
#   araclar/kilit_reg_kampanya.sh <ad> <tekrar> <sure_s> [senaryolar]
#
# TEK DEGISKEN: KILIT fazinin HIZ REGULATORU. Kilit esigi (%5), denge
# mesafesi (7.0 m) ve kilit fazinin kendisi IKI KOLDA DA AYNI.
#
#   V1 (kol "1") = bugun ucan sert yasa
#        KFWD 0.35 · IMAX 8 · VMIN 0 · VMAX 28 · SLEW yok
#        -> olculdu: komut tek tikte 28->0 m/s, 139 olayda +18.8 m geri dusus
#   V2 (kol "2") = yumusak regulator (varsayilan)
#        KFWD 0.10 · IMAX 22 · VMIN 12 · VMAX 33 · SLEW 20 m/s^2 + anti-windup
#
# ⚠ TEK FARK ANTI-WINDUP'TA DA VAR: V1 kolunda anti-windup ACIKTIR (kod
#   ayrilmadi). Etkisi yalniz doyumda; V1'in asil imzasi olan BASAMAK FREN
#   SLEW=0 ile birebir korunuyor.
#
# BIRINCIL OLCUT : kilit_saglandi (%5 esigi)
# MEKANIZMA (S5.1): sert_fren sayaci — V2 kolunda 0 OLMALI, degilse
#   regulator devreye girmemistir ve o kosu GECERSIZDIR.
# REGRESYON (S5.10): isabet, erken_temas, en_yakin
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1
AD="${1:?kampanya adi}"; TEKRAR="${2:-6}"; SURE="${3:-150}"
SENARYOLAR="${4:-duz,kademeli}"
IFS="," read -ra SEN_LISTE <<< "$SENARYOLAR"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"

# Kol tanimlari DISARIDAN verilebilir (KOL1/KOL2 ortam degiskeni, bosluklu).
# Verilmezse varsayilan: sert (V1) vs yumusak (V2) regulator kiyasi.
if [ -n "${KOL1:-}" ]; then read -ra V1_ENV <<< "$KOL1"; else
  V1_ENV=(DOW_KILIT_KFWD=0.35 DOW_KILIT_IMAX=8 DOW_KILIT_VMIN=0 DOW_KILIT_VMAX=28 DOW_KILIT_SLEW=0)
fi
if [ -n "${KOL2:-}" ]; then read -ra V2_ENV <<< "$KOL2"; else
  V2_ENV=(DOW_KILIT_KFWD=0.10 DOW_KILIT_IMAX=22 DOW_KILIT_VMIN=12 DOW_KILIT_VMAX=33 DOW_KILIT_SLEW=20)
fi

# ---- UCUS ONCESI KAPI: iki kol gercekten farkli mi cozuluyor? ----
python3 - "${#V1_ENV[@]}" "${V1_ENV[@]}" "${V2_ENV[@]}" <<'PYEOF' || exit 1
import os, subprocess, sys
def oku(kv):
    e = dict(os.environ)
    for x in kv: k, v = x.split("=", 1); e[k] = v
    # ⚠ KAPI, DENENEN HER AYARI BASMALI. 2026-08-28'de kosegen deneyinde
    #   bu liste MENZIL_OLCU'yu icermiyordu ve kapi iki kolu AYNI sanip
    #   kampanyayi bloke edecekti (ya da daha kotusu, fark gormeden gecirecekti).
    c = ("import sys;sys.path.insert(0,'.');from dow.ayarlar import Ayar as A;"
         "from dow.gudum.ibvs import IbvsCfg as I;"
         "print('KFWD=%.2f IMAX=%.0f VMIN=%.0f VMAX=%.0f SLEW=%.0f MENZIL=%.1f "
         "BOYUT%%=%.1f OLCU=%s'"
         "%(A.KILIT_K_FWD,A.KILIT_I_MAX,A.KILIT_V_MIN,A.KILIT_V_MAX,A.KILIT_SLEW,"
         "A.KILIT_MENZIL_M,A.KILIT_BOYUT_YUZDE,I.MENZIL_OLCU))")
    return subprocess.check_output([sys.executable, "-c", c], env=e).decode().strip()
_n = int(sys.argv[1])
v1, v2 = oku(sys.argv[2:2 + _n]), oku(sys.argv[2 + _n:])
print("    V1 -> %s" % v1); print("    V2 -> %s" % v2)
if v1 == v2:
    print("⛔⛔ IKI KOL AYNI COZULUYOR — kampanya BASLATILMADI."); sys.exit(1)
PYEOF

echo "=== KILIT REGULATORU A/B — $AD ==="
echo "    kosu : $((TEKRAR*2*${#SEN_LISTE[@]}))  (V1/V2 donusumlu, ${SEN_LISTE[*]})"
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
    for KOL in 1 2; do
      I=$((I+1))
      if [ "$KOL" = "1" ]; then ENVK=("${V1_ENV[@]}"); else ENVK=("${V2_ENV[@]}"); fi
      ETIKET="$(printf '%02d' $I)_V${KOL}__${SEN}"
      echo "=== [$(date +%H:%M:%S)] KOSU $I/$((TEKRAR*2*${#SEN_LISTE[@]})) — $ETIKET ==="
      pkill -f "araclar/manevra.py" 2>/dev/null
      _kopru_notr
      if [ "$SEN" = "kademeli" ]; then
        pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null; sleep 4
      fi
      for DENEME in 1 2; do
        if [ "$DENEME" = "2" ]; then
          echo "    ⚠ kosu dustu — OYUN yeniden kuruluyor"
          rm -rf "logs/$AD/$ETIKET"
          pkill -f "DronesOfWa[r]" 2>/dev/null; pkill -f "umu-ru[n]" 2>/dev/null; sleep 4
        fi
        if ! python3 araclar/sim.py >> "logs/$AD.sim.log" 2>&1; then
          echo "⛔ SIM HAZIRLANAMADI"; exit 1
        fi
        # ⛔ KOL ENV'I EN SONA: sabit env kol env'ini EZMESIN (2026-08-27 dersi)
        env DOW_GORSEL=1 DOW_DET_GOSTER=1 DOW_KIP=hibrit DOW_KILIT_FAZI=1 "${ENVK[@]}" \
          timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
          >> "logs/$AD.log" 2>&1 &
        KOSU_PID=$!; HEDEF_PID=""
        if [ "$SEN" = "kademeli" ]; then
          python3 araclar/manevra.py kademeli --ad "$AD/$ETIKET" >> "logs/$AD.hedef.log" 2>&1 &
          HEDEF_PID=$!
        fi
        wait $KOSU_PID
        [ -n "$HEDEF_PID" ] && { kill "$HEDEF_PID" 2>/dev/null; wait "$HEDEF_PID" 2>/dev/null; }
        pkill -f "araclar/manevra.py" 2>/dev/null
        _kosu_dustu "logs/$AD/$ETIKET" || break
        [ "$DENEME" = "2" ] && { echo "⛔⛔ $ETIKET IKI KEZ DUSTU"; exit 1; }
      done
      [ -f "logs/$AD/$ETIKET/ozet.csv" ] && awk -F, 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR==2{
        printf("    SONUC kilit=%s en_iyi=%s SERT_FREN=%s isabet=%s enyakin=%s tespit%%=%s\n",
          $h["kilit_saglandi"],$h["kilit_en_iyi_s"],$h["sert_fren"],
          $h["isabet"],$h["en_yakin_m"],$h["gorsel_tespit_yuzde"])}' "logs/$AD/$ETIKET/ozet.csv"
    done
  done
done
_kopru_notr
echo "=== KAMPANYA $AD BITTI ($(date +%H:%M)) ==="
