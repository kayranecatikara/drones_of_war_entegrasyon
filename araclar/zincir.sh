#!/usr/bin/env bash
# Birbirinden BAĞIMSIZ A/B bloklarını sırayla koş (her biri kendi içinde
# dönüşümlü). Bloklar arası sim hazırlığı blok.sh içinde yapılır.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
while pgrep -f "tarama.p[y]" >/dev/null; do sleep 20; done
for spec in "$@"; do
  IFS='|' read -r ad alan degerler tekrar sure <<< "$spec"
  echo "=== ZİNCİR: $ad başlıyor $(date +%H:%M) ==="
  ./araclar/blok.sh "$ad" "$alan" "$degerler" "$tekrar" "$sure"
done
echo "=== ZİNCİR BİTTİ $(date +%H:%M) ==="
