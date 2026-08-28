#!/bin/bash
# Full WRF pipeline runner — launched via setsid from the Streamlit app.
# Runs: real.exe (optional) -> wrf.exe nudged -> wrf.exe control
# All in bash so wrf.exe's parent is always bash (not Python).
#
# Usage:
#   setsid bash run_full_pipeline.sh <args...>
#
# Args (positional):
#   1 = run_dir       (WRF run directory)
#   2 = env_bash      (path to env.bash)
#   3 = namelist      (path to base namelist.input)
#   4 = case_dir      (results case directory)
#   5 = run_real      ("yes" or "no")
#   6 = skip_control  ("yes" or "no")
#   7 = log_file      (path to combined log)
#   8 = status_file   (path to write final status)
set -uo pipefail

RUN_DIR="${1:?run_dir}"
ENV_BASH="${2:?env_bash}"
NAMELIST="${3:?namelist}"
CASE_DIR="${4:?case_dir}"
RUN_REAL="${5:-no}"
SKIP_CONTROL="${6:-no}"
LOG_FILE="${7:?log_file}"
STATUS_FILE="${8:?status_file}"

# Progress file: only script-level lines (no raw wrf.exe dump)
PROGRESS_FILE="$CASE_DIR/wrf_progress.log"
rm -f "$PROGRESS_FILE"

NUDGED_STATUS="$CASE_DIR/.nudged_status"
CONTROL_STATUS="$CASE_DIR/.control_status"

mkdir -p "$CASE_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }
plog() { echo "[$(date '+%H:%M:%S')] $*" >> "$PROGRESS_FILE"; }

log "=== Full pipeline: run_dir=$RUN_DIR ==="
log "run_real=$RUN_REAL skip_control=$SKIP_CONTROL"
plog "Pipeline WRF iniciado (nudged + control)"

# Limpiar el entorno heredado del proceso padre (Streamlit) para que wrf.exe
# corra con un ambiente de librerias limpio y consistente. Sin esto, variables
# como LD_LIBRARY_PATH del servidor pueden cargar librerias incompatibles y
# provocar el SIGSEGV intermitente en el obs nudging.
# (Nota: se inicializa vacio y no se hace unset para no romper 'set -u' al
#  hacer source de env.bash, que referencia ${LD_LIBRARY_PATH}.)
export LD_LIBRARY_PATH=""
unset LD_PRELOAD 2>/dev/null || true
unset OMP_NUM_THREADS OMP_STACKSIZE KMP_STACKSIZE 2>/dev/null || true
# Quitar rutas de conda/anaconda del PATH para evitar librerias/so de python
# que puedan chocar con las de WRF.
export PATH="/usr/local/bin:/usr/bin:/bin"

# Load environment (limpio)
# shellcheck disable=SC1090
source "$ENV_BASH" >> "$LOG_FILE" 2>&1
export OMP_NUM_THREADS=1

log "LD_LIBRARY_PATH tras env.bash: ${LD_LIBRARY_PATH}"
cd "$RUN_DIR"

# --- real.exe (optional) ---
if [ "$RUN_REAL" = "yes" ]; then
    WI="$RUN_DIR/wrfinput_d01"
    WB="$RUN_DIR/wrfbdy_d01"
    if [ -f "$WI" ] && [ -s "$WI" ] && [ -f "$WB" ] && [ -s "$WB" ]; then
        log "wrfinput/wrfbdy ya existen y son validos; se reutilizan (real.exe omitido)"
    else
        log "Ejecutando real.exe..."
        rm -f rsl.* 2>/dev/null || true
        START=$(date +%s)
        ./real.exe >> "$LOG_FILE" 2>&1
        RC=$?
        END=$(date +%s)
        ELAPSED=$(( END - START ))
        ELAPSED_FMT=$(printf '%02d:%02d:%02d' $((ELAPSED/3600)) $(( (ELAPSED%3600)/60 )) $((ELAPSED%60)))
        if [ $RC -ne 0 ] || ! grep -q "SUCCESS COMPLETE REAL_EM INIT" rsl.out.0000 2>/dev/null; then
            log "real.exe FALLO (RC=$RC, tiempo=$ELAPSED_FMT)"
            plog "real.exe FALLO"
            echo "REAL_FAIL" > "$STATUS_FILE"
            exit 1
        fi
        log "real.exe completado en $ELAPSED_FMT"
        plog "real.exe completado en $ELAPSED_FMT"
    fi
fi

# --- wrf.exe nudged ---
log "=== NUDGED (obs_nudge_opt=1) ==="
plog "=== NUDGED (obs_nudge_opt=1) ==="
cp "$CASE_DIR/namelist_nudged.input" "$RUN_DIR/namelist.input"

run_wrf() {
    local etiqueta="$1"   # nudged|control
    local opt="${2:-1}"   # obs_nudge_opt
    local max_reintentos=5
    local intento=1
    while :; do
        rm -f wrfout_d01_* rsl.* 2>/dev/null || true
        log "Iniciando wrf.exe $etiqueta (intento $intento)..."
        plog "Iniciando wrf.exe $etiqueta (obs_nudge_opt=$opt)..."
        local START=$(date +%s)
        ./wrf.exe >> "$LOG_FILE" 2>&1
        local RC=$?
        local END=$(date +%s)
        local ELAPSED=$(( END - START ))
        local ELAPSED_FMT=$(printf '%02d:%02d:%02d' $((ELAPSED/3600)) $(( (ELAPSED%3600)/60 )) $((ELAPSED%60)))
        if { [ -f rsl.out.0000 ] && grep -q "SUCCESS COMPLETE WRF" rsl.out.0000; } \
           || grep -q "SUCCESS COMPLETE WRF" "$LOG_FILE" 2>/dev/null; then
            log "SUCCESS COMPLETE WRF encontrado ($etiqueta, intento $intento, $ELAPSED_FMT)"
            plog "wrf.exe $etiqueta OK en $ELAPSED_FMT"
            return 0
        fi
        log "wrf.exe $etiqueta FALLO (RC=$RC, intento $intento, $ELAPSED_FMT)"
        if [ "$intento" -gt "$max_reintentos" ]; then
            plog "wrf.exe $etiqueta FALLO definitivo (RC=$RC)"
            return 1
        fi
        log "Reintentando $etiqueta ($((intento+1))/$((max_reintentos+1)))..."
        intento=$((intento+1))
        sleep 2
    done
}

# --- wrf.exe nudged ---
if run_wrf "nudged" 1; then
    echo "OK" > "$NUDGED_STATUS"
    mkdir -p "$CASE_DIR/nudged"
    cp wrfout_d01_* "$CASE_DIR/nudged/" 2>/dev/null || true
else
    echo "FAIL" > "$NUDGED_STATUS"
    echo "NUDGED_FAIL" > "$STATUS_FILE"
    exit 1
fi

# --- wrf.exe control ---
if [ "$SKIP_CONTROL" != "yes" ]; then
    log "=== CONTROL (obs_nudge_opt=0) ==="
    plog "=== CONTROL (obs_nudge_opt=0) ==="
    cp "$CASE_DIR/namelist_control.input" "$RUN_DIR/namelist.input"
    if run_wrf "control" 0; then
        echo "OK" > "$CONTROL_STATUS"
        mkdir -p "$CASE_DIR/control"
        cp wrfout_d01_* "$CASE_DIR/control/" 2>/dev/null || true
    else
        echo "FAIL" > "$CONTROL_STATUS"
        echo "CONTROL_FAIL" > "$STATUS_FILE"
        exit 1
    fi
fi

log "=== PIPELINE COMPLETO ==="
plog "=== PIPELINE COMPLETO ==="
echo "DONE" > "$STATUS_FILE"
exit 0
