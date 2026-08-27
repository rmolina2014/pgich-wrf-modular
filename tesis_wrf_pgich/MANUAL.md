# Manual de Ejecución - Proyecto PGICH

## Requisitos previos
```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Paso 1: Ingesta de Datos
```bash
.venv\Scripts\python.exe src\ingesta\lector_pgich.py
```
**Salida**: `data/raw/ecowitt_todos_YYYYMMDD_HHMM.json`

## Paso 2: Limpieza y Control de Calidad
```bash
.venv\Scripts\python.exe src\calidad\limpiador_pgich.py
```
**Salida**: `data/processed/datos_validados_YYYYMMDD_HHMM.csv`

## Paso 3: Interfaz Gráfica (opcional)
```bash
.venv\Scripts\streamlit.exe run app.py
```
**URL**: http://localhost:8501

## Ejecución completa en un paso
```bash
.venv\Scripts\python.exe src\ingesta\lector_pgich.py ; .venv\Scripts\python.exe src\calidad\limpiador_pgich.py
```

## Ver resultados
```bash
type data\processed\datos_validados_*.csv
```

## Apagar servidor Streamlit
```bash
.venv\Scripts\streamlit.exe cache streamlit shutdown
```
O presiona `Ctrl+C` en la terminal