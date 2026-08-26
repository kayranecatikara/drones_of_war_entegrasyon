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

# ⭐ UE4SS (2026-08-26) — hedef İHA'yı elle/betikle sürebilmek için.
#   `dwmapi.dll` UE4SS'in proxy'sidir: oyun onu yükleyince UE4SS devreye
#   girer ve ue4ss/Mods altındaki modları çalıştırır. Wine varsayılan olarak
#   KENDİ dwmapi'sini yükler, o yüzden "native önce, sonra builtin" demek
#   ZORUNLU — bu satır olmadan mod yükleyici SESSİZCE hiç çalışmaz
#   (oyun modsuz da sorunsuz açılır, hata vermez).
#   Yüklendiğini anlamanın tek yolu: ue4ss/UE4SS.log zaman damgası.
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-dwmapi=n,b}"
#   ⚠ ÖLÇÜLDÜ 2026-08-26: Proton, gelen WINEDLLOVERRIDES'i KENDİ listesiyle
#     EZİYOR (süreç ortamında yalnız Proton'un kendi girdileri görüldü).
#     Bu yüzden üç yol birden kuruluyor:
#       1. WINEDLLOVERRIDES        (Proton dışı yollar için)
#       2. PROTON_DLL_OVERRIDES    (Proton bunu KENDİ listesine EKLER)
#       3. önek kayıt defteri      (calistirma/prefix/pfx/user.reg ->
#          AppDefaults\DronesOfWar-Win64-Shipping.exe\DllOverrides)
#     Üçüncüsü env'den bağımsız ve kalıcıdır; asıl güvence odur.
export PROTON_DLL_OVERRIDES="${PROTON_DLL_OVERRIDES:-dwmapi=n,b}"

# Pencere modunda aç: ekran yakalama ve iki-ekran çalışma için şart.
# (Tam ekran, X11'de yakalamayı ve alt+tab'ı zorlaştırır.)
ARGS="${ARGS:--fullscreen -ResX=1920 -ResY=1080}"

cd "$KOK/oyun/Drones of War Teknofest" || exit 1
exec python3 "$KOK/calistirma/umu/umu-run" "$OYUN" $ARGS
