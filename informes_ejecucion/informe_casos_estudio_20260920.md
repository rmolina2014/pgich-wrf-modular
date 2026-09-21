# Informe consolidado de casos de estudio — Fase 4

Generado el 2026-09-20 21:53 por `src/casos/run_casos.py`.

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
| 01Z | 2.86 | 5.08 | +0.208 | -0.878 | 24.80 | 33.39 | +0.713 | +0.629 |
| 02Z | 2.48 | 4.93 | +0.511 | -0.891 | 27.07 | 34.57 | +0.690 | +0.659 |
| 03Z | 2.14 | 4.70 | +0.745 | -0.447 | 26.90 | 36.21 | +0.681 | +0.682 |
| 04Z | 2.34 | 4.92 | +0.689 | -0.740 | 27.29 | 37.19 | +0.627 | +0.611 |
| 05Z | 1.62 | 4.21 | +0.882 | -0.481 | 24.87 | 33.54 | +0.671 | +0.670 |
| 06Z | 2.10 | 3.63 | +0.488 | -0.809 | 16.64 | 27.57 | +0.869 | +0.819 |
| 07Z | 5.26 | 6.16 | +0.418 | -0.881 | 11.38 | 23.83 | +0.946 | +0.849 |
| 08Z | 6.23 | 6.73 | +0.675 | -0.568 | 14.72 | 22.65 | +0.925 | +0.826 |
| 09Z | 6.72 | 7.01 | +0.749 | -0.373 | 17.81 | 19.47 | +0.891 | +0.852 |
| 10Z | 7.90 | 7.30 | +0.718 | -0.182 | 22.01 | 19.11 | +0.831 | +0.770 |
| 11Z | 8.98 | 8.71 | +0.340 | +0.200 | 24.60 | 18.53 | +0.778 | +0.807 |
| 12Z | 9.81 | 11.01 | +0.772 | +0.792 | 25.47 | 27.82 | +0.672 | +0.750 |

### Caso 2 - Calor de verano (Año Nuevo) (2026-01-01)

| Tiempo | RMSE T2 N | RMSE T2 C | r T2 N | r T2 C | RMSE RH N | RMSE RH C | r RH N | r RH C |
|--------|-----------|-----------|--------|--------|-----------|-----------|--------|--------|
| 00Z | 3.66 | 3.66 | +0.350 | +0.350 | 19.71 | 19.71 | +0.441 | +0.441 |
| 06Z | 3.33 | 3.73 | -0.258 | -0.371 | 16.21 | 23.32 | +0.260 | -0.305 |
| 12Z | 5.27 | 5.61 | +0.863 | +0.902 | 7.75 | 8.07 | +0.502 | +0.290 |

### Caso 3 - Ingreso de frente frio (2026-05-16)

| Tiempo | RMSE T2 N | RMSE T2 C | r T2 N | r T2 C | RMSE RH N | RMSE RH C | r RH N | r RH C |
|--------|-----------|-----------|--------|--------|-----------|-----------|--------|--------|
| 00Z | 3.45 | 3.45 | -0.727 | -0.727 | 22.26 | 22.26 | +0.850 | +0.850 |
| 06Z | 2.13 | 2.70 | +0.689 | +0.402 | 11.97 | 15.85 | +0.939 | +0.804 |
| 12Z | 2.48 | 2.25 | -0.011 | +0.134 | 10.09 | 14.23 | +0.293 | +0.077 |

## Limitación del dominio y criterio de análisis

15 km, errores de terreno +201..+918 m. En todos los casos el análisis se apoya en la firma térmica (T2/RH); el viento se interpreta de forma cualitativa. Detalles en los informes por caso.

---
*Informe consolidado generado automáticamente.*