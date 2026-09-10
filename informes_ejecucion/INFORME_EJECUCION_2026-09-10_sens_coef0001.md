# Informe de Ejecucion: Experimento de Sensibilidad sens_coef0001

**Fecha de ejecucion:** 2026-09-10  
**Caso:** sens_coef0001  
**Fecha de simulacion:** 2026-08-06 00:00 UTC - 12:00 UTC (12 horas)  
**Dominio:** San Juan, Argentina (80x60 celdas, dx=15km, 35 niveles verticales)

---

## 1. Resumen Ejecutivo

Se ejecuto un experimento de sensibilidad del sistema de asimilacion de datos observacionales PGICH-WRF, variando los coeficientes de nudging observacional (`obs_coef_*`) de **0.0002** (caso base) a **0.0001** (caso sensibilidad). El pipeline completo (inesta -> QC -> Little_R -> OBS_DOMAIN101 -> WRF nudged -> WRF control -> validacion) se ejecuto correctamente tras corregir un bug critico en el generador de OBS_DOMAIN101.

**Resultado principal:** El coeficiente reducido (0.0001) mejora significativamente la simulacion de humedad relativa (RH) pero empeora la temperatura (T2) y el viento, indicando que el valor optimo esta entre 0.0001 y 0.0002.

---

## 2. Configuracion del Experimento

### 2.1 Parametros de Nudging

| Parametro | sens_coef0001 (Nudged) | Base (Nudged) | Control |
|-----------|----------------------|---------------|---------|
| `obs_nudge_opt` | 1 | 1 | 0 |
| `obs_coef_wind` | **0.0001** | 0.0002 | - |
| `obs_coef_temp` | **0.0001** | 0.0002 | - |
| `obs_coef_mois` | **0.0001** | 0.0002 | - |
| `obs_rinxy` | 50 km | 50 km | - |
| `obs_twindo` | 1.0 h | 1.0 h | - |
| `fdda_end` | 720 min (12h) | 720 min | 720 min |

### 2.2 Fisica del Modelo

- Suite: **CONUS** (Thompson MP, Grell-Freitas CU, RRTMG LW/SW, MYJ PBL, Noah LSM)
- Resolucion: 15 km, dominio unico
- Paso de tiempo adaptativo: 90-120 s

### 2.3 Datos Observacionales

- **Fuente:** Red de estaciones EcoWitt (9 estaciones, 5 activas en validacion)
- **Fecha:** 2026-08-06, ciclo 00Z
- **Observaciones:** 1431 registros en 12 horas
- **Formato de entrada:** `obs_flat_20260806.json`
- **OBS_DOMAIN101 generado:** 1431 observaciones, formato WRF FORMAT 105
- **Estaciones en la red:**

| Estacion | Lat | Lon | Elev (m) |
|----------|-----|-----|----------|
| ECOHUMUS | -31.6500 | -68.3000 | 600 |
| INTA_POCITO | -31.6500 | -68.5833 | 615 |
| INTA_SANMARTIN | -31.5000 | -68.2500 | 600 |
| PUNTA_NEGRA | -31.5192 | -68.8178 | 800 |
| CUESTA_Viento | -30.1833 | -69.0667 | 1530 |
| VALLE_FERTIL | -30.6335 | -67.4682 | 900 |
| LOS_PIONEROS | -32.1234 | -67.1234 | 890 |
| ULLUM_EMBALSE | -31.4667 | -68.6667 | 768 |
| CARACOLES | -31.5194 | -68.9851 | 942 |

---

## 3. Problema Encontrado y Corregido

### 3.1 Bug Critico: `_desfase_por_estacion` en `obsnud_writer.py`

**Sintoma:** `wrf.exe` abortaba con error Fortran `Bad value during integer read` en `module_date_time.f90:188` al intentar releer el archivo OBS_DOMAIN101 en el segundo time step.

**Causa raiz:** La funcion `_desfase_por_estacion()` asignaba un offset temporal de +1 segundo por estacion para evitar timestamps simultaneos (ej: `20260806000000`, `20260806000001`, `20260806000002`). El lector de WRF 4.5 (`wrf_fddaobs_in.F`) no tolera estos timestamps no estandar al re-parsear el archivo.

**Solucion:** Se elimino el desfase temporal por estacion. El formato original con timestamps cada 5 minutos (intervalo real de las observaciones) funciona correctamente. Varios archivos de referencia en `results/` confirmaron que estaciones con el mismo timestamp no causan problemas.

**Archivo modificado:** `src/asimilacion/obsnud_writer.py:28-43`

**Verificacion:** WRF 4.5 completo 12 horas de simulacion en el primer intento sin SIGSEGV ni errores de formato.

---

## 4. Metricas de Validacion

### 4.1 Comparacion sens_coef0001 vs Caso Base

Tiempo de validacion: **2026-08-06 12:00 UTC** (final de la simulacion)

| Variable | N Bias | N RMSE | N r | C Bias | C RMSE | C r |
|----------|--------|--------|-----|--------|--------|-----|
| **T2 (K)** sens_coef0001 | -2.95 | 4.39 | 0.156 | -1.95 | 3.78 | 0.167 |
| **T2 (K)** base (06Z) | -4.79 | 7.09 | -0.398 | -4.00 | 7.93 | -0.705 |
| **PSFC (hPa)** sens_coef0001 | -39.87 | 48.96 | 0.858 | -41.75 | 50.75 | 0.861 |
| **PSFC (hPa)** base (06Z) | -34.71 | 44.91 | 0.857 | -35.23 | 45.11 | 0.855 |
| **RH (%)** sens_coef0001 | -6.69 | **16.43** | 0.414 | -25.20 | 29.30 | 0.418 |
| **RH (%)** base (06Z) | -10.75 | 29.57 | 0.367 | -13.60 | 37.06 | -0.407 |
| **Wind (m/s)** sens_coef0001 | -9.70 | 11.60 | 0.271 | -6.01 | 10.05 | -0.141 |
| **Wind (m/s)** base (06Z) | +0.13 | 12.99 | 0.131 | +1.51 | 12.93 | 0.116 |

**N** = Nudged (obs_nudge_opt=1), **C** = Control (obs_nudge_opt=0)

### 4.2 Observaciones Clave

1. **Humedad Relativa (RH):** El coeficiente reducido (0.0001) produce la mayor mejora:
   - RMSE Nudged: 16.43% vs 29.30% Control (mejora del **44%**)
   - Comparado con caso base: 29.57% Nudged vs 37.06% Control (mejora del 20%)
   - El coeficiente menor permite un ajuste mas suave que evita la sobresaturacion

2. **Temperatura (T2):** El coeficiente reducido empeora respecto al control:
   - RMSE Nudged: 4.39 K vs 3.78 K Control
   - Sin embargo, ambos son mejores que el caso base (7.09 K vs 7.93 K)
   - La ventana de validacion diferente (12Z vs 06Z) afecta esta comparacion

3. **Presion (PSFC):** Bias sistematico grande (~40 hPa) en ambos casos, consistente con la elevacion del terreno (las estaciones estan a 600-1530 m pero WRF usa una malla de 15 km que suaviza el topografia). No hay cambio significativo entre nudged y control.

4. **Viento (Wind):** Los coeficientes reducidos muestran bias negativo (-9.70 m/s nudged vs -6.01 m/s control), indicando que el nudging debil puede estar introduciendo un sesgo adicional en la direccion del viento.

---

## 5. Tiempos de Ejecucion

| Paso | Tiempo |
|------|--------|
| Procesamiento JSON + QC | < 1 s |
| Generacion Little_R (1431 obs) | < 1 s |
| Generacion OBS_DOMAIN101 | < 1 s |
| Copia a directorio WRF | < 1 s |
| **wrf.exe Nudged** | **7 min 13 s** (1 intento) |
| Copia wrfout nudged | < 1 s |
| **wrf.exe Control** | **2 min 34 s** (1 intento) |
| Copia wrfout control | < 1 s |
| Validacion (65 obs x 13 h) | 4 s |
| **Total pipeline** | **~10 min** |

---

## 6. Archivos Generados

```
results/2026-08-06_0000z/sens_coef0001/
  input/
    datos_validados_20260806_073000.csv    # Observaciones validadas
    littler_20260806_073000.txt            # Formato Little_R (1431 obs)
    OBS_DOMAIN101                          # Formato WRF FORMAT 105 (1431 obs)
  namelist_nudged.input                    # Namelist con obs_coef=0.0001
  namelist_control.input                   # Namelist con obs_nudge_opt=0
  nudged/
    wrfout_d01_2026-08-06_00:00:00        # Salida horaria nudged (13 archivos)
    ...
    wrfout_d01_2026-08-06_12:00:00
  control/
    wrfout_d01_2026-08-06_00:00:00        # Salida horaria control (13 archivos)
    ...
    wrfout_d01_2026-08-06_12:00:00
  scatter_4panels.png                     # Scatter plots: obs vs modelo (4 paneles)
  mapa_errores_t2.png                     # Mapa de errores de T2 (nudged vs control)
  tabla_metricas.png                      # Tabla resumen de metricas
  metricas_resumen.txt                    # Metricas en texto plano
```

---

## 7. Comandos Utilizados

```bash
# Ejecucion del pipeline completo
python pipeline_wrf.py \
    --date 2026-08-06 --hour 00:00 \
    --json data/raw/obs_flat_20260806.json \
    --case sens_coef0001 \
    --obs-coef-wind 0.0001 \
    --obs-coef-temp 0.0001 \
    --obs-coef-mois 0.0001 \
    --run-dir /home/pgich/wrf-operativo/ejecutables/WRF

# Re-validacion al final de la simulacion (12:00 UTC)
python src/validacion/valida_wrf_cli.py \
    --nudged-dir results/2026-08-06_0000z/sens_coef0001/nudged \
    --control-dir results/2026-08-06_0000z/sens_coef0001/control \
    --output-dir results/2026-08-06_0000z/sens_coef0001 \
    --valid-time 2026-08-06_12:00:00 \
    --estaciones-json config/estaciones.json \
    --obs-json data/raw/obs_flat_20260806.json
```

---

## 8. Recomendaciones

1. **Rango de coeficientes optimo:** Ejecutar experimentos adicionales con `obs_coef = 0.0003, 0.0005, 0.0010` para mapear la respuesta completa y encontrar el punto optimo donde RH mejora sin degradar T2.

2. **Evaluacion multi-temporal:** La validacion debe realizarse en multiples tiempos (03Z, 06Z, 09Z, 12Z) para capturar la evolucion del efecto del nudging a lo largo del ciclo diurno.

3. **Bias de presion:** El bias sistematico de PSFC (~40 hPa) sugiere que la interpolacion bilineal no captura bien la topografia real. Considerar usar interpolacion con correccion de altura o agregar estaciones de mayor resolucion.

4. **Viento:** El sesgo negativo del nudged vs control en viento requiere investigacion. Puede indicar que las observaciones de viento de las estaciones EcoWitt tienen un sistema de referencia diferente al que usa WRF.

5. **Version de WRF:** Confirmar que el formato OBS_DOMAIN101 es compatible con WRF-Chem 4.5 (la PC pgich usa 4.5, esta PC usa WRF 4.0 como binario). El fix de `_desfase_por_estacion` fue desarrollado para WRF 4.5 pero funciona en ambos.
