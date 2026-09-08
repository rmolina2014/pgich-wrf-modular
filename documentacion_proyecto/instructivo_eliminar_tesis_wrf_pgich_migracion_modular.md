# Instructivo: eliminar `tesis_wrf_pgich` y migrar a la arquitectura modular

Guía reproducible de qué respaldar, qué migrar y cómo eliminar definitivamente la
carpeta legada `tesis_wrf_pgich/` del repositorio modular `pgich-wrf-modular`.

> Estado: **ya ejecutado** en el commit `6a98dcc` (62 archivos: 51 eliminados del
> legado, 11 modificados/nuevos en la arquitectura modular). Este documento queda
> como instructivo y registro del procedimiento.
>
> **Nota (2026-09-08):** ese commit `6a98dcc` se hizo en otra máquina (Windows) y
> nunca llegó a este repo remoto. En esta PC (Linux) la migración se rehizo en el
> commit `c640b52`: la única dependencia real que quedaba era
> `tesis_wrf_pgich/src/calidad/valida_wrf.py` (usado por `pipeline_wrf.py` en el
> paso de validación), migrado a `src/validacion/valida_wrf_cli.py`. El resto de lo
> que describe este documento (`obsnud_writer.py`, `littler_writer.py`,
> `cleaner.py`/`qc_rules.py`, `ecowitt_client.py`, `config/estaciones.json`) ya
> estaba migrado en este repo desde antes. También se eliminó `probar_circuito.py`
> (prototipo Streamlit standalone del flujo viejo por contenedor Docker, sin
> referencias activas, superado por `app_streamlit.py`). Los históricos de
> `tesis_wrf_pgich/historico/` (§5.1/5.2 de este documento) no se migraron a
> `data/historico/` porque nada en este repo los lee actualmente; quedan
> recuperables del backup externo o del historial de git si hicieran falta.

---

## 1. Objetivo

La carpeta `tesis_wrf_pgich/` concentraba scripts, configuraciones y datos del
prototipo original (monolítico, con Docker y subprocesos). La arquitectura modular
(`src/`, `config/`, `data/`, `pipeline_wrf.py`, `app_streamlit.py`) reemplaza esas
funcionalidades. El objetivo es:

1. Respaldar todo el legado antes de tocar nada.
2. Migrar a la estructura modular únicamente lo **necesario y no regenerable**.
3. Eliminar la carpeta sin romper el pipeline ni la app.

---

## 2. Paso 0 — Respaldo obligatorio del legado

Antes de cualquier paso, crear un ZIP con todo `tesis_wrf_pgich`:

```powershell
# Desde la raíz del proyecto (E:\Proyectos_2026\pgich-wrf-modular)
Compress-Archive -Path tesis_wrf_pgich -DestinationPath "$env:TEMP\tesis_wrf_pgich_backup.zip" -Force
Test-Path "$env:TEMP\tesis_wrf_pgich_backup.zip"   # debe dar True
```

El backup quedó en: `C:\Users\usuario\AppData\Local\Temp\opencode\tesis_wrf_pgich_backup.zip` (~0.5 MB, 52 archivos).

> Guardar este ZIP **fuera** del repo (no versionarlo). Es la única copia del
> código y datos del prototipo original.

### Contenido que se respaldó (inventario)

| Bloque | Archivos | Decisión al migrar |
| --- | --- | --- |
| `src/calidad/` | `limpiador_pgich.py`, `generador_littler.py`, `historico_a_obsnud.py`, `littler_a_obsnud.py`, `valida_wrf.py`, `check_nudge_effect.py`, `check_nudge_fixed.py`, `diff_*.py` | Migrar a módulos modulares (ver §4) |
| `src/ingesta/` | `lector_pgich.py`, `obtener_historico.py` | Reemplazado por `src/ingesta/ecowitt_client.py` |
| `config/` | `estaciones.json`, `estaciones_backup_20260625.json` | Consolidar en `config/estaciones.json` (fuente única) |
| `historico/` | `ecowitt_historico_20260702/05/0811/0812.csv/.json`, `obs_flat_20260705.json`, `obs_flat_20260812.json` | Copiar fechas únicas + convertir esquema (ver §5) |
| `data/processed/` | `OBS_DOMAIN101`, `littler_*.txt`, `datos_validados_*.csv/.xlsx`, `namelist.wps` | **No migrar** (artefactos regenerables desde el pipeline) |
| `data/raw/` | `ecowitt_todos_2026*.json` | No migrar (regenerable vía API EcoWitt) |
| Docker | `Dockerfile`, `docker-compose.yml` | No migrar (el flujo actual usa contenedor externo/servidor) |
| Docs | `MANUAL.md`, `README.md`, `SEGURIDAD.md`, `docs/experimento_nudging_20260812.md` | Conservar en el backup; documentación modular vive en `documentacion_proyecto/` |
| Otros | `app.py`, `main.py`, `pyproject.toml`, `uv.lock`, `pites_eta.php`, `.python-version`, `api_gateway.py` | No migrar (obsoletos / ajenos a la nueva estructura) |

---

## 3. Que NO se migra (y por qué)

Solo se migra lo **necesario para seguir operando y no regenerable**:

| Elemento | Motivo |
| --- | --- |
| `OBS_DOMAIN101`, `OBS_DOMAIN101_test` | Se regeneran con `src/asimilacion/obsnud_writer.py` |
| `littler_*.txt`, `datos_validados_*.csv/.xlsx` | Se regeneran con `src/asimilacion/littler_writer.py` |
| `ecowitt_todos_*.json` | Se regeneran con `EcowittIngestor.obtener_datos_historicos()` |
| Dockerfile / docker-compose.yml | El WRF corre en el contenedor del servidor, no en el repo |
| `pites_eta.php`, `api_gateway.py`, `main.py`, `app.py` | Herramientas del prototipo, reemplazadas por la app modular |

---

## 4. Migración de código (qué va a dónde)

| Legado (`tesis_wrf_pgich/src/`) | Modular (`src/`) | Nota |
| --- | --- | --- |
| `calidad/valida_wrf.py` | `src/validacion/valida_wrf_cli.py` | Copiado/adaptado; ruta de estaciones resuelta a `config/estaciones.json`. Git lo detecta como rename (97%). |
| `calidad/historico_a_obsnud.py` | `src/asimilacion/obsnud_writer.py` (`ObsNudWriter`) | OBS_DOMAIN101 (FORMAT 105). Se invoca por import, no por subprocess. |
| `calidad/generador_littler.py` | `src/asimilacion/littler_writer.py` (`LittleRWriter`) | Formato Little_R. |
| `calidad/limpiador_pgich.py` | `src/calidad/cleaner.py` + `qc_rules.py` | `ObservacionesCleaner`. |
| `calidad/littler_a_obsnud.py` | `src/asimilacion/obsnud_writer.py` | Conversión absorbed by `ObsNudWriter`. |
| `calidad/check_nudge_effect.py`, `check_nudge_fixed.py`, `diff_3d.py`, `diff_all.py`, `diff_check.py` | `src/validacion/metrics.py` + `spatial_interp.py` | Métricas ΔT2/ΔRH y comparación nudged vs control. |
| `ingesta/lector_pgich.py` | `src/ingesta/ecowitt_client.py` (`EcowittIngestor`) | Consulta MAC + histórico v3 (grupos outdoor/wind/pressure/rainfall/solar). |
| `ingesta/obtener_historico.py` | `src/ingesta/ecowitt_client.py` | Histórico día completo, ciclo 5 min. |
| `config/estaciones.json` | `config/estaciones.json` | Catálogo unificado: lat/lon/elev/`mac`. Es la única fuente (CLI del `EcowittIngestor` lo lee). |

### Referencias que se engancharon (subprocess → módulo)

- `pipeline_wrf.py:370` → `valida_script_local = str(PROJECT_DIR / "src/validacion/valida_wrf_cli.py")`
- `probar_circuito.py` → `Generar_obsdomain` ahora llama a `ObsNudWriter.generar_desde_dataframe()`; `valida_script` apunta a `src/validacion/valida_wrf_cli.py`
- `PROJECT_DIR` en `pipeline_wrf.py` dejó de apuntar a `tesis_wrf_pgich` (ahora es la raíz del repo)
- `wrf_runner_cli.py` resuelve `pipeline_wrf.py` por rutas candidatas portables (Windows/Linux)

---

## 5. Migración de datos

### 5.1 Históricos EcoWitt (`data/historico/`)

Estado modular (pre-existente): `20260812`, `20260831`, `20260926`.
Fechas únicas del legado a incorporar: **`20260702`, `20260705`, `20260811`**.

```powershell
$uniq = @("20260702","20260705","20260811")
foreach ($d in $uniq) {
  foreach ($ext in @(".csv",".json")) {
    $src = "tesis_wrf_pgich\historico\ecowitt_historico_$d$ext"
    $dst = "data\historico\ecowitt_historico_$d$ext"
    if (Test-Path $src) { Copy-Item $src $dst -Force }
  }
}
```

**OJO (esquema):** el CSV legado usa columnas `temp_c`, `humedad_pct`,
`viento_kmh`, `direcc_grados`, `presion_*_hpa`, `lluvia_diaria_mm`, `hora_unix`.
El esquema modular (obs_flat) usa `temp`, `humedad`, `viento`, `direcc`,
`presion_relativa`, `time_unix`, `hora`. Por eso se debe **convertir** el CSV al
esquema modular y reescribir el `.json` (lista plana de obs):

```python
import json
import pandas as pd
COL = {"hora_unix":"time_unix","temp_c":"temp","humedad_pct":"humedad",
       "viento_kmh":"viento","viento_rafaga_kmh":"viento_rafaga",
       "direcc_grados":"direcc","presion_relativa_hpa":"presion_relativa",
       "presion_absoluta_hpa":"presion_absoluta","lluvia_diaria_mm":"rain_daily",
       "solar_wm2":"solar"}
for f in ["20260702","20260705","20260811"]:
    p = f"data/historico/ecowitt_historico_{f}.csv"
    df = pd.read_csv(p).rename(columns=COL)
    df["hora"] = (pd.to_datetime(df["time_unix"], unit="s", utc=True)
                  .dt.tz_localize(None).dt.strftime("%H:%M"))
    df["time_unix"] = df["time_unix"].astype("Int64").astype(str)
    df.to_csv(p, index=False)
    with open(f"data/historico/ecowitt_historico_{f}.json", "w", encoding="utf-8") as w:
        json.dump(df.to_dict(orient="records"), w, ensure_ascii=False)
```

Resultado verificado: `20260702` → 2303 obs · `20260705` → 1152 obs · `20260811` → 576 obs (cargables por `_cargar_historico_df`).

### 5.2 Flats (`data/historical_flat/`)

Copiar los `obs_flat_*.json` únicos (no sobrescribir los existentes):

```powershell
foreach ($f in @("obs_flat_20260705.json","obs_flat_20260812.json")) {
  if (Test-Path "tesis_wrf_pgich\historico\$f" -and !(Test-Path "data\historical_flat\$f")) {
    Copy-Item "tesis_wrf_pgich\historico\$f" "data\historical_flat\$f"
  }
}
```

Resultado: `obs_flat_20260705.json`, `obs_flat_20260812.json`, `obs_flat_20260831.json`.

> `data/` no se versiona (`.gitignore`: `data/raw/`, `data/processed/`; el resto
> tampoco se commitea por ser datos/generados). Conservar respaldo físico.

---

## 6. Procedimiento de eliminación

### 6.1 Verificar que ninguna referencia queda activa

```powershell
# El único resto permitido: docstring de valida_wrf_cli.py y ruta candidata
# inofensiva en wrf_runner_cli.py (no existe → se descarta).
Select-String -Path *.py, src\**\*.py -Pattern "tesis_wrf_pgich"
```

Referencias aceptables tras migrar:
- `src/validacion/valida_wrf_cli.py` (solo docstring de migración)
- `wrf_runner_cli.py` (ruta candidata `Path(...)/tesis_wrf_pgich` que no existe → se saltea)

### 6.2 Borrar con git (preserva el historial de cambios)

```powershell
# tesis_wrf_pgich/app.py tenía modificaciones locales: usar --force
git rm -r --force tesis_wrf_pgich
```

Luego limpiar el `__pycache__` residual (archivo compilado no trackeado):

```powershell
Remove-Item tesis_wrf_pgich\__pycache__ -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item tesis_wrf_pgich -Force -ErrorAction SilentlyContinue   # si quedó shell vacío
Test-Path tesis_wrf_pgich   # debe dar False
```

---

## 7. Verificación post-eliminación

```powershell
# 1) Sintaxis de los archivos tocados
uv run python -m py_compile app_streamlit.py pipeline_wrf.py probar_circuito.py wrf_runner_cli.py src\validacion\valida_wrf_cli.py

# 2) La app arranca y las vistas clave renderizan (dominio geográfico, ingesta)
uv run python -c "from streamlit.testing.v1 import AppTest; at = AppTest.from_file('app_streamlit.py', default_timeout=30); at.run(); print('excepciones:', len(at.exception))"

# 3) El servidor de la app sigue vivo (HTTP 200)
Invoke-WebRequest -Uri http://127.0.0.1:8501 -UseBasicParsing -TimeoutSec 10

# 4) Los históricos migrados cargan
uv run python -c "import app_streamlit as app; print(app._listar_fechas_historico())"
```

Si el servidor 8501 murió, relanzarlo de forma persistente vía **Task Scheduler**:

```powershell
schtasks /Create /TN "PGICH_Streamlit" /TR "C:\Users\usuario\AppData\Local\Temp\opencode\run_pgich_streamlit.bat" /SC ONCE /ST 00:00 /F
schtasks /Run /TN "PGICH_Streamlit"
```

(No usar `Start-Process cmd.exe`: los hijos mueren al retornar el comando del shell.)

---

## 8. Commit

```powershell
git add app_streamlit.py pipeline_wrf.py probar_circuito.py wrf_runner_cli.py `
        config/estaciones.json config/namelist.input.template config/namelist.wps.template `
        namelist.input namelist.wps src/ingesta/__init__.py src/ingesta/ecowitt_client.py `
        src/validacion/valida_wrf_cli.py   # NO agregar data/ ni documentacion_proyecto/
git commit -m "Migrar a arquitectura modular; ..."
```

Resultado en el repo: commit `6a98dcc` — 62 archivos, `valida_wrf.py` → `src/validacion/valida_wrf_cli.py` detectado como rename (97%).

> Importante: **no** hacer `git add data/` ni `git add documentacion_proyecto/`
> (datos regenerables + documentos del usuario, no parte de la migración).

---

## 9. Reintento / recuperación

Si algo falla, toda la información original está en el ZIP de respaldo:

```powershell
Expand-Archive -Path "$env:TEMP\tesis_wrf_pgich_backup.zip" -DestinationPath tesis_wrf_pgich_restaurado
```

- Restaurar la carpeta en su lugar y rehacer la migración corrigiendo solo el paso en cuestión.
- Si el pipeline quedó a mitad: los productos `data/processed/*` regenerables se recalculan ejecutando `pipeline_wrf.py` (pasos 1-3 de la sección de ejecución de la app).
- Los históricos originales (esquema legacy) se conservan intactos en el ZIP; la conversión a obs_flat es idempotente sobre las copias de `data/historico/`.