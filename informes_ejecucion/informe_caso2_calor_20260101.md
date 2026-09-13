# Caso 2 - Calor de verano (Año Nuevo)

**Fecha del evento:** 2026-01-01 | **Ciclo:** 00Z -> 12Z | **Informe generado:** 2026-09-13 00:11

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
| Validación | multi-temporal 00Z, 06Z, 12Z vs observaciones de estaciones |

## Limitación conocida del dominio (relevant para el análisis)

El dominio de 15 km no resuelve la topografía profunda de la precordillera (errores de altura del modelo de entre +201 m y +918 m en las estaciones, con máximos en CARACOLES +918 m, PUNTA_NEGRA +420 m y CUESTA_Viento +378 m). Por eso el análisis del caso 1 (Zonda) se restringe a la **firma térmica** (salto de T2 y caída de RH), y el viento se interpreta solo de forma cualitativa. Ver también `documentacion_proyecto/informe_avances_fases_proyecto.md`.

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

RMSE/Bias de la corrida nudgada (N) y de control (C) por tiempo de validación. dRMSE = RMSE(C) - RMSE(N) (negativo ⇒ el nudging no degrada). 00Z: N≡C por construcción.

### T2 (K)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 14 | 3.74 | 3.74 | +0.00 | +1.14 | +1.14 |
| 06Z | 18 | 3.34 | 3.74 | +0.40 | -0.12 | +0.83 |
| 12Z | 18 | 5.29 | 5.62 | +0.34 | -4.74 | -5.19 |


### PSFC (hPa)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 14 | 41.63 | 41.63 | +0.00 | -32.71 | -32.71 |
| 06Z | 18 | 41.78 | 41.72 | -0.06 | -31.04 | -31.03 |
| 12Z | 18 | 41.31 | 41.56 | +0.25 | -30.86 | -31.14 |


### RH (%)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 14 | 20.50 | 20.50 | +0.00 | -16.10 | -16.10 |
| 06Z | 18 | 16.35 | 23.42 | +7.06 | -9.62 | -17.99 |
| 12Z | 18 | 7.83 | 8.15 | +0.32 | +4.04 | +4.22 |


### Wind (m/s)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 14 | 4.62 | 4.62 | +0.00 | +0.61 | +0.61 |
| 06Z | 18 | 3.37 | 3.52 | +0.15 | -0.77 | -1.35 |
| 12Z | 18 | 5.17 | 5.68 | +0.51 | -3.97 | -4.31 |


### Conclusiones del caso

Para la interpretación completa (series, gráficos y comparación con observaciones) ver `results/2026-01-01_0000z/caso2_calor/` (informe de evolución, tablas por horario y wrfouts).

---
*Informe generado automáticamente por `src/casos/run_casos.py`.*