# PGICH WRF Modular - Sistema de Asimilación de Datos Observacionales

**Proyecto de Tesis de Maestría en Informática**  
**Sistema modular para asimilación de datos observacionales en el modelo WRF para la provincia de San Juan, Argentina**

## 📋 Descripción del Proyecto

Este proyecto implementa un sistema modular para la asimilación de datos observacionales en tiempo real en el modelo Weather Research and Forecasting (WRF) para la provincia de San Juan, Argentina. El sistema integra observaciones meteorológicas de estaciones EcoWitt con el modelo WRF utilizando técnicas de nudging observacional.

## 🎯 Objetivos

1. **Ingesta de datos observacionales**: Captura y procesamiento de datos meteorológicos de estaciones EcoWitt
2. **Control de calidad**: Validación y limpieza de datos observacionales
3. **Generación de Little_R**: Conversión de observaciones al formato requerido por WRF
4. **Asimilación de datos**: Integración de observaciones mediante nudging observacional
5. **Validación**: Comparación entre simulaciones con y sin asimilación de datos

## 🏗️ Arquitectura Modular

### Módulos Principales

1. **`src/ingesta/`** - Captura de datos
   - `ecowitt_client.py`: Cliente para API de EcoWitt
   - `gfs_downloader.py`: Descarga de datos GFS para inicialización

2. **`src/calidad/`** - Control de calidad
   - `cleaner.py`: Limpieza y normalización de datos
   - `qc_rules.py`: Reglas de control de calidad

3. **`src/asimilacion/`** - Preparación para asimilación
   - `littler_writer.py`: Generación de archivos Little_R
   - `obsnud_writer.py`: Conversión a formato OBS_DOMAIN101

4. **`src/modelo/`** - Ejecución del modelo
   - `wps_runner.py`: Ejecución de preprocesamiento WPS
   - `wrf_runner.py`: Ejecución del modelo WRF
   - `namelist_manager.py`: Gestión de configuraciones

5. **`src/validacion/`** - Validación de resultados
   - `metrics.py`: Cálculo de métricas de validación
   - `spatial_interp.py`: Interpolación espacial

6. **`src/reporting/`** - Reportes y visualización
   - `plot_generator.py`: Generación de gráficos
   - `report_builder.py`: Construcción de reportes
   - `experiment_registry.py`: Registro de experimentos

### Scripts Exploratorios

- **`scripts/exploratory/`**: Scripts de desarrollo y pruebas
- **`pipeline_wrf.py`**: Pipeline principal de ejecución
- **`probar_circuito.py`**: Pruebas del circuito completo

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.11+
- WRF instalado localmente
- Credenciales de API EcoWitt
- Acceso a datos GFS (NOMADS o AWS S3)

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/rmolina2014/pgich-wrf-modular.git
cd pgich-wrf-modular

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Configuración

1. Copiar `.env.example` a `.env`
2. Configurar las credenciales de EcoWitt
3. Configurar las rutas de WRF en `pipeline_wrf.py`

## 📊 Uso

### Ejecución del Pipeline Completo

```bash
python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \
    --json data/raw/ecowitt_todos_20260525_2059.json \
    --case base --namelist namelist.input
```

### Generación de OBS_DOMAIN101

```bash
python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \
    --json data/raw/ecowitt_todos_20260525_2059.json \
    --case base --prepare-only
```

### Solo Validación

```bash
python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \
    --case base --validate-only
```

## 🧪 Experimentos de Sensibilidad

El sistema permite experimentos con diferentes coeficientes de nudging:

```bash
# Coeficientes reducidos
python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \
    --json data/raw/ecowitt_todos_20260525_2059.json \
    --case coef0001 --obs-coef-wind 0.0001 --obs-coef-temp 0.0001 --obs-coef-mois 0.0001
```

## 📁 Estructura del Proyecto

```
pgich-wrf-modular/
├── src/                    # Código fuente modular
├── scripts/               # Scripts exploratorios
├── config/               # Archivos de configuración
├── wps_sanjuan/          # Configuración WPS específica
├── data/                 # Datos (excluido de git)
├── results/              # Resultados (excluido de git)
├── pipeline_wrf.py       # Pipeline principal
├── pyproject.toml        # Dependencias
├── README.md            # Este archivo
└── .gitignore           # Archivos excluidos
```

## 🔧 Configuración WPS

La carpeta `wps_sanjuan/` contiene configuraciones específicas para el dominio de San Juan:
- `namelist.wps.template`: Plantilla de configuración
- `run_wps_sanjuan.sh`: Script de ejecución

## 📈 Resultados

Los resultados se almacenan en `results/` con la estructura:
```
results/
└── YYYY-MM-DD_HHMMz/
    └── caso/
        ├── nudged/      # Simulación con nudging
        ├── control/     # Simulación de control
        ├── input/       # Archivos de entrada
        └── plots/       # Gráficos de validación
```

## 🤝 Contribución

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para detalles.

## 📞 Contacto

Rodrigo Molina - [GitHub](https://github.com/rmolina2014)

---

**Nota**: Este proyecto es parte de una tesis de maestría en informática enfocada en la asimilación de datos observacionales en modelos meteorológicos.