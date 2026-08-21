#!/usr/bin/env bash
# Oyunu açar ve menüleri geçip göreve sokar; TCP 12345 açılınca döner.
# Adımlar (V5.0.0): PRESS FOR START -> FLY -> E (drone spawn)
set -u
export DISPLAY=:1
KOK="/home/kayra/projects/drones_of_war_entegrasyon"
cd "$KOK/calistirma"

if ! pgrep -f "DronesOfWar-Win64" >/dev/null; then
  echo "[1/5] oyun başlatılıyor..."
  nohup ./oyunu_ac.sh > oyun_calisma.log 2>&1 &
  for i in $(seq 1 90); do pgrep -f "DronesOfWar-Win64" >/dev/null && break; sleep 2; done
  sleep 25   # gölgelendirici derleme + menü
fi

W=""
for i in $(seq 1 30); do
  W=$(xdotool search --name "^DronesOfWar" 2>/dev/null | head -1)
  [ -n "$W" ] && break; sleep 2
done
[ -z "$W" ] && { echo "HATA: pencere bulunamadı"; exit 1; }
echo "[2/5] pencere=$W -> 2. ekrana (HDMI-0, 0,0)"
xdotool windowmove "$W" 0 0 2>/dev/null
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 2

echo "[3/5] PRESS FOR START"
xdotool mousemove 960 866 click 1; sleep 4
echo "[4/5] FLY"
xdotool mousemove 188 477 click 1; sleep 8
echo "[5/5] E — drone spawn"
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1
xdotool key --window "$W" e; sleep 4

for i in $(seq 1 20); do
  ss -tln | grep -q 12345 && { echo "✅ TCP 12345 AÇIK — göreve girildi"; exit 0; }
  sleep 1
done
echo "⚠ port açılmadı; ekran görüntüsüne bak"
exit 2
