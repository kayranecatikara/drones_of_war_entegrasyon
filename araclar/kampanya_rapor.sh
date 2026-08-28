#!/usr/bin/env bash
# =============================================================================
# KAMPANYA RAPORU — bir kampanyanin BUTUN zorunlu analizlerini tek komutta
#   araclar/kampanya_rapor.sh logs/HZ2
#
# CLAUDE.md'nin rapor oncesi zorunlu adimlarini SIRAYLA kosar, boylece
# gece boyunca hicbiri atlanmaz:
#   1. kol ici ozet + gecerlilik esleri (§5.2, §5.9)   -> hz_ozet.py
#   2. VURUS SINIFI KONTROLLU/SANS (§4)                -> vurus_kalitesi.py
#   3. menzil kalibrasyonu (olcum borcu)               -> menzil_kalibre.py
#   4. gecerlilik: ihlal sutunu (§4)
# =============================================================================
set -u
cd /home/kayra/projects/drones_of_war_entegrasyon || exit 1
D="${1:?kampanya dizini, or. logs/HZ2}"

echo
echo "##############################################################################"
echo "#  KAMPANYA RAPORU — $D"
echo "##############################################################################"

python3 araclar/hz_ozet.py "$D" 2>&1

echo
echo "------------------------------------------------------------------------------"
python3 araclar/vurus_kalitesi.py "$D" 2>&1 | sed -n '2,40p'

echo
echo "------------------------------------------------------------------------------"
python3 araclar/menzil_kalibre.py "$D" 2>&1

echo
echo "------------------------------------------------------------------------------"
echo "  GECERLILIK (§4 — ihlal sutunu)"
python3 - "$D" <<'PYEOF'
import csv, glob, os, sys
d = sys.argv[1]
kotu = tot = 0
for oz in sorted(glob.glob(os.path.join(d, "*", "ozet.csv"))):
    for r in csv.DictReader(open(oz)):
        tot += 1
        i = (r.get("ihlal") or "-").strip()
        if i not in ("-", "", "0"):
            kotu += 1
            print("    ⚠ %-24s ihlal=%s" % (os.path.basename(os.path.dirname(oz)), i))
print("    ihlalli kosu: %d / %d" % (kotu, tot))
PYEOF
echo "##############################################################################"
