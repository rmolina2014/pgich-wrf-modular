# Chequeos previos a la ejecución del pipeline WRF (Preflight Checks)

**Proyecto:** PGICH-WRF — Asimilación de observaciones de superficie mediante Observation Nudging
**Objetivo del documento:** definir un conjunto de verificaciones automáticas a ejecutar **antes** de lanzar `wrf.exe`, para detectar en segundos condiciones que hoy solo se descubren después de varios minutos de cómputo (o directamente con la corrida abortada).
**Origen:** este plan surge de analizar los bugs y fallas encontradas en los informes de ejecución del 06/08/2026, del 12/08/2026 y del experimento `sens_coef0001` (10/09/2026). En cada uno de esos ciclos, el error se detectó recién durante o después de la corrida de WRF, con el consiguiente costo de tiempo de cómputo y de diagnóstico manual.

---

## 1. Alcance

Este chequeo aplica **antes de invocar `wrf.exe`**, tanto para la corrida Nudged (`obs_nudge_opt=1`) como para la Control (`obs_nudge_opt=0`), y se ejecuta como una etapa propia del pipeline (`pipeline_wrf.py` o su reemplazo), inmediatamente después de generar `OBS_DOMAIN101` y antes de invocar el binario del modelo.

Si cualquier chequeo bloqueante falla, el pipeline debe **detenerse sin ejecutar WRF** y reportar la causa específica. Los chequeos no bloqueantes deben quedar registrados como advertencia en el log de la corrida.

---

## 2. Categorías de chequeo

### 2.1 Datos de entrada (GFS / WPS)

| # | Chequeo | Cómo verificar | Criterio | Acción si falla |
|---|---|---|---|---|
| 2.1.1 | Completitud de los archivos GFS | Verificar que existan todos los `f000`–`f012` esperados según `run_hours` | Todos los archivos presentes y con tamaño > 0 | Bloqueante: abortar y reportar archivo faltante |
| 2.1.2 | Éxito de WPS | Revisar los logs de `geogrid.exe`, `ungrib.exe`, `metgrid.exe` | Cada uno debe terminar con `Successful completion` | Bloqueante: abortar |
| 2.1.3 | Cantidad de niveles verticales de `met_em` | Comparar `num_metgrid_levels` del namelist contra los niveles reales de los `met_em` generados | Deben coincidir | Bloqueante: abortar |
| 2.1.4 | Vientos extremos en niveles altos | Escanear el campo de viento en los `met_em` (o en el GRIB de GFS) buscando valores anómalos en la tropopausa/estratosfera | Advertir si `\|viento\| > 80 m/s` en algún nivel (umbral ajustable) | No bloqueante, pero fuerza a activar el perfil de estabilidad reforzada (ver 2.4.4) — motivado por el jet de ~114 m/s del 06/08/2026 |

### 2.2 Observaciones y generación de OBS_DOMAIN101

| # | Chequeo | Cómo verificar | Criterio | Acción si falla |
|---|---|---|---|---|
| 2.2.1 | Existencia y tamaño del JSON de observaciones | Verificar que el archivo de entrada exista y tenga registros | `n_registros > 0` | Bloqueante: abortar |
| 2.2.2 | Formato de observación de superficie (FORMAT 105) | Contar los pares de campos por línea del `OBS_DOMAIN101` generado | Deben ser exactamente 9 pares (slp, ref_pres, height, temperature, u, v, rh, psfc, precip); rechazar si tiene 6 pares (formato 104, de sondeos) | Bloqueante: abortar — motivado por el bug de formato del 12/08/2026 |
| 2.2.3 | Identificador de plataforma | Verificar que el campo de plataforma en el header sea `SYNOP`, correctamente alineado en la posición esperada | Coincidencia exacta de posición y valor | No bloqueante (es cosmético según lo documentado), pero registrar advertencia |
| 2.2.4 | Timestamps de las observaciones | Verificar que no existan desfases artificiales (p. ej. +1 segundo por estación) y que el formato de fecha sea el estándar de WRF | Timestamps en el formato e intervalo reales de las observaciones (p. ej. cada 5 min), sin offsets sintéticos | Bloqueante: abortar — motivado por el bug de `_desfase_por_estacion` (bug crítico corregido en `obsnud_writer.py`, `sens_coef0001`) |
| 2.2.5 | Cantidad de observaciones vs. `max_obs` | Comparar el número de registros en `OBS_DOMAIN101` contra el valor de `max_obs` del namelist | `max_obs > 0` y `max_obs >= n_registros` | Bloqueante: abortar — motivado por el caso `max_obs=0` (default) que dejaba `NIOBF=0` y no leía ninguna observación (12/08/2026) |
| 2.2.6 | Cobertura temporal de las observaciones | Verificar que existan observaciones distribuidas a lo largo de toda la ventana de simulación (no solo al inicio) | Al menos N observaciones por cada tercio del período simulado (umbral configurable) | No bloqueante, advertencia — para poder interpretar correctamente por qué el nudging no actúa en cierto tramo |

### 2.3 Namelist y configuración numérica

| # | Chequeo | Cómo verificar | Criterio | Acción si falla |
|---|---|---|---|---|
| 2.3.1 | Coherencia `fdda_end` vs `run_hours` | Comparar `fdda_end` (minutos) contra `run_hours * 60` | `fdda_end` debe cubrir la duración total deseada del nudging | Bloqueante o advertencia según la intención declarada de la corrida |
| 2.3.2 | Coeficientes de nudging dentro de rango conocido | Verificar que `obs_coef_wind/temp/mois` estén dentro del rango explorado y validado (p. ej. 0.0001–0.0005) | Advertir si están fuera de ese rango, ya que no hay evidencia de estabilidad/desempeño fuera de él | No bloqueante, advertencia |
| 2.3.3 | Parámetros de estabilidad numérica presentes | Verificar que `use_adaptive_time_step`, `diff_6th_opt`, `damp_opt`/`dampcoef`/`zdamp` estén configurados según el perfil de estabilidad vigente | Deben estar activos si el chequeo 2.1.4 detectó vientos extremos | Bloqueante si 2.1.4 marcó riesgo alto y estos parámetros no están activos |
| 2.3.4 | Consistencia entre namelist Nudged y Control | Verificar que ambos namelists sean idénticos salvo por los parámetros de `obs_nudge_opt`/`obs_coef_*` | Diferencias limitadas a los parámetros de nudging | Bloqueante: abortar — evita comparar corridas con configuraciones físicas distintas por error |

### 2.4 Entorno de ejecución

| # | Chequeo | Cómo verificar | Criterio | Acción si falla |
|---|---|---|---|---|
| 2.4.1 | Variable `OMP_NUM_THREADS` | Verificar que esté fijada explícitamente antes de lanzar `wrf.exe` en builds `smpar`/OpenMP | `OMP_NUM_THREADS=1` (o el valor validado para el build en uso) | Bloqueante: abortar — motivado por el requisito de builds `smpar` (12/08/2026) |
| 2.4.2 | `LD_LIBRARY_PATH` limpio | Verificar que no contenga librerías MPICH incompatibles ni rutas de un entorno virtual que interfieran (p. ej. `HDF5_PLUGIN_PATH`) | Entorno "limpio" validado para la ejecución de `wrf.exe` | Bloqueante: abortar — motivado por el SIGSEGV intermitente del 06/08/2026 |
| 2.4.3 | Redirección de salida del proceso | Confirmar que la invocación de `wrf.exe` redirige stdout/stderr a archivo, en lugar de usar `capture_output=True` por pipe | Redirección a archivo de log configurada | Bloqueante: abortar — motivado por el SIGSEGV reproducible al capturar por pipe (12/08/2026) |
| 2.4.4 | Perfil de estabilidad reforzada activo cuando corresponde | Si 2.1.4 marcó vientos extremos, verificar que el timestep adaptativo y la difusión de 6º orden estén activos (ver 2.3.3) | Ver 2.3.3 | Bloqueante si no está activo |
| 2.4.5 | Versión de WRF y compatibilidad de formato | Registrar y verificar la versión del binario de `wrf.exe` (4.0/4.5/4.6.x) contra la versión para la que fue validado el generador de `OBS_DOMAIN101` | Coincidencia documentada o confirmación explícita de compatibilidad cruzada | No bloqueante por ahora (pendiente de confirmación formal), pero debe quedar registrado en el log — motivado por la duda de compatibilidad 4.0 vs 4.5 (`sens_coef0001`) |

### 2.5 Recursos y tiempo estimado

| # | Chequeo | Cómo verificar | Criterio | Acción si falla |
|---|---|---|---|---|
| 2.5.1 | Espacio en disco disponible | Verificar espacio libre en el directorio de resultados | Suficiente para 13 wrfout × 2 corridas + productos de validación | Bloqueante: abortar |
| 2.5.2 | Corrida anterior no finalizada | Verificar que no exista un proceso `wrf.exe` colgado o un lock de una corrida previa incompleta para el mismo caso | Sin proceso ni lock activo | Bloqueante: abortar o requerir limpieza explícita |
| 2.5.3 | Tiempo estimado de ejecución | Registrar el tiempo esperado según el histórico de corridas equivalentes | Advertir si no hay referencia histórica, para poder detectar luego desvíos anómalos (ver nota) | No bloqueante, informativo |

> **Nota sobre 2.5.3:** en `sens_coef0001` la corrida Nudged tardó 7 min 13 s contra 2 min 34 s de la Control, mientras que en los ciclos del 06/08 y 12/08 ambas corridas duraron aproximadamente lo mismo. Este chequeo no diagnostica la causa, pero deja registrado el tiempo esperado para poder detectar automáticamente esa clase de desvíos en corridas futuras.

---

## 3. Resultado del preflight

El resultado de todos los chequeos debe resumirse en un reporte corto (`preflight_<caso>.json` o `.log`) con tres posibles estados por chequeo:

- **OK** — condición verificada correctamente.
- **ADVERTENCIA** — no bloquea la corrida, pero se registra para su revisión posterior.
- **BLOQUEANTE** — impide el lanzamiento de `wrf.exe`; el pipeline debe detenerse y reportar el motivo exacto.

El pipeline solo debe invocar `wrf.exe` si no existe ningún chequeo en estado BLOQUEANTE.

---

## 4. Próximos pasos de implementación

1. Implementar los chequeos de la sección 2.2 (observaciones/formato) como módulo independiente y testeable, dado que ahí se concentraron los tres bugs críticos encontrados hasta ahora.
2. Integrar el preflight como una etapa explícita del pipeline, entre la generación de `OBS_DOMAIN101` y la invocación de `wrf.exe`.
3. Definir los umbrales configurables (vientos extremos, rango de coeficientes, espacio en disco) en un archivo de configuración único, no hardcodeados.
4. Acompañar cada chequeo bloqueante con un mensaje de error que indique explícitamente la causa y el chequeo que lo originó, para mantener la trazabilidad con este documento.
5. Una vez estabilizado, agregar pruebas de regresión automáticas (caso de referencia pequeño) que corran este preflight en cada cambio del pipeline.
