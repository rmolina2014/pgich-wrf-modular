# Plan de implementación: ejecución automática y recuperable de WRF

Fecha: 17/09/2026. Estado: propuesta de implementación, no implementada.

## 1. Objetivo y alcance

Implementar la opción 2 adaptada a la decisión del usuario: inicio manual exclusivo por el operador en una PC Linux y ejecución automática de las etapas del ciclo solicitado, con registro de avance y recuperación de fallos. Por ahora no se habilitarán horarios, temporizadores ni arranque automático de corridas al encender el equipo.

La prioridad es ejecutar automáticamente casos históricos con simulaciones control y nudged, validación e informes. Una segunda etapa incorporará pronósticos diarios y su validación posterior. Ambas modalidades compartirán el motor de ejecución, pero tendrán políticas diferentes sobre disponibilidad de observaciones.

La primera versión usará una sola máquina y una sola simulación WRF a la vez. La distribución entre máquinas, una interfaz nueva y cambios de física o dominio quedan fuera del alcance inicial. Windows seguirá siendo un entorno de edición; las pruebas integrales y el servicio se ejecutarán en Linux con WRF instalado.

## 2. Punto de partida verificado

Revisión del repositorio actualizado al commit `0dbffeb`:

| Componente existente | Base aprovechable | Mejora necesaria |
|---|---|---|
| `src/casos/run_casos.py` | Coordina observaciones históricas, GFS, WPS, pipeline e informes | Persistir cada transición; separar etapas; propagar fallos al terminar el lote |
| `config/casos_estudio.json` | Tres casos históricos y configuración común de 12 horas | Conservar compatibilidad y permitir lotes, ciclos y duraciones configurables |
| `pipeline_wrf.py` | QC, observaciones, preflight, WRF y validación; manifest de control | Delegar en el coordinador común y ampliar la identidad de entradas reutilizables |
| `src/modelo/wrf_runner.py` | Límites de tiempo, mensajes de éxito y reintentos | Aislar intentos, preservar logs, supervisar procesos y clasificar fallos |
| `src/ingesta/gfs_downloader.py` | Descarga GFS desde fuentes configuradas | Descargas atómicas, integridad, reintentos y disponibilidad histórica explícita |
| `src/modelo/wps_runner.py` y scripts WPS | Preparación meteorológica existente | Integrar toda la cadena y comprobar fechas, dominios y cobertura |
| Scripts Bash de ejecución | Compatibilidad con el entorno WRF actual | Mantener un solo responsable del estado y de los reintentos |

Observaciones concretas para la implementación:

- El ejecutor de WRF limpia `wrfout` y `rsl` antes de reintentar y contempla hasta cinco reintentos adicionales. Esa limpieza no debe operar sobre directorios compartidos ni eliminar evidencia del intento anterior.
- El gestor de casos guarda el estado al terminar el recorrido principal y su `main()` termina con código 0 aunque existan casos fallidos. Se necesita persistencia durante la ejecución y un resultado global interpretable por el servicio.
- Algunas comprobaciones se basan en contar cinco archivos, coherente con la configuración actual de 12 horas pero insuficiente para generalizar períodos y dominios.
- La preparación fija `fdda_end = 720`. La ventana de nudging deberá derivarse de la configuración y del modo de ejecución.
- El descargador puede escribir directamente sobre el destino y reutiliza archivos por tamaño. Un archivo interrumpido no debe considerarse válido por ese criterio.
- La revisión científica existente deja pendientes la independencia de las observaciones de evaluación y el emparejamiento temporal. Automatizar no resuelve esos puntos.

## 3. Diseño propuesto

### Control del inicio

Solo el operador podrá iniciar un ciclo mediante una acción explícita. Podrá autorizar un caso individual o un lote concreto; en ese caso, los casos incluidos se ejecutarán secuencialmente dentro de esa solicitud. Registrar o preparar trabajos no los inicia.

Tras el inicio manual, las etapas y los reintentos limitados del trabajo autorizado serán automáticos. Una cancelación, el agotamiento de reintentos o la interrupción del coordinador dejarán el trabajo detenido hasta que el operador ordene reanudarlo. Reiniciar Linux no iniciará ni reanudará simulaciones. La futura ejecución por horarios requerirá una decisión posterior del usuario.

### Coordinador único

Crear `src/orquestacion/` como motor común. Los comandos existentes se conservarán como adaptadores durante la migración. Los scripts Bash podrán ejecutar binarios cuando lo requiera el entorno, pero no mantendrán una segunda lógica de estados o reintentos.

Cadena histórica:

```text
Inicio manual del operador → planificar caso o lote y reservar recursos
  → obtener observaciones y GFS
  → verificar cobertura e integridad
  → QC y preparación de OBS_DOMAIN101
  → WPS: geogrid, ungrib y metgrid
  → preparar namelists y ejecutar preflight
  → real.exe y WRF para cada variante, según sus entradas
  → verificar y registrar salidas control/nudged
  → validación
  → informes y cierre
```

La reutilización de geogrid, met_em o entradas de real.exe requerirá equivalencia verificada de configuración y datos. No se asumirá que las entradas del control y nudged son intercambiables.

### Identidad, archivos y estado

- Separar el identificador lógico del trabajo de los intentos. La identidad incluirá modo, fecha/ciclo UTC, dominio, duración, configuración y versión del código. Cada etapa tendrá además un manifest de sus entradas y productos.
- Registrar estado en SQLite sobre disco local, con transacciones; exportar un resumen JSON para consulta y compatibilidad. No alojar la base en una carpeta de red.
- Usar directorios independientes por trabajo, variante e intento. Compartir solamente datos estáticos o caché validada mediante accesos de solo lectura.
- Registrar rutas, versiones de WRF/WPS, ejecutables, configuración efectiva, huellas de archivos, fuentes, tiempos, códigos de salida y motivo de cada transición.
- Reservar CPU, memoria y disco antes de iniciar. Aplicar bloqueo del trabajador y exclusión de trabajos duplicados.

Estados de etapa: `PENDIENTE`, `ESPERANDO_DATOS`, `LISTA`, `EJECUTANDO`, `COMPLETADA`, `FALLIDA`, `BLOQUEADA` y `CANCELADA`. La espera debe tener fecha límite; un fallo agotará un número definido de intentos antes de requerir intervención.

Separar el estado de simulación del estado de validación. Un pronóstico disponible puede tener validación pendiente; un experimento histórico completo requiere todos sus productos obligatorios.

### Configuración

Agregar un archivo de configuración operativo con rutas por máquina, recursos, tiempos máximos, reintentos, retención, políticas de datos faltantes e inicio manual obligatorio. Mantener credenciales en el entorno local, sin incluirlas en manifests ni logs.

Valores iniciales propuestos: un trabajador, casos históricos secuenciales y parámetros científicos actuales. Los límites de recursos y tiempos se fijarán después de medir una corrida real. Cambiar configuración científica generará una nueva identidad de experimento.

## 4. Fases de implementación

### Fase 0 — Línea de base y entorno Linux

**Tareas**

- Seleccionar la PC Linux inicial y comprobar rutas, bibliotecas, MPI, WRF/WPS, Python y permisos.
- Inventariar los puntos de entrada utilizados y las instrucciones locales aplicables antes de modificar código.
- Preservar resultados actuales y medir una corrida histórica representativa: duración por etapa, memoria y espacio.
- Verificar disponibilidad real de observaciones y GFS para los tres casos. Incorporar datos locales como fuente explícita; no asumir que los servidores operativos conservan cualquier fecha histórica.
- Registrar resultados de referencia y tolerancias de comparación numérica.

**Entregables:** diagnóstico de entorno, perfil de máquina y referencia reproducible.

**Aceptación:** un caso completo puede ejecutarse y verificarse con entradas identificadas; si faltan datos o ejecutables, queda documentado el bloqueo antes de desarrollar sobre supuestos.

### Fase 1 — Estado persistente y aislamiento

**Tareas**

- Implementar configuración, identidad, manifests, SQLite y transiciones de estado.
- Crear áreas de trabajo separadas para WPS, control, nudged e intentos.
- Añadir bloqueo de ejecución y deduplicación de solicitudes.
- Guardar el estado antes y después de cada etapa; registrar también fallos de arranque.
- Implementar consulta de estado, cancelación y reanudación explícita.

**Aceptación:** dos solicitudes iguales no lanzan dos corridas; una interrupción conserva el avance; ningún intento borra archivos de otro trabajo.

### Fase 2 — Datos históricos y preprocesamiento confiables

**Tareas**

- Adaptar el catálogo actual de casos y permitir intervalos de fechas sin modificar código.
- Descargar a archivos temporales y promoverlos al destino solo después de validarlos.
- Añadir reintentos con espera creciente y límite para fallos transitorios de red. Diferenciar credenciales inválidas, datos ausentes y archivos corruptos.
- Verificar GFS por fecha, ciclo, pasos previstos y lectura GRIB; verificar observaciones por ventana UTC, estaciones y variables requeridas.
- Generar la lista esperada de archivos según duración, intervalo y dominios, reemplazando los conteos fijos.
- Integrar y verificar geogrid, ungrib y metgrid. Invalidar caché cuando cambien entradas relevantes.
- Conservar la política histórica inicial: si no hay observaciones suficientes para la comparación, bloquear el caso con causa explícita.

**Aceptación:** un archivo truncado no llega a WPS; no se mezclan ciclos; un caso sin datos termina identificado como bloqueado y el lote puede continuar con los casos independientes.

### Fase 3 — Supervisión y recuperación de WRF

**Tareas**

- Encapsular cada lanzamiento de real.exe y wrf.exe con límites de tiempo y control del grupo completo de procesos, incluidos procesos MPI.
- Conservar salida estándar, `rsl` y configuración de cada intento, incluso tras timeout o cancelación.
- Reintentar únicamente fallos clasificados y con presupuesto limitado. Investigar el SIGSEGV descrito en el ejecutor; reintentar no se considerará su corrección.
- Exigir mensaje de finalización, código de salida correcto y productos NetCDF legibles con tiempos y dominios esperados.
- Reanudar el flujo desde la primera etapa incompleta o invalidada. Una validación fallida no volverá a ejecutar WRF si sus salidas siguen siendo válidas.
- Evaluar reinicio interno con `wrfrst`: verificar compatibilidad de versión, dominio, configuración, ventana de nudging y continuidad de salidas. Activarlo solo tras una prueba comparativa satisfactoria.
- Al abrir el coordinador, reconciliar trabajos que figuraban en ejecución con procesos y archivos reales; relanzarlos únicamente tras una orden manual de reanudación.

**Aceptación:** timeout y cancelación no dejan procesos huérfanos; se conserva evidencia; la recuperación por etapas funciona. Si el reinicio interno no es compatible, se permite repetir solo la simulación afectada desde el inicio y se registra esa limitación.

### Fase 4 — Lotes históricos completos e informes

**Tareas**

- Integrar control, nudged, validación e informes en el motor común.
- Ampliar los manifests de reutilización con entradas meteorológicas, configuración efectiva y versiones relevantes.
- Corregir la propagación del resultado global: éxito, lote parcial o fallo; no marcar como completo un lote con productos obligatorios ausentes.
- Generar un resumen por caso y lote con cobertura, etapas, intentos, duración, métricas y rutas de resultados.
- Etiquetar si las observaciones de validación también se asimilaron. Mantener la metodología actual como referencia y documentar cualquier futura separación de estaciones o cambio temporal como otra configuración científica.

**Aceptación:** los tres casos actuales, siempre que estén disponibles sus entradas, se procesan sin intervención entre etapas y se comparan con la referencia. Un segundo lanzamiento reutiliza resultados válidos; modificar una entrada invalida las etapas dependientes.

### Fase 5 — Operación Linux con inicio manual

**Tareas**

- Preparar un comando de inicio manual y, si hace falta ejecución independiente de la terminal, un servicio systemd iniciado explícitamente por el operador. No instalar temporizadores ni habilitar arranque automático de corridas; ejecutar el modelo con un usuario sin privilegios administrativos.
- Separar preparación e inicio: el operador selecciona y lanza un caso o lote concreto; el trabajador procesa exclusivamente esa solicitud y termina al completarla, sin consumir trabajos nuevos por su cuenta.
- Procesar primero la cola histórica. Las interrupciones del servicio no deben perder ni duplicar solicitudes.
- Añadir consulta de estado, logs por etapa y resumen de fallos que requieren intervención. Preparar avisos opcionales; elegir y configurar el canal antes de habilitar envíos.
- Establecer retención por tipo de producto y mínimo de espacio libre. La limpieza empezará en modo de simulación y nunca eliminará trabajos activos ni datos únicos sin copia verificada.
- Documentar instalación, arranque, parada, recuperación y reversión a los comandos existentes. Pausar la cola antes de actualizar código; no actualizar el repositorio automáticamente durante una corrida.

**Aceptación:** un lote iniciado manualmente completa sus etapas sin intervención rutinaria y mantiene historial consultable. Tras un reinicio controlado conserva el avance y espera la orden manual para reanudar. Registrar un trabajo o encender Linux no inicia una corrida. Los ciclos sin cambios no generan avisos repetitivos.

**Hito H1:** automatización histórica terminada. No avanzar al modo diario hasta superar las pruebas de recuperación y reproducibilidad.

### Fase 6 — Pronósticos diarios con inicio manual; programación futura opcional

**Tareas**

- Agregar modo operativo con ciclo UTC, horizonte y plazo de disponibilidad configurables. Empezar con un ciclo diario iniciado manualmente por el operador; ampliar frecuencia después de medir capacidad. La periodicidad diaria no habilita por sí misma un inicio automático.
- Separar hora inicial del modelo, hora de emisión y fecha límite de recepción de observaciones.
- Esperar el conjunto GFS completo hasta un plazo definido. Si no llega, marcar el ciclo fallido o vencido según política; no sustituir silenciosamente su fecha o ciclo.
- Diseñar y verificar una ventana de asimilación anterior o igual a la emisión y el paso al pronóstico libre. No usar observaciones futuras ni trasladar sin cambios el nudging histórico de 12 horas.
- Decidir mediante experimento cómo transferir el estado asimilado al pronóstico, mantener condiciones de borde compatibles y comparar con el control. Este diseño es una dependencia científica de la puesta en operación.
- Definir explícitamente si un ciclo sin estaciones queda bloqueado o produce solo control, identificado como degradado. La política inicial será bloquear hasta que se elija y valide una alternativa.
- Generar productos de pronóstico al terminar WRF y encolar la validación diferida cuando existan observaciones del período previsto.
- Tras días sin servicio, mostrar pendientes históricos para reanudación manual y omitir pronósticos ya vencidos salvo solicitud explícita de reconstrucción. La validación diferida pendiente se iniciará por orden del operador si el trabajo original ya no está activo.

**Aceptación:** una reproducción histórica del modo operativo demuestra que solo usa información disponible al emitir; la validación diferida no repite WRF; cada producto muestra ciclo, emisión y modalidad.

**Hito H2:** piloto de al menos siete ciclos diarios consecutivos, cada uno iniciado por el operador. Aceptar operación habitual solo si los ciclos completan dentro del plazo acordado, o cada incumplimiento queda identificado y resuelto antes de habilitar la operación regular.

## 5. Pruebas y evidencias

| Escenario | Resultado requerido |
|---|---|
| Corte durante descarga | Archivo temporal descartado o recuperado; destino nunca considerado completo sin validar |
| Datos de otro ciclo en caché | Rechazo antes de WPS |
| Observaciones históricas insuficientes | Caso bloqueado con cobertura y motivo |
| Dos solicitudes iguales | Un trabajo lógico y una ejecución activa |
| Fallo WPS o real.exe | Etapas dependientes no se lanzan; se conservan logs |
| Timeout o cancelación MPI | Grupo de procesos detenido y estado persistido |
| Mensaje de éxito con NetCDF incompleto | Simulación rechazada |
| Fallo de validación o informe | Se repite esa etapa y sus dependientes, sin repetir WRF válido |
| Reinicio del equipo | Estado conservado; ninguna corrida se inicia; reanudación solo por orden manual, sin duplicados |
| Trabajo registrado sin orden de inicio | Permanece pendiente |
| Fin del lote autorizado | El ejecutor termina y no inicia otros trabajos |
| Cambio de configuración o entradas | Invalidación de productos dependientes |
| Disco insuficiente | No inicia la etapa; conserva productos existentes |
| Reinicio desde wrfrst | Continuidad temporal y comparación numérica dentro de tolerancias acordadas |
| Pronóstico con observaciones futuras | Rechazo de esas observaciones antes de asimilar |

Usar pruebas unitarias para transiciones y políticas, integración con ejecutables simulados para fallos y pruebas reales en Linux para WRF/WPS. Las pruebas simuladas no certifican la estabilidad del modelo. Comparar resultados numéricos con tolerancias documentadas, sin exigir identidad binaria entre entornos.

## 6. Archivos y entregables previstos

Los siguientes son destinos propuestos, no archivos ya implementados:

| Destino | Responsabilidad |
|---|---|
| `src/orquestacion/config.py` | Configuración y validación de parámetros |
| `src/orquestacion/estado.py` | Persistencia, transacciones y eventos |
| `src/orquestacion/manifests.py` | Identidad de entradas, productos y reutilización |
| `src/orquestacion/coordinador.py` | Dependencias, recuperación y decisiones de ejecución |
| `src/orquestacion/worker.py` | Cola local, exclusión y reconciliación |
| `src/orquestacion/cli.py` | Planificar, ejecutar, consultar, cancelar y reanudar |
| `config/automatizacion.example.json` | Configuración operativa sin secretos |
| `deploy/systemd/` | Servicio opcional de inicio manual e instrucciones, sin temporizador ni arranque automático |
| `tests/test_orquestacion_*.py` | Pruebas de comportamiento y recuperación |
| `documentacion_proyecto/operacion_automatica.md` | Manual de operación y diagnóstico |

Cada fase debe entregarse con sus comprobaciones antes de integrar la siguiente. Mantener los comandos actuales utilizables hasta que su reemplazo supere la aceptación correspondiente.

## 7. Orden y decisiones pendientes

Orden obligatorio: **F0 → F1 → F2 → F3 → F4 → F5 → H1 → F6 → H2**.

El primer incremento será un caso histórico aislado con estado persistente y reanudación por etapas. Después se ampliará a los tres casos y a la operación de lotes iniciados manualmente. La optimización MPI se realizará con mediciones tras estabilizar la ejecución; no se asumirá que aumentar procesos mejora el rendimiento.

Antes del despliegue deben resolverse:

1. PC Linux inicial y rutas definitivas de WRF/WPS y Python.
2. CPU, memoria, almacenamiento y tiempo disponible para los lotes.
3. Fuente y disponibilidad verificadas de los datos históricos.
4. Plazos, número de reintentos y política de conservación.
5. Para el modo diario: ciclo, horizonte, hora de emisión, ventana de asimilación y política ante observaciones faltantes.
6. Canal de avisos, si se desea habilitarlo.

No se fija un calendario de implementación hasta medir el entorno y confirmar los datos de referencia. El esfuerzo principal está en la recuperación comprobable y la validación de WRF; la programación horaria queda fuera del alcance actual y solo se incorporará si el usuario la solicita posteriormente.

## 8. Referencias

- Código y configuración local citados en la sección 2.
- `documentacion_proyecto/analisis_codigo_modular_16092026.md`: revisión científica y técnica previa.
- [NCAR: ejercicio de reinicio WRF](https://www2.mmm.ucar.edu/wrf/site/online_tutorial/restart_exercise.html): base para diseñar y probar el uso de `wrfrst`; no sustituye verificar su compatibilidad con este experimento.

Este documento no instala servicios, modifica parámetros científicos ni ejecuta simulaciones. Define el trabajo y las condiciones para considerar completa cada etapa.
