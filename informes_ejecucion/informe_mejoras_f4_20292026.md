# Informe de mejoras — Fase 4 (casos de estudio)

**Fecha del informe:** 20 de septiembre de 2026
**Alcance:** revisión de `src/validacion/valida_wrf_cli.py`, `pipeline_wrf.py`, `config/estaciones.json` y `src/asimilacion/obsnud_writer.py`, contrastada contra los hallazgos de los informes de ejecución previos (ciclos 06/08, 12/08, `sens_coef0001`, y los tres casos de estudio Zonda/Calor/Frente frío).

---

## 1. Objetivo del documento

Este informe actualiza el listado priorizado de problemas entregado anteriormente, incorporando lo que surge de revisar el código fuente actual. Dos cosas cambian respecto de la lista previa:

1. Se confirma que el **hold-out espacial** (separar estaciones "asimiladas" de estaciones "de evaluación") ya está completamente implementado y conectado — no es una funcionalidad pendiente, es una funcionalidad **construida y corriendo, pero cuyos resultados nadie está mirando todavía**.
2. Se encuentra una **inconsistencia de documentación** en `obsnud_writer.py` que puede inducir a error a quien lea el código en el futuro.

El resto de los puntos de la lista anterior se revisó contra el código actual y se marca explícitamente como resuelto, vigente o parcialmente vigente.

---

## 2. Hallazgo principal de esta revisión: el hold-out ya funciona, pero está "apagado" a nivel de reporte

Verificado en tres archivos, de punta a punta:

- **`config/estaciones.json`** ya tiene el campo `"rol"` asignado para las 9 estaciones de la red: `CARACOLES`, `ULLUM_EMBALSE` e `INTA_SANMARTIN` están marcadas `"evaluacion"`; el resto, `"asimilacion"`.
- **`src/asimilacion/obsnud_writer.py`**, método `generar_desde_dataframe()` (línea ~130): excluye explícitamente de `OBS_DOMAIN101` a toda observación cuya estación tenga `rol == "evaluacion"` — es decir, esas estaciones **nunca se asimilan**, quedan genuinamente "ciegas" para el modelo.
- **`src/validacion/valida_wrf_cli.py`**, función `main()` (líneas 636-661): para cada horario de validación, separa las estaciones en `idx_asim` / `idx_eval` según ese mismo campo `rol`, y si ambos grupos tienen datos, escribe dos archivos separados:
  - `metricas_resumen_asimiladas.txt` (ajuste: qué tan bien el modelo reproduce lo que ya se le dio)
  - `metricas_resumen_holdout.txt` (generalización: mejora real de pronóstico en lugares nunca asimilados)
- **`pipeline_wrf.py`**, función `run_valida_wrf()` (línea 374): pasa `--estaciones-json` en cada invocación de `valida_wrf_cli.py`, así que esta separación se ejecuta automáticamente en cada corrida del pipeline, incluidas las de los tres casos de estudio.

**Conclusión:** para el Caso 1 (Zonda), de las 7 estaciones con datos en la ventana, `CARACOLES` y `ULLUM_EMBALSE` son hold-out. Eso significa que **muy probablemente ya existan, en el disco de resultados, los archivos `metricas_resumen_asimiladas.txt` y `metricas_resumen_holdout.txt`** para cada horario (00Z/06Z/12Z) de los tres casos ya ejecutados — el archivo con la respuesta a "¿el nudging generaliza a lugares sin datos?" ya se generó y nadie lo abrió todavía.

Sin embargo, `src/casos/run_casos.py` (el script que redacta los `.md` que venimos analizando) **no lee ni menciona estos archivos en ningún lugar** — se verificó que no contiene ninguna referencia a `holdout`, `asimiladas` ni `evaluacion`. Es decir: el dato más valioso para la tesis (generalización real, no solo ajuste) existe en disco pero no llega a ningún informe.

---

## 3. Lista priorizada de problemas (actualizada)

### 🔴 Crítico

**3.1. Los resultados de hold-out existen pero no se reportan**
- **Estado:** nuevo hallazgo de esta revisión (ver sección 2).
- **Solución:** antes de generar cualquier informe nuevo, revisar si ya existen `metricas_resumen_holdout.txt` / `metricas_resumen_asimiladas.txt` en `results/<ciclo>/<caso>/<hora>Z/` de los tres casos ya corridos. Si existen, incorporarlos al informe de cada caso (una sección "Ajuste vs. generalización"). Si no existen para algún caso, alcanza con volver a correr la validación (no la simulación) para generarlos.
- **Mejora de código sugerida:** que `write_tabla_evolutiva()` incluya también los resultados de ajuste/holdout en `tabla_evolutiva.json`, para que `run_casos.py` pueda leerlos con el mismo mecanismo que ya usa para las métricas generales, en lugar de tener que parsear un `.txt` aparte.

**3.2. Casos 2 y 3 no están re-corridos con el método de validación sin pseudo-replicación**
- **Estado:** sigue vigente, sin cambios desde la revisión anterior.
- **Solución:** volver a correr `valida_wrf_cli.py` sobre los wrfout ya generados de ambos casos.

### 🟠 Alto

**3.3. Tamaño de muestra chico para r y viento (N=6-9 estaciones, y ahora también el hold-out reduce aún más la muestra por grupo)**
- **Estado:** vigente. Con el hold-out activo, el grupo de ajuste queda con ~5 estaciones y el de evaluación con 2-3 — muestras todavía más chicas que antes para calcular r de forma confiable.
- **Solución:** no sacar conclusiones fuertes de un único caso/horario/grupo; acumular casos y, si es posible, reportar con intervalos de confianza.

**3.4. `fdda_end` sigue fijado siempre a 720 min, independientemente de `run_hours`**
- **Estado:** confirmado vigente en esta revisión. `pipeline_wrf.py` línea 158: `mgr.contenido = re.sub(r'fdda_end\s*=\s*\d+', 'fdda_end = 720', mgr.contenido)`, sin condicionarlo al `run_hours` leído en la línea 148.
- **Solución:** calcular `fdda_end` como `run_hours * 60` en lugar de un valor fijo.

**3.5. Sesgo sistemático de PSFC (~-30 a -40 hPa) sin corrección**
- **Estado:** vigente, sin cambios.
- **Solución:** corrección aditiva por estación en post-proceso, dado lo predecible del sesgo (r≈0.86-0.88 estable en todos los casos).

### 🟡 Medio

**3.6. Inconsistencia de documentación en `obsnud_writer.py` (hallazgo nuevo)**
- **Descripción:** el docstring de `escribir_obsnud()` afirma: *"cada estación recibe un desfase único de segundos (ver `_desfase_por_estacion`) para evitar observaciones simultáneas de estaciones distintas, que disparan un SIGSEGV en el binario WRF 4.5"*. Pero `_desfase_por_estacion()` (según su propio docstring y su implementación actual) **devuelve desfase cero para todas las estaciones**, precisamente porque un desfase distinto de cero fue lo que causó el bug corregido en el experimento `sens_coef0001` (error `Bad value during integer read`). Las dos funciones documentan objetivos contradictorios: una dice que el desfase evita un SIGSEGV; la otra dice que el desfase fue eliminado porque causaba un error de lectura.
- **Riesgo:** quien lea solo el docstring de `escribir_obsnud()` puede creer que existe una protección contra observaciones simultáneas de distintas estaciones que en realidad no está activa. Si ese escenario (dos estaciones con el mismo timestamp exacto) alguna vez causa un problema real, el código no lo previene pese a lo que dice el comentario.
- **Solución:** actualizar el docstring de `escribir_obsnud()` para que refleje el comportamiento real (desfase cero, orden cronológico estable como única protección), y documentar explícitamente si el caso de estaciones simultáneas fue probado y resultó inofensivo, o si sigue siendo un riesgo no verificado.

**3.7. Texto de "limitación de dominio" hardcodeado citando siempre "el caso 1 (Zonda)"**
- **Estado:** vigente, sin cambios (no se subió `run_casos.py` en esta tanda, pero nada indica que se haya corregido).
- **Solución:** parametrizar el párrafo para que cite el caso correspondiente.

**3.8. Cálculo de `r` duplicado en dos módulos (`metrics.py` y `valida_wrf_cli.py`)**
- **Estado:** vigente.
- **Solución:** unificar en una sola función compartida.

**3.9. Asimetría de tiempos de ejecución sin diagnosticar (Nudged vs. Control)**
- **Estado:** vigente, sin información nueva en los archivos revisados esta vez.
- **Solución:** que `WRFRunner` reporte cuántos reintentos consumió cada corrida.

### 🟢 Bajo / mejora a futuro

**3.10. No hay barrido automático de coeficientes de nudging.** Sin cambios.

**3.11. El flujo automatizado llega hasta la validación, no hasta un producto de pronóstico.** Sin cambios.

---

## 4. Próximos pasos recomendados, en orden

1. Revisar si ya existen los archivos `metricas_resumen_asimiladas.txt` / `metricas_resumen_holdout.txt` para los tres casos ya ejecutados (sección 3.1). Es el paso de menor esfuerzo y mayor valor: puede que la respuesta a "¿el nudging generaliza?" ya esté calculada.
2. Re-correr la validación (no la simulación) de los Casos 2 y 3 con la versión actual de `valida_wrf_cli.py`, para que los tres casos sean comparables entre sí (sección 3.2).
3. Incorporar los resultados de ajuste/holdout a los informes de caso, aunque sea de forma manual al principio.
4. Corregir `fdda_end` hardcodeado (3.4) antes de correr cualquier ciclo con duración distinta a 12 h.
5. Actualizar el docstring de `obsnud_writer.py` (3.6) para que no induzca a error.
6. El resto de los puntos (PSFC, texto hardcodeado, duplicación de `r`, tiempos de ejecución, barrido de coeficientes, automatización end-to-end) quedan en la cola en el orden ya priorizado.
