# Informe de Avance por Fases del Proyecto

**Fecha:** 2026-09-12
**Proyecto:** Asimilación de observaciones de la red meteorológica del PGICH en el modelo WRF para mejorar pronósticos locales en el Valle de Tulum
**Autor:** Roberto Nicolas Molina
**Referencia:** Anteproyecto de Tesis (2025-12-18)

---

Este informe mapea el estado de implementación del sistema modular PGICH-WRF frente a las **cinco fases metodológicas** del anteproyecto, identificando qué está cumplido, qué está parcialmente cubierto y qué falta por desarrollar.

## Resumen ejecutivo

| Fase | Estado | Observaciones |
|---|---|---|
| Fase 1: Preparación de datos | **Parcial** | Falta el paso de agregación horaria (promediado/muestreo a 1 h) |
| Fase 2: Configuración del modelo WRF | **Completa** | Análisis de base y adaptación de scripts (WPS y WRF) realizados |
| Fase 3: Asimilación de datos | **Completa** | Esquema elegido: Observation Nudging. Decisión adoptada y justificada |
| Fase 4: Evaluación | **Parcial** | Faltan métricas por estación y análisis de casos de estudio (Zonda, heladas, olas de calor) |
| Fase 5: Integración y entrega | **Completa (con matices)** | Visualizador implementado con Streamlit (el anteproyecto mencionaba Plotly o Dash) |

---

## Fase 1: Preparación de datos — PARCIAL

Ítems del anteproyecto y su estado:

- **Adquisición (10 estaciones)** — ✅ CUBIERTO
  - `src/ingesta/ecowitt_client.py`: cliente HTTP de la API EcoWitt v3 (tiempo real e histórico), catálogo unificado de estaciones en `config/estaciones.json`, control de rate limit, manejo de errores, soporte de credenciales separadas (ECOHUMUS).
  - `src/ingesta/gfs_downloader.py`: descarga de forzamiento global GFS 0.25° desde AWS S3 / NOMADS para la inicialización de WPS.
- **Formateo (unidades SI)** — 🟠 CUBIERTO DE FORMA IMPLÍCITA
  - La conversión a SI (°C→K, hPa→Pa, km/h→m/s) ocurre en `src/asimilacion/obsnud_writer.py` al generar el archivo OBS_DOMAIN101, y no como una etapa explícita de normalización en la capa de datos (`src/calidad/cleaner.py` y `qc_rules.py`), donde las unidades se preservan tal cual vienen de la fuente (°C, hPa, km/h).
- **Control de Calidad** — ✅ CUBIERTO
  - `src/calidad/qc_rules.py`: límites físicos y climatológicos para el Valle de Tulum / precordillera; valores espurios anulados a NaN.
  - `src/calidad/cleaner.py`: procesamiento de JSON/CSV, normalización de timestamps, exportación a CSV/Excel validados.
- **Agregación (resolución horaria)** — ❌ NO IMPLEMENTADO
  - No existe módulo de promediado o muestreo a resolución horaria. El circuito actual inyecta las observaciones de 5 min directamente en OBS_DOMAIN101.
  - Acción pendiente: agregar una etapa de resampleo horario en `src/calidad/` compatible con los ciclos de asimilación.

## Fase 2: Configuración del modelo WRF — COMPLETA

- **Análisis de Base** — ✅
  - Configuración operativa documentada y parametrizada: `namelist.input`, `namelist.wps`.
  - El pull del 2026-09-12 fijó el entorno por defecto de esta PC a WRF-4.5 / WPS-4.5 (configuración operativa PGICH).
- **Adaptación de scripts (WPS y WRF)** — ✅
  - `src/modelo/namelist_manager.py`: gestión de namelist, incluyendo FDDA (`configurar_fdda`, `obs_nudge_opt`).
  - `src/modelo/wps_runner.py`: orquestación de geogrid/ungrib/metgrid y verificación de met_em.
  - `src/modelo/wrf_runner.py`: ejecución de `real.exe`/`wrf.exe` (local o Docker), verificación de éxito ("SUCCESS COMPLETE"), reintentos ante SIGSEGV intermitente.
  - `wps_sanjuan/run_wps_sanjuan.sh`: script operativo de la cadena WPS.

## Fase 3: Asimilación de datos — COMPLETA

- **Decisión del esquema** — ✅ ADOPTADA Y JUSTIFICADA
  - Se eligió **Observation Nudging** sobre **3D-Var** por bajo costo computacional, probada eficacia en redes de baja densidad y disponibilidad de recursos HPC (criterio exigido por el anteproyecto para el fin de la Fase 1).
- **Implementación** — ✅
  - `src/asimilacion/obsnud_writer.py`: generador de OBS_DOMAIN101 en formato WRF 105 (superficie, 9 pares valor/QC, plataforma "FM-12 SYNOP", orden cronológico estricto).
  - `src/modelo/namelist_manager.py`: activación de `obs_nudge_opt` y parámetros FDDA.
  - Problemas del binario WRF 4.5 encontrados y resueltos:
    - Timestamps sintéticos con desfase de 1 s por estación ("Bad value during integer read", "in4dob STOP 111"): corregido devolviendo desfase cero.
    - Formato 104 (sondeos) vs 105 (superficie): asegurado el FORMAT 105.
    - Obs simultáneas y archivos sin marcador de fin: manejados correctamente.

## Fase 4: Evaluación — PARCIAL

- **Validación cuantitativa (3 conjuntos: control, asimilación, observaciones)** — ✅
  - `src/validacion/valida_wrf_cli.py`: comparación Control vs Nudged vs observaciones en múltiples tiempos de validación (00Z/06Z/12Z), con subdirectorios por horario e informe de evolución del nudging.
  - `src/validacion/metrics.py`: cálculo formal de métricas.
- **Métricas: RMSE, MAE, sesgo, correlación de Pearson** para temperatura a 2 m, humedad relativa y velocidad del viento — ✅
  - `build_tables` en `valida_wrf_cli.py` agrega además presión en superficie (PSFC).
- **Análisis por estación (mejora espacialmente distribuida)** — 🟠 PARCIAL
  - Existe mapa de error de T2 por estación (`plot_map`), pero **no hay tabla con métricas (RMSE/MAE/bias/r) disgregadas por estación**; las tablas actuales agregan por variable en conjunto.
  - Acción pendiente: generar tabla de métricas por estación.
- **Casos de estudio (viento Zonda, heladas, ondas de calor)** — ❌ NO IMPLEMENTADO
  - Solo mencionado como recomendación en `informes_ejecucion/INFORME_EJECUCION_2026-09-10_sens_coef0001.md`.
  - Acción pendiente: definir fechas de eventos críticos y aplicarlas al circuito de validación.

## Fase 5: Integración y entrega — COMPLETA (con matices)

- **Prototipo automatizado en Python** — ✅
  - `pipeline_wrf.py`: orquesta el circuito completo (descarga → QC → generación de observaciones → preflight → ejecución de asimilación y WRF → validación → reporte).
  - `run_full_pipeline.sh`: front-end operativo de la cadena completa.
- **Flujo: descarga → obs → asimilación → ejecución WRF** — ✅
  - Generación de archivos de observación (OBS_DOMAIN101) y ejecución de las rutinas de pronóstico con el estado inicial mejorado.
- **Visualizador interactivo** — 🟠 CUBIERTO CON STREAMLIT
  - `app_streamlit.py` (Streamlit) cumple la función de visualizador interactivo (gráficos de observaciones, configuración y ejecución del pipeline).
  - El anteproyecto menciona Plotly o Dash: funcionalmente equivalente, pero con librería distinta.
- **Extras no exigidos por el anteproyecto** — ✅
  - `src/preflight/`: chequeos previos a la ejecución de WRF (Sección 2.2: JSON de obs, FORMAT 105, plataforma SYNOP, timestamps, max_obs, cobertura temporal).
  - Validación multi-temporal (00Z/06Z/12Z) con informe de evolución del nudging.
  - Control de versiones con Git y ejecución vía contenedores Docker (cumple "Infraestructura y Reproducibilidad" del marco teórico).

---

## Acciones pendientes (gaps detectados)

1. **Agregación a resolución horaria** (Fase 1): módulo de promediado/muestreo a 1 h en la capa de datos.
2. **Métricas por estación** (Fase 4): tabla de RMSE/MAE/bias/correlación disgregada por estación de la red.
3. **Casos de estudio** (Fase 4): Zonda, heladas y olas de calor — fechas de eventos críticos y corridas de validación dedicadas.
4. **Visualizador Plotly/Dash** (Fase 5, opcional): mantener Streamlit o migrar a Plotly/Dash para alinearse literalmente con el anteproyecto.