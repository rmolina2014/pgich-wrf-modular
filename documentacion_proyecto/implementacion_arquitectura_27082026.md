# Guía de Implementación y Réplica de Arquitectura en Producción
**Documento:** `implementacion_arquitectura_27082026.md`  
**Fecha:** 27 de agosto de 2026  
**Proyecto:** Tesis de Maestría en Informática — Asimilación de Datos Meteorológicos EcoWitt en WRF (Obs Nudging / FDDA)  
**Dominio de Estudio:** San Juan / Cuyo (Argentina)  
**Versión del Sistema:** PGICH v0.2.0 (Arquitectura Modular Python)

---

## 1. Visión General y Objetivos de Producción

Este documento detalla la arquitectura modular implementada y los pasos técnicos para su despliegue y réplica exacta en un entorno de producción (servidor Linux nativo, clúster o contenedor Docker).

### 1.1 Diagrama de Arquitectura Modular del Sistema

```text
                                 Fuentes Externas
                        ┌───────────────────────────────┐
                        │   API EcoWitt v3 (Tiempo Real)│
                        │   AWS S3 / NOMADS (GFS 0.25°) │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                          PAQUETE MODULAR (src/)                               │
│                                                                               │
│  [src.ingesta]                                                                │
│  ├── ecowitt_client.py  ──> data/raw/ecowitt_todos_*.json                     │
│  └── gfs_downloader.py  ──> data/gfs/gfs.t*z.pgrb2.0p25.f*                   │
│                                                                               │
│  [src.calidad]                                                                │
│  ├── qc_rules.py        ──> Límites físicos y control de coherencia           │
│  └── cleaner.py         ──> data/processed/datos_validados_*.csv              │
│                                                                               │
│  [src.asimilacion]                                                            │
│  ├── littler_writer.py  ──> data/processed/littler_*.txt                      │
│  └── obsnud_writer.py   ──> data/processed/OBS_DOMAIN101 (FORMAT 105 SYNOP)   │
│                                                                               │
│  [src.modelo]                                                                 │
│  ├── namelist_manager.py──> namelist.input (parcheo dinámico de fechas/FDDA) │
│  ├── wps_runner.py      ──> geogrid / ungrib / metgrid (met_em.d01.*.nc)      │
│  └── wrf_runner.py      ──> real.exe / wrf.exe (OMP_NUM_THREADS=1, logs)     │
│                                                                               │
│  [src.validacion]                                                             │
│  ├── spatial_interp.py  ──> Interpolación 4 nodos, Tetens (HR), viento u/v    │
│  └── metrics.py         ──> Bias, MAE, RMSE, Pearson r, % mejora nudged      │
│                                                                               │
│  [src.reporting]                                                              │
│  ├── plot_generator.py  ──> plots/scatter_4panels.png, plots/mapa_errores.png │
│  ├── report_builder.py  ──> experiments/manifest.json, INFORME.md            │
│  └── experiment_registry.py ──> experiments/experiment_registry.jsonl         │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                 [Panel Streamlit]             [CLI / Cron Batch]
                 tesis_wrf_pgich/app.py        pipeline_wrf.py
```

---

## 2. Inventario de Componentes y Archivos de Implementación

### 2.1 Módulos Centrales (`src/`)

| Módulo | Archivo | Responsabilidad Principal |
|---|---|---|
| Ingesta | `src/ingesta/ecowitt_client.py` | Cliente HTTP con rate limit (1s) para consultar estaciones EcoWitt y Ecohumus. |
| Ingesta | `src/ingesta/gfs_downloader.py` | Descarga de forzantes globales GFS 0.25° desde AWS S3 Open Data o NOMADS. |
| Calidad | `src/calidad/qc_rules.py` | Reglas de filtrado de rangos físicos y umbrales climatológicos de San Juan. |
| Calidad | `src/calidad/cleaner.py` | Normalización de timestamps y exportación de DataFrames limpios a CSV/Excel. |
| Asimilación | `src/asimilacion/littler_writer.py` | Conversión a formato Little_R (ASCII Fortran WRFDA). |
| Asimilación | `src/asimilacion/obsnud_writer.py` | Generación de `OBS_DOMAIN101` bajo formato estricto FORMAT 105 con cabecera `SYNOP` (plfo=4) y flags QC. |
| Modelo | `src/modelo/namelist_manager.py` | Actualización programática de `namelist.input` (`&time_control`, `&fdda`). |
| Modelo | `src/modelo/wps_runner.py` | Verificación de archivos `met_em` y ejecución de la cadena WPS. |
| Modelo | `src/modelo/wrf_runner.py` | Ejecución y monitoreo de `real.exe` y `wrf.exe` (Nudged y Control). |
| Validación | `src/validacion/spatial_interp.py` | Interpolación espacial a coordenadas de estaciones, cálculo de HR y corrección barométrica. |
| Validación | `src/validacion/metrics.py` | Métricas estadísticas objetivas: Bias, MAE, RMSE, correlación $r$ de Pearson y porcentaje de mejora. |
| Reporting | `src/reporting/plot_generator.py` | Gráficos científicos de dispersión (4 paneles) y mapas espaciales de errores. |
| Reporting | `src/reporting/report_builder.py` | Generación del archivo `manifest.json` y del informe reproducible `INFORME.md`. |
| Reporting | `src/reporting/experiment_registry.py` | Registro atómico de experimentos en `experiments/experiment_registry.jsonl`. |

### 2.2 Archivos de Configuración y Templates (`config/`)

- `config/estaciones.json`: **Fuente única de verdad** de la red de estaciones:
  ```json
  {
      "INTA_POCITO": {"lat": -31.6500, "lon": -68.5833, "elev": 615},
      "ULLUM_EMBALSE": {"lat": -31.4667, "lon": -68.6667, "elev": 768},
      "ECOHUMUS": {"lat": -31.6500, "lon": -68.3000, "elev": 600},
      "PUNTA_NEGRA": {"lat": -31.5192, "lon": -68.8178, "elev": 800}
  }
  ```
- `config/namelist.input.template`: Plantilla base configurada para el dominio de 15 km de San Juan (80×60 puntos, 35 niveles) y bloque `&fdda`.
- `config/namelist.wps.template`: Plantilla WPS para `geogrid`, `ungrib` y `metgrid`.

### 2.3 Interfaces y Pruebas

- `tesis_wrf_pgich/app.py`: Panel de control interactivo Streamlit con 6 módulos.
- `tests/test_circuito_modular.py`: Suite de 10 pruebas unitarias y de integración end-to-end.
- `pyproject.toml`: Declaración de dependencias del proyecto optimizado para `uv`.
- `tesis_wrf_pgich/Dockerfile`: Receta para despliegue en contenedores.

---

## 3. Requisitos del Sistema en Producción

### 3.1 Servidor de Cómputo (Host Linux)
- **Sistema Operativo:** Ubuntu 22.04 LTS o Debian 12 / RHEL 8+.
- **Python:** Python 3.11 o superior.
- **Gestor de Entornos:** `uv` (recomendado para máxima velocidad y reproducibilidad) o `conda`/`virtualenv`.
- **Compiladores y Librerías WRF:**
  - NetCDF-C / NetCDF-Fortran (con soporte HDF5).
  - MPICH / OpenMPI.
  - WRF v4.5 compilado con soporte FDDA (`obs_nudge_opt=1`).
  - WPS v4.5 (`geogrid.exe`, `ungrib.exe`, `metgrid.exe`).

### 3.2 Variables de Entorno de Producción (`.env`)
Crear un archivo `.env` en la raíz del proyecto:

```bash
# Credenciales API EcoWitt (Red PGICH)
ECOWITT_APP_KEY="tu_app_key_aqui"
ECOWITT_API_KEY="tu_api_key_aqui"

# Credenciales EcoWitt para estación Ecohumus
ECOWITT_APP_KEY_ECOHUMUS="tu_app_key_ecohumus_aqui"
ECOWITT_API_KEY_ECOHUMUS="tu_api_key_ecohumus_aqui"

# Rutas del Servidor WRF / WPS
LOCAL_WRF_DIR="/home/pgich/wrf-operativo/ejecutables/WRF"
WPS_DIR="/home/pgich/wrf-operativo/WPS"
WRF_ENV_BASH="/home/pgich/wrf-operativo/ejecutables/env.bash"
VALIDATION_PYTHON="/home/pgich/anaconda3/envs/wrf-operativo-p3/bin/python"

# Configuración de Hilos OpenMP (CRÍTICO: Evita SIGSEGV en runs smpar)
OMP_NUM_THREADS="1"
```

---

## 4. Guía Paso a Paso para Despliegue en Producción

### Paso 1: Clonar el Repositorio e Instalar `uv`

```bash
# 1. Clonar el repositorio
git clone https://github.com/rmolina2014/tesisMaestriaInformatica_2026.git
cd tesisMaestriaInformatica_2026

# 2. Instalar uv (si no está instalado)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Paso 2: Crear el Entorno Virtual e Instalar Dependencias

```bash
# Sincronizar el entorno virtual con Python 3.11+
uv venv --python 3.11 .venv
source .venv/bin/activate

# Instalar las dependencias del proyecto
uv pip install -e .
```

### Paso 3: Configurar Estructura de Directorios

```bash
# Crear estructura de datos y experimentos
mkdir -p data/raw data/processed data/gfs
mkdir -p experiments
mkdir -p plots
mkdir -p logs
```

### Paso 4: Ejecutar la Suite de Pruebas Automatizadas

Antes de iniciar cualquier proceso operativo, validar la integridad de todos los módulos:

```bash
uv run python -m unittest tests/test_circuito_modular.py
```

*Salida esperada:*
```text
Ran 10 tests in ~2s
OK
```

---

## 5. Modos de Operación en Producción

### 5.1 Modo Interactivo (Panel Web Streamlit)

Para operar el sistema de forma visual, ideal para demostraciones, auditoría y análisis de casos de estudio:

```bash
# Iniciar el servidor Streamlit en segundo plano
uv run streamlit run tesis_wrf_pgich/app.py --server.port 8501 --server.address 0.0.0.0
```

Acceso: `http://<IP-DEL-SERVIDOR>:8501`

### 5.2 Modo Script / Pipeline por Lotes (CLI)

Para ejecutar simulaciones desde la terminal o scripts de bash:

```bash
# 1. Ingesta y generación de OBS_DOMAIN101
uv run python -c "
from src.ingesta.ecowitt_client import EcowittIngestor
from src.calidad.cleaner import ObservacionesCleaner
from src.asimilacion.obsnud_writer import ObsNudWriter

# Ingesta
ing = EcowittIngestor()
raw_data = ing.consultar_todas_las_estaciones()
raw_path = ing.guardar_json_crudo(raw_data)

# Limpieza
cln = ObservacionesCleaner()
df_qc = cln.procesar_json(raw_path)
cln.guardar_procesado(df_qc)

# Generación OBS_DOMAIN101
writer = ObsNudWriter()
writer.generar_desde_dataframe(df_qc, output_path='data/processed/OBS_DOMAIN101')
print('OBS_DOMAIN101 generado con éxito.')
"

# 2. Orquestar corrida completa mediante pipeline_wrf.py
uv run python pipeline_wrf.py \
    --date 2026-08-12 \
    --hour 00:00 \
    --json data/raw/ecowitt_todos_actual.json \
    --case sanjuan_fdda_prod \
    --obs-coef-temp 0.0005 \
    --obs-coef-wind 0.0005 \
    --obs-coef-mois 0.0005 \
    --obs-twindo 1.0
```

### 5.3 Despliegue con Docker (Alternativa Contenedorizada)

```bash
# 1. Construir la imagen
docker build -t pgich-wrf:latest -f tesis_wrf_pgich/Dockerfile .

# 2. Ejecutar contenedor montando volúmenes de datos y configuración
docker run -d \
    --name pgich_app \
    -p 8501:8501 \
    -v $(pwd)/data:/workspace/data \
    -v $(pwd)/config:/workspace/config \
    -v $(pwd)/experiments:/workspace/experiments \
    -v $(pwd)/.env:/workspace/.env \
    pgich-wrf:latest
```

---

## 6. Parámetros Clave de Calibración FDDA (Obs Nudging)

Para los experimentos científicos de sensibilidad, configurar los siguientes rangos en `namelist.input` (sección `&fdda`):

| Parámetro | Default | Rango Recomendado | Función Física |
|---|---|---|---|
| `obs_coef_temp` | `0.0005` | `0.0001` a `0.0020` | Coeficiente de relajación de temperatura ($s^{-1}$). Valores > 0.0010 pueden forzar el modelo excesivamente en la transición matutina (12z). |
| `obs_coef_wind` | `0.0005` | `0.0001` a `0.0010` | Coeficiente de relajación del viento ($s^{-1}$). |
| `obs_coef_mois` | `0.0005` | `0.0001` a `0.0010` | Coeficiente de relajación de humedad ($s^{-1}$). |
| `obs_twindo` | `1.0` | `0.5` a `2.0` | Ventana temporal de asimilación (horas antes/después de la observación). |
| `obs_rinxy` | `50.0` | `25.0` a `100.0` | Radio de influencia horizontal de cada estación (km). |
| `obs_sfcfacr` | `2.0` | `1.0` a `3.0` | Factor de escala de influencia en superficie. |
| `obs_npfi` | `30` | `10` a `60` | Frecuencia de cálculo del nudging (pasos de tiempo del modelo). |

---

## 7. Gobernanza y Reproducibilidad Científica

Cada experimento ejecutado en producción produce tres artefactos inmutables en `experiments/`:

1. **`manifest.json`:** Metadatos completos de la corrida, versión de código, commit hash, parámetros `&fdda`, estado de cada etapa y checksums de entradas.
2. **`INFORME.md`:** Documento Markdown generado automáticamente con tablas comparativas de Bias, MAE, RMSE, correlación $r$ y porcentaje de mejora Nudged vs Control.
3. **`experiments/experiment_registry.jsonl`:** Registro maestro atómico en formato JSON Lines para trazabilidad histórica.

---

## 8. Mantenimiento y Troubleshooting

| Síntoma / Error | Causa Probable | Solución |
|---|---|---|
| `SIGSEGV` al correr `wrf.exe` | Colisión de hilos en binario compilado con `smpar`. | Asegurar `export OMP_NUM_THREADS=1` antes de la ejecución. |
| `FATAL ERROR: CAMtr_volume_mixing_ratio does not exist` | Falta archivo auxiliar de radiación/química en el run dir. | Crear symlink a `CAMtr_volume_mixing_ratio` desde `$WRF_DIR/run/` o `$WRF_DIR/test/em_real/` hacia el directorio de corrida. |
| `Unknown ob of type SYNOP` | Cabecera FORMAT 105 incorrecta. | Utilizar siempre `src.asimilacion.obsnud_writer.ObsNudWriter` que aplica el padding correcto de 16 caracteres (`SYNOP` en chars 7–11, plfo=4). |
| `No observations within time window` | Discrepancia entre fecha de simulación y timestamp de observaciones. | Verificar que los datos en `OBS_DOMAIN101` caigan dentro del rango `[start_date - twindo, end_date + twindo]`. |
| Ingesta falla con código 40001 | Rate limit de la API EcoWitt excedido. | El cliente `EcowittIngestor` ya incorpora una pausa mínima de 1.0 segundo entre peticiones consecutivas. |
