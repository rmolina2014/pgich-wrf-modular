# Estado de las ejecuciones y posibilidades de reutilización

Revisión: 01/10/2026. Alcance: copia local de PGICH-WRF Modular. Objetivo: determinar qué se puede aprovechar para demostrar el flujo informático observaciones → asimilación → WRF → producto de pronóstico.

## Resultado

Los tres casos principales tienen salidas horarias completas de 00Z a 12Z para control y nudging. Son reutilizables para generar productos y recalcular la validación sin volver a ejecutar WRF. La completitud de salidas no equivale a un archivo experimental íntegro ni certifica calidad meteorológica o reproducción exacta desde cero.

Se examinaron 182 archivos wrfout de 7 pares ciclo/configuración, distribuidos en 6 carpetas con salidas. Todos se abrieron correctamente usando lectores NetCDF clásico o HDF5 según su formato. En cada archivo se leyeron Times, configuración relevante y los campos T2, PSFC, Q2, U10, V10, HGT, XLAT y XLONG. No se encontraron variables ausentes, NaN o infinitos en esos ocho campos. No se auditó la integridad numérica de todas las variables tridimensionales, ni se certificó ausencia de todos los posibles errores físicos.

## Clasificación por ejecución

| Ejecución | Salidas existentes | Configuración nudging en wrfout | Estado y reutilización |
|---|---|---|---|
| Caso 1, Zonda, 31/07/2026 | 13 control + 13 nudged, 00–12Z | 0,0001 en viento, temperatura y humedad | Completa en salidas. Reutilizar; hay 13 láminas de productos, entradas procesadas y namelists. |
| Caso 2, calor, 01/01/2026 | 13 + 13, 00–12Z | 0,0001 | Completa en salidas. Reutilizar para productos y validación horaria; informes presentes solo 00/06/12Z. |
| Caso 3, frente frío, 16/05/2026 | 13 + 13, 00–12Z | 0,0001 | Completa en salidas. Reutilizar; actualizar validación, especialmente hold-out n=1. |
| 06/08/2026, sanjuan_20260806 | 13 + 13, 00–12Z | 0,0002 | Reutilizable como ejecución histórica; contiene estado DONE y validación puntual. |
| 06/08/2026, sens_coef0001 | 13 + 13, 00–12Z | 0,0001 | Reutilizable como otro experimento del mismo día, no como día independiente. |
| 12/08/2026, dentro de validate | 13 + 13, 00–12Z | 0,0005 | Salidas completas; separar documentalmente del ciclo del día siguiente. Faltan entradas/configuración archivadas en esa carpeta. |
| 13/08/2026, dentro de validate | 13 + 13, 00–12Z | 0,0005 | Salidas completas; mismo pendiente de trazabilidad. No constituye continuación del día 12. |
| 25/05/2026, base | Sin wrfout | No verificable | Solo preparación: CSV, Little_R y OBS_DOMAIN101. Reutilizables como entradas históricas tras comprobar fechas, dominio y formato; falta ejecución WRF. |
| 06/08/2026, refactor_test | Sin wrfout | Solo namelist | Preparación/prueba incompleta. No acredita pronóstico generado. |

Las dos jornadas en `results/2026-08-12_0000z/validate` tienen START_DATE distintos. No deben concatenarse como una corrida continua de 36 horas.

## Cambios respecto de revisiones anteriores

La copia actual contiene el Zonda corregido: todos los wrfout nudged tienen OBS_COEF_WIND/TEMP/MOIS=0,0001 y OBS_NUDGE_OPT=1; controles tienen OBS_NUDGE_OPT=0. El namelist nudged también declara 0,0001. El hash del namelist control coincide con `control_manifest.json`. Esto resuelve la discrepancia de coeficiente observada antes en esta carpeta, aunque el manifiesto solo cubre ese namelist, no todas las entradas.

En cambio, no está presente en esta copia la carpeta `validacion_horaria_20260921` del frente frío revisada anteriormente. El informe `caso3_frentefrio/06Z/metricas_resumen_holdout.txt` todavía devuelve N=0 para CARACOLES. No es ausencia de salidas WRF: se debe recuperar esa revalidación o recalcularla con tratamiento correcto de n=1.

## Qué falta para considerar cerrado cada paquete

1. **Validación y productos:** los tres casos guardan informes en 00Z, 06Z y 12Z; la presencia de 13 wrfout permite completar las horas restantes. Zonda ya guarda 13 productos PNG. Calor y frente frío no tienen carpeta equivalente de productos en este inventario.
2. **Índice del producto Zonda:** `productos/indice.html` apunta a PNG en el directorio del índice, pero están en subcarpetas horarias. Las imágenes existen; los enlaces deben corregirse. No requiere WRF.
3. **Trazabilidad:** no se encontraron logs rsl ni archivos wrfinput, wrfbdy o wrfrst en la búsqueda local. Las carpetas de resultados no contienen el paquete completo de entradas GFS/WPS y binarios necesario para certificar repetición exacta desde cero. Pueden estar en el equipo de ejecución.
4. **Agosto 12–13:** la carpeta validate carece de namelists y OBS_DOMAIN101; tampoco aparecen obs_flat de esas fechas en data/raw. Sus salidas sirven para mapas y extracción de series, pero la validación contra estaciones requiere recuperar observaciones y documentar su zona horaria.
5. **Observaciones:** existen obs_flat para enero, mayo, julio y agosto 6, además de entradas procesadas de los casos principales. Sin embargo, `time_unix` en los tres casos principales no representa segundos Unix correctos: por ejemplo enero comienza con 1767225, que interpretado como segundos corresponde a 1970, mientras fecha/hora declara 2026-01-01 00:00. Los campos fecha/hora sí corresponden a los eventos y el cleaner los prioriza; no reutilizar time_unix sin normalizar y comprobar la zona horaria. En agosto 6, time_unix comienza a 03Z mientras fecha/hora comienza a 00:00: explicitar si es hora local antes de comparar.

## Cómo reutilizarlas según la operación

| Operación deseada | ¿Requiere ejecutar WRF nuevamente? |
|---|---|
| Crear mapas, series y productos de las horas ya guardadas | No; utilizar wrfout existentes. |
| Recalcular métricas o corregir hold-out | No; utilizar salidas y observaciones temporalmente alineadas. |
| Actualizar informes, panel o índice HTML | No. |
| Comparar configuraciones históricas ya archivadas | No para postprocesar; verificar comparabilidad de entradas/física antes de atribuir diferencias solo al coeficiente. |
| Cambiar coeficientes, física, dominio u observaciones asimiladas | Sí, ejecutar una nueva integración afectada por esos cambios. El control solo puede reutilizarse si las entradas y configuración relevantes coinciden. |
| Emitir pronóstico para otra fecha | Sí; requiere condiciones iniciales/de borde y observaciones del nuevo ciclo. |
| Extender más allá de 12 horas | No se acredita reinicio directo: no se encontraron wrfrst. Recuperar archivos de reinicio válidos y condiciones de borde, o preparar una integración nueva. |

## Recomendación para el objetivo informático

Usar Zonda como demostración inicial porque ya reúne observaciones procesadas, archivos de asimilación, control/nudging completos y productos gráficos. Completar su trazabilidad y corregir el índice. Después generar productos y validación horaria de calor y frente frío usando sus salidas existentes. No repetir los tres casos solamente para obtener gráficos nuevos o informes actualizados.

Estas ejecuciones históricas permiten demostrar la generación de salidas y productos del modelo. Para acreditar un pronóstico operativo posterior a la disponibilidad de observaciones, documentar la hora de emisión, el último dato asimilado y el horizonte futuro; la cobertura 00–12Z por sí sola no demuestra ese aspecto.

## Evidencia reproducible

- `scripts/auditar_ejecuciones.py`: inventario y lectura de campos NetCDF.
- `scripts/auditar_ejecuciones_detalle.py`: comparación de namelists, verificación de manifiesto e inventario observacional.
- `informes_ejecucion/auditoria_ejecuciones_20261001/inventario.json`: detalle por archivo, tiempos internos, configuración, dimensiones y extremos de campos.
- `resumen_tecnico.txt` y `detalle.txt` en esa misma carpeta.

No se modificaron las ejecuciones existentes ni se lanzaron simulaciones. El análisis confirma disponibilidad técnica para reutilización de los campos revisados; no sustituye una auditoría completa de la calidad meteorológica.
