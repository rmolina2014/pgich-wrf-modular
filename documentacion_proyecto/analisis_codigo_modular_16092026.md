# Análisis del código modular — 16/09/2026 (revisión)

## Alcance y conclusión

Este documento actualiza [el análisis del 14/09/2026](analisis_codigo_modular_14092026.md), que revisó el núcleo del proyecto, la configuración, las pruebas y los informes existentes para evaluar su objetivo: comparar ejecuciones del modelo WRF con y sin asimilación de datos de estaciones meteorológicas.

De los seis hallazgos del análisis original, **tres ya fueron corregidos en commits posteriores** (unidades del viento, signo de dRMSE y propagación de errores de validación), **uno (reuso del control) se corrige en esta revisión**, y **dos quedan en evaluación** (independencia de la evaluación y emparejamiento temporal/ponderación), sin cambios de código por decisión del equipo.

El circuito implementado (observaciones EcoWitt → QC → Little_R/OBS_DOMAIN101 → GFS/WPS → WRF nudged + control → validación) permite la comparación con/sin asimilación, pero las métricas de viento de los informes generados antes del fix de unidades son inválidas y fueron regeneradas en esta misma revisión.

## Circularidad de la revisión

Como trabajo nuevo desde el análisis del 14/09, se aplicaron dos commits de corrección y esta revisión agrega la verificación del control:

| Commit | Contenido |
|---|---|
| `e7cc715` | Fix de unidades de viento en `valida_wrf_cli.py` (km/h → m/s). |
| `224c199` | Fix de 3 bugs: `wrf_runner_cli.py` (crash `AttributeError`), `pipeline_wrf.py` (return 0 aunque falle validación) y texto de dRMSE en `run_casos.py`. |
| *este trabajo* | Fix de reuso del control sin verificar (h2 H6): manifest `control_manifest.json`. |

## Circuito implementado

1. Obtener observaciones EcoWitt y aplicar controles de calidad.
2. Generar Little_R y `OBS_DOMAIN101`; este último se construye directamente desde los datos depurados, sin utilizar el archivo Little_R como entrada de esa conversión.
3. Preparar condiciones meteorológicas mediante GFS y WPS.
4. Ejecutar WRF con nudging y una corrida de control.
5. Comparar temperatura, humedad, presión y velocidad del viento mediante sesgo, MAE, RMSE y correlación.

La técnica utilizada es **nudging observacional**: WRF ajusta campos cerca de las estaciones según sus observaciones. Esto coincide con la descripción de [NCAR en la guía de WRF](https://www2.mmm.ucar.edu/wrf/users/wrf_users_guide/build/html/running_wrf.html).

La organización principal del código es:

| Componente | Responsabilidad |
|---|---|
| `src/ingesta/` | Obtención de observaciones EcoWitt y datos GFS. |
| `src/calidad/` | Limpieza, normalización y controles de calidad. |
| `src/asimilacion/` | Generación de Little_R y OBS_DOMAIN101. |
| `src/modelo/` | Configuración y ejecución de WPS y WRF. |
| `src/preflight/` | Comprobaciones previas a las corridas. |
| `src/validacion/` | Extracción de variables y cálculo de métricas. |
| `src/reporting/` | Reportes, gráficos y registro de experimentos. |
| `src/casos/` | Orquestación de casos de estudio. |
| `pipeline_wrf.py` | Coordinación de preparación, corridas y validación. |

## Estado de los hallazgos

| Prioridad | Hallazgo | Estado (16/09/2026) |
|---|---|---|
| Alta | Unidades del viento en el validador | ✅ **Corregido** (commit `e7cc715`; informes regenerados). |
| Alta | Misma obs para asimilación y evaluación | ⏳ **En evaluación** (sin cambios). |
| Alta | Emparejamiento ±30 min / múltiples registros por estación | ⏳ **En evaluación** (sin cambios). |
| Alta | Pipeline devuelve éxito aunque falle la validación | ✅ **Corregido** (commit `224c199`). |
| Media | Signo de dRMSE interpretado al revés | ✅ **Corregido** (commit `224c199`; informes regenerados). |
| Media | Reuso del control sin verificar configuración | ✅ **Corregido** (esta revisión). |

### 1. Unidades del viento — CORREGIDO

El validador ahora convierte la velocidad observada de km/h a m/s (`valida_wrf_cli.py`, asignación de `speed`). Se regeneraron la validación 00/06/12Z y los informes de los tres casos de estudio. Ejemplo del cambio en el caso 1 (Zonda, 12Z): el RMSE de viento pasó de ~20 (km/h comparados contra m/s) a **6,93 m/s (N) vs 10,86 m/s (C)**.

| Caso y tiempo | RMSE viento C | RMSE viento N |
|---|---:|---:|
| Zonda, 06Z | 4,14 | 3,39 |
| Zonda, 12Z | 10,86 | 6,93 |

Fuente: `results/2026-07-31_0000z/caso1_zonda/informe_evolucion_nudging.txt`.

### 2. Independencia de la evaluación — EN EVALUACIÓN

El pipeline prepara la asimilación a partir de `args.json` y pasa ese mismo archivo al proceso de validación (`pipeline_wrf.py`, preparación y llamada a `run_valida_wrf`). No se establece separación explícita entre observaciones a asimilar y a evaluar.

La comparación mide ajuste a los datos utilizados, no generalización. El equipo evalúa cómo y cuándo introducir una estrategia de estaciones u observaciones independientes (hold-out) dentro del alcance del anteproyecto. Sin cambios implementados en esta revisión.

### 3. Emparejamiento temporal y ponderación — EN EVALUACIÓN

El validador conserva todos los registros dentro de ±30 min del instante de evaluación (`validacion`, `cargar_estaciones_desde_json` y `build_tables`). Cada registro se compara contra el campo del modelo al instante único, por lo que una estación puede aparecer varias veces y las de mayor cobertura pesan más. Por ejemplo, el informe de Zonda registra 91 pares válidos de T2 a las 06Z aunque documenta siete estaciones con datos.

El equipo evalúa definir un criterio explícito (observación más cercana por estación, promedio temporal, o emparejamiento con salidas temporalmente equivalentes). Sin cambios implementados en esta revisión.

### 4. Propagación de errores de validación — CORREGIDO

`pipeline()` ahora termina con `return 0 if valid_ok else 1` (`pipeline_wrf.py`). El gestor de casos (`src/casos/run_casos.py`) interpreta rc==0 como `EJECUTADO`, por lo que una validación fallida ya no queda silenciosamente marcada como exitosa.

### 5. Signo de la mejora del RMSE — CORREGIDO

El texto del informe ahora explica correctamente `dRMSE = RMSE(control) − RMSE(nudged)`: positivo ⇒ mejora con nudging; negativo ⇒ degradación (`src/casos/run_casos.py`). Los informes de los casos fueron regenerados con la explicación corregida.

### 6. Reuso de la corrida de control — CORREGIDO (esta revisión)

Antes, el control se reutilizaba si existía cualquier `wrfout_d01*`, sin verificar que correspondiera a la configuración, el período y las entradas del experimento actual (`pipeline_wrf.py`, bloque de corrida control).

Ahora, al generar el control se registra `case_dir/control_manifest.json` con el SHA-256 del `namelist_control.input`, la fecha/hora de inicio y la duración del período. Antes de reutilizar, `_control_reutilizable()` verifica:

- que existan wrfout y que la fecha de inicio coincida con el período del experimento;
- que exista el manifest;
- que el SHA-256 del `namelist_control.input` actual coincida con el guardado.

Si alguna condición falla, se re-corre el control. Se agregaron 6 pruebas unitarias (`tests/test_run_casos.py`).

## Lectura de los resultados existentes

Los informes regenerados muestran un comportamiento variable del nudging según el caso y la hora (solo T2/RH se citan aquí; el viento, ya corregido, se interpreta de forma cualitativa en el caso Zonda):

| Caso y tiempo | RMSE T2 control | RMSE T2 nudging | Lectura |
|---|---:|---:|---|
| Zonda, 06Z | 4,85 K | 3,51 K | Mejora en la comparación reportada. |
| Frente frío, 12Z | 2,31 K | 2,54 K | Degradación en la comparación reportada. |

Fuente: [informe consolidado de casos del 16/09/2026](../informes_ejecucion/informe_casos_estudio_20260916.md).

Estos valores no permiten afirmar una mejora uniforme. Además de los problemas de validación aún en evaluación (independencia y emparejamiento), el dominio de 15 km y los errores de elevación documentados condicionan la comparación con estaciones. El informe de Zonda señala diferencias de altura del modelo de entre +201 y +918 m y restringe la interpretación del evento a su firma térmica, con evaluación cualitativa del viento.

## Verificación realizada

A diferencia del análisis del 14/09 (donde la recolección de `test_circuito_modular.py` y `test_validacion_multitemporal.py` falló por ausencia de `xarray`), en el entorno actual el `.venv` del proyecto declara `xarray` y la suite completa se ejecuta:

```text
.venv/bin/python -m pytest tests/ -q
```

Resultado: **35 pruebas aprobadas** (29 previas + 6 nuevas del manifest de control). Estas pruebas no sustituyen un experimento independiente de generalización ni una ejecución de WRF dominada fuera de la evaluación en curso.

## Prioridades propuestas

1. ✅ Corregir unidades del viento (hecho), signo de dRMSE (hecho) y propagación de errores (hecho).
2. ✅ Verificar la reutilización de corridas de control (hecho en esta revisión).
3. ⏳ Definir emparejamiento temporal por estación y documentar la ponderación (en evaluación).
4. ⏳ Separar observaciones de asimilación y evaluación para medir desempeño independiente (en evaluación).
5. ⏳ Revisar la independencia de la evaluación y, si se decide, incorporar estaciones hold-out.
6. ⏳ Ampliar las corridas una vez estabilizado y verificado el procedimiento.

La prioridad es cerrar la evaluación de emparejamiento e independencia antes de ampliar el conjunto de experimentos.