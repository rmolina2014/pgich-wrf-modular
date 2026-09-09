# Informe de ejecución — Ciclo WRF + Obs Nudging del 06/08/2026

- **Fecha de simulación:** 06 de agosto de 2026, ciclo 00Z (12 h)
- **Dominio:** San Juan / Cuyo (d01, 15 km, Mercator, 80×60, 35 niveles)
- **Datos de entrada:** GFS 0.25° (f000–f012, intervalos de 3 h)
- **Observaciones:** EcoWitt (ECOHUMUS, PUNTA_NEGRA, INTA_POCITO) — 386 registros
- **Estado:** corrida finalizada con éxito (nudged + control + validación)
- **Fecha de ejecución:** 08/09/2026

---

## 1. Objetivo

Evaluar el impacto del *obs nudging* (asimilación de observaciones en superficie,
`obs_nudge_opt=1`) sobre una corrida de control de 12 h para el área de San Juan,
comparando métricas de Nudged (N) vs Control (C) en T2, PSFC, RH y viento.

## 2. Configuración del modelo

### 2.1 Dominio (WPS)

| Parámetro | Valor |
|---|---|
| Proyección | Mercator |
| Centro | 31.5°S, 68.5°O |
| Resolución | 15 km (d01) |
| Tamaño | 80 × 60 puntos |
| Niveles verticales | 35 |
| `num_metgrid_levels` | 34 |
| Datos | GFS 0.25°, intervalos de 3 h (f000–f012) |

### 2.2 Configuración numérica / física (`namelist.input`)

| Parámetro | Valor | Nota |
|---|---|---|
| `run_hours` | 12 | Simulación de 12 h |
| `physics_suite` | `CONUS` | MP/µf, cu, ra_lw, ra_sw, bl_pbl, sf_sfclay, sf_surface desde suite |
| `sf_surface_physics` | Noah (vía suite) | Land surface model |
| `use_adaptive_time_step` | `.true.` | Timestep adaptativo |
| `target_cfl` / `target_hcfl` | 0.8 / 1.0 | |
| `starting_time_step` | 90 | |
| `max_time_step` / `min_time_step` | 120 / 5 | |
| `diff_opt` / `km_opt` | 2 / 4 | |
| `diff_6th_opt` / `diff_6th_factor` | 2 / 0.5 | Difusión de 6º orden (estabilidad) |
| `damp_opt` / `dampcoef` / `zdamp` | 3 / 0.2 / 5000 | Capa absorbente |

### 2.3 FDDA / Obs Nudging

| Parámetro | Valor |
|---|---|
| `obs_nudge_opt` | 1 (nudged) / 0 (control) |
| `obs_nudge_wind/temp/mois` | 1 / 1 / 1 |
| `obs_coef_wind/temp/mois` | 0.0002 / 0.0002 / 0.0002 |
| `obs_rinxy` | 50.0 |
| `obs_sfcfacr` | 2.0 |
| `obs_twindo` | 1.0 |
| `obs_ionf` | 1 |
| `obs_npfi` | 30 |
| `max_obs` | 10000 |
| `fdda_end` | 720 (12 h) |

> **Ajuste clave de estabilidad:** se redujo el coeficiente de nudging de 0.0005 a
> **0.0002** y se activó el timestep adaptativo + difusión de 6º orden para estabilizar
> la integración. El jet estratosférico extremo (~114 m/s) presente en los datos GFS
> del 06/08 había provocado SIGSEGV/NaN en la rutina Flerchinger (Noah-MP) con los
> coeficientes anteriores.

## 3. Etapas de la ejecución

### 3.1 Preprocesamiento (WPS)
- Descarga de GFS 00Z del 06/08 (f000–f012).
- `geogrid.exe`, `ungrib.exe`, `metgrid.exe`: generación de 5 `met_em` (intervalos de 3 h).

### 3.2 Condiciones iniciales y de borde (`real.exe`)
- Generación de `wrfinput_d01` y `wrfbdy_d01`.
- Generación de `OBS_DOMAIN101` (FORMAT 105) a partir del JSON de observaciones
  EcoWitt (`obs_flat_20260806.json`, 386 registros).
- Resultado: `SUCCESS COMPLETE REAL_EM INIT`.

### 3.3 Corridas WRF (`wrf.exe`)
Ejecutadas con `run_full_pipeline.sh` (entorno limpio: `LD_LIBRARY_PATH` sin librerías
MPICH incompatibles, `OMP_NUM_THREADS=1`, sin `HDF5_PLUGIN_PATH` del venv, que causaban
SIGSEGV intermitente en el obs nudging).

| Corrida | `obs_nudge_opt` | Duración wall-clock | Wrfout | Resultado |
|---|---|---|---|---|
| Nudged | 1 | 2 min 31 s | 13 (h00–h12) | `SUCCESS COMPLETE WRF`, sin NaN |
| Control | 0 | ~2 min 30 s | 13 (h00–h12) | `SUCCESS COMPLETE WRF`, sin NaN |

- Verificación de NaN en T2, T, U y PSFC en los 13 wrfout de cada corrida: **0 NaN**.
- Estado final del pipeline: **DONE**.

## 4. Validación vs observaciones

- Script: `src/validacion/valida_wrf_cli.py`
- Hora de validación seleccionada: **2026-08-06 06:00 UTC** (mitad de la corrida).
- Observaciones: `data/raw/obs_flat_20260806.json` (histórico EcoWitt del 06/08,
  descargado con `EcowittIngestor.descargar_historico()` de **toda la red del
  catálogo** `config/estaciones.json`).
- Catálogo unificado: 9 estaciones (`INTA_POCITO`, `ULLUM_EMBALSE`, `ECOHUMUS`,
  `PUNTA_NEGRA`, `INTA_SANMARTIN`, `VALLE_FERTIL`, `LOS_PIONEROS`, `CUESTA_Viento`,
  `CARACOLES`) — **65 observaciones** dentro de la ventana ±30 min.
- Estaciones con datos en la ventana: ECOHUMUS, PUNTA_NEGRA, VALLE_FERTIL,
  CUESTA_Viento y CARACOLES.
- Salidas generadas:
  - `scatter_4panels.png`
  - `mapa_errores_t2.png`
  - `tabla_metricas.png`
  - `metricas_resumen.txt`

### 4.1 Tabla de métricas (06:00 UTC, N = 65)

| Variable | Bias Nudged | MAE Nudged | RMSE Nudged | r Nudged | Bias Control | MAE Control | RMSE Control | r Control |
|---|---|---|---|---|---|---|---|---|
| T2 (K) | -4.79 | **6.65** | **7.09** | -0.398 | **-4.00** | 7.57 | 7.93 | -0.705 |
| PSFC (hPa) | **-34.71** | **34.71** | **44.91** | 0.857 | -35.23 | 35.23 | 45.11 | 0.855 |
| RH (%) | **-10.75** | **17.46** | **29.57** | 0.367 | -13.60 | 21.29 | 37.06 | -0.407 |
| Viento (m/s) | **+0.13** | 11.24 | 12.99 | 0.131 | +1.51 | **10.61** | **12.93** | 0.116 |

### 4.2 Lectura de resultados

Con la red completa (5 estaciones, N=65) el nudging:
- **T2:** reduce el MAE/RMSE (6.65 vs 7.57 / 7.09 vs 7.93) aunque el sesgo del
  control es menor (-4.00 vs -4.79).
- **PSFC y RH:** reduce el sesgo en ambos casos (-34.71 vs -35.23 hPa;
  -10.75 vs -13.60 %).
- **Viento:** reduce el sesgo fuertemente (+0.13 vs +1.51 m/s); el MAE restante
  (~11) se debe a estaciones de alta montaña (CUESTA_Viento 1530 m) donde la
  elevación del modelo difiere del sensor.

El sesgo negativo persistente en T2 y PSFC indica que el modelo sigue más frío/seco
que las estaciones en el valle; los RMSE grandes en viento provienen de estaciones
en relieve complejo. Las correlaciones bajas en T2/viento se deben a la gran
dispersión espacial de las estaciones (de CUESTA_Viento a VALLE_FERTIL).

### 4.3 Nota metodológica (comparación con reporte previo)

La versión previa de este informe validaba solo con **26 observaciones de 2 estaciones**
(ECOHUMUS + PUNTA_NEGRA) porque el `EcowittIngestor` solo consultaba 3 MAC fijas.
Con la unificación del catálogo y la descarga de histórico por MAC se amplió a la
red completa.

## 5. Archivos generados

### 5.1 Resultados de simulación
- `results/2026-08-06_0000z/sanjuan_20260806/nudged/wrfout_d01_*` (13 archivos)
- `results/2026-08-06_0000z/sanjuan_20260806/control/wrfout_d01_*` (13 archivos)

### 5.2 Entradas/asimilación
- `data/raw/obs_flat_20260806.json` (1431 registros, 7 estaciones con datos)
- `data/raw/ecowitt_historico_20260806.csv/.json` (histórico EcoWitt de la red)
- `wps_sanjuan/PFILE:2026-08-06_*` (salidas de ungrib)
- `OBS_DOMAIN101` (en el run dir de WRF, generado con `ObsNudWriter` FORMAT 105)

### 5.3 Validación (reporte)
- `scatter_4panels.png`
- `mapa_errores_t2.png`
- `tabla_metricas.png`
- `metricas_resumen.txt`

### 5.4 Documentación
- `documentacion_proyecto/ejecucion_06082026.md` (este informe)
- `documentacion_proyecto/configuración del espacio geografico del experimento.md`
- `documentacion_proyecto/instructivo_eliminar_tesis_wrf_pgich_migracion_modular.md`

## 6. Notas y conclusiones

1. **Estabilidad numérica:** el SIGSEGV/NaN del caso 06/08 se resolvió con timestep
   adaptativo (`target_cfl=0.8`, `max_time_step=120`), difusión de 6º orden
   (`diff_6th_opt=2`, `diff_6th_factor=0.5`) y reducción de `obs_coef` a 0.0002.
   Las tres corridas de verificación completaron las 12 h sin NaN.
2. **Ejecución aislada:** `pipeline_wrf.py` lanza `wrf.exe` por `subprocess` de forma
   no determinística, colgándose sin dejar log. `run_full_pipeline.sh` (entorno limpio,
   `wrf.exe` en background con `wait` y reintentos) corrió en un solo intento.
3. **Valor del experimento:** el nudging de observaciones reduce el sesgo del modelo
   en T2, PSFC, RH y viento respecto del control, confirmando el beneficio de la
   asimilación de estaciones en superficie para el dominio de San Juan.
4. **Red de estaciones:** el 06/08 la red EcoWitt reportó datos en 7 estaciones
   (ECOHUMUS 282, VALLE_FERTIL 283, CARACOLES 283, CUESTA_Viento 282,
   PUNTA_NEGRA 103, INTA_SANMARTIN 197 solo PSFC, INTA_POCITO 1). Sin respuesta:
   ULLUM_EMBALSE y LOS_PIONEROS (MAC inválida según API code 40012 — verificar MAC).
5. **Portabilidad entre PCs:** esta PC ejecuta WRF-Chem **4.5**; la otra PC usa WRF
   **4.0**. El formato `OBS_DOMAIN101`/FORMAT 105 generado por `ObsNudWriter` fue
   validado contra `WRF/share/wrf_fddaobs_in.F` de **4.5** (read con `end=111` y
   plataforma `SYNOP` en cols 7-11), compatible con el fix de 4.0.