# Caso 3 - Ingreso de frente frio

**Fecha del evento:** 2026-05-16 | **Ciclo:** 00Z -> 12Z | **Informe generado:** 2026-09-13 00:58

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
| Validación | multi-temporal 00Z, 06Z, 12Z vs observaciones de estaciones |

## Limitación conocida del dominio (relevant para el análisis)

El dominio de 15 km no resuelve la topografía profunda de la precordillera (errores de altura del modelo de entre +201 m y +918 m en las estaciones, con máximos en CARACOLES +918 m, PUNTA_NEGRA +420 m y CUESTA_Viento +378 m). Por eso el análisis del caso 1 (Zonda) se restringe a la **firma térmica** (salto de T2 y caída de RH), y el viento se interpreta solo de forma cualitativa. Ver también `documentacion_proyecto/informe_avances_fases_proyecto.md`.

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

RMSE/Bias de la corrida nudgada (N) y de control (C) por tiempo de validación. dRMSE = RMSE(C) - RMSE(N) (negativo ⇒ el nudging no degrada). 00Z: N≡C por construcción.

### T2 (K)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 12 | 3.45 | 3.45 | +0.00 | +1.77 | +1.77 |
| 06Z | 18 | 2.15 | 2.71 | +0.56 | -0.37 | -0.37 |
| 12Z | 18 | 2.54 | 2.31 | -0.23 | -1.18 | -0.98 |


### PSFC (hPa)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 12 | 44.98 | 44.98 | +0.00 | -35.46 | -35.46 |
| 06Z | 18 | 44.20 | 45.21 | +1.01 | -34.23 | -35.47 |
| 12Z | 18 | 46.19 | 47.31 | +1.12 | -36.47 | -37.91 |


### RH (%)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 12 | 22.26 | 22.26 | +0.00 | -21.55 | -21.55 |
| 06Z | 18 | 12.00 | 15.87 | +3.87 | -11.24 | -14.73 |
| 12Z | 18 | 10.77 | 14.72 | +3.95 | +2.32 | -2.13 |


### Wind (m/s)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |
|--------|----|--------|--------|-------|--------|--------|
| 00Z | 12 | 6.12 | 6.12 | +0.00 | -0.90 | -0.90 |
| 06Z | 18 | 7.70 | 7.26 | -0.44 | -2.22 | -2.83 |
| 12Z | 18 | 11.45 | 11.23 | -0.23 | -8.32 | -8.30 |


### Conclusiones del caso

Para la interpretación completa (series, gráficos y comparación con observaciones) ver `results/2026-05-16_0000z/caso3_frentefrio/` (informe de evolución, tablas por horario y wrfouts).

---
*Informe generado automáticamente por `src/casos/run_casos.py`.*