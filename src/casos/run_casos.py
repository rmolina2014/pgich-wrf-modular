#!/usr/bin/env python3
"""Fase 4 - Ejecución de casos de estudio WRF (ciclo 00Z->12Z, con/sin obs nudging).

Para cada caso de config/casos_estudio.json:
  1. Descarga histórico EcoWitt del día y mide la cobertura de observaciones.
  2. Si la cobertura es insuficiente -> "NO EJECUTADO - SIN DATOS (causa)".
  3. Descarga GFS 00Z, corre WPS (geogrid+ungrib+metgrid) y copia met_em al run dir.
  4. Corre el pipeline WRF (Little_R -> OBS_DOMAIN101 -> real.exe -> wrf.exe
     nudged/control -> validacion multi-temporal 00/06/12Z).
  5. Redacta informe .md por caso y un informe consolidado al final.

Uso:
    python -m src.casos.run_casos --dry-run        # solo disponibilidad
    python -m src.casos.run_casos --solo 2         # ejecutar solo el caso 2
    python -m src.casos.run_casos                  # ejecutar todos los casos
    python -m src.casos.run_casos --force          # re-ejecutar aunque existan resultados
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.calidad.cleaner import ObservacionesCleaner
from src.ingesta.ecowitt_client import EcowittIngestor
from src.ingesta.gfs_downloader import GFSDownloader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_casos")

CONFIG_JSON = ROOT / "config" / "casos_estudio.json"
RAW = ROOT / "data" / "raw"
INFORMES = ROOT / "informes_ejecucion"
ESTADO_DIR = ROOT / "results" / "casos_estudio"
ESTADO_JSON = ESTADO_DIR / "estado_casos.json"
WPS_DIR = ROOT / "wps_sanjuan"
WPS_SH = WPS_DIR / "run_wps_sanjuan.sh"
RUN_DIR = Path(os.environ.get("LOCAL_WRF_DIR", "/home/pgich/wrf-operativo/ejecutables/WRF"))
PYTHON = ROOT / ".venv" / "bin" / "python"
PIPELINE = ROOT / "pipeline_wrf.py"
GFS_URLS = {
    "aws": "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{fecha}/{ciclo}/atmos/{file}",
    "nomads": "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.{fecha}/{ciclo}/atmos/{file}",
}
PC_PGICH_ENV = {
    "WRF_BASE": "/home/pgich/Build_WRF",
    "WPS_DIR": "/home/pgich/Build_WRF/WPS",
    "WRF_EJECUTABLES": "/home/pgich/wrf-operativo/ejecutables",
    "GEOG_DATA_PATH": "/home/pgich/wrf-operativo/datos/WPS_GEOG",
}


# --------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------
def _leer_casos(cfg_path: Path = CONFIG_JSON) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("configuracion_comun", {}), cfg.get("casos", [])


def _estado() -> Dict[str, Any]:
    if ESTADO_JSON.exists():
        with open(ESTADO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _guardar_estado(estado: Dict[str, Any]):
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    with open(ESTADO_JSON, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# Observaciones (EcoWitt historico -> obs_flat)
# --------------------------------------------------------------------------
def csv_historico(fecha: str) -> Path:
    fc = fecha.replace("-", "")
    return RAW / f"ecowitt_historico_{fc}.csv"


def descargar_obs_historico(fecha: str) -> Path:
    """Descarga el historico diario si no existe y devuelve la ruta del CSV."""
    csv = csv_historico(fecha)
    if csv.exists() and csv.stat().st_size > 100:
        logger.info(f"Historico ya descargado: {csv.name}")
        return csv
    logger.info(f"Descargando historico EcoWitt de {fecha}...")
    EcowittIngestor().descargar_historico(fecha, output_dir=str(RAW))
    if not csv.exists():
        raise RuntimeError(f"No se genero el CSV historico para {fecha}")
    return csv


def cobertura_obs(csv_path: Path, fecha: str, ciclo: str = "00") -> Dict[str, Any]:
    """Mide la cobertura de observaciones validas (dia completo y ventana 00-12Z)."""
    df = pd.read_csv(csv_path)
    if df.empty or "temp_c" not in df.columns:
        return {"dia": 0, "ventana": 0, "estaciones": 0, "por_estacion": {}}

    ts_ini = int(datetime.strptime(f"{fecha} 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp())
    ts_fin = ts_ini + 12 * 3600
    df["ts"] = pd.to_numeric(df["hora_unix"], errors="coerce")
    df["temp_ok"] = df["temp_c"].apply(lambda v: _num(v) is not None and pd.notna(v))

    dia = int(df["temp_ok"].sum())
    ventana = int((df["temp_ok"] & df["ts"].between(ts_ini, ts_fin)).sum())
    por_estacion = (
        df[df["temp_ok"] & df["ts"].between(ts_ini, ts_fin)]
        .groupby("estacion")["temp_ok"].sum().astype(int).to_dict()
    )
    return {"dia": dia, "ventana": ventana, "estaciones": len(por_estacion), "por_estacion": por_estacion}


def _num(v: Any) -> Optional[float]:
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def generar_obs_flat(csv_path: Path, fecha: str, salida: Optional[Path] = None) -> Path:
    """Convierte el CSV historico (limpio/QC) al JSON obs_flat usado por el pipeline."""
    if salida is None:
        salida = RAW / f"obs_flat_{fecha.replace('-', '')}.json"
    if salida.exists() and salida.stat().st_size > 100:
        logger.info(f"obs_flat ya existe: {salida.name}")
        return salida

    cleaner = ObservacionesCleaner(str(RAW))
    df = cleaner.procesar_csv_historico(str(csv_path))
    df["time_unix"] = df["timestamp"].astype("int64") // 10**9

    filas = []
    hora_ok = df["hora"].astype(str).str.split(":").apply(lambda x: len(x) >= 2)
    for _, r in df[hora_ok].iterrows():
        try:
            horas = str(r["hora"]).split(":")
            hora = f"{int(horas[0]):02d}:{int(horas[1]):02d}:00"
        except (ValueError, TypeError):
            continue
        filas.append({
            "estacion": str(r["estacion"]),
            "time_unix": int(r["time_unix"]),
            "fecha": str(r["fecha"]),
            "hora": hora,
            "temp": _num(r.get("temp")),
            "humedad": _num(r.get("humedad")),
            "viento": _num(r.get("viento")),
            "viento_rafaga": _num(r.get("viento_rafaga")),
            "direcc": _num(r.get("direcc")),
            "presion_relativa": _num(r.get("presion_relativa")),
            "presion_absoluta": _num(r.get("presion_absoluta")),
            "rain_daily": _num(r.get("rain_daily")),
            "solar": _num(r.get("solar")),
        })
    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, indent=1)
    logger.info(f"obs_flat generado: {salida.name} ({len(filas)} registros)")
    return salida


# --------------------------------------------------------------------------
# GFS
# --------------------------------------------------------------------------
def gfs_disponible(fecha: str, ciclo: str = "00", fhour: int = 0) -> Optional[str]:
    """Verifica disponibilidad del artico pgrb2 0.25 en AWS/NOMADS. Devuelve la fuente o None."""
    fstr = f"{fhour:03d}"
    file = f"gfs.t{ciclo}z.pgrb2.0p25.f{fstr}"
    fecha_nodash = fecha.replace("-", "")
    for fuente, tpl in GFS_URLS.items():
        url = tpl.format(fecha=fecha_nodash, ciclo=ciclo, file=file)
        try:
            r = requests.head(url, timeout=30, allow_redirects=True)
            if r.status_code == 200:
                return fuente
        except Exception as e:
            logger.debug(f"HEAD {fuente} fallo: {e}")
    return None


def _tamano_esperado_gfs(fecha: str, ciclo: str, fhour: int) -> Optional[int]:
    """HEAD a AWS para conocer el Content-Length del archivo GFS."""
    fstr = f"{fhour:03d}"
    file = f"gfs.t{ciclo}z.pgrb2.0p25.f{fstr}"
    url = GFS_URLS["aws"].format(fecha=fecha.replace("-", ""), ciclo=ciclo, file=file)
    try:
        r = requests.head(url, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return int(r.headers.get("Content-Length") or 0)
    except Exception:
        pass
    return None


def descargar_gfs(fecha: str, ciclo: str = "00") -> int:
    """Descarga el ciclo GFS 00Z (0-12h) hacia wps_sanjuan/gfs_data/<fecha>_<ciclo>.

    Antes de descargar verifica tamano contra AWS y elimina archivos truncados
    (descargas interrumpidas) que el descargador consideraria completos."""
    out = WPS_DIR / "gfs_data" / f"{fecha}_{ciclo}"
    for fhour in range(0, 13, 3):
        fname = f"gfs.t{ciclo}z.pgrb2.0p25.f{fhour:03d}"
        p = out / fname
        if not p.exists():
            continue
        esperado = _tamano_esperado_gfs(fecha, ciclo, fhour)
        if esperado and abs(p.stat().st_size - esperado) > 0.02 * esperado:
            logger.warning(f"GFS corrupto/truncado ({p.stat().st_size} vs {esperado} B): re-descargando {fname}")
            p.unlink()
    desc = GFSDownloader(str(out)).descargar_ciclo(fecha, ciclo_hora=ciclo)
    return len(list(out.glob(f"gfs.t{ciclo}z.pgrb2.0p25.f*")))


# --------------------------------------------------------------------------
# WPS + run dir
# --------------------------------------------------------------------------
def ejecutar_wps(fecha: str, ciclo: str = "00", timeout: int = 3600) -> Tuple[bool, str]:
    """Corre WPS (geogrid+ungrib+metgrid) para el caso. Devuelve (ok, log)."""
    log = ESTADO_DIR / f"wps_{fecha.replace('-', '')}_{ciclo}.log"
    env = dict(os.environ)
    env.update(PC_PGICH_ENV)
    try:
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run(
                ["bash", str(WPS_SH), fecha, ciclo],
                env=env, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT, timeout=timeout,
            )
        return r.returncode == 0, str(log)
    except subprocess.TimeoutExpired:
        logger.error(f"WPS excedio el timeout ({timeout}s)")
        return False, str(log)


def propagar_metem(fecha: str) -> int:
    """Copia los met_em de WPS al directorio de corrida de real.exe."""
    n = 0
    for src in sorted(WPS_DIR.glob(f"met_em.d01.{fecha}_*")):
        shutil.copy2(src, RUN_DIR / src.name)
        n += 1
    return n


# --------------------------------------------------------------------------
# Pipeline WRF
# --------------------------------------------------------------------------
def ejecutar_pipeline(caso: Dict[str, Any], comun: Dict[str, Any], fecha: str,
                      obs_flat: Path, ciclo: str = "00", timeout: int = 8 * 3600) -> Tuple[int, str]:
    """Corre pipeline_wrf.py para el caso (nudged + control + validacion 00/06/12Z)."""
    label = f"caso{int(caso['num'])}_NvC"
    run_case = Path(caso["resultados_dir"]).name  # directorio de resultados del caso
    cmd = [
        str(PYTHON), str(PIPELINE),
        "--date", fecha, "--hour", f"{ciclo}:00",
        "--json", str(obs_flat),
        "--case", run_case,
        "--namelist", str(ROOT / comun.get("namelist_base", "namelist.input")),
        "--run-real",
        "--obs-coef-wind", str(comun.get("obs_coef_wind")),
        "--obs-coef-temp", str(comun.get("obs_coef_temp")),
        "--obs-coef-mois", str(comun.get("obs_coef_mois")),
        "--valid-times", ",".join(comun.get("valid_times", ["00:00:00"])),
        "--label", label,
        "--wrf-timeout", "7200",
    ]
    log = ESTADO_DIR / f"pipeline_{caso['id']}.log"
    logger.info(f"Pipeline: {' '.join(cmd)}")
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    return r.returncode, str(log)


# --------------------------------------------------------------------------
# Informes
# --------------------------------------------------------------------------
def _leer_tabla_evolutiva(caso: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    t = Path(caso["resultados_dir"])
    if not t.is_absolute():
        t = ROOT / t
    t = t / "tabla_evolutiva.json"
    if not t.exists():
        return None
    with open(t, "r", encoding="utf-8") as f:
        return json.load(f)


def _md_tabla_variable(rows: List[Dict[str, Any]], variable: str) -> str:
    """Tabla markdown compacta de RMSE/bias Nudged vs Control para una variable."""
    subset = [r for r in rows if r["var"] == variable]
    if not subset:
        return "_Sin métricas para esta variable._\n"
    lineas = ["| Tiempo | N | RMSE N | RMSE C | dRMSE | Bias N | Bias C |",
              "|--------|----|--------|--------|-------|--------|--------|"]
    for r in sorted(subset, key=lambda x: int(x["tiempo"].replace("Z", ""))):
        n, nr, cr = r["n"], r["nudged_rmse"], r["control_rmse"]
        nb, cb = r["nudged_bias"], r["control_bias"]
        d = (cr - nr) if (nr == nr and cr == cr) else float("nan")
        d_txt = f"{d:+.2f}" if d == d else "n/d"
        lineas.append(f"| {r['tiempo']} | {n} | {nr:.2f} | {cr:.2f} | {d_txt} | {nb:+.2f} | {cb:+.2f} |")
    return "\n".join(lineas) + "\n"


def redactar_informe_caso(caso: Dict[str, Any], estado_entry: Dict[str, Any],
                          cobertura: Optional[Dict[str, Any]] = None) -> Path:
    """Escribe el informe .md de un caso."""
    ruta = ROOT / caso["informe"]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    estado = estado_entry.get("estado")
    detalle = estado_entry.get("detalle", "")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    L = []
    L.append(f"# {caso['titulo']}")
    L.append("")
    L.append(f"**Fecha del evento:** {caso['fecha']} | **Ciclo:** 00Z -> 12Z | **Informe generado:** {ts}")
    L.append("")
    L.append("## Descripción del evento")
    L.append("")
    L.append(caso["descripcion"])
    L.append("")
    L.append(f"**Fuente:** {caso['fuente']}")
    L.append("")
    L.append("## Estado de la ejecución")
    L.append("")
    if estado == "EJECUTADO":
        L.append(f"**Estado:** ✅ EJECUTADO")
    elif estado.startswith("NO EJECUTADO"):
        L.append(f"**Estado:** ⛔ NO EJECUTADO — {detalle}")
    else:
        L.append(f"**Estado:** ❌ {estado} — {detalle}")
    L.append("")

    L.append("## Configuración aplicada")
    L.append("")
    L.append("| Parámetro | Valor |")
    L.append("|-----------|-------|")
    L.append("| Dominio | 1 dominio, 15 km, 80×60, mercator (-31.5°, -68.5°) |")
    L.append("| Ciclo | 00Z–12Z (12 h) |")
    L.append("| Forzante | GFS 0.25° (AWS) |")
    L.append("| Obs nudging | `obs_nudge_opt=1`, coef viento/temp/humedad=0.0001, `obs_twindo=1.0` |")
    L.append("| Nudged vs Control | misma inicialización; solo cambia `obs_nudge_opt` (1 vs 0) |")
    L.append("| Validación | multi-temporal 00Z, 06Z, 12Z vs observaciones de estaciones |")
    L.append("")
    L.append("## Limitación conocida del dominio (relevant para el análisis)")
    L.append("")
    L.append("El dominio de 15 km no resuelve la topografía profunda de la precordillera "
             "(errores de altura del modelo de entre +201 m y +918 m en las estaciones, "
             "con máximos en CARACOLES +918 m, PUNTA_NEGRA +420 m y CUESTA_Viento +378 m). "
             "Por eso el análisis del caso 1 (Zonda) se restringe a la **firma térmica** "
             "(salto de T2 y caída de RH), y el viento se interpreta solo de forma cualitativa. "
             "Ver también `documentacion_proyecto/informe_avances_fases_proyecto.md`.")
    L.append("")

    if cobertura:
        L.append("## Observaciones disponibles")
        L.append("")
        L.append(f"- Registros válidos: **{cobertura['dia']}** en el día, **{cobertura['ventana']}** en la ventana 00Z–12Z.")
        L.append(f"- Estaciones con datos en ventana: **{cobertura['estaciones']}**")
        pe = cobertura.get("por_estacion", {})
        if pe:
            L.append("")
            L.append("| Estación | Registros (00Z–12Z) |")
            L.append("|----------|--------------------|")
            for k, v in sorted(pe.items(), key=lambda kv: (-kv[1], kv[0])):
                L.append(f"| {k} | {v} |")
        L.append("")

    if estado == "EJECUTADO":
        tabla = _leer_tabla_evolutiva(caso)
        if tabla:
            L.append("## Resultados: Nudged vs Control")
            L.append("")
            L.append("RMSE/Bias de la corrida nudgada (N) y de control (C) por tiempo de validación. "
                     "dRMSE = RMSE(C) - RMSE(N) (negativo ⇒ el nudging no degrada). 00Z: N≡C por construcción.")
            L.append("")
            for var in tabla.get("variables", []):
                L.append(f"### {var}")
                L.append("")
                rows = []
                for t in tabla.get("por_tiempo", []):
                    for r in t.get("rows", []):
                        rr = dict(r)
                        rr["tiempo"] = t["tiempo"]
                        rows.append(rr)
                L.append(_md_tabla_variable(rows, var))
                L.append("")
            L.append("### Conclusiones del caso")
            L.append("")
            L.append("Para la interpretación completa (series, gráficos y comparación con observaciones) ver "
                     f"`{caso['resultados_dir']}/` (informe de evolución, tablas por horario y wrfouts).")
            L.append("")
        else:
            L.append("## Resultados parciales")
            L.append("")
            L.append("La corrida se ejecutó pero no se encontraron métricas en "
                     f"`{caso['resultados_dir']}/tabla_evolutiva.json` (revisar logs).")
            L.append("")

    L.append("---")
    L.append("*Informe generado automáticamente por `src/casos/run_casos.py`.*")
    ruta.write_text("\n".join(L), encoding="utf-8")
    logger.info(f"Informe del caso escrito: {ruta}")
    return ruta


def _resumen_metricas(tabla: Optional[Dict[str, Any]], variable: str, tiempo: str) -> Dict[str, Any]:
    if not tabla:
        return {}
    for t in tabla.get("por_tiempo", []):
        if t["tiempo"] == tiempo:
            for r in t.get("rows", []):
                if r["var"] == variable:
                    return r
    return {}


def redactar_informe_consolidado(casos: List[Dict[str, Any]], estado: Dict[str, Any]) -> Path:
    ts = datetime.now().strftime("%Y%m%d")
    ruta = INFORMES / f"informe_casos_estudio_{ts}.md"
    ruta.parent.mkdir(parents=True, exist_ok=True)

    L = []
    L.append(f"# Informe consolidado de casos de estudio — Fase 4")
    L.append("")
    L.append(f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} por `src/casos/run_casos.py`.")
    L.append("")
    L.append("## Resumen de ejecución")
    L.append("")
    L.append("| Caso | Fecha | Evento | Estado | Informe |")
    L.append("|------|-------|--------|--------|---------|")
    for c in casos:
        e = estado.get(c["id"], {})
        st = e.get("estado", "PENDIENTE")
        det = e.get("detalle", "")
        estado_txt = st
        if st == "EJECUTADO":
            estado_txt = "EJECUTADO"
        elif "SIN DATOS" in st:
            estado_txt = f"NO EJECUTADO — SIN DATOS ({det})"
        L.append(f"| {c['titulo']} | {c['fecha']} | {c['evento']} | {estado_txt} | `{c['informe']}` |")
    L.append("")
    L.append("## Métricas por caso (RMSE del nudging vs control)")
    L.append("")
    L.append("Se reporta el RMSE de T2 (K) y RH (%) en la ventana de mayor divergencia (06Z y 12Z).")
    L.append("")
    for c in casos:
        e = estado.get(c["id"], {})
        L.append(f"### {c['titulo']} ({c['fecha']})")
        L.append("")
        if e.get("estado") != "EJECUTADO":
            L.append(f"_No ejecutado: {e.get('detalle', '')}_")
            L.append("")
            continue
        tabla = _leer_tabla_evolutiva(c)
        if not tabla:
            L.append("_Sin tabla de métricas._")
            L.append("")
            continue
        L.append("| Tiempo | RMSE T2 N | RMSE T2 C | RMSE RH N | RMSE RH C |")
        L.append("|--------|-----------|-----------|-----------|-----------|")
        def _fmt(r: Dict[str, Any], k: str) -> str:
            v = r.get(k)
            return f"{v:.2f}" if v is not None and isinstance(v, (int, float)) else "n/d"
        for t in tabla.get("por_tiempo", []):
            t2 = _resumen_metricas(tabla, "T2 (K)", t["tiempo"])
            rh = _resumen_metricas(tabla, "RH (%)", t["tiempo"])
            L.append(f"| {t['tiempo']} | {_fmt(t2, 'nudged_rmse')} | {_fmt(t2, 'control_rmse')}"
                     f" | {_fmt(rh, 'nudged_rmse')} | {_fmt(rh, 'control_rmse')} |")
        L.append("")
    L.append("## Limitación del dominio y criterio de análisis")
    L.append("")
    L.append("15 km, errores de terreno +201..+918 m. El Zonda (caso 1) se analiza por firma térmica; "
             "el viento es cualitativo. Detalles en los informes por caso.")
    L.append("")
    L.append("---")
    L.append("*Informe consolidado generado automáticamente.*")
    ruta.write_text("\n".join(L), encoding="utf-8")
    logger.info(f"Informe consolidado escrito: {ruta}")
    return ruta


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
def ejecutar_caso(caso: Dict[str, Any], comun: Dict[str, Any], estado: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta un caso completo (obs -> GFS -> WPS -> pipeline). Actualiza estado."""
    cid = caso["id"]
    fecha = caso["fecha"]
    ciclo = comun.get("hora_ciclo", "00")
    obs_min = int(comun.get("obs_min_registros", 60))
    obs_min_est = int(comun.get("obs_min_estaciones", 3))

    resultado: Dict[str, Any] = {"estado": "PENDIENTE", "detalle": "", "ts": datetime.now().isoformat(timespec="seconds")}

    # 1) Observaciones
    try:
        csv = descargar_obs_historico(fecha)
        cov = cobertura_obs(csv, fecha, ciclo)
    except Exception as e:
        logger.exception(f"{cid}: fallo al obtener observaciones")
        resultado = {"estado": "NO EJECUTADO - SIN DATOS (obs)", "detalle": f"fallo de descarga: {e}",
                     "ts": datetime.now().isoformat(timespec="seconds")}
        return resultado

    if cov["ventana"] < obs_min or cov["estaciones"] < obs_min_est:
        detalle = f"cobertura insuficiente ({cov['ventana']} registros, {cov['estaciones']} estaciones en ventana)"
        resultado = {"estado": "NO EJECUTADO - SIN DATOS (obs)", "detalle": detalle,
                     "ts": datetime.now().isoformat(timespec="seconds")}
        estado[cid] = resultado
        return resultado

    try:
        obs_flat = generar_obs_flat(csv, fecha)
    except Exception as e:
        logger.exception(f"{cid}: fallo al generar obs_flat")
        resultado = {"estado": "FALLIDO", "detalle": f"generar obs_flat: {e}",
                     "ts": datetime.now().isoformat(timespec="seconds")}
        estado[cid] = resultado
        return resultado

    # 2) GFS
    fuente = gfs_disponible(fecha, ciclo)
    if fuente is None:
        resultado = {"estado": "NO EJECUTADO - SIN DATOS (gfs)", "detalle": "GFS 00Z no disponible en AWS/NOMADS",
                     "ts": datetime.now().isoformat(timespec="seconds")}
        estado[cid] = resultado
        return resultado
    n_gfs = descargar_gfs(fecha, ciclo)
    if n_gfs < 5:
        resultado = {"estado": "NO EJECUTADO - SIN DATOS (gfs)", "detalle": f"se bajaron {n_gfs} ficheros GFS",
                     "ts": datetime.now().isoformat(timespec="seconds")}
        estado[cid] = resultado
        return resultado

    # 3) WPS
    ok_wps, log_wps = ejecutar_wps(fecha, ciclo)
    if not ok_wps:
        resultado = {"estado": "FALLIDO", "detalle": f"WPS fallo (ver {log_wps})",
                     "ts": datetime.now().isoformat(timespec="seconds")}
        estado[cid] = resultado
        return resultado
    n_metem = propagar_metem(fecha)
    if n_metem < 5:
        resultado = {"estado": "FALLIDO", "detalle": f"WPS no genero met_em suficientes ({n_metem})",
                     "ts": datetime.now().isoformat(timespec="seconds")}
        estado[cid] = resultado
        return resultado

    # 4) Pipeline WRF (nudged + control + validacion)
    rc, log_pipe = ejecutar_pipeline(caso, comun, fecha, obs_flat, ciclo)
    if rc == 0:
        resultado = {"estado": "EJECUTADO", "detalle": f"fuente GFS {fuente}",
                     "ts": datetime.now().isoformat(timespec="seconds")}
    else:
        resultado = {"estado": "FALLIDO", "detalle": f"pipeline rc={rc} (ver {log_pipe})",
                     "ts": datetime.now().isoformat(timespec="seconds")}
    estado[cid] = resultado
    return resultado


def main():
    parser = argparse.ArgumentParser(description="Casos de estudio Fase 4 (WRF con/sin obs nudging).")
    parser.add_argument("--dry-run", action="store_true", help="Solo verificar disponibilidad (obs + GFS).")
    parser.add_argument("--solo", type=int, default=None, help="Ejecutar solo el caso con ese numero.")
    parser.add_argument("--force", action="store_true", help="Re-ejecutar aunque existan resultados.")
    parser.add_argument("--skip-wrf", action="store_true", help="No correr WRF (solo obs/GFS/informes).")
    args = parser.parse_args()

    comun, casos = _leer_casos()
    todos_casos = casos
    if args.solo:
        casos = [c for c in casos if c["num"] == args.solo]
        if not casos:
            logger.error(f"No existe el caso {args.solo}")
            return 1

    estado = _estado()

    for caso in casos:
        cid = caso["id"]
        prev = estado.get(cid, {})
        if not args.force and not args.dry_run and prev.get("estado") == "EJECUTADO" and not args.skip_wrf:
            logger.info(f"{cid}: ya fue EJECUTADO, salteando (--force para re-ejecutar)")
            continue

        if args.dry_run:
            # Solo disponibilidad: obs + GFS, sin WRF
            try:
                csv = descargar_obs_historico(caso["fecha"])
                cov = cobertura_obs(csv, caso["fecha"], comun.get("hora_ciclo", "00"))
            except Exception as e:
                cov = {"dia": 0, "ventana": 0, "estaciones": 0, "por_estacion": {}}
                logger.error(f"{cid}: obs fallo: {e}")
            fuente = gfs_disponible(caso["fecha"], comun.get("hora_ciclo", "00"))
            logger.info(f"[DRY] {cid} {caso['fecha']}: obs dia={cov['dia']} ventana={cov['ventana']} "
                        f"estaciones={cov['estaciones']} | GFS={fuente or 'NO DISPONIBLE'}")
            estado[cid] = {"estado": "DRY_RUN",
                           "detalle": f"obs ventana {cov['ventana']} / {cov['estaciones']} est; gfs {fuente or 'no'}",
                           "ts": datetime.now().isoformat(timespec="seconds")}
            continue

        if args.skip_wrf:
            # Solo preparar obs/GFS/WPS sin correr el pipeline
            try:
                csv = descargar_obs_historico(caso["fecha"])
                cov = cobertura_obs(csv, caso["fecha"], comun.get("hora_ciclo", "00"))
                obs_flat = generar_obs_flat(csv, caso["fecha"])
                fuente = gfs_disponible(caso["fecha"], comun.get("hora_ciclo", "00"))
                n_gfs = descargar_gfs(caso["fecha"], comun.get("hora_ciclo", "00")) if fuente else 0
                estado[cid] = {"estado": "PREPARADO", "detalle": f"obs {cov['ventana']}, gfs {n_gfs}, obs_flat {obs_flat.name}",
                               "ts": datetime.now().isoformat(timespec="seconds")}
            except Exception as e:
                estado[cid] = {"estado": "FALLIDO", "detalle": f"preparacion: {e}",
                               "ts": datetime.now().isoformat(timespec="seconds")}
            continue

        logger.info(f"=== {caso['titulo']} ({caso['fecha']}) ===")
        ejecutar_caso(caso, comun, estado)

    _guardar_estado(estado)

    if not args.dry_run:
        for caso in casos:
            entry = estado.get(caso["id"], {})
            cobertura = None
            if entry.get("estado") == "EJECUTADO":
                try:
                    csv = csv_historico(caso["fecha"])
                    if csv.exists():
                        cobertura = cobertura_obs(csv, caso["fecha"], comun.get("hora_ciclo", "00"))
                except Exception:
                    cobertura = None
            redactar_informe_caso(caso, entry, cobertura)
        redactar_informe_consolidado(todos_casos, estado)
    return 0


if __name__ == "__main__":
    sys.exit(main())