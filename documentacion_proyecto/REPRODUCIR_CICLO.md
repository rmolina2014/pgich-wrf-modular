# Reproducir el ciclo completo WRF + Obs Nudging

## Prerrequisitos

- Docker Desktop (Windows) o Docker Engine (Linux)
- Contenedor `teachme` basado en `davegill/wrf-coop:fourteenthtry` con WRF v4.6.1 + WPS v4.6.0 compilado
- Python 3.11+ con: `pandas`, `xarray`, `matplotlib`, `scipy`, `netCDF4`, `metpy`, `numpy`
- Archivos estáticos WPS (`geogrid`, `met_em*` para la fecha deseada)
- Archivo `namelist.input` base

## Estructura de archivos

```
C:\tesis2026\
├── pipeline_wrf.py                    # Orquestador principal
├── namelist.input                     # Template base del namelist
├── gestion_pendientes.txt             # Pendientes con encargados
├── results/                           # Outputs de cada corrida
│   └── {YYYY-MM-DD}_{HH}Z/
│       └── {nombre_caso}/
│           ├── input/                 # OBS_DOMAIN101, Little_R, CSV
│           ├── nudged/                # wrfout* de corrida nudged
│           ├── control/               # wrfout* de corrida control
│           ├── scatter_4panels.png    # Grafico scatter 4 paneles
│           ├── mapa_errores_t2.png    # Mapa de errores T2
│           ├── tabla_metricas.png     # Tabla de metricas
│           └── metricas_resumen.txt   # Metricas en texto
│
├── tesis_wrf_pgich/
│   ├── config/estaciones.json         # Lat, lon, elev de cada estacion
│   ├── data/raw/                      # JSON crudos de EcoWitt
│   ├── data/processed/               # Archivos intermedios
│   ├── pites_eta.php                  # Scraper PHP (produccion)
│   └── src/
│       ├── ingesta/lector_pgich.py    # Lector API EcoWitt (Python)
│       └── calidad/
│           ├── limpiador_pgich.py     # Raw JSON -> CSV
│           ├── generador_littler.py   # CSV -> formato Little_R
│           ├── littler_a_obsnud.py    # Little_R -> OBS_DOMAIN101
│           └── valida_wrf.py          # WRFout vs estaciones -> metricas
│
└── contenedor:/wrf/WRF/test/em_real/
    ├── wrfinput_d01                   # Iniciales (de real.exe)
    ├── wrfbdy_d01                     # Condiciones de borde
    ├── met_em.d01.*.nc               # Entradas meteorologicas (WPS)
    ├── OBS_DOMAIN101                  # Observaciones para nudging
    ├── namelist.input                 # Configuracion de la corrida
    ├── wrf.exe                        # Ejecutable WRF
    ├── wrfout_d01_*                   # Outputs (13 archivos, 1 c/hora)
    ├── nudged/                        # Backup de ultima corrida nudged
    ├── control/                       # Backup de corrida control
    └── rsl.out.0000 / rsl.error.0000  # Logs de WRF
```

## Pipeline completo paso a paso

### Paso 0: Preparar datos de estaciones

```bash
# Opcion A: Desde archivo existente
# Archivo en: tesis_wrf_pgich/data/raw/ecowitt_todos_{YYYYMMDD}_{HHMM}.json

# Opcion B: Descargar datos frescos desde API EcoWitt
cd tesis_wrf_pgich
python -c "
from src.ingesta.lector_pgich import EcowittIngestor, ESTACIONES
from dotenv import load_dotenv
load_dotenv()
import os
ingestor = EcowittIngestor(os.getenv('ECOWITT_APP_KEY'), os.getenv('ECOWITT_API_KEY'))
resultados = ingestor.guardar_todos_con_ecohumus()
print(f'Guardados {len(resultados)} registros')
"
```

### Paso 1: Generar OBS_DOMAIN101

```bash
# Usando el pipeline (modo prepare-only)
python pipeline_wrf.py \
    --date YYYY-MM-DD \
    --hour HH:MM \
    --json tesis_wrf_pgich/data/raw/ecowitt_todos_{fecha}_{hora}.json \
    --case nombre_caso \
    --prepare-only
```

Esto ejecuta automaticamente:
1. `limpiador_pgich.py` — JSON -> CSV validado
2. `generador_littler.py` — CSV -> Little_R
3. `littler_a_obsnud.py` — Little_R -> OBS_DOMAIN101 + copia al contenedor

Output: `results/{fecha}_{hora}z/{caso}/input/`
- `OBS_DOMAIN101` (se copia a `/wrf/WRF/test/em_real/` en el contenedor)
- `littler_{timestamp}.txt`
- `datos_validados_{timestamp}.csv`

### Paso 2: Configurar namelist

Ubicar el template en `C:\tesis2026\namelist.input`.

Parametros clave para obs nudging (seccion `&fdda`):

| Parametro | Valor | Descripcion |
|---|---|---|
| `obs_nudge_opt` | 1=activado, 0=desactivado | Activa nudging |
| `obs_coef_wind` | 0.001 | Coeficiente nudging viento |
| `obs_coef_temp` | 0.001 | Coeficiente nudging temperatura |
| `obs_coef_mois` | 0.001 | Coeficiente nudging humedad |
| `obs_twindo` | 1.0 (horas) | Ventana temporal |
| `obs_rinxy` | 50.0 km | Radio de influencia |
| `fdda_end` | 720 minutos | Duracion del nudging |
| `max_obs` | 10000 | Maximo numero de observaciones |
| `auxinput11_inname` | `"OBS_DOMAIN101"` | Archivo de observaciones |
| `auxinput11_interval_m` | 30 | Intervalo de lectura |

### Paso 3: Correr WRF con nudging (corrida nudged)

```bash
python pipeline_wrf.py \
    --date YYYY-MM-DD \
    --hour HH:MM \
    --json tesis_wrf_pgich/data/raw/ecowitt_todos_{fecha}_{hora}.json \
    --case nombre_caso \
    --skip-control     # Reusa la corrida control existente
```

Opcional: modificar coeficientes para sensibilidad:

```bash
python pipeline_wrf.py \
    --date YYYY-MM-DD --hour HH:MM \
    --json ruta/al/json.json \
    --case sens_coef001 \
    --obs-coef-wind 0.001 \
    --obs-coef-temp 0.001 \
    --obs-coef-mois 0.001 \
    --obs-twindo 1.0 \
    --skip-control
```

### Paso 4: Correr WRF sin nudging (corrida control)

```bash
# Solo necesario UNA VEZ por fecha.
# Se reusa para todas las sensibilidades.
python pipeline_wrf.py \
    --date YYYY-MM-DD \
    --hour HH:MM \
    --json tesis_wrf_pgich/data/raw/ecowitt_todos_{fecha}_{hora}.json \
    --case control \
    --skip-control     # No, en este caso NO skip-control
```

O manualmente:

```bash
docker cp namelist_control.input teachme:/wrf/WRF/test/em_real/namelist.input
docker exec teachme bash -c "cd /wrf/WRF/test/em_real && mpirun -np 4 ./wrf.exe"
```

Verificar `rsl.out.0000` confirma `SUCCESS COMPLETE WRF`.

### Paso 5: Validacion

```bash
# Si las corridas nudged y control ya existen:
python pipeline_wrf.py \
    --date YYYY-MM-DD \
    --hour HH:MM \
    --case nombre_caso \
    --validate-only \
    --json ruta/al/json.json
```

La validacion:
1. Interpola WRF a puntos de estacion (bilineal)
2. Computa: BIAS, MAE, RMSE, coeficiente de correlacion (r)
3. Genera graficos:
   - `scatter_4panels.png` — Obs vs WRF para T2, PSFC, RH, Wind
   - `mapa_errores_t2.png` — Error espacial de T2 sobre topografia
   - `tabla_metricas.png` — Tabla comparativa nudged vs control
   - `metricas_resumen.txt` — Metricas en texto

### Paso 6: Interpretacion de resultados

La tabla muestra para cada variable:

| Columna | Significado |
|---|---|
| N | Numero de estaciones con datos validos |
| Bias N | Sesio medio nudged (modelo - obs) |
| MAE N | Error absoluto medio nudged |
| RMSE N | Raiz del error cuadratico medio nudged |
| r N | Correlacion nudged |
| Bias C / MAE C / RMSE C / r C | Mismo para control |

Si RMSE_N < RMSE_C y r_N > r_C, el nudging mejoro el pronostico.

## Sensibilidad de parametros (Fase 1)

Ejecutar secuencialmente:

```bash
# Probar distintos coeficientes (nominal: 3-5 corridas ~15 min c/u)
for coef in 0.0001 0.001 0.005; do
    python pipeline_wrf.py \
        --date 2026-05-25 --hour 21:00 \
        --json tesis_wrf_pgich/data/raw/ecowitt_todos_20260525_2059.json \
        --case sens_coef$coef \
        --obs-coef-wind $coef \
        --obs-coef-temp $coef \
        --obs-coef-mois $coef \
        --skip-control
done

# Probar ventanas temporales
for twindo in 0.5 2.0; do
    python pipeline_wrf.py \
        --date 2026-05-25 --hour 21:00 \
        --json tesis_wrf_pgich/data/raw/ecowitt_todos_20260525_2059.json \
        --case sens_twindo$twindo \
        --obs-twindo $twindo \
        --skip-control
done
```

Resultados obtenidos (2026-05-25 21z):

| Caso | T2 RMSE | T2 mejora | RH RMSE | RH mejora | Wind RMSE | Wind mejora |
|---|---|---|---|---|---|---|
| Control | 6.25 | — | 23.37 | — | 3.64 | — |
| coef=0.0001 | 5.84 | -6.6% | 21.11 | -9.7% | 3.64 | 0% |
| coef=0.0005 | 4.94 | -21% | 14.84 | -36% | 3.36 | -8% |
| **coef=0.001** | **4.55** | **-27%** | 11.82 | -49% | 3.23 | -11% |
| coef=0.005 | 4.61 | -26% | **11.43** | **-51%** | **3.19** | **-12%** |
| twindo=0.5h | 5.44 | -13% | 18.52 | -21% | 3.36 | -8% |
| **twindo=2.0h** | **4.53** | **-28%** | 11.91 | -49% | 3.56 | -2% |

Recomendacion: `obs_coef = 0.001` con `obs_twindo = 1.0-2.0h`.

## Tiempos de ejecucion

| Etapa | Duracion |
|---|---|
| JSON -> CSV -> Little_R -> OBS_DOMAIN101 | <1 min |
| wrf.exe (12h, 15km, 4 cores) | ~3 min |
| Validacion (lectura wrfout + graficos) | ~5 seg |
| **Total por corrida** | **~4 min** |
| Sensibilidad completa (5 corridas) | ~20 min |

Nota: el primer arranque de Docker/WRF puede tomar mas tiempo.
Si se usa restart o se cambia la configuracion del dominio, wrf.exe
puede demorar 45-60 min (como ocurrio en la corrida inicial).

## Solucion de problemas comunes

### `NSTA = 0` en rsl.out.0000
Causa: WRF no encuentra observaciones en la ventana temporal.
- Verificar `obs_twindo` (debe cubrir la hora de la observacion)
- Verificar `max_obs` (debe ser > 0, ej: 10000)
- Verificar `fdda_end` (debe ser >= minutos de simulacion, ej: 720)
- Verificar que `OBS_DOMAIN101` este en el directorio correcto

### wrf.exe falla con `FATAL CALL`
Causas comunes:
- `namelist.input` mal formateado (faltan comas, slashes)
- `max_obs` = 0 (impide lectura de observaciones)
- Formato incorrecto en la fecha del OBS_DOMAIN101
  - Debe ser `YYYYMMDDHHMMSS` (14 digitos, SIN guiones ni underscores)

### Error al copiar wrfout a Windows
Los archivos wrfout tienen `:` en el nombre (ej: `wrfout_d01_..._21:00:00`).
Windows no permite `:` en nombres de archivo.
El pipeline los renombra con `_` al copiar.
La validacion se ejecuta dentro del contenedor Linux, no requiere copia local.

## Notas importantes

1. Toda la validacion se ejecuta DENTRO del contenedor (xarray solo esta alli)
2. Los resultados (graficos, tablas) se copian automaticamente al host
3. El control run se ejecuta UNA SOLA VEZ y se reusa para todas las sensibilidades
4. Las observaciones de estaciones tienen timestamp 20:59, la validacion se hace
   contra wrfout de las 21:00 (dentro de la ventana obs_twindo)
5. El modelo presenta sesio calido sistematico de ~4-5K (posible causa:
   resolucion 15 km no resuelve topografia, hora crepuscular 18h local)
