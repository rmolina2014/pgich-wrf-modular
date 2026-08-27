import os
import glob
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
import pandas as pd

# Biz logic imports
from src.ingesta.lector_pgich import EcowittIngestor, ESTACIONES
from src.calidad.limpiador_pgich import procesar_json_ecowitt, guardar_procesado

app = FastAPI(title="PGICH Gateway", version="0.1.0")

# Simple in-process cache for last ingest (optional, improves UX)
_LAST_INGEST = None


def _get_last_raw_json():
    raw_dir = Path("data/raw")
    pattern = str(raw_dir / "ecowitt_todos_*.json")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def _get_last_processed_csv():
    processed_dir = Path("data/processed")
    files = sorted(
        glob.glob(str(processed_dir / "datos_validados_*.csv")),
        key=os.path.getmtime,
        reverse=True,
    )
    return files[0] if files else None


def _get_last_processed_excel():
    processed_dir = Path("data/processed")
    files = sorted(
        glob.glob(str(processed_dir / "datos_validados_*.xlsx")),
        key=os.path.getmtime,
        reverse=True,
    )
    return files[0] if files else None


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/stations")
def stations():
    return [{"name": k, "mac": v} for k, v in ESTACIONES.items()]


@app.post("/ingest")
def ingest():
    app_key = os.getenv("ECOWITT_APP_KEY")
    api_key = os.getenv("ECOWITT_API_KEY")
    if not app_key or not api_key:
        raise HTTPException(status_code=400, detail="Missing API credentials in .env")
    ingestor = EcowittIngestor(app_key, api_key)
    results = ingestor.obtener_todas_estaciones(ESTACIONES)
    global _LAST_INGEST
    _LAST_INGEST = results
    return {"status": "ok", "stations": results}


@app.post("/clean")
def clean():
    last_raw = _get_last_raw_json()
    if not last_raw:
        raise HTTPException(
            status_code=404, detail="No raw data found to clean (data/raw missing)"
        )
    df = procesar_json_ecowitt(last_raw)
    csv_path, excel_path = guardar_procesado(df)
    return {"status": "ok", "csv": csv_path, "excel": excel_path, "rows": len(df)}


@app.get("/data/latest/json")
def latest_json():
    csv_path = _get_last_processed_csv()
    if not csv_path:
        raise HTTPException(status_code=404, detail="No processed CSV found")
    df = pd.read_csv(csv_path)
    return JSONResponse(df.to_json(orient="records"))


@app.get("/data/latest/csv")
def latest_csv():
    csv_path = _get_last_processed_csv()
    if not csv_path:
        raise HTTPException(status_code=404, detail="No processed CSV found")
    return FileResponse(
        csv_path, media_type="text/csv", filename=os.path.basename(csv_path)
    )


@app.get("/data/latest/excel")
def latest_excel():
    excel_path = _get_last_processed_excel()
    if not excel_path:
        raise HTTPException(status_code=404, detail="No processed Excel found")
    return FileResponse(
        excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(excel_path),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
