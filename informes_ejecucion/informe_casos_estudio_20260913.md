# Informe consolidado de casos de estudio — Fase 4

Generado el 2026-09-13 00:58 por `src/casos/run_casos.py`.

## Resumen de ejecución

| Caso | Fecha | Evento | Estado | Informe |
|------|-------|--------|--------|---------|
| Caso 1 - Viento Zonda | 2026-07-31 | viento_zonda | EJECUTADO | `informes_ejecucion/informe_caso1_zonda_20260731.md` |
| Caso 2 - Calor de verano (Año Nuevo) | 2026-01-01 | calor_verano | EJECUTADO | `informes_ejecucion/informe_caso2_calor_20260101.md` |
| Caso 3 - Ingreso de frente frio | 2026-05-16 | frente_frio | EJECUTADO | `informes_ejecucion/informe_caso3_frentefrio_20260516.md` |

## Métricas por caso (RMSE del nudging vs control)

Se reporta el RMSE de T2 (K) y RH (%) en la ventana de mayor divergencia (06Z y 12Z).

### Caso 1 - Viento Zonda (2026-07-31)

| Tiempo | RMSE T2 N | RMSE T2 C | RMSE RH N | RMSE RH C |
|--------|-----------|-----------|-----------|-----------|
| 00Z | 4.44 | 4.44 | 27.85 | 27.85 |
| 06Z | 3.51 | 4.85 | 27.58 | 32.98 |
| 12Z | 9.13 | 9.28 | 14.67 | 14.02 |

### Caso 2 - Calor de verano (Año Nuevo) (2026-01-01)

| Tiempo | RMSE T2 N | RMSE T2 C | RMSE RH N | RMSE RH C |
|--------|-----------|-----------|-----------|-----------|
| 00Z | 3.74 | 3.74 | 20.50 | 20.50 |
| 06Z | 3.34 | 3.74 | 16.35 | 23.42 |
| 12Z | 5.29 | 5.62 | 7.83 | 8.15 |

### Caso 3 - Ingreso de frente frio (2026-05-16)

| Tiempo | RMSE T2 N | RMSE T2 C | RMSE RH N | RMSE RH C |
|--------|-----------|-----------|-----------|-----------|
| 00Z | 3.45 | 3.45 | 22.26 | 22.26 |
| 06Z | 2.15 | 2.71 | 12.00 | 15.87 |
| 12Z | 2.54 | 2.31 | 10.77 | 14.72 |

## Limitación del dominio y criterio de análisis

15 km, errores de terreno +201..+918 m. El Zonda (caso 1) se analiza por firma térmica; el viento es cualitativo. Detalles en los informes por caso.

---
*Informe consolidado generado automáticamente.*