#!/usr/bin/env bash
set -euo pipefail

# ===== Configura estas rutas según tu entorno =====
SRC="/home/user/test_ocr/E54311224013702R001395301400.PDF"
ENDPOINT="http://localhost:8001/ocr"
OUT_DIR="$HOME/test_ocr"
REPEATS=3
# ==================================================

# Crea el directorio de salida si no existe
mkdir -p "$OUT_DIR"

# Escenarios (usa arrays paralelos para compatibilidad amplia de bash)
PREFS=("ocr_curl_2GB_10x" "ocr_curl_4GB_5x" "ocr_curl_8GB_2x")
VRAMS=(2048 4096 8192)
CONCS=(10   5    2)

# Cabecera
printf "%-3s %-6s %-4s %-18s %-60s %s\n" "Run" "VRAM" "Conc" "Pref" "FileName" "Time"

# Recorre escenarios
for idx in "${!PREFS[@]}"; do
  pref="${PREFS[$idx]}"
  vram="${VRAMS[$idx]}"
  conc="${CONCS[$idx]}"

  for run in $(seq 1 "$REPEATS"); do
    out="${OUT_DIR}/${pref}_${run}.zip"

    start=$(date +%s)
    # -f: falla si HTTP != 2xx  -S: muestra errores  -s: silencioso
    if curl -fSs -X POST "$ENDPOINT" \
        -F "file=@${SRC}" \
        -F "vram_limit=${vram}" \
        -F "concurrency=${conc}" \
        -F "use_gpu=true" \
        -F "device=cuda" \
        -F "backend=pipeline" \
        --output "$out"; then
      end=$(date +%s)
      runtime=$((end - start))
    else
      # En caso de error HTTP, marcamos tiempo -1
      runtime=-1
    fi

    # Imprime la fila inmediatamente (salida "dinámica")
    printf "%-3s %-6s %-4s %-18s %-60s %s\n" "$run" "$vram" "$conc" "$pref" "$out" "$runtime"
  done
done