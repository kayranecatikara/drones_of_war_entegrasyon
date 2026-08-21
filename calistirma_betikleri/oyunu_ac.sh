#!/usr/bin/env bash
# =============================================================================
# DRONES OF WAR — Ubuntu'da başlatma (GE-Proton + umu-launcher)
# -----------------------------------------------------------------------------
# NEDEN BU YOL: oyun UE5 + Direct3D 12 (D3D12Core.dll Agility SDK). D3D12'yi
# Linux'ta çalıştıran tek olgun katman VKD3D-Proton; o da Proton'un içinde
# hazır gelir. Düz Wine'ın wined3d'si D3D12 desteklemez.
# sudo GEREKMEZ: her şey ~/ altında.
# =============================================================================
set -u
KOK="/home/kayra/projects/drones_of_war_entegrasyon"
OYUN="$KOK/oyun/Drones of War Teknofest/DronesOfWar.exe"
export PROTONPATH="$HOME/.local/share/Steam/compatibilitytools.d/GE-Proton11-5-x86_64"
export WINEPREFIX="$KOK/calistirma/prefix"
export STEAM_COMPAT_DATA_PATH="$WINEPREFIX"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.local/share/Steam"
export GAMEID="0"                       # umu: Steam'de olmayan oyun
export STORE="none"
# NVIDIA: gölgelendirici önbelleği (ilk açılışta takılmayı azaltır)
export __GL_SHADER_DISK_CACHE=1
export __GL_SHADER_DISK_CACHE_PATH="$KOK/calistirma/shadercache"
export DXVK_STATE_CACHE_PATH="$KOK/calistirma/shadercache"
export VKD3D_SHADER_CACHE_PATH="$KOK/calistirma/shadercache"
mkdir -p "$WINEPREFIX" "$__GL_SHADER_DISK_CACHE_PATH"

# Pencere modunda aç: ekran yakalama ve iki-ekran çalışma için şart.
# (Tam ekran, X11'de yakalamayı ve alt+tab'ı zorlaştırır.)
ARGS="${ARGS:--fullscreen -ResX=1920 -ResY=1080}"

cd "$KOK/oyun/Drones of War Teknofest" || exit 1
exec python3 "$KOK/calistirma/umu/umu-run" "$OYUN" $ARGS
