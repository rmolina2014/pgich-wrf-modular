# Caso 2 - Calor de verano (Año Nuevo)

**Fecha del evento:** 2026-01-01 | **Ciclo:** 00Z -> 12Z | **Informe generado:** 2026-09-20 21:42

## Descripción del evento

Ola de calor de verano con temperaturas maximas elevadas en el inicio de ano en San Juan. Caso representativo de la circulacion calida de verano.

**Fuente:** SMN (temperaturas maximas de enero), prensa local

## Estado de la ejecución

**Estado:** ✅ EJECUTADO

## Configuración aplicada

| Parámetro | Valor |
|-----------|-------|
| Dominio | 1 dominio, 15 km, 80×60, mercator (-31.5°, -68.5°) |
| Ciclo | 00Z–12Z (12 h) |
| Forzante | GFS 0.25° (AWS) |
| Obs nudging | `obs_nudge_opt=1`, coef viento/temp/humedad=0.0001, `obs_twindo=1.0` |
| Nudged vs Control | misma inicialización; solo cambia `obs_nudge_opt` (1 vs 0) |
| Validación | multi-temporal 00Z 06Z 12Z vs observaciones de estaciones |

## Limitación conocida del dominio (relevant para el análisis)

El dominio de 15 km no resuelve la topografía profunda de la precordillera (errores de altura del modelo de entre +201 m y +918 m en las estaciones, con máximos en CARACOLES +918 m, PUNTA_NEGRA +420 m y CUESTA_Viento +378 m). Por eso el análisis de **Caso 2 - Calor de verano (Año Nuevo)** se restringe a la **firma térmica** (salto de T2 y caída de RH), y el viento se interpreta solo de forma cualitativa. Ver también `documentacion_proyecto/informe_avances_fases_proyecto.md`.

## Observaciones disponibles

- Registros válidos: **290** en el día, **152** en la ventana 00Z–12Z.
- Estaciones con datos en ventana: **7**

| Estación | Registros (00Z–12Z) |
|----------|--------------------|
| CARACOLES | 25 |
| CUESTA_Viento | 25 |
| ECOHUMUS | 25 |
| PUNTA_NEGRA | 25 |
| ULLUM_EMBALSE | 25 |
| VALLE_FERTIL | 25 |
| INTA_POCITO | 2 |

## Resultados: Nudged vs Control

RMSE/Bias de la corrida nudgada (N) y de control (C) por tiempo de validación. dRMSE = RMSE(C) - RMSE(N) (positivo ⇒ mejora con nudging; negativo ⇒ degrada). 00Z: N≡C por construcción.

### T2 (K)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 3.66 | 3.66 | +0.00 | +1.14 | +1.14 | +0.350 | +0.350 |
| 06Z | 6 | 3.33 | 3.73 | +0.40 | -0.12 | +0.83 | -0.258 | -0.371 |
| 12Z | 6 | 5.27 | 5.61 | +0.34 | -4.74 | -5.19 | +0.863 | +0.902 |


### PSFC (hPa)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 41.63 | 41.63 | +0.00 | -32.71 | -32.71 | +0.874 | +0.874 |
| 06Z | 6 | 41.78 | 41.72 | -0.06 | -31.04 | -31.03 | +0.859 | +0.859 |
| 12Z | 6 | 41.31 | 41.55 | +0.25 | -30.86 | -31.14 | +0.860 | +0.859 |


### RH (%)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 19.71 | 19.71 | +0.00 | -16.10 | -16.10 | +0.441 | +0.441 |
| 06Z | 6 | 16.21 | 23.32 | +7.10 | -9.62 | -17.99 | +0.260 | -0.305 |
| 12Z | 6 | 7.75 | 8.07 | +0.32 | +4.04 | +4.22 | +0.502 | +0.290 |


### Wind (m/s)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 4.33 | 4.33 | +0.00 | +4.12 | +4.12 | +0.408 | +0.408 |
| 06Z | 6 | 1.82 | 1.21 | -0.61 | +1.58 | +1.00 | +0.407 | +0.598 |
| 12Z | 6 | 1.05 | 1.42 | +0.37 | +0.40 | +0.06 | +0.104 | -0.388 |


### Ajuste vs. Generalización (hold-out espacial)

Las estaciones con `rol='evaluacion'` en `config/estaciones.json` nunca se asimilan (quedan fuera de `OBS_DOMAIN101`); sus métricas miden si el nudging **generaliza** a lugares sin datos, no solo si reproduce lo que ya se le dio (estaciones 'asimiladas').

#### T2 (K)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 2 | 3.85 | 3.85 | 3.14 | 3.14 |
| 06Z | 4 | 2 | 3.66 | 4.23 | 2.54 | 2.43 |
| 12Z | 4 | 2 | 4.88 | 5.15 | 5.97 | 6.42 |


#### PSFC (hPa)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 2 | 28.75 | 28.75 | 63.24 | 63.24 |
| 06Z | 4 | 2 | 27.71 | 27.66 | 60.84 | 60.76 |
| 12Z | 4 | 2 | 27.22 | 27.41 | 60.30 | 60.65 |


#### RH (%)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 2 | 23.07 | 23.07 | 5.49 | 5.49 |
| 06Z | 4 | 2 | 17.87 | 24.88 | 12.26 | 19.84 |
| 12Z | 4 | 2 | 9.28 | 9.36 | 2.82 | 4.52 |


#### Wind (m/s)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 2 | 4.13 | 4.13 | 4.79 | 4.79 |
| 06Z | 4 | 2 | 2.05 | 1.23 | 1.25 | 1.15 |
| 12Z | 4 | 2 | 1.15 | 1.70 | 0.84 | 0.53 |


### Conclusiones del caso

Para la interpretación completa (series, gráficos y comparación con observaciones) ver `results/2026-01-01_0000z/caso2_calor/` (informe de evolución, tablas por horario y wrfouts).

---
*Informe generado automáticamente por `src/casos/run_casos.py`.*