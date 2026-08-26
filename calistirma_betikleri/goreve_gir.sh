#!/usr/bin/env bash
# =============================================================================
# DoW: oyunu aç, menüleri geç, göreve gir. TCP 12345 açılınca döner.
# Öğrenilenler (2026-08-21):
#  * Kenarlıksız tam ekran ŞART — pencere süslemesi kadrajı kırpıp kamera iç
#    parametrelerini bozuyor ve dedektöre sahte kenar veriyor.
#  * Pencere 2. ekrana (HDMI-0, 0,0) alınır ki terminal/tarayıcı örtmesin;
#    örttüğünde ekran yakalama YANLIŞ pencereyi çeker (bir kez yaşandı).
#  * fullscreen bayrağı konumu geri alıyor -> önce kaldır, taşı, sonra ekle.
# =============================================================================
set -u
export DISPLAY="${DISPLAY:-:0}"
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOK/calistirma"

# 0) çalışan örneği kapat (desen köşeli parantezle kırık: kendi kabuğunu öldürme)
if pgrep -f "DronesOfWa[r]-Win64" >/dev/null; then
  echo "[0/6] eski örnek kapatılıyor..."; pkill -f "DronesOfWa[r]"; sleep 5
fi

echo "[1/6] oyun başlatılıyor..."
nohup "$KOK/calistirma_betikleri/oyunu_ac.sh" > oyun_calisma.log 2>&1 &
for i in $(seq 1 120); do pgrep -f "DronesOfWa[r]-Win64" >/dev/null && break; sleep 2; done
sleep 22   # gölgelendirici derleme + menü

W=""
for i in $(seq 1 30); do
  W=$(xdotool search --name "^DronesOfWar" 2>/dev/null | head -1); [ -n "$W" ] && break; sleep 2
done
[ -z "$W" ] && { echo "HATA: pencere yok"; exit 1; }

echo "[2/6] pencere -> 2. ekran, kenarlıksız tam ekran"
wmctrl -i -r "$W" -b remove,fullscreen 2>/dev/null; sleep 1
xdotool windowmove "$W" 0 0 2>/dev/null; sleep 1
wmctrl -i -r "$W" -b add,fullscreen 2>/dev/null; sleep 2
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1

echo "[3/6] örten pencereleri küçült"
for ad in "Google Chrome" "gedit"; do
  ID=$(xdotool search --name "$ad" 2>/dev/null | tail -1)
  [ -n "$ID" ] && xdotool windowminimize "$ID" 2>/dev/null
done
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1

echo "[4/6] PRESS FOR START"; xdotool mousemove 960 890 click 1; sleep 5
echo "[5/6] FLY";            xdotool mousemove 188 477 click 1; sleep 9
echo "[6/6] E — drone spawn"
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1
xdotool key --window "$W" e; sleep 5

for i in $(seq 1 25); do
  ss -tln | grep -q 12345 && { echo "✅ TCP 12345 AÇIK — göreve girildi"; exit 0; }
  sleep 1
done
echo "⚠ port açılmadı"; exit 2
