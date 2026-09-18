# Caso 1 - Viento Zonda

**Fecha del evento:** 2026-07-31 | **Ciclo:** 00Z -> 12Z | **Informe generado:** 2026-09-17 21:27

## Descripción del evento

Jornada con alerta naranja por viento Zonda en el oeste de San Juan (Diario de Cuyo, 31/07/2026); rafagas > 70 km/h, min ~7 C y max ~28 C. Analisis restringido a la firma termica (salto de T2 y caida de RH) por la limitacion del dominio de 15 km (ver informe). El viento se reporta de forma cualitativa.

**Fuente:** Diario de Cuyo (31/07/2026), SMN (alerta naranja)

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

- Registros válidos: **1880** en el día, **984** en la ventana 00Z–12Z.
- Estaciones con datos en ventana: **7**

| Estación | Registros (00Z–12Z) |
|----------|--------------------|
| CARACOLES | 145 |
| CUESTA_Viento | 145 |
| ECOHUMUS | 145 |
| PUNTA_NEGRA | 145 |
| VALLE_FERTIL | 145 |
| ULLUM_EMBALSE | 134 |
| INTA_POCITO | 125 |

## Resultados: Nudged vs Control

RMSE/Bias de la corrida nudgada (N) y de control (C) por tiempo de validación. dRMSE = RMSE(C) - RMSE(N) (positivo ⇒ mejora con nudging; negativo ⇒ degrada). 00Z: N≡C por construcción.

### T2 (K)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 4.43 | 4.43 | +0.00 | +2.98 | +2.98 | -0.610 | -0.610 |
| 06Z | 7 | 2.10 | 3.63 | +1.53 | -0.68 | +1.82 | +0.488 | -0.809 |
| 12Z | 7 | 9.81 | 11.01 | +1.20 | -9.62 | -10.83 | +0.772 | +0.792 |


### PSFC (hPa)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 8 | 41.92 | 41.92 | +0.00 | -32.39 | -32.39 | +0.861 | +0.861 |
| 06Z | 8 | 42.14 | 42.45 | +0.31 | -32.17 | -32.78 | +0.859 | +0.861 |
| 12Z | 8 | 43.54 | 43.48 | -0.06 | -33.85 | -33.74 | +0.861 | +0.860 |


### RH (%)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 27.96 | 27.96 | +0.00 | -24.75 | -24.75 | +0.818 | +0.818 |
| 06Z | 7 | 16.64 | 27.57 | +10.92 | -11.56 | -24.34 | +0.869 | +0.819 |
| 12Z | 7 | 25.47 | 27.82 | +2.35 | +22.34 | +21.41 | +0.672 | +0.750 |


### Wind (m/s)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 7 | 2.32 | 2.32 | +0.00 | +1.65 | +1.65 | -0.192 | -0.192 |
| 06Z | 7 | 1.97 | 2.32 | +0.35 | +1.51 | +1.80 | +0.217 | -0.424 |
| 12Z | 7 | 5.05 | 5.07 | +0.02 | -1.77 | -1.34 | +0.160 | +0.091 |


### Conclusiones del caso

Para la interpretación completa (series, gráficos y comparación con observaciones) ver `results/2026-07-31_0000z/caso1_zonda/` (informe de evolución, tablas por horario y wrfouts).

---
*Informe generado automáticamente por `src/casos/run_casos.py`.*