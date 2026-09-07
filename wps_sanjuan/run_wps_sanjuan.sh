#!/bin/bash
# WPS para el dominio San Juan (tesis): geogrid + ungrib + metgrid.
#
# Uso:
#   ./run_wps_sanjuan.sh YYYY-MM-DD HH     (ej: 2026-08-13 00)
#
# Requisitos:
#   - GFS descargado en wps_sanjuan/gfs_data/ con nombre GFS_YYYYMMDDHH+HHH.grib2
#     (o en el patron que link_grib.csh pueda enlazar)
#
# Salida:
#   wps_sanjuan/met_em.d01.*.nc  (forzante para real.exe)

set -e

FECHA=$1
HORA=$2

if [ -z "$FECHA" ] || [ -z "$HORA" ]; then
    echo "Uso: $0 YYYY-MM-DD HH"
    exit 1
fi

START_DATE="${FECHA}_${HORA}:00:00"
END_DATE=$(date -d "${FECHA} ${HORA}:00:00 12 hours" +%Y-%m-%d_%H:00:00)

export WRF_BASE=/home/roberto/opencode/wrf
export WPS_DIR=/home/roberto/opencode/wrf/WPS-4.0
export WRF_EJECUTABLES=/home/roberto/opencode/wrf/WRF-4.0
source ${WRF_EJECUTABLES}/run/env.bash 2>/dev/null || true

cd "$(dirname "$0")"

# Vincular ejecutables y tablas de la instalacion WPS local si no estan presentes
for bin in geogrid.exe metgrid.exe ungrib.exe link_grib.csh; do
    [ -e "$bin" ] || ln -sf "$WPS_DIR/$bin" "$bin"
done
[ -e Vtable ] || ln -sf "$WPS_DIR/ungrib/Variable_Tables/Vtable.GFS" Vtable

# Preparar namelist.wps con las fechas del caso
sed -e "s/START_DATE/${START_DATE}/g" \
    -e "s/END_DATE/${END_DATE}/g" \
    namelist.wps.template > namelist.wps
echo "start_date = ${START_DATE} / end_date = ${END_DATE}"

echo "
		********** geogrid.exe **********
"
./geogrid.exe

echo "
		********** ungrib.exe **********
"
# Enlazar GFS (link_grib.csh enlaza cualquier patrón de grib)
ls gfs_data/${FECHA}_${HORA}/ > /dev/null 2>&1 || { echo "No hay GFS en gfs_data/${FECHA}_${HORA}/"; exit 1; }
./link_grib.csh gfs_data/${FECHA}_${HORA}/
./ungrib.exe

echo "
		********** metgrid.exe **********
"
./metgrid.exe

echo "
		****** WPS SAN JUAN COMPLETADO ******
"
ls -la met_em.d01.*
