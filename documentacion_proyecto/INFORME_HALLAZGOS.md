# Informe de Hallazgos — PGICH WRF Modular

**Fecha:** 14 de septiembre de 2026
**Alcance:** Análisis estático del repositorio `pgich-wrf-modular-main` (sistema de asimilación de datos observacionales en WRF para San Juan, Argentina).
**Método:** Revisión de código fuente, configuración, documentación y estructura del repositorio; verificación puntual de hallazgos con búsquedas en el código.

---

## 1. Resumen ejecutivo

El proyecto está bien estructurado y modular, con separación clara de responsabilidades (ingesta → calidad → asimilación → modelo → validación → reporting) y un sistema de preflight extensible. Sin embargo, se detectaron:

| Severidad | Cantidad | Área |
|---|---|---|
| Crítica (rompe ejecución) | 1 | `wrf_runner_cli.py` |
| Alta | 2 | Documentación obsoleta, dependencias muertas |
| Media | 4 | Rutas hardcodeadas, versionado de binarios, coord. inconsistentes |
| Baja | 3 | Riesgos operativos y de mantenimiento |

---

## 2. Hallazgos críticos

### 2.1 Bug activo: `wrf_runner_cli.py:37` — `pw.PROJECT_DIR` no existe

```python
p.add_argument("--namelist", default=str(pw.PROJECT_DIR.parent / "namelist.input"),
```

- `pw.PROJECT_DIR` **no está definido** en `pipeline_wrf.py` (verificado con búsqueda global: solo aparece en `wrf_runner_cli.py` y en un instructivo que documenta su remoción).
- Impacto: `AttributeError` al invocar `wrf_runner_cli.py` sin el argumento `--namelist`, es decir, **en el flujo normal** desde la app Streamlit u otro llamador.
- Fix sugerido: usar `Path(__file__).resolve().parent / "namelist.input"` (mismo patrón usado en `pipeline_wrf.py` para rutas del proyecto), o exponer una constante `PROJECT_DIR` en `pipeline_wrf.py`.

---

## 3. Inconsistencias documentación vs código

### 3.1 `README.md` referencia recursos inexistentes
- `scripts/exploratory/` — directorio inexistente.
- `probar_circuito.py` — archivo inexistente.
- `requirements.txt` — el proyecto usa `pyproject.toml` + `uv` (`uv.lock`).
- `.env.example` — no existe (y `pipeline_wrf.py`/`ecowitt_client.py` hacen `load_dotenv()`, fallando silenciosamente sin `.env`).
- Sección "Instalación" indica `pip install -r requirements.txt` (no aplica).

### 3.2 Documentación legacy que ya no corresponde al código actual
- `MANUAL.md` y `REPRODUCIR_CICLO.md` referencian scripts antiguos ya eliminados (`lector_pgich.py`, `limpiador_pgich.py`, `generador_littler.py`, `littler_a_obsnud.py`, `valida_wrf.py`, `app.py`).
- `REPRODUCIR_CICLO.md` describe una estructura Docker que el proyecto actual no usa (el pipeline es nativo Linux/sin Docker).

---

## 4. Rutas hardcodeadas y configuración frágil

Equilibrio delicado entre dos PCs Linux (roberto / pgich). Las rutas por defecto difieren por PC y están comentadas alternativamente:

| Archivo | Línea aprox. | Detalle |
|---|---|---|
| `pipeline_wrf.py` | 71–98 | `LOCAL_WRF_DIR`, `WRF_ENV_BASH`, `MPIRUN`, `VALIDATION_PYTHON` apuntan a `/home/roberto/opencode/wrf/WRF-4.5/run`; variantes para pgich comentadas. |
| `src/modelo/wrf_runner.py` | 25 | Default `run_dir` hardcodeado a `/home/roberto/opencode/wrf/WRF-4.5/run`. |
| `src/casos/run_casos.py` | 52 | `RUN_DIR` default a `/home/pgich/wrf-operativo/ejecutables/WRF`. |
| `run_wrf_shell.sh` | — | `WRF_ENV` default a `/home/roberto/opencode/wrf/WRF-4.5/run/env.bash`. |
| `wps_sanjuan/run_wps_sanjuan.sh` | — | Detección de PC vía `whoami`. |

Riesgo: un cambio de host o de instalación WRF rompe el pipeline aunque haya `.env`. Se recomienda migrar **todas** las rutas a variables de entorno y dejar la detección por PC solo como fallback.

---

## 5. Dependencias declaradas sin uso

En `pyproject.toml` se declaran dependencias que no se importan en el código fuente actual:

`fastapi`, `uvicorn`, `pydeck`, `pydantic`, `netCDF4` (vía `xarray`/`netcf4` real es `netcdf4`), `openpyxl`.

Son residuales de versiones anteriores o planificadas. Se sugiere depurarlas para reducir superficie de instalación y riesgos de versionado.

---

## 6. Versionado del repositorio

### 6.1 `results/` versionado (intencional pero riesgoso)
- `.gitignore` documenta que `results/` **se versiona completo** (wrfouts binarios .nc de cientos de MB por corrida).
- Impacto: el repositorio crece rápidamente y los diffs de binarios ensucian el historial.
- `data/processed/` está ignorado implícitamente (no existe en el repo) — consistente, pero verificar que quede excluido de git si se crea.

### 6.2 Coordenadas inconsistentes en salidas de validación
`validacion/metricas_resumen.txt` contiene coordenadas de estaciones que no coinciden con `config/estaciones.json` (ej. `INTA_SANMARTIN` lat=-31.1234 lon=-67.5432 en validación vs lat=-31.5000 lon=-68.2500 en config). Pudo deberse a una corrida antigua con catálogo distinto; conviene re-validar esas métricas.

---

## 7. Riesgos operativos

### 7.1 SIGSEGV intermitente de `wrf.exe` con obs nudging
Mitigado con `setsid` + ejecución vía bash en proceso fresco + reintentos (default 5) en `WRFRunner`. El problema es dependiente del binario WRF compilado; en la PC roberto se revalidó contra WRF-4.5 (WRF-4.0 quedó instalado sin usarse). Mantener documentada la versión de WRF en uso.

### 7.2 Timestamps de observaciones
`obsnud_writer._desfase_por_estacion()` devuelve desfase cero para todas las estaciones (documenta un bug previo de WRF 4.5 con timestamps desfasados). El preflight 2.2.4 detecta el síntoma (cadencia 5 min) pero no la causa raíz.

### 7.3 `.env` ausente no reporta error
`load_dotenv()` no verifica presencia de `.env`; si falta, las credenciales EcoWitt y rutas WRF quedan con defaults y el fallo aparece más tarde. Considerar un chequeo temprano (tipo preflight de configuración).

---

## 8. Fortalezas verificadas

- Arquitectura modular limpia con separación por capas y patrón de "strangling" sobre los scripts legacy.
- Sistema de preflight (6 chequeos, estados OK/ADVERTENCIA/BLOQUEANTE) extensible y testeado por separado.
- Suites de tests (`tests/`) cubriendo circuito modular, preflight, casos de estudio y validación multitemporal.
- Configuración centralizada (`config/estaciones.json`, `config/casos_estudio.json`, `config/preflight_config.json`).
- Documentación del sistema (arquitectura, SEGURIDAD, instructivos) amplia en `documentacion_proyecto/`.

---

## 9. Acciones recomendadas (orden de prioridad)

1. **Corregir el bug de `wrf_runner_cli.py:37`** (`pw.PROJECT_DIR` → path basado en `__file__`).
2. **Actualizar `README.md`** (instalación con uv, scripts reales, eliminar referencias a archivos inexistentes).
3. **Migrar todas las rutas WRF a variables de entorno** y eliminar el hardcode por PC.
4. **Depurar dependencias sin uso** en `pyproject.toml`.
5. **Revisar la política de versionado de `results/`** (considerar ignorar `*.nc` salvo manifiestos/JSON).
6. **Re-validar métricas históricas** con el catálogo actual de estaciones.
7. **Añadir chequeo de configuración** temprano (presencia de `.env`, rutas WRF válidas).