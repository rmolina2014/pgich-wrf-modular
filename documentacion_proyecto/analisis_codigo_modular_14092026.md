# Análisis del código modular — 14/09/2026

## Alcance y conclusión

Se revisaron el núcleo del proyecto, la configuración, las pruebas y los informes existentes para evaluar su objetivo: comparar ejecuciones del modelo WRF con y sin asimilación de datos de estaciones meteorológicas.

La estructura permite realizar esa comparación, pero hay problemas en la validación que deben corregirse antes de sacar conclusiones definitivas sobre la mejora producida por la asimilación.

No se modificó el código ni se ejecutó WRF durante esta revisión. Los resultados meteorológicos citados provienen de los informes guardados; no fueron recalculados.

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

## Hallazgos principales

| Prioridad | Hallazgo | Consecuencia |
|---|---|---|
| Alta | El validador toma el viento observado en km/h y lo compara con WRF en m/s, sin dividir por 3,6. | Las métricas de viento quedan afectadas. |
| Alta | El pipeline entrega el mismo archivo de observaciones a la asimilación y a la evaluación. | Mide ajuste a datos utilizados; no demuestra por sí solo mejora frente a observaciones independientes. |
| Alta | Se comparan todas las observaciones de una ventana de ±30 minutos con una única salida del modelo. | Una estación aparece varias veces y las estaciones con mayor cobertura pesan más. |
| Alta | El pipeline devuelve éxito incluso cuando falla la validación. | Un caso puede quedar marcado como ejecutado sin evaluación satisfactoria. |
| Media | Los informes interpretan incorrectamente el signo de `RMSE(control) − RMSE(nudged)`. | Un valor positivo indica mejora; uno negativo, degradación. |
| Media | Se reutiliza el control existente sin comprobar que corresponde a la configuración y entradas actuales. | Puede comprometer la comparabilidad entre experimentos. |

### 1. Unidades del viento

El cliente EcoWitt y las reglas de calidad manejan el viento en km/h. El generador de OBS_DOMAIN101 convierte esa velocidad a m/s mediante una división por 3,6. Sin embargo, `cargar_estaciones_desde_json` en el validador asigna directamente `float(speed)` a la velocidad observada y luego la compara con la velocidad de WRF en m/s.

Se debe unificar el contrato de unidades y corregir la conversión antes de recalcular las métricas de viento.

Referencias: [cliente EcoWitt](../src/ingesta/ecowitt_client.py), [reglas de calidad](../src/calidad/qc_rules.py), [generador OBS_DOMAIN101](../src/asimilacion/obsnud_writer.py) y [validador](../src/validacion/valida_wrf_cli.py), especialmente la asignación de `speed` alrededor de la línea 89.

### 2. Independencia de la evaluación

El pipeline prepara la asimilación a partir de `args.json` y pasa ese mismo archivo al proceso de validación. En el circuito revisado no se establece una separación explícita entre observaciones destinadas a asimilar y observaciones destinadas a evaluar.

Esta comparación es útil para medir el ajuste a las observaciones utilizadas, pero no basta para demostrar capacidad de generalización. Para ese objetivo se propone reservar estaciones u observaciones independientes y distinguir los resultados de ajuste de los resultados de evaluación independiente.

Referencia: [pipeline](../pipeline_wrf.py), preparación de observaciones y llamada a `run_valida_wrf` alrededor de las líneas 478–480.

### 3. Emparejamiento temporal y ponderación

El validador conserva todos los registros dentro de ±30 minutos del instante de evaluación. Cada registro se incorpora a la lista de estaciones y se compara con el campo del modelo correspondiente a ese único instante.

Por ello, el tamaño de muestra reportado puede representar múltiples registros por estación, no estaciones independientes. Por ejemplo, el informe de Zonda registra 91 pares válidos para temperatura a las 06Z, aunque documenta siete estaciones con datos en la ventana de ejecución.

Se debe definir un criterio explícito: observación más cercana por estación, promedio temporal por estación o emparejamiento con salidas temporales equivalentes del modelo. También conviene informar por separado el número de estaciones y el número de pares válidos.

Referencias: [validador](../src/validacion/valida_wrf_cli.py), funciones `cargar_estaciones_desde_json`, `load_run` y `build_tables`; [informe de Zonda](../informes_ejecucion/informe_caso1_zonda_20260731.md).

### 4. Propagación de errores de validación

Cuando `run_valida_wrf` devuelve un resultado fallido, el pipeline escribe una advertencia, pero termina con `return 0`. A su vez, el gestor de casos interpreta un código de salida cero como `EJECUTADO`.

El estado final debe distinguir una corrida terminada de una comparación validada correctamente y propagar un código de error cuando la validación requerida falla.

Referencias: [pipeline](../pipeline_wrf.py), final de la función `pipeline`; [gestor de casos](../src/casos/run_casos.py), función `ejecutar_caso`.

### 5. Signo de la mejora del RMSE

El generador de informes utiliza la diferencia:

`dRMSE = RMSE(control) − RMSE(nudged)`

La interpretación correcta es:

- `dRMSE > 0`: menor error con nudging; mejora.
- `dRMSE = 0`: igual RMSE.
- `dRMSE < 0`: mayor error con nudging; degradación.

El texto generado afirma actualmente «negativo ⇒ el nudging no degrada», lo cual contradice la fórmula. Debe corregirse la explicación y regenerarse los informes afectados.

Referencia: [generador de informes](../src/casos/run_casos.py), alrededor de la línea 392.

### 6. Reutilización de la corrida de control

El pipeline reutiliza el control si encuentra archivos `wrfout_d01*` en su directorio. Esa condición no verifica que coincidan las entradas, la configuración física, el dominio, el período ni la versión del modelo con el experimento actual.

Se recomienda registrar y comparar las configuraciones y las huellas de los archivos de entrada antes de reutilizar resultados.

Referencia: [pipeline](../pipeline_wrf.py), alrededor de las líneas 424–425.

## Lectura de los resultados existentes

Los informes guardados muestran un comportamiento variable del nudging según el caso y la hora:

| Caso y tiempo | RMSE de temperatura: control | RMSE de temperatura: nudging | Lectura |
|---|---:|---:|---|
| Zonda, 06Z | 4,85 K | 3,51 K | Mejora en la comparación reportada. |
| Frente frío, 12Z | 2,31 K | 2,54 K | Degradación en la comparación reportada. |

Fuente: [informe consolidado de casos del 13/09/2026](../informes_ejecucion/informe_casos_estudio_20260913.md).

Estos valores no permiten afirmar una mejora uniforme. Además de los problemas de validación identificados, el dominio de 15 km y los errores de elevación documentados condicionan la comparación con estaciones. El informe de Zonda señala diferencias de altura del modelo de entre +201 y +918 m y restringe la interpretación del evento a su firma térmica, con evaluación cualitativa del viento.

## Verificación realizada

Se intentó ejecutar:

```text
python -m pytest tests -q
```

La suite completa no pudo ejecutarse: la recolección de `test_circuito_modular.py` y `test_validacion_multitemporal.py` falló por la ausencia de `xarray` en el entorno Python disponible. Esto es una limitación del entorno de esta revisión; `xarray` sí está declarado como dependencia en `pyproject.toml`.

Se ejecutó después el subconjunto disponible:

```text
python -m pytest tests/test_preflight.py tests/test_run_casos.py -q
```

Resultado: **17 pruebas aprobadas**. Estas pruebas no sustituyen la validación del circuito meteorológico completo ni una ejecución real de WRF.

## Prioridades propuestas

1. Corregir las unidades del viento, la interpretación del signo de dRMSE y la propagación de errores de validación.
2. Definir un emparejamiento temporal por estación y documentar la ponderación de las muestras.
3. Separar observaciones de asimilación y evaluación para medir desempeño independiente.
4. Registrar las entradas y configuraciones que garantizan una comparación equivalente entre control y nudging.
5. Completar el entorno de dependencias, ejecutar la suite y recalcular los informes con el validador corregido.
6. Ampliar las corridas una vez estabilizado y verificado el procedimiento de evaluación.

La prioridad es fortalecer la validación antes de ampliar el conjunto de experimentos.
