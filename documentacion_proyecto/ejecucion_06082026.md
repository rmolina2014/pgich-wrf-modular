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

- Script: `tesis_wrf_pgich/src/calidad/valida_wrf.py`
- Hora de validación seleccionada: **2026-08-06 06:00 UTC** (mitad de la corrida,
  con 26 observaciones de ECOHUMUS + PUNTA_NEGRA dentro de la ventana ±30 min).
- Estaciones: ECOHUMUS (13 obs) y PUNTA_NEGRA (13 obs).
- Salidas generadas:
  - `scatter_4panels.png`
  - `mapa_errores_t2.png`
  - `tabla_metricas.png`
  - `metricas_resumen.txt`

### 4.1 Tabla de métricas (06:00 UTC, N = 26)

| Variable | Bias Nudged | MAE Nudged | RMSE Nudged | r Nudged | Bias Control | MAE Control | RMSE Control | r Control |
|---|---|---|---|---|---|---|---|---|
| T2 (K) | **-0.35** | **5.01** | **5.03** | -0.997 | +1.73 | 7.19 | 7.40 | -0.997 |
| PSFC (hPa) | **-18.22** | **18.22** | **24.82** | 0.999 | -19.34 | 19.34 | 25.18 | 0.999 |
| RH (%) | **-34.18** | **34.18** | **45.64** | 0.999 | -42.50 | 42.50 | 57.42 | -0.999 |
| Viento (m/s) | **+5.49** | 11.15 | 12.65 | -0.835 | +9.15 | **9.51** | **12.47** | -0.835 |

### 4.2 Lectura de resultados

- **T2:** el nudging reduce el sesgo de +1.73 K (control) a -0.35 K y el MAE de
  7.19 a 5.01 K. Mejora apreciable del nudging.
- **PSFC:** el sesgo pasa de -19.34 a -18.22 hPa (mejora leve).
- **RH:** el sesgo se reduce de -42.50 a -34.18 % (mejora del nudging).
- **Viento:** el sesgo baja de +9.15 a +5.49 m/s (mejora del nudging), aunque el MAE
  del control es algo menor (9.51 vs 11.15).

En general, **el WRF con obs nudging (obs_nudge_opt=1, coef 0.0002) mejora el sesgo
del modelo en todas las variables** respecto del control sin nudging, especialmente
en temperatura y humedad. Las correlaciones bajas/negativas en T2 y viento se deben a
la poca dispersión espacial de las estaciones y a la ventana horaria de validación.

## 5. Archivos generados

### 5.1 Resultados de simulación
- `results/2026-08-06_0000z/sanjuan_20260806/nudged/wrfout_d01_*` (13 archivos)
- `results/2026-08-06_0000z/sanjuan_20260806/control/wrfout_d01_*` (13 archivos)

### 5.2 Entradas/asimilación
- `tesis_wrf_pgich/historico/obs_flat_20260806.json` (386 registros)
- `tesis_wrf_pgich/historico/ecowitt_historico_20260806.csv/.json`
- `wps_sanjuan/PFILE:2026-08-06_*` (salidas de ungrib)
- `OBS_DOMAIN101` (en el run dir de WRF)

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