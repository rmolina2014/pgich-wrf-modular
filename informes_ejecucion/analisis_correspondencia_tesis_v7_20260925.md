# Correspondencia entre tesis v7 y sistema construido

Fecha de revisión: 25/09/2026.

Documento: `E:/Proyectos_2026/documentacion_tesis_wrf-master/documentacion_tesis_wrf-master/tesis_borrador_22092026_v7.docx`.

Repositorio revisado: `E:/Proyectos_2026/pgich-wrf-modular-main/pgich-wrf-modular-main`.

## Dictamen

La tesis refleja el núcleo de ingeniería implementado: adquisición de observaciones, control de calidad, generación de archivos de asimilación, integración WRF con Observation Nudging y comparación contra control. Sin embargo, no describe fielmente toda la versión disponible. Mezcla alcance propuesto, funcionamiento histórico y capacidades actuales; contiene diferencias de configuración y resultados desactualizados. No corresponde declarar cumplimiento completo de todos los objetivos ni mejora meteorológica generalizada con la evidencia revisada.

La revisión fue documental y estática, contrastada con resultados archivados. Se extrajeron 252 bloques de texto/tablas del Word; las referencias siguientes son a secciones, no a páginas. No se auditó la maquetación del documento, no se ejecutaron nuevas simulaciones y no se verificó el despliegue remoto ni el proceso servido actualmente en el navegador. Existencia de código, integración en un flujo y validación experimental son evidencias diferentes.

## Matriz de correspondencia

| Aspecto | Evidencia actual | Evaluación |
|---|---|---|
| Arquitectura modular, §4.1 | Paquetes `src/ingesta`, `calidad`, `asimilacion`, `modelo`, `validacion`, `reporting` | Reflejado en la estructura. No prueba que todas las clases estén conectadas al flujo principal. |
| Limpieza y QC | `src/calidad/cleaner.py:48` llama `aplicar_control_calidad`; `pipeline_wrf.py:167` prepara observaciones | Implementado. Faltan indicadores operativos consolidados para justificar tasas de éxito y rendimiento. |
| Little_R y OBS_DOMAIN101, §4.2 | `pipeline_wrf.py:167` y `src/asimilacion/obsnud_writer.py` | Implementado, pero son productos generados desde datos procesados; no describir como una conversión obligatoria Little_R → OBS_DOMAIN101. |
| Asimilación | Namelist `&fdda`, `obs_nudge_opt`, coeficientes observacionales y `wrf.exe` | Observation Nudging implementado. No se acreditó ejecución WRFDA/3DVar. |
| Adquisición GFS y WPS | `src/casos/run_casos.py:610` y `:618` | Existen, en el ejecutor de casos. No atribuir todo a `pipeline_wrf.py` ni afirmar descarga paralela sin demostrarla. |
| Control y nudging | `pipeline_wrf.py:500` y `run_full_pipeline.sh:129`/`:140` | Ejecución secuencial sobre directorio compartido, no dos corridas simultáneas como dice §4.2. |
| Métricas | `src/validacion/metrics.py`, resultados y tablas por hora | Implementadas. Debe explicarse tamaño muestral, agregación espacial y separación por roles. |
| Hold-out espacial | `src/asimilacion/obsnud_writer.py:174` excluye rol evaluación | Implementado en código actual. El rol actual no demuestra por sí solo exclusión en cada corrida histórica; comprobar OBS_DOMAIN101 archivados y procedencia. |
| Informes | Resultados, gráficos y reportes en `results/` e `informes_ejecucion/` | Implementado; algunos resultados posteriores no fueron incorporados a la tesis. |
| Registro automático de experimentos | Existe `src/reporting/experiment_registry.py`; no se encontraron llamadas a `ExperimentRegistry` fuera de su definición/exportación en fuentes revisadas | Integración no acreditada. Tampoco existe el directorio raíz `experiments` en esta copia. |
| Interfaz de seis páginas, §4.6 | `app_streamlit.py:145` define una sola interfaz operativa; tiene botones de preparación y ejecución | No coincide con las seis páginas descritas ni con la afirmación de que no permite lanzar WRF. |
| Mapa de inicio | Existen `src/ui/home.py:75`, `:152` y `domain_data.py` | Los componentes existen, pero el `app_streamlit.py` actual no importa ni llama a esas vistas. No certificar mapa integrado a partir de su mera existencia. |
| Operación periódica sin intervención | Se observan CLI y lanzamiento manual desde Streamlit | Automatización de etapas sí; servicio periódico desatendido no acreditado en esta revisión. |

## Correcciones prioritarias

### 1. Unificar el método de asimilación en objetivos, metodología y conclusiones

Los capítulos I–III y la matriz del anexo hablan de WRFDA y modificación de condiciones iniciales. Los capítulos IV y VI describen Observation Nudging durante la integración. Son alcances distintos. El sistema observado utiliza FDDA observacional dentro de WRF; generar Little_R no demuestra haber ejecutado WRFDA.

Reescritura sugerida del alcance implementado: «Se implementó un flujo de preparación de observaciones de superficie y su incorporación durante la integración de WRF mediante Observation Nudging, con evaluación frente a una corrida de control». Mantener WRFDA/3DVar como alternativa o trabajo futuro salvo que se aporten ejecutables, configuraciones y resultados de esa ruta.

Referencia técnica primaria: [guía oficial de Observation Nudging](https://www2.mmm.ucar.edu/wrf/users/docs/How_to_run_obs_fdda.html), que describe términos de relajación y activación mediante `obs_nudge_opt`; [documentación oficial de WRFDA](https://github.com/wrf-model/Users_Guide/blob/main/wrfda.rst), que describe el sistema variacional.

### 2. Distinguir red institucional, estaciones configuradas y estaciones válidas

La tesis declara diez estaciones. `config/estaciones.json` contiene nueve. La cantidad con datos depende del caso, hora y variable. Esto no demuestra que la institución tenga solamente nueve: demuestra que esta copia no configura diez. Corregir las afirmaciones de implementación y documentar la décima estación si existe. Tampoco describir toda la cobertura como restringida al valle de Tulum sin aclarar estaciones regionales como Valle Fértil y Cuesta del Viento.

### 3. Resolver la diferencia 4 km / 15 km

El alcance (§3.3) menciona dominio operativo de 4 km, mientras `namelist.input:41`–`:49` declara 80 × 60 puntos nominales y `dx=dy=15000 m`. La discusión posterior usa correctamente 15 km. Si 4 km corresponde a otro sistema institucional, distinguirlo explícitamente del dominio experimental utilizado aquí.

### 4. Auditar los coeficientes antes de discutir un valor óptimo

La tesis (§5.4) y `config/casos_estudio.json` atribuyen 0,0001 al Zonda. Sin embargo, `results/2026-07-31_0000z/caso1_zonda/namelist_nudged.input:87`–`:89` contiene 0,0005 para viento, temperatura y humedad. El namelist base tiene 0,0002. Son tres fuentes distintas que no deben intercambiarse.

La discrepancia del archivo archivado debe resolverse con atributos de wrfout, logs y manifiesto antes de afirmar qué coeficiente produjo cada tabla; el nombre del directorio o la configuración actual no bastan. La declaración de 0,001 «óptimo» (§5.3) requiere una tabla reproducible de sensibilidad con mismas entradas, periodo, física y criterios de evaluación. En esta revisión no quedó establecida esa trazabilidad.

### 5. Actualizar el frente frío: la revalidación ya existe

§5.4 y trabajos futuros dejan pendiente recalcular el hold-out con una sola estación. Ya existe `results/2026-05-16_0000z/caso3_frentefrio/validacion_horaria_20260921/`, con trece horas (00Z–12Z), métricas y resumen. Se reprocesaron salidas existentes, no se volvió a ejecutar WRF. Para n=1 se dispone de sesgo, MAE y RMSE; correlación e intervalos quedan no disponibles.

Además, la tabla del frente frío rotula como «ajuste» valores que corresponden al conjunto global. Los deltas T2 +0,57 a 06Z y −0,23 a 12Z son globales; no deben presentarse como resultado exclusivo de estaciones asimiladas.

| Hora UTC | Variable | RMSE nudging | RMSE control | Interpretación |
|---|---|---:|---:|---|
| 02Z | Viento (m/s) | 19,967 | 1,357 | Degradación fuerte |
| 10Z | Viento (m/s) | 13,039 | 1,833 | Degradación fuerte |
| 06Z | T2 (K) | 2,129 | 2,698 | Mejora |
| 12Z | T2 (K) | 2,479 | 2,247 | Degradación |
| 06Z | RH (puntos porcentuales) | 11,971 | 15,852 | Mejora |
| 10Z | RH (puntos porcentuales) | 21,713 | 10,961 | Degradación |

Fuente: `resumen_validacion.md` en esa carpeta. Los picos no establecen por sí solos una causa numérica o física. Revisar campos, observaciones y registros antes de explicarlos.

### 6. Matizar las conclusiones científicas

«Mejora consistente en temperatura y humedad en los seis casos» (§5.5 y §6.1) es demasiado amplia ante las degradaciones por hora. Usar: «Se observaron mejoras dependientes de variable, hora, evento y grupo de estaciones, junto con degradaciones significativas en magnitud que requieren investigación». Aquí “significativas en magnitud” no equivale a significación estadística.

No se acredita una mejora estadísticamente significativa y generalizable de pronósticos operativos mediante unos pocos casos y una o dos estaciones de evaluación. Una validación durante la ventana de asimilación tampoco demuestra por sí sola mejora de pronóstico libre posterior al corte de observaciones. Especificar ventana de asimilación, periodo evaluado y horizonte de pronóstico.

La asociación entre error de altura y sesgo de PSFC es una hipótesis razonable, pero correlación alta y diferencias topográficas no «confirman» por sí solas una causa única. Hacen falta controles de presión absoluta/reducida, unidades, alturas e interpolación y un experimento de corrección.

### 7. Normalizar identificación y evidencia de los seis casos

| Tesis §5.4 | Sistema actual | Fecha |
|---|---|---|
| Caso 4, Zonda | caso1 / caso1_zonda | 31/07/2026 |
| Caso 5, calor | caso2 / caso2_calor | 01/01/2026 |
| Caso 6, frente frío | caso3 / caso3_frentefrio | 16/05/2026 |

La diferencia de numeración no implica que falten esos tres experimentos. Sin embargo, no se acreditaron todos los resultados históricos de §5.2: el directorio del 25/05 encontrado contiene entradas de preparación, no las salidas y métricas de la tabla; no hay carpeta de resultados del 05/07 en el nivel de ciclos revisado. Pueden existir en otro equipo o archivo. Conservarlos como resultados históricos solo con fuente, versión y artefactos verificables. No equiparar número de configuraciones con número de días independientes.

### 8. Actualizar arquitectura operativa e interfaz

La aplicación principal disponible se presenta explícitamente como WRF nativo sin Docker. Docker puede haber sido el entorno histórico, pero debe fecharse y diferenciarse del actual. La interfaz sí ofrece «Ejecutar pipeline completo». No coincide con la aplicación descriptiva de seis páginas que expone §4.6.

El mapa y la vista de validación están en `src/ui`, pero no conectados al punto de entrada actual. Determinar si se está ejecutando otro archivo o una versión previa antes de presentar capturas como evidencia de esta copia. La URL abierta por sí sola no identifica el código servido.

`run_full_pipeline.sh` reinicia `LD_LIBRARY_PATH`, pero no contiene la limpieza de `HDF5_PLUGIN_PATH` ni el mecanismo `wait` descritos en §4.5; `wrf.exe` se ejecuta en primer plano dentro del script. El servidor puede iniciar el script como proceso independiente, que es una cuestión distinta.

### 9. Limitar las garantías de trazabilidad y reproducibilidad

Existe un manifiesto para reutilizar controles en `pipeline_wrf.py:298`. No equivale a procedencia completa de todas las entradas ni garantiza resultados idénticos en distinto hardware. Documentar versiones, binarios, configuración física, entradas GFS/observaciones, hashes y entorno de ejecución.

`ExperimentRegistry.registrar` sustituye registros con el mismo ID y reescribe el JSONL: a pesar de su docstring, no es un registro inmutable ni una escritura atómica. Su integración automática no quedó acreditada. La estimación de menos de un minuto con 16–32 procesadores debe presentarse como hipótesis pendiente de benchmark, no como rendimiento demostrado.

## Orden recomendado para cerrar la correspondencia

1. Corregir método de asimilación, dominio, catálogo y numeración en objetivos, metodología y anexo.
2. Resolver procedencia de coeficientes y respaldar las tablas históricas antes de reutilizarlas.
3. Incorporar la validación horaria y el hold-out actualizado del frente frío; separar global/ajuste/evaluación.
4. Reescribir conclusiones distinguiendo resultado medido, hipótesis explicativa y trabajo futuro.
5. Sincronizar la descripción de la interfaz con el punto de entrada realmente desplegado e integrar el mapa si esa es la versión objetivo.
6. Demostrar un ciclo completo trazable y documentar qué parte es manual, automatizada o todavía propuesta.

Texto de cierre sugerido: «El sistema implementa y evalúa un flujo modular de asimilación observacional mediante nudging. La evaluación evidencia mejoras variables según evento y horario, junto con limitaciones en viento, representación topográfica y generalización espacial. La operación desatendida, la trazabilidad integral y la evaluación de pronósticos posteriores a la asimilación requieren validación adicional».

No se modificó el documento original ni el código funcional. Se guardaron este informe y un auxiliar de extracción textual para hacer revisable el contraste.
