#!/usr/bin/env bash
# =============================================================================
#  TALON WEB KONTROL MODUNU OYUNA KUR
# -----------------------------------------------------------------------------
#  Panelden hedef İHA'yı sürmek için oyun tarafında UE4SS modu gerekir.
#  Zincir:  panel -> /api/talon -> /tmp/talon_kopru.txt -> BU MOD -> Talon
#
#  Mod kaynağı repoda durur (dow/ue4ss_modlari/), bu betik onu oyunun
#  ue4ss/Mods klasörüne kopyalar ve mods.txt'ye kaydeder.
#
#  ⚠ ÖNKOŞUL: oyunda UE4SS'in kendisi kurulu olmalı (dwmapi.dll proxy +
#     MSVCP140_CODECVT_IDS.dll + WINEDLLOVERRIDES="dwmapi=n,b").
#     Yüklendiğini anlamanın tek yolu: ue4ss/UE4SS.log zaman damgası.
# =============================================================================
set -u
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KAYNAK="$KOK/dow/ue4ss_modlari/TalonWebControl"

# Oyun klasörü: önce repo içi, sonra masaüstü
for aday in "$KOK/oyun/Drones of War Teknofest" "$HOME/Desktop/Drones of War Teknofest"; do
  if [ -d "$aday/DronesOfWar/Binaries/Win64/ue4ss/Mods" ]; then OYUN="$aday"; break; fi
done
if [ -z "${OYUN:-}" ]; then
  echo "HATA: oyunun ue4ss/Mods klasörü bulunamadı."
  echo "  bakılan yerler:"
  echo "    $KOK/oyun/Drones of War Teknofest"
  echo "    $HOME/Desktop/Drones of War Teknofest"
  exit 1
fi

MODS="$OYUN/DronesOfWar/Binaries/Win64/ue4ss/Mods"
echo "oyun     : $OYUN"
echo "hedef    : $MODS/TalonWebControl"

mkdir -p "$MODS/TalonWebControl/Scripts"
cp "$KAYNAK/Scripts/main.lua" "$MODS/TalonWebControl/Scripts/main.lua"
: > "$MODS/TalonWebControl/enabled.txt"

# mods.txt'ye kaydet (zaten varsa tekrar ekleme; Keybinds EN SONDA kalmalı)
MODS_TXT="$MODS/mods.txt"
if [ -f "$MODS_TXT" ] && ! grep -q "^TalonWebControl" "$MODS_TXT"; then
  python3 - "$MODS_TXT" <<'PY'
import sys, io
p = sys.argv[1]
satirlar = [l.rstrip('\r\n') for l in io.open(p, encoding='utf-8', errors='replace')]
cikti = []
konuldu = False
for l in satirlar:
    if not konuldu and l.startswith(';') and 'Built-in' in l:
        cikti.append('TalonWebControl : 1'); cikti.append(''); konuldu = True
    cikti.append(l)
if not konuldu:
    cikti.append('TalonWebControl : 1')
io.open(p, 'w', encoding='utf-8', newline='\r\n').write('\n'.join(cikti) + '\n')
PY
  echo "mods.txt : TalonWebControl eklendi"
else
  echo "mods.txt : zaten kayıtlı"
fi
echo "TAMAM — oyunu yeniden başlat, sonra panelden 🎯 Talon Kontrol."
