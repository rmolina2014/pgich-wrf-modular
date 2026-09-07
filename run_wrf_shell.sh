#!/bin/bash
# Shell-script runner for wrf.exe — launched via setsid so bash is the
# direct parent of wrf.exe (avoids the SIGSEGV that occurs when Python
# is the parent process of wrf.exe with obs nudging).
#
# Usage:
#   setsid bash run_wrf_shell.sh <mode> <run_dir> <namelist> <log_file> <status_file> [max_retries]
#
# Arguments:
#   mode        = "nudged" or "control"
#   run_dir     = WRF run directory (contains wrf.exe, wrfinput, wrfbdy)
#   namelist    = path to namelist.input to copy into run_dir
#   log_file    = path to write combined stdout/stderr log
#   status_file = path to write final status marker ("OK" or "FAIL")
#   max_retries = number of retries on failure (default: 5)
set -euo pipefail

MODE="${1:?mode required (nudged|control)}"
RUN_DIR="${2:?run_dir required}"
NAMELIST="${3:?namelist path required}"
LOG_FILE="${4:?log_file required}"
STATUS_FILE="${5:?status_file required}"
MAX_RETRIES="${6:-5}"

WRF_ENV="${WRF_ENV:-/home/roberto/opencode/wrf/WRF-4.0/run/env.bash}"

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }

log "=== wrf_shell.sh mode=$MODE run_dir=$RUN_DIR ==="
log "namelist=$NAMELIST max_retries=$MAX_RETRIES"

# Load WRF environment (opcional: solo si existe; WRF enlaza libs del sistema)
if [ -f "$WRF_ENV" ]; then
    # shellcheck disable=SC1090
    source "$WRF_ENV" >> "$LOG_FILE" 2>&1
fi
export OMP_NUM_THREADS=1

# Copy namelist
cp "$NAMELIST" "$RUN_DIR/namelist.input"
log "Namelist copied to $RUN_DIR/namelist.input"

cd "$RUN_DIR"

INTENTO=1
while [ "$INTENTO" -le "$((MAX_RETRIES + 1))" ]; do
    # Clean previous outputs
    rm -f wrfout_d01_* rsl.* 2>/dev/null || true
    log "Intento $INTENTO/$((MAX_RETRIES + 1)): limpiando wrfout/rsl"

    log "Iniciando wrf.exe ($MODE)..."
    START=$(date +%s)

    # Run wrf.exe — bash is the direct parent here (via setsid)
    ./wrf.exe >> "$LOG_FILE" 2>&1
    RC=$?

    END=$(date +%s)
    ELAPSED=$(( END - START ))
    ELAPSED_FMT=$(printf '%02d:%02d:%02d' $((ELAPSED/3600)) $(( (ELAPSED%3600)/60 )) $((ELAPSED%60)))
    log "wrf.exe finalizo con codigo $RC en $ELAPSED_FMT"

    # Check for SUCCESS in rsl.out.0000
    if [ -f rsl.out.0000 ] && grep -q "SUCCESS COMPLETE WRF" rsl.out.0000; then
        log "SUCCESS COMPLETE WRF encontrado en rsl.out.0000"
        echo "OK" > "$STATUS_FILE"
        log "=== RESULTADO: OK ($MODE, intento $INTENTO, $ELAPSED_FMT) ==="
        exit 0
    fi

    if [ "$INTENTO" -gt "$MAX_RETRIES" ]; then
        log "=== RESULTADO: FAIL ($MODE, agotados $((MAX_RETRIES + 1)) intentos) ==="
        echo "FAIL" > "$STATUS_FILE"
        exit 1
    fi

    log "Intento $INTENTO fallo (RC=$RC). Reintentando..."
    INTENTO=$((INTENTO + 1))
done
