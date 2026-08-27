# Arquitectura y Plan de Mejoras — WRF + Obs Nudging (San Juan)

Estado: 2026-08-14 · Repo: `tesisMaestriaInformatica_2026`
Versión WRF instalada: **v4.5** (Build_WRF) · Python 3.11 (entorno `wrf-operativo-p3`)

---

## 1. Visión General

**Objetivo:** sistema de pronóstico meteorológico para la provincia de San Juan
(Argentina) que asimila observaciones de estaciones meteorológicas **EcoWitt** de
uso doméstico en WRF vía **obs nudging** (relajación del modelo hacia las obs).

**Resumen del flujo de datos:**

```
API EcoWitt (real_time / history)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  INGESTA                                            │
│  lector_pgich.py (tiempo real)                      │
│  obtener_historico.py (histórico, por día)          │
│  → data/raw/ecowitt_todos_*.json                    │
│  → historico/ecowitt_historico_*.csv/.json          │
│  → [ad-hoc] historico/obs_flat_*.json               │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│  CALIDAD + CONVERSIÓN                               │
│  limpiador_pgich → DataFrame validado                │
│  generador_littler → archivo Little_R (Fortran)     │
│  littler_a_obsnud → OBS_DOMAIN101 (formato 105)    │
│  ──→ copiado a WRF run_dir                         │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│  PRE-PROCESAMIENTO (WPS)                            │
│  GFS 0.25° pgrb2 (NOMADS) → ungrib → metgrid       │
│  → met_em.d01.*.nc → copiados al run_dir           │
│  (wps_sanjuan/run_wps_sanjuan.sh)                   │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│  MODELO WRF                                         │
│  real.exe → wrfinput/wrfbdy (+ wrfdda si FDDA)     │
│  wrf.exe NUDGED (obs_nudge_opt=1)  ─┐              │
│  wrf.exe CONTROL (obs_nudge_opt=0)  ─┤  1 proceso,  │
│                                       │  OMP_NUM…=1  │
│                                       └──────────────│
│  → wrfout_d01_*.nc (archivados por caso)            │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│  VALIDACIÓN                                         │
│  valida_wrf.py (±30 min, interp bilineal)           │
│  → Bias/MAE/RMSE/r, scatter, mapa errores, tabla   │
│  → metricas_resumen.txt + PNGs                      │
└─────────────────────────────────────────────────────┘
```

**Dos mundos conviven en el servidor:**

| Aspecto | Sistema operativo (`wrf-operativo/`) | Pipeline de tesis (`tesisMaestriaInformatica_2026/`) |
|---|---|---|
| Estado | En uso desde 2025 (cron, mails, FTP) | Activo desde Ago-2026 (experimentos tesis) |
| Python | **2.7** (mayoría scripts legacy) | **3.11** (`wrf-operativo-p3`) |
| GFS | 0.25° subregión (-96..-15, -75..-10), 12 vars, 17 archivos/ciclo | 0.25° **completo**, todas las vars, 5 archivos/ciclo (12 h) |
| WRF/WPS | v4.5 nativo (`Build_WRF/`) | **Mismo** (comparte `Build_WRF/` y `WRF/` run dir) |
| Región por defecto | PARAGUAY (600×600 @1 km) | San Juan (80×60 @15 km) |
| Obs nudging | No implementado | Activo (OBS_DOMAIN101, FORMAT 105) |
| Run dir | `/home/pgich/wrf-operativo/ejecutables/WRF/` | **Mismo** (compartido) |

> ⚠️ **`WRF/` run dir es compartido.** La tesis escribe `namelist.input` y
> `OBS_DOMAIN101` allí; `limpiar.bash` del operativo borra todo el contenido.

---

## 2. Repositorio de la Tesis

**Root:** `/home/pgich/asimilacionWRF/tesisMaestriaInformatica_2026/`
**Remote:** `github.com/rmolina2014/tesisMaestriaInformatica_2026`
**Commits:** 5 (último: `eaf45cf` feat: ciclo validado 2026-08-12)

### 2.1 `pipeline_wrf.py` — Orquestador (625 líneas)

Flujo completo con las **12 funciones principales**:

| Paso | Función | Líneas | Qué genera |
|---|---|---|---|
| Validación args | `main()` | 530–621 | CLI parser, resolución de rutas |
| Verificar run dir | `check_run_dir()` | 81–90 | `bool` (existe `wrf.exe`) |
| **1–2** | `generar_littler_desde_json()` | 217–238 | `input/datos_validados_*.csv`, `input/littler_*.txt` |
| **3** | `generar_obsdomain()` | 241–265 | `input/OBS_DOMAIN101` → copiado a run dir |
| Namelist | `preparar_namelist()` | 174–214 | `results/…/namelist_{nudged,control}.input` |
| Dates | `_parchear_fechas()` | 150–171 | Reescribe `start/end_*` en namelist |
| **4** real.exe | `ejecutar_real()` | 275–297 | `wrfinput_d01`, `wrfbdy_d01` |
| **5** wrf.exe | `ejecutar_wrf()` | 300–333 | `wrfout_d01_*.nc` |
| Archivar | `copiar_wrfout()` | 336–352 | `results/…/nudged/` o `control/` |
| **6** valida | `run_valida_wrf()` | 355–382 | `metricas_resumen.txt` + PNGs |
| Ejecutar | `ejecutar_comando()` | 109–134 | wrapper bash (con parches) |
| Verificar | `verificar_success()` | 137–147 | `SUCCESS COMPLETE WRF` en `rsl.out.0000` |

**Flujo `pipeline()` (L385–527):**

1. Parsear args, crear dirs de resultados
2. Verificar run dir
3. Generar OBS_DOMAIN101 (pasos 1–3)
4. Preparar namelist nudged → copiar al run dir
5. (Opcional) real.exe con `--run-real`
6. wrf.exe nudged (`obs_nudge_opt=1`) → archivar en `nudged/`
7. Preparar namelist control → wrf.exe control (`obs_nudge_opt=0`) → archivar en `control/`
8. Ejecutar validación (`valida_wrf.py`)

**Variables de entorno y defaults:**

| Variable | Default | Uso |
|---|---|---|
| `LOCAL_WRF_DIR` | `/home/pgich/wrf-operativo/ejecutables/WRF` | run dir |
| `WRF_ENV_BASH` | `…/ejecutables/env.bash` | `source` para LD_LIBRARY_PATH |
| `MPIRUN` | `…/Build_WRF/libraries/MPICH/bin/mpirun` | MPI (no usado con np=1) |
| `WRF_NP` | `"1"` | Un solo proceso |
| `VALIDATION_PYTHON` | `…/anaconda3/envs/wrf-operativo-p3/bin/python` | Python con xarray |

**Argumentos de CLI:**

```
--date/-d YYYY-MM-DD          (requerido)
--hour/-t HH:MM               (default 21:00)
--json/-j  archivo.json       (requerido salvo --validate-only)
--case/-c  nombre_caso        (default "default")
--namelist/-n  namelist.input (template base)
--run-real                     ejecuta real.exe antes de wrf.exe
--prepare-only                 solo genera OBS_DOMAIN101
--validate-only                solo validación sobre wrfouts existentes
--skip-wrf                     salta corridas WRF
--skip-control                 solo nudged, sin control
--obs-coef-wind/temp/mois      override coefs FDDA (float)
--obs-twindo                   override obs_twindo (float)
--wrf-timeout                  timeout wrf.exe (default 7200 s)
--mpirun / --np                configuración MPI
--label                        etiqueta para gráficos
```

**Parches aplicados (commit `eaf45cf`):**

| Parche | Línea | Detalle |
|---|---|---|
| `OMP_NUM_THREADS=1` | 117 | Después de `source env.bash` (que pone 12) |
| Archivo temporal stdout | 114–128 | `mkstemp` en vez de `capture_output` (evita SIGSEGV) |
| `--ventana-min 30` | valida_wrf 434 | Filtra obs a ±30 min (NO propagado desde CLI del pipeline) |

### 2.2 `tesis_wrf_pgich/` — Paquete Python

#### `src/ingesta/`

**`lector_pgich.py`** (215 líneas) — API tiempo real (`api/v3/device/real_time`)
- Clase `EcowittIngestor` con `obtener_todas_estaciones()` y `guardar_todos_con_ecohumus()`
- Lee `ECOWITT_APP_KEY/API_KEY` + `ECOWITT_APP_KEY_ECOHUMUS/API_KEY_ECOHUMUS` de `.env`
- Salida: `data/raw/ecowitt_todos_YYYYMMDD_HHMM.json`

**`obtener_historico.py`** (272 líneas) — API histórica (`api/v3/device/history`)
- 4 requests/estación (`outdoor`, `wind`, `pressure`, `rainfall`) + sleep 0.34 s
- `--fecha YYYY-MM-DD` → `historico/ecowitt_historico_YYYYMMDD.csv/.json`
- Código muerto: `_merge_lists()` nunca se llama
- ⚠️ `convertir_a_csv()` solo usa temp/hum/wind/press_rel para timestamps; si temp falla, se pierden filas de viento

#### `src/calidad/`

**`limpiador_pgich.py`** (112 líneas) — conversión JSON→DataFrame
- `procesar_json_ecowitt()` exige campos `fecha` + `hora`; descarta obs con `"error"`; coerción numérica de 12 columnas
- ⚠️ No hay control de calidad real (sin rangos físicos, sin eliminación de outliers)

**`generador_littler.py`** (194 líneas) — DataFrame→Little_R (Fortran)
- Conversión de unidades: temp→K, pres→Pa, vel→u/v meteorológica
- `u = -speed·sin(dir)`, `v = speed` (el campo "v" lleva rapidez, no componente V; Little_R parseado como tal en littler_a_obsnud)
- Si una estación no está en `estaciones.json`, lat/lon/elev = `0.0` silenciosamente

**`littler_a_obsnud.py`** (217 líneas) — Little_R→**OBS_DOMAIN101** ✅ MÓDULO CORREGIDO
- `parse_littler_custom()`: parsea header por slicing fijo, detecta fin de archivo con heurísticas
- `convertir_a_obsnud()`: emite **FORMAT 105** `1x,9(f11.3,1x,f11.3,1x)`
- **Fix平台 SYNOP** (L140): `f"{'SYNOP':>11s}" + " " * 5` → chars 7–11 (plfo=4)
- **Fix 9 pares** (L147–157): `slp, ref_pres, height, temp, u, v, rh, psfc, precip` (18 col `f11.3`)
- ⚠️ QC inconsistente: missing `-999999` del Little_R se escribe con QC `0.0` (válido) en el OBS_DOMAIN101; puede confundir a WRF

**`historico_a_obsnud.py`** (530 líneas) — monolito legacy ✅ DUPLICADO
- Repite código de `generador_littler` y `littler_a_obsnud` (copias literales de funciones)
- **NO tiene el fix SYNOP** (usa `f"{'SYNOP':<16s}"` → plfo=99, "unknown ob of type SYNOP")
- Sí tiene el fix de 9 pares
- Ordena por `fecha_hora` (cronológico) — `littler_a_obsnud` no lo hace
- Incluye Docker `docker exec/cp` al contenedor `teachme`
- **No se importa desde ningún otro módulo** (solo CLI standalone)

**`valida_wrf.py`** (452 líneas) — validación nudged vs control
- `cargar_estaciones_desde_json()`: lee obs JSON, filtra por `--ventana-min` (±30 min default)
- `bilinear_interp()`: en realidad es **inverso de distancia ponderada** sobre 4 nodos (no bilineal)
- Métricas: Bias, MAE, RMSE, r por variable (T2, PSFC, RH, Wind)
- ⚠️ N duplica por obs (una estación 5 veces en 25 min = 5 entradas, no 1)

#### `app.py` (272 líneas) — Streamlit
- 5 módulos: Inicio (mapa pydeck), Ingesta, Limpieza, LITTLE_R, Resultados
- **No llega a OBS_DOMAIN101 ni al pipeline WRF**
- Dependencia `pydeck` no declarada en `pyproject.toml`
- `generar_littler(df)` sin `output_path` usa `datetime.now()` (timestamp local)

#### `config/estaciones.json` — 4 estaciones

| Estación | lat | lon | elev (m) |
|---|---|---|---|
| INTA_POCITO | -31.6500 | -68.5833 | 615 |
| ULLUM_EMBALSE | -31.4667 | -68.6667 | 768 |
| ECOHUMUS | -31.6500 | -68.3000 | 600 |
| PUNTA_NEGRA | -31.5192 | -68.8178 | 800 |

> **5 copias de estaciones existen en el proyecto** con coordenadas
> inconsistentes: config json, `ESTACIONES` dict en `lector_pgich` y
> `obtener_historico`, `stations_fallback` en `valida_wrf`, backup json
> (20260625, con coords distintas), y `pites_eta.php`.

### 2.3 `wps_sanjuan/` — WPS para el caso

- `run_wps_sanjuan.sh YYYY-MM-DD HH` → geogrid+ungrib+metgrid
- `namelist.wps.template` con placeholders `START_DATE`/`END_DATE`
- GFS en `gfs_data/YYYY-MM-DD_HH/` (archivos NOMADS 0.25° completos)
- `met_em.d01.*.nc` generados (10 archivos para 2026-08-12 y 08-13)

### 2.4 `results/` — Salidas por caso

```
results/2026-08-12_0000z/sanjuan_20260812/
├── input/            → littler, OBS_DOMAIN101, CSV
├── namelist_nudged.input
├── namelist_control.input
├── nudged/wrfout_*   → 13 archivos (00z-12z)
├── control/wrfout_*  → 13 archivos
├── scatter_4panels.png
├── mapa_errores_t2.png
├── tabla_metricas.png
└── metricas_resumen.txt
```

---

## 3. Sistema Operativo (`wrf-operativo/`)

**Root:** `/home/pgich/wrf-operativo/`
**Build WRF/WPS:** `/home/pgich/Build_WRF/` — versión **4.5** (no 4.6.1 como
documenta `CONFIG_WRF_SAN_JUAN.md`, que referenciaba el Docker de diseño)

### 3.1 Scripts operativos

| Script | Python | Función |
|---|---|---|
| `cron.bash` | — | Punto de entrada cron (diario) |
| `runEureka.bash` | — | Orquesta descarga+WPS+WRF+postproceso |
| `runWPS.bash` | — | geogrid→ungrib→metgrid (template + sed) |
| `runWRF.bash` | — | real.exe→wrf.exe (template + sed) |
| `descarga_GFS025.py` | **2** (urllib2) | Descarga NOMADS 0.25° subregión, 12 vars, 17 archivos |
| `informe.py` | **2** (pandas 0.22) | Genera informe HTML + envía por mutt |
| `mail_v2.py/v3.py` | **2** | Envío email (credenciales hardcodeadas) |
| `ftp.py/ftp.sh` | 2/— | Publicación web FTP (credenciales hardcodeadas) |
| `wrfplot/` | **2** (cPickle, Basemap) | Post-proceso: mapas T2, ppn, viento; genera GIFs |
| `env.bash` | — | Variables de entorno (WRF_BASE, OMP…, librerías) |
| `limpiar.bash` | — | ⚠️ `rm WRF/* WPS/*` — **peligroso** |

### 3.2 `Build_WRF/` — Versiones instaladas

| Componente | Versión instalada | Versión documentada (CONFIG_WRF) |
|---|---|---|
| WRF | **4.5** (`inc/version_decl`) | 4.6.1 |
| WPS | **4.5** | 4.6.0 |
| WRFDA | 4.5 | — |
| Libraries | grib2, NETCDF, MPICH | — |

### 3.3 `ejecutables/WRF/` — Run dir compartido

- Symlinks a `Build_WRF/WRF/test/em_real/` (`real.exe`, `wrf.exe`, tablas)
- `met_em.d01.2026-08-12_*.nc` → symlinks a `wps_sanjuan/met_em.*.nc` (tesis)
- `wrfinput_d01`, `wrfbdy_d01`, `OBS_DOMAIN101`, `namelist.input` → archivos de la tesis
- `control/`, `nudged/` → subdirs de la tesis

---

## 4. Configuración Clave

### Dominio San Juan (tesis)

| Parámetro | Valor |
|---|---|
| Centro | 31.5°S, 68.5°O |
| Resolución | 15 km |
| Puntos | 80 × 60 (e_we × e_sn) |
| Niveles verticales | 35 |
| Time step | 90 s |
| Cobertura | ~1200×900 km: San Juan, Mendoza, La Rioja, San Luis, Córdoba |

### Namelist FDDA (obs nudging) — valores activos

```fortran
grid_fdda        = 1
obs_nudge_opt    = 1       (0 para control)
fdda_start       = 0.
fdda_end         = 720.    (12 h, hardcodeado por pipeline)
obs_coef_wind    = 0.0005
obs_coef_temp    = 0.0005
obs_coef_mois    = 0.0005
obs_rinxy        = 50.0    (radio de búsqueda, km)
obs_rinfxy       = 500.0
obs_sfcfacr      = 2.0
obs_twindo       = 1.0     (ventana temporal, h)
obs_npfi         = 30
obs_ionf         = 1
max_obs          = 10000   (default 0 → no lee obs)
auxinput11_inname = "OBS_DOMAIN101"
auxinput11_interval_m = 30
```

### Formato OBS_DOMAIN101 (FORMAT 105 — superficie)

- Header: platform(16s), source(16s), elev(f7.1), `F F 1`
- Datos: 9 pares `(valor, QC)` en `1x,9(f11.3,1x,f11.3,1x)`:
  `slp, ref_pres, height, temperature, u, v, rh, psfc, precip`
- Platform: `SYNOP` en chars 7–11 (plfo=4)

### GFS (tesis)

- Fuente: NOMADS `filter_gfs_0p25.pl` (HTTPS, archivos completos)
- Archivos por ciclo: 5 (`f000, f003, f006, f009, f012` = 12 h, 3 h intervalo)
- Tamaño: ~500 MB × 5 ≈ 2.5 GB por ciclo
- WPS prefix: `FILE` (namelist.wps)

---

## 5. Deuda Técnica Priorizada

| # | Problema | Severidad | Archivos |
|---|---|---|---|
| 1 | **`obs_flat_*.json` sin script reproducible** (generado ad-hoc) | 🔴 Alta | `historico/obs_flat_*.json` |
| 2 | **5 copias de estaciones con coordenadas inconsistentes** | 🔴 Alta | `estaciones.json`, `lector_pgich`, `obtener_historico`, `valida_wrf`, `pites_eta.php` |
| 3 | **`historico_a_obsnud.py` duplicado y sin fix SYNOP** | 🟠 Media | `src/calidad/historico_a_obsnud.py` |
| 4 | **Dockerfile roto** (`pip install -r pyproject.toml`) | 🟠 Media | `tesis_wrf_pgich/Dockerfile` |
| 5 | **`limpiar.bash` borra `WRF/*`** (run dir compartido) | 🔴 Alta | `ejecutables/limpiar.bash` |
| 6 | **`--ventana-min` no se propaga** desde CLI del pipeline | 🟡 Baja | `pipeline_wrf.py` (L355–382) |
| 7 | **QC inconsistente**: `-999999` con QC `0.0` en OBS_DOMAIN101 | 🟠 Media | `littler_a_obsnud.py` (L156) |
| 8 | **Python 2 legacy** en scripts operativos (descarga GFS, wrfplot, mail) | 🟠 Media | `ejecutables/*.py`, `wrfplot/` |
| 9 | **Rutas hardcodeadas** `/home/pgich/...` en pipeline | 🟡 Baja | `pipeline_wrf.py` (L52–72) |
| 10 | **`subprocess.run` sin manejo de excepciones** (TimeoutExpired) | 🟡 Baja | `pipeline_wrf.py` (L120, L376) |
| 11 | **No se verifica `met_em`** antes de `--run-real` | 🟡 Baja | `pipeline_wrf.py` (L450–453) |
| 12 | **Dead code**: `_merge_lists`, `fmt_data`, `_LAST_INGEST` | 🟡 Baja | `obtener_historico`, `littler_a_obsnud`, `api_gateway` |
| 13 | **`bilinear_interp` no es bilineal** (es IDW inverso) | 🟡 Baja | `valida_wrf.py` (L105–147) |
| 14 | **N duplica por estación** en métricas de validación | 🟡 Baja | `valida_wrf.py` |
| 15 | **Credenciales hardcodeadas** en `mail*.py`, `ftp.py` | 🔴 Seguridad | `ejecutables/mail*.py`, `ftp.py` |
| 16 | **Config region PARAGUAY** en `env.bash` (no San Juan) | 🟡 Baja | `ejecutables/env.bash` (L28–33) |

---

## 6. Plan de Mejoras

### Fase 0 — Crítico (impacto inmediato, esfuerzo bajo-medio)

#### 6.1 Script reproducible `obs_flat_*.json`
- **Problema:** `historico/obs_flat_*.json` se generó ad-hoc sin script versionado
- **Acción:** crear `tesis_wrf_pgich/src/ingesta/historico_a_flat.py` (CLI `--fecha YYYY-MM-DD`) que lea `historico/ecowitt_historico_*.csv`, aplique el esquema `ecowitt_todos` (fecha, hora, time_unix, temp, humedad, etc.) y escriba `historico/obs_flat_*.json`
- **Archivos:** nuevo `src/ingesta/historico_a_flat.py`; eliminar `obs_flat_*.json` de git tracking (regenerable)

#### 6.2 Fuente única de verdad de estaciones
- **Problema:** 5 copias con coordenadas distintas
- **Acción:** unificar TODO a `config/estaciones.json` como fuente única; eliminar `ESTACIONES` de `lector_pgich.py` y `obtener_historico.py` (importar desde config); eliminar `stations_fallback` de `valida_wrf.py` (obligar `--estaciones-json`); sincronizar `pites_eta.php`
- **Archivos:** `config/estaciones.json`, `lector_pgich.py`, `obtener_historico.py`, `valida_wrf.py`

#### 6.3 Proteger `limpiar.bash`
- **Problema:** borra `WRF/*` (run dir compartido con tesis)
- **Acción:** renombrar a `limpiar.bash.deprecated` o agregar verificación: solo borrar si `namelist.input` contiene la config operativa (no la tesis)
- **Archivos:** `ejecutables/limpiar.bash`

#### 6.4 Propagar `--ventana-min` al pipeline
- **Problema:** `pipeline_wrf.py` no pasa `--ventana-min` a `valida_wrf.py`; queda fijo en 30 min
- **Acción:** agregar `--ventana-min` al parser de `pipeline_wrf.py` (L588) y pasarlo en `run_valida_wrf()` (L362–373)
- **Archivos:** `pipeline_wrf.py`

#### 6.5 Arreglar Dockerfile
- **Problema:** `pip install -r pyproject.toml` no es válido; docker-compose no monta `config/` ni `.env`
- **Acción:** cambiar a `pip install .` (pyproject esPEP 621 válido con uv/pip moderno) o `uv sync`; agregar volumes de `config/` y `.env`
- **Archivos:** `tesis_wrf_pgich/Dockerfile`, `tesis_wrf_pgich/docker-compose.yml`

---

### Fase 1 — Consolidación (mes 1–2)

#### 6.6 Unificar `historico_a_obsnud.py` → `littler_a_obsnud.py`
- **Problema:** duplicación masiva (530 líneas copiadas); `historico_a_obsnud` sin fix SYNOP
- **Acción:** eliminar `historico_a_obsnud.py` (o mover a `deprecated/`); si se necesita la ruta `CSV→obs` directa, crear un wrapper que use `limpiador_pgich` + `generador_littler` + `littler_a_obsnud` (sin duplicar funciones)
- **Archivos:** `historico_a_obsnud.py`, `littler_a_obsnud.py`, `generador_littler.py`

#### 6.7 Corregir QC de `-999999` en OBS_DOMAIN101
- **Problema:** missing del Little_R (`-999999.0`) se escribe con QC `0.0` (válido); puede confundir a WRF
- **Acción:** en `convertir_a_obsnud()`, si el valor es `-999999.0` o `< -999998`, escribir QC `129` (missing) en vez de `0.0`
- **Archivos:** `littler_a_obsnud.py` (L156–159)

#### 6.8 Robustecer pipeline
- Agregar `try/except` para `subprocess.TimeoutExpired` en `ejecutar_comando()` (L120) y `run_valida_wrf()` (L376)
- Verificar existencia de `met_em.d01.*.nc` antes de `ejecutar_real()` con `--run-real` (L450)
- Quoting de rutas en comandos bash inline (`f"cd {run_dir} && ..."` → `shlex.quote`)
- **Archivos:** `pipeline_wrf.py`

#### 6.9 Interpolación bilineal real + métricas por estación
- Reemplazar `bilinear_interp()` por interpolación bilineal real (numpy/scipy `RegularGridInterpolator`)
- Agregar métricas **por estación** (no duplicar por cada obs de la misma estación)
- **Archivos:** `valida_wrf.py`

#### 6.10 Script reproducible `obtener_historico.py`
- Agregar reintentos con backoff exponencial (hoy solo `time.sleep(0.34)`)
- Incluir TODOS los campos en `convertir_a_csv()` (no solo temp/hum/wind/press_rel para timestamps)
- Agregar flag `--timezone` (default `America/Argentina/San_Juan`)
- **Archivos:** `obtener_historico.py`

---

### Fase 2 — Modernización del Operativo (mes 2–4)

#### 6.11 Portar descarga GFS a Python 3
- Reescribir `descarga_GFS025.py` usando `urllib.request` (como `descargar_gfs_full.py` de la tesis)
- Unificar: un solo script parametrizable (fecha, hora, horizonte, subregión opcional, vars)
- Eliminar la subregión innecesariamente amplia (-96..-15)
- **Archivos:** `ejecutables/descarga_GFS025.py` → reemplazar por versión py3

#### 6.12 Portar post-proceso a Python 3
- `wrfplot/`: reemplazar `cPickle`→`pickle`, `Basemap`→`cartopy`, `wrf-python` py3
- Priorizar: `productos_eureka.py`, `tabla_datos.py`, `gif*.py`
- **Archivos:** `wrfplot/`

#### 6.13 Cablear config San Juan al cron
- Cambiar `env.bash` `REGION=PARAGUAY`→`REGION=CUYO` o parametrizar por argumento
- O usar `sanjuan/env.bash` como default
- **Archivos:** `ejecutables/env.bash`, `cron.bash`

#### 6.14 Unificar GFS 0.25° completo
- Migrar el operativo de subregión+12vars a archivos completos (como la tesis)
- Ventaja: más simple, sin filtros NOMADS, sin riesgo de variables faltantes
- **Archivos:** `descarga_GFS025.py` (nueva versión)

---

### Fase 3 — Avance Científico (mes 4+)

#### 6.15 Tuning de coeficientes nudging
- `T2` empeora a 12z (MAE 3.16 nudged vs 2.60 control); `RH` mejora consistentemente
- Sensibilidad a `obs_coef_temp` (probado 0.0005; probar 0.0001–0.001)
- Sensibilidad a `obs_rinxy` (50 km actual; probar 25–100 km)
- Sensibilidad a `obs_twindo` (1 h actual; probar 0.5–2 h)
- **Archivos:** `namelist.input`, `pipeline_wrf.py` (flags `--obs-coef-*`)

#### 6.16 Experimentos multi-fecha
- Correr 5–10 ciclos para establecer estadísticas robustas
- Evaluar estabilidad del nudging en diferentes condiciones sinópticas
- **Archivos:** `pipeline_wrf.py`, scripts de batch

#### 6.17 Integración Streamlit → OBS_DOMAIN101
- Extender `app.py` con módulo "Ejecutar WRF" que invoque `pipeline_wrf.py`
- Dashboard de resultados: mostrar metricas_resumen + gráficos interactivos
- **Archivos:** `app.py`, `pipeline_wrf.py`

---

## 7. Seguridad

| Problema | Ubicación | Solución |
|---|---|---|
| Credenciales EcoWitt en `.env` | Raíz (gitignored) | ✅ Ya gitignored; rotar expuesto en chat |
| Credenciales email/FTP hardcodeadas | `mail*.py`, `ftp.py`, `ftp.sh` | Migrar a `.env` + `python-dotenv` |
| API key de GitHub expuesta en chat | — | Ya recomendado: rotar token |
| `limpiar.bash` sin guarda | `ejecutables/` | Ver §6.3 |

Ver también `tesis_wrf_pgich/docs/SEGURIDAD.md` para las mejoras implementadas
en la ingesta EcoWitt (validación de credenciales, rate limit, logging seguro).

---

## 8. Documentación Existente (referencia)

| Archivo | Contenido | Estado |
|---|---|---|
| `CONFIG_WRF_SAN_JUAN.md` | Configuración WRF (dominio, namelist, FDDA) | ✅ Útil, verificar WRF 4.5 vs 4.6.1 |
| `REPRODUCIR_CICLO.md` | Pasos para reproducir el ciclo | ⚠️ Parcialmente desactualizado (menciona Docker `teachme`) |
| `PLAN_CICLO_WINDOWS_2026-08-05.md` | Plan original Windows+Docker | ❌ Obsoleto (el sistema corre nativo en Linux) |
| `MANUAL.md` (tesis_wrf_pgich) | Manual Streamlit | ❌ Desactualizado (Windows-only, `requirements.txt` inexistente) |
| `docs/SEGURIDAD.md` | Mejoras de seguridad ingesta | ✅ Válido |
| `docs/experimento_nudging_20260812.md` | Experimento caso 08-12 (métricas, fixes) | ✅ Válido |
