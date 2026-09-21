# Caso 3 - Ingreso de frente frio

**Fecha del evento:** 2026-05-16 | **Ciclo:** 00Z -> 12Z | **Informe generado:** 2026-09-20 21:42

## Descripción del evento

Ingreso de un frente frio con descenso de temperatura y rotacion del viento en el centro-este de Argentina. Caso representativo del pasaje frontal.

**Fuente:** SMN (pronostico sinoptico)

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

El dominio de 15 km no resuelve la topografía profunda de la precordillera (errores de altura del modelo de entre +201 m y +918 m en las estaciones, con máximos en CARACOLES +918 m, PUNTA_NEGRA +420 m y CUESTA_Viento +378 m). Por eso el análisis de **Caso 3 - Ingreso de frente frio** se restringe a la **firma térmica** (salto de T2 y caída de RH), y el viento se interpreta solo de forma cualitativa. Ver también `documentacion_proyecto/informe_avances_fases_proyecto.md`.

## Observaciones disponibles

- Registros válidos: **287** en el día, **149** en la ventana 00Z–12Z.
- Estaciones con datos en ventana: **6**

| Estación | Registros (00Z–12Z) |
|----------|--------------------|
| CARACOLES | 25 |
| CUESTA_Viento | 25 |
| ECOHUMUS | 25 |
| INTA_POCITO | 25 |
| PUNTA_NEGRA | 25 |
| VALLE_FERTIL | 24 |

## Resultados: Nudged vs Control

RMSE/Bias de la corrida nudgada (N) y de control (C) por tiempo de validación. dRMSE = RMSE(C) - RMSE(N) (positivo ⇒ mejora con nudging; negativo ⇒ degrada). 00Z: N≡C por construcción.

### T2 (K)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 6 | 3.45 | 3.45 | +0.00 | +1.77 | +1.77 | -0.727 | -0.727 |
| 06Z | 6 | 2.13 | 2.70 | +0.57 | -0.37 | -0.37 | +0.689 | +0.402 |
| 12Z | 6 | 2.48 | 2.25 | -0.23 | -1.18 | -0.98 | -0.011 | +0.134 |


### PSFC (hPa)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 6 | 44.98 | 44.98 | +0.00 | -35.46 | -35.46 | +0.878 | +0.878 |
| 06Z | 6 | 44.20 | 45.21 | +1.01 | -34.23 | -35.47 | +0.877 | +0.876 |
| 12Z | 6 | 46.19 | 47.31 | +1.12 | -36.47 | -37.91 | +0.877 | +0.876 |


### RH (%)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 6 | 22.26 | 22.26 | +0.00 | -21.55 | -21.55 | +0.850 | +0.850 |
| 06Z | 6 | 11.97 | 15.85 | +3.88 | -11.24 | -14.73 | +0.939 | +0.804 |
| 12Z | 6 | 10.09 | 14.23 | +4.14 | +2.32 | -2.13 | +0.293 | +0.077 |


### Wind (m/s)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 6 | 2.90 | 2.90 | +0.00 | +1.32 | +1.32 | -0.334 | -0.334 |
| 06Z | 6 | 2.26 | 1.45 | -0.81 | +1.25 | +0.64 | +0.510 | +0.830 |
| 12Z | 6 | 2.73 | 2.06 | -0.67 | -0.68 | -0.66 | +0.342 | +0.552 |


### Ajuste vs. Generalización (hold-out espacial)

Las estaciones con `rol='evaluacion'` en `config/estaciones.json` nunca se asimilan (quedan fuera de `OBS_DOMAIN101`); sus métricas miden si el nudging **generaliza** a lugares sin datos, no solo si reproduce lo que ya se le dio (estaciones 'asimiladas').

#### T2 (K)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 0 | 3.67 | 3.67 | n/d | n/d |
| 06Z | 5 | 0 | 1.58 | 2.48 | n/d | n/d |
| 12Z | 5 | 0 | 1.54 | 1.08 | n/d | n/d |


#### PSFC (hPa)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 0 | 28.28 | 28.28 | n/d | n/d |
| 06Z | 5 | 0 | 27.17 | 28.23 | n/d | n/d |
| 12Z | 5 | 0 | 28.96 | 30.25 | n/d | n/d |


#### RH (%)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 0 | 23.01 | 23.01 | n/d | n/d |
| 06Z | 5 | 0 | 12.12 | 15.88 | n/d | n/d |
| 12Z | 5 | 0 | 7.56 | 12.46 | n/d | n/d |


#### Wind (m/s)

| Tiempo | N_asim | N_eval | RMSE N (asim) | RMSE C (asim) | RMSE N (eval) | RMSE C (eval) |
|--------|--------|--------|---------------|---------------|---------------|---------------|
| 00Z | 5 | 0 | 3.15 | 3.15 | n/d | n/d |
| 06Z | 5 | 0 | 2.28 | 1.45 | n/d | n/d |
| 12Z | 5 | 0 | 3.00 | 2.21 | n/d | n/d |


### Conclusiones del caso

Para la interpretación completa (series, gráficos y comparación con observaciones) ver `results/2026-05-16_0000z/caso3_frentefrio/` (informe de evolución, tablas por horario y wrfouts).

---
*Informe generado automáticamente por `src/casos/run_casos.py`.*