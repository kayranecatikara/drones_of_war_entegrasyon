#!/usr/bin/env bash
# =============================================================================
# KARMA KAMPANYA — hedef her koşuda BAŞKA davransın, sistemin bugünkü hâli
#                  bütün senaryolarda birden ölçülsün
#   araclar/karma_kampanya.sh <ad> <kol1,kol2,...> <sure_s>
#
# KULLANICI (2026-08-27): "bu 10 koşuda hedef araca farklı rotalar çizdir...
#   bazısında kare bazısında daire. drone hedef araca görsel güdüm ile
#   yaklaşırken hedef araca manevra yaptırıp droneun bu manevraya karşı
#   verdiği reaksiyona bakalım."
#
# KOLLAR:
#   taban     -> hiç devralma YOK; hedef kendi rotasında (KIYAS ÇİZGİSİ, §3.3)
#   kademeli  -> manevra.py kademeli  yakında HAFİF, GÖRSEL fazda SERT manevra
#
# ⛔ `kare` ve `daire` KOLLARI SİLİNDİ (2026-08-27, kullanıcı kararı): desen
#    senaryoları gerçekçi değildi ve oyun tarafında hedefin parçalarını
#    koparıyordu. `araclar/desen.py` ve UE4SS modundaki desen kodu da
#    çıkarıldı. Ölçülen sonuçlar `docs/GORSEL_GUDUM_SICILI.md`de duruyor.
#
# ⛔ `taban` HER KAMPANYADA koşulur: hedef hiç kaçmazken ne olduğunu bilmeden
#    kaçarken çıkan sonuç yorumlanamaz.
# ⛔ SIRA DÖNÜŞÜMLÜDÜR (§4): kollar sırayla gider, bir kolun hepsi arka arkaya
#    koşulmaz — yoksa sim kayması tek kola yazılır.
# ⛔ HER KOŞUDAN ÖNCE OYUN KOMPLE YENİDEN BAŞLAR: UE4SS modu hedefi spline
#    rotasından koparınca kirlilik birikiyor ve görev restart'ı temizlemiyor
#    (ölçüldü: sade koşuda bile en_yakin 1803 m). Bedeli ~2.5 dk/koşu.
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
export DISPLAY=:1

AD="${1:?kampanya adi}"; KOLLAR="${2:?kol listesi}"; SURE="${3:-150}"
echo -n hibrit > .gudum_kipi
mkdir -p "logs/$AD"
IFS=',' read -ra LISTE <<< "$KOLLAR"

echo "=== KARMA KAMPANYA $AD ==="
echo "    kol sirasi : ${LISTE[*]}"
echo "    kosu sayisi: ${#LISTE[@]}   (her biri ${SURE}s kayit + ~2.5 dk kurulum)"
echo "    model      : talon_v3 (TEK model; v5 2026-08-27'de silindi)"
echo "    O-M        : ACIK (DOW_GORUS_ISP=1) — olculmus en iyi hal"
date

I=0
for D in "${LISTE[@]}"; do
  I=$((I+1))
  ETIKET="$(printf '%02d' $I)_${D}"
  echo "=== [$(date +%H:%M:%S)] KOSU $I/${#LISTE[@]} — $ETIKET ==="

  # --- hedefi suren onceki surec kalmasin, kopru notr olsun ---
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
    timeout 900 python3 araclar/kosu.py "$AD/$ETIKET" 1 "$SURE" \
    >> "logs/$AD.log" 2>&1 &
  KOSU_PID=$!

  # --- kol adina gore DOGRU hedef surucusunu baslat ---
  HEDEF_PID=""
  case "$D" in
    kademeli)
      python3 araclar/manevra.py kademeli --ad "$AD/$ETIKET" \
        >> "logs/$AD.hedef.log" 2>&1 &
      HEDEF_PID=$! ;;
    taban)
      : ;;                      # devralma YOK — hedef kendi rotasında
    *)
      echo "⛔ BILINMEYEN KOL: $D"; kill $KOSU_PID 2>/dev/null; exit 1 ;;
  esac

  wait $KOSU_PID
  [ -n "$HEDEF_PID" ] && { kill "$HEDEF_PID" 2>/dev/null; wait "$HEDEF_PID" 2>/dev/null; }
  pkill -f "araclar/manevra.py" 2>/dev/null

  # ⛔ KOR KOSU KAPISI — hic tespit yoksa kampanyayi ORADA durdur
  SON="logs/$AD/$ETIKET/k01/cikarim.csv"
  if [ -f "$SON" ]; then
    T=$(awk -F, 'NR>1 && $3==1' "$SON" | wc -l)
    if [ "$T" -eq 0 ]; then
      echo "⛔⛔ KOR KOSU: $ETIKET icinde HIC TESPIT YOK — oyun 'press E' durumunda olabilir."
      echo "=== KAMPANYA $AD DURDURULDU ==="; exit 1
    fi
  fi
  echo "    bitti  ($(date +%H:%M:%S))"
done

echo "=== KAMPANYA $AD BITTI ($(date +%H:%M)) — kosu dizini: $(ls logs/$AD | grep -c '^[0-9]') ==="
