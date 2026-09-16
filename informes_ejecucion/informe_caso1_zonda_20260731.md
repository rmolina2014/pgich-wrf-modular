# Caso 1 - Viento Zonda

**Fecha del evento:** 2026-07-31 | **Ciclo:** 00Z -> 12Z | **Informe generado:** 2026-09-16 11:16

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
| 00Z | 49 | 4.44 | 4.44 | +0.00 | +2.98 | +2.98 | -0.605 | -0.605 |
| 06Z | 91 | 3.51 | 4.85 | +1.33 | +1.61 | +2.87 | -0.074 | -0.616 |
| 12Z | 91 | 9.13 | 9.28 | +0.15 | -8.87 | -8.86 | +0.786 | +0.674 |


### PSFC (hPa)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 56 | 39.34 | 39.34 | +0.00 | -30.40 | -30.40 | +0.871 | +0.871 |
| 06Z | 104 | 38.98 | 39.35 | +0.37 | -29.81 | -30.34 | +0.866 | +0.865 |
| 12Z | 104 | 39.01 | 38.78 | -0.23 | -30.05 | -29.71 | +0.869 | +0.869 |


### RH (%)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 49 | 27.85 | 27.85 | +0.00 | -24.64 | -24.64 | +0.819 | +0.819 |
| 06Z | 91 | 27.58 | 32.98 | +5.40 | -21.76 | -27.67 | +0.768 | +0.721 |
| 12Z | 91 | 14.67 | 14.02 | -0.65 | +9.55 | +0.91 | +0.627 | +0.611 |


### Wind (m/s)

| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C | r N | r C |
|--------|----|--------|--------|-------|--------|--------|-----|-----|
| 00Z | 49 | 2.32 | 2.32 | +0.00 | +1.63 | +1.63 | -0.187 | -0.187 |
| 06Z | 91 | 3.39 | 4.14 | +0.76 | +2.23 | +2.31 | +0.004 | -0.198 |
| 12Z | 91 | 6.93 | 10.86 | +3.93 | +0.43 | +8.44 | -0.196 | +0.301 |


### Conclusiones del caso

Para la interpretación completa (series, gráficos y comparación con observaciones) ver `results/2026-07-31_0000z/caso1_zonda/` (informe de evolución, tablas por horario y wrfouts).

---
*Informe generado automáticamente por `src/casos/run_casos.py`.*