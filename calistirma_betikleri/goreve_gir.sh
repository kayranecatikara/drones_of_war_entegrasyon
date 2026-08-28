#!/usr/bin/env bash
# =============================================================================
# DoW: oyunu aç, menüleri geç, göreve gir. TCP 12345 açılınca döner.
# Öğrenilenler (2026-08-21):
#  * Kenarlıksız tam ekran ŞART — pencere süslemesi kadrajı kırpıp kamera iç
#    parametrelerini bozuyor ve dedektöre sahte kenar veriyor.
#  * Pencere AOC monitörüne (araclar/ekran.py seçer) alınır; GNOME üst
#    çubuğu yalnız BİRİNCİL monitörde durduğu için kadraj temiz kalır.
#    örttüğünde ekran yakalama YANLIŞ pencereyi çeker (bir kez yaşandı).
#  * fullscreen bayrağı konumu geri alıyor -> önce kaldır, taşı, sonra ekle.
# =============================================================================
set -u
export DISPLAY=:1
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOK/calistirma"

# 0) çalışan örneği kapat (desen köşeli parantezle kırık: kendi kabuğunu öldürme)
if pgrep -f "DronesOfWa[r]-Win64" >/dev/null; then
  echo "[0/6] eski örnek kapatılıyor..."; pkill -f "DronesOfWa[r]"; sleep 5
fi

echo "[1/6] oyun başlatılıyor..."
nohup ./oyunu_ac.sh > oyun_calisma.log 2>&1 &
for i in $(seq 1 120); do pgrep -f "DronesOfWa[r]-Win64" >/dev/null && break; sleep 2; done
sleep 22   # gölgelendirici derleme + menü

W=""
for i in $(seq 1 30); do
  W=$(xdotool search --name "^DronesOfWar" 2>/dev/null | head -1); [ -n "$W" ] && break; sleep 2
done
[ -z "$W" ] && { echo "HATA: pencere yok"; exit 1; }

# ⭐ HEDEF EKRAN OTOMATIK SECILIR (2026-08-28). Eskiden sabit "0 0" yaziyordu
#    (ustteki yorum "HDMI-0, 0,0" diyor -- yazildiginda AOC oradaydi). Ekran
#    duzeni degisince 0,0 dizustu paneli oldu ve oyun GNOME UST CUBUGUNUN
#    ALTINA acildi (0,27): kadrajin ilk 27 satiri cubuk oldu, oyun 27 px
#    kaydi -> CY=540 varsayiminda 2.9 derece dikey sapma. Bir kampanyayi
#    cope atacakti; sadece sayisal kontrol yakaladi.
#    Simdi araclar/ekran.py AOC monitorunu (yoksa birincil OLMAYANI) secer.
#    GNOME cubugu YALNIZ birincilde durur -> sorun kokunden cozulur.
EKRAN=$(python3 "$KOK/araclar/ekran.py" 2>/dev/null | head -1)
KONUM=$(echo "$EKRAN" | grep -oE '\+[0-9]+\+[0-9]+' | head -1)
EX=$(echo "$KONUM" | cut -d+ -f2); EY=$(echo "$KONUM" | cut -d+ -f3)
EX=${EX:-0}; EY=${EY:-0}
echo "[2/6] pencere -> ${EKRAN:-0,0}  (kenarliksiz tam ekran)"
wmctrl -i -r "$W" -b remove,fullscreen 2>/dev/null; sleep 1
xdotool windowmove "$W" "$EX" "$EY" 2>/dev/null; sleep 1
wmctrl -i -r "$W" -b add,fullscreen 2>/dev/null; sleep 2
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1

echo "[3/6] örten pencereleri küçült"
for ad in "Google Chrome" "gedit" "Visual Studio Code" "Code"; do
  ID=$(xdotool search --name "$ad" 2>/dev/null | tail -1)
  [ -n "$ID" ] && xdotool windowminimize "$ID" 2>/dev/null
done
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1

# ⛔⛔ TAZE ACILISTA **IKI** "PRESS FOR START" EKRANI VAR (2026-08-26).
#   Betik tek tiklama yapiyordu ve oyun ana menuye HIC ulasamiyordu:
#     1. ekran: kar/tank baslik ekrani      -> "PRESS FOR START"
#     2. ekran: harita secim ekrani         -> "PRESS FOR START"
#     3. ekran: hangar ana menusu           -> FLY dugmesi
#   Sonuc: sim.py uc denemede de "HAZIRLANAMADI" diyordu; her deneme oyunu
#   bastan aciyordu, yani 6+ dakika bosa gidiyordu. Gorev-sonu kurtarmasinda
#   (PLAY AGAIN yolu) tek ekran cikiyor, o yuzden hata simdiye kadar
#   gizlenmisti -- ancak oyun KOMPLE yeniden baslatilinca ortaya cikti.
#   Care: tiklamayi TEKRARLA ve arada ana menuyu bekle. Fazla tiklama
#   zararsiz (ana menude 960,890 bos alan).
echo "[4/6] PRESS FOR START (x2 — taze acilista iki ekran var)"
# ⚠ Koordinatlar oyunun KENDI kadrajina gore; ekran ofseti (EX,EY) eklenir.
xdotool mousemove $((EX+960)) $((EY+890)) click 1; sleep 5
xdotool mousemove $((EX+960)) $((EY+890)) click 1; sleep 6
echo "[5/6] FLY";            xdotool mousemove $((EX+143)) $((EY+475)) click 1; sleep 9
echo "[6/6] E — drone spawn"
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1
# ⛔ `--window` ILE GONDERILEN TUS OYUNA ULASMIYOR (2026-08-28 olculdu):
#    menuler gecildi, gorev acildi ama "Press E to spawn" ekraninda
#    kalindi ve port acilmadi. UE oyunlari yonlendirilmis tusu degil,
#    ODAKLI pencereye giden GERCEK tusu isliyor.
xdotool windowactivate --sync "$W" 2>/dev/null; sleep 1
xdotool key e

for i in $(seq 1 25); do
  ss -tln | grep -q 12345 && { echo "✅ TCP 12345 AÇIK — göreve girildi"; exit 0; }
  sleep 1
done
echo "⚠ port açılmadı"; exit 2
