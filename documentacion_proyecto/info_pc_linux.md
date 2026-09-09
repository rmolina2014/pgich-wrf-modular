# Información de PC y sistema — WRF-PGICH

> Archivo de diagnóstico del sistema donde se ejecuta el modelo WRF.
> Generado el 08/09/2026.

## 1. Identidad y sistema operativo

| Item | Valor |
|---|---|
| Usuario | `pgich` |
| HOME | `/home/pgich` |
| Hostname | `idih48-wrf` |
| SO | Linux, kernel `6.1.0-13-amd64` |
| Distribución | Debian (PREEMPT_DYNAMIC), build `6.1.55-1` |
| Arquitectura | x86_64 GNU/Linux |

## 2. Modelos meteorológicos

| Modelo | Versión | Ubicación |
|---|---|---|
| WRF (WRF-Chem) | **4.5** | `/home/pgich/Build_WRF/WRF` |
| WPS (Pre-Processing System) | **4.5** | `/home/pgich/Build_WRF/WPS` |
| WRFDA | — | `/home/pgich/Build_WRF/WRFDA` |
| WRFDomainWizard | — | `/home/pgich/Build_WRF/WRFDomainWizard` |
| wrf_hydro (NWM público) | — | `/home/pgich/Build_WRF/wrf_hydro_nwm_public` |

- La versión de WRF se verifica en el atributo `TITLE` de los wrfout:
  `OUTPUT FROM * PROGRAM:WRF-Chem V4.5 MODEL` y en el `README`:
  `WRF Model Version 4.5`.
- La versión de WPS se verifica en la salida de geogrid:
  `OUTPUT FROM GEOGRID V4.5` / `WRF Pre-Processing System Version 4.5`.

## 3. Directorios de trabajo

| Directorio | Ruta |
|---|---|
| Build base | `/home/pgich/Build_WRF/` |
| Ejecutables/scripts | `/home/pgich/wrf-operativo/ejecutables/` |
| Datos operativos | `/home/pgich/wrf-operativo/datos/` |
| GFS 0.25° descargados | `/home/pgich/wrf-operativo/datos/GFS025` |
| Namelistas | `/home/pgich/wrf-operativo/datos/namelists` |
| Salidas wrfout | `/home/pgich/wrf-operativo/salidas/wrfout` |
| Mapas/figuras | `/home/pgich/wrf-operativo/salidas/mapas` |
| Logs | `/home/pgich/wrf-operativo/salidas/logs` |
| WRFplot | `/home/pgich/wrf-operativo/ejecutables/wrfplot` |

> Hinario local de referencia: los directorios operativos se pueden inspeccionar
> con `env.bash` (ver sección 6), que define todas las variables WRF_* usadas por
> los scripts.

## 4. Datos de geografía (WPS_GEOG)

Ruta: `/home/pgich/wrf-operativo/datos/WPS_GEOG/`

Primeras entradas del directorio:

```
albedo_modis
albedo_ncep
greenfrac
greenfrac_fpar_modis
greenfrac_fpar_modis_5m
```

## 5. Compiladores y librerías

- **MPICH:** `/home/pgich/Build_WRF/libraries/MPICH/bin/mpirun` — HYDRA build 4.0.3
- **Librerías** (en `/home/pgich/Build_WRF/libraries/`):

| Librería | Ruta |
|---|---|
| NETCDF | `$LIBDIR/NETCDF` |
| HDF5 | `$LIBDIR/HDF5` |
| grib2 (incluye JASPER, ZLIB, LIBPNG) | `$LIBDIR/grib2` |
| MPICH | `$LIBDIR/MPICH` |

## 6. Variables de entorno (`env.bash`)

Script: `/home/pgich/wrf-operativo/ejecutables/env.bash`

Variables principales definidas:

```
WRF_BASE=/home/pgich/Build_WRF
WRF_DATA=/home/pgich/wrf-operativo
WRF_EJECUTABLES=$WRF_DATA/ejecutables
WRF_GFS=$WRF_DATA/datos/GFS025
WRF_NAMELISTS=$WRF_DATA/datos/namelists
WPS_GEOG=$WRF_DATA/datos/WPS_GEOG
WRF_WRFOUT=$WRF_DATA/salidas/wrfout
WRF_MAPAS=$WRF_DATA/salidas/mapas
WRF_WRFPLOT=/home/pgich/wrf-operativo/ejecutables/wrfplot
```

Parámetros operativos del ciclo:

```
NUM_FILES=17
RUN_HOURS=48
REGION=SAN_JUAN
CODIGO=A
REF_LAT=-31.53
REF_LON=-68.53
TRUELAT1=-31.53
TRUELAT2=-31.53
STAND_LON=-68.53
REGION_LON_MIN=-70.50
REGION_LON_MAX=-66.50
REGION_LAT_MIN=-33.00
REGION_LAT_MAX=-28.50
```

Ajustes de paralelismo/rendimiento:

```
ulimit -s unlimited
KMP_STACKSIZE=128m
KMP_HW_SUBSET=4c,2t
WRF_NUM_TILES_X=1
WRF_NUM_TILES_Y=8
OMP_NUM_THREADS=12
```

`RUN_COMMAND` está vacío (la ejecución la maneja cada script, normalmente vía
`mpirun` de MPICH).

## 7. Python y herramientas

| Herramienta | Versión / Ruta |
|---|---|
| Python de validación | `/home/pgich/anaconda3/envs/wrf-operativo-p3/bin/python` (existe) |
| Python del sistema | 3.11.5 |
| uv | 0.12.7 |

## 8. Repositorio y proyecto (pgich-wrf-modular)

- Repo local: `/home/pgich/pgich-wrf-modular` (rama `main`)
- Remoto: `https://github.com/rmolina2014/pgich-wrf-modular.git`
- Documentación del proyecto: `/home/pgich/pgich-wrf-modular/documentacion_proyecto/`
- Entorno virtual del proyecto gestionado con `uv` (`.venv313/` presente en el repo)
- Script principal de corrida: `pipeline_wrf.py` y `run_full_pipeline.sh`
- Validación: `tesis_wrf_pgich/src/calidad/valida_wrf.py`