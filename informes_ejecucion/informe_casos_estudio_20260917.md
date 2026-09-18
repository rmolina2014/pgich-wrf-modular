# Informe consolidado de casos de estudio — Fase 4

Generado el 2026-09-17 21:27 por `src/casos/run_casos.py`.

## Resumen de ejecución

| Caso | Fecha | Evento | Estado | Informe |
|------|-------|--------|--------|---------|
| Caso 1 - Viento Zonda | 2026-07-31 | viento_zonda | EJECUTADO | `informes_ejecucion/informe_caso1_zonda_20260731.md` |
| Caso 2 - Calor de verano (Año Nuevo) | 2026-01-01 | calor_verano | EJECUTADO | `informes_ejecucion/informe_caso2_calor_20260101.md` |
| Caso 3 - Ingreso de frente frio | 2026-05-16 | frente_frio | EJECUTADO | `informes_ejecucion/informe_caso3_frentefrio_20260516.md` |

## Métricas por caso (RMSE y r del nudging vs control)

Se reporta el RMSE y el coeficiente de correlación (r) de T2 (K) y RH (%) en la ventana de mayor divergencia (06Z y 12Z).

### Caso 1 - Viento Zonda (2026-07-31)

| Tiempo | RMSE T2 N | RMSE T2 C | r T2 N | r T2 C | RMSE RH N | RMSE RH C | r RH N | r RH C |
|--------|-----------|-----------|--------|--------|-----------|-----------|--------|--------|
| 00Z | 4.43 | 4.43 | -0.610 | -0.610 | 27.96 | 27.96 | +0.818 | +0.818 |
| 06Z | 2.10 | 3.63 | +0.488 | -0.809 | 16.64 | 27.57 | +0.869 | +0.819 |
| 12Z | 9.81 | 11.01 | +0.772 | +0.792 | 25.47 | 27.82 | +0.672 | +0.750 |

### Caso 2 - Calor de verano (Año Nuevo) (2026-01-01)

| Tiempo | RMSE T2 N | RMSE T2 C | r T2 N | r T2 C | RMSE RH N | RMSE RH C | r RH N | r RH C |
|--------|-----------|-----------|--------|--------|-----------|-----------|--------|--------|
| 00Z | 3.74 | 3.74 | +0.305 | +0.305 | 20.50 | 20.50 | +0.394 | +0.394 |
| 06Z | 3.34 | 3.74 | -0.255 | -0.366 | 16.35 | 23.42 | +0.257 | -0.301 |
| 12Z | 5.29 | 5.62 | +0.833 | +0.870 | 7.83 | 8.15 | +0.490 | +0.283 |

### Caso 3 - Ingreso de frente frio (2026-05-16)

| Tiempo | RMSE T2 N | RMSE T2 C | r T2 N | r T2 C | RMSE RH N | RMSE RH C | r RH N | r RH C |
|--------|-----------|-----------|--------|--------|-----------|-----------|--------|--------|
| 00Z | 3.45 | 3.45 | -0.714 | -0.714 | 22.26 | 22.26 | +0.848 | +0.848 |
| 06Z | 2.15 | 2.71 | +0.685 | +0.400 | 12.00 | 15.87 | +0.935 | +0.801 |
| 12Z | 2.54 | 2.31 | -0.009 | +0.110 | 10.77 | 14.72 | +0.274 | +0.072 |

## Limitación del dominio y criterio de análisis

15 km, errores de terreno +201..+918 m. El Zonda (caso 1) se analiza por firma térmica; el viento es cualitativo. Detalles en los informes por caso.

---
*Informe consolidado generado automáticamente.*