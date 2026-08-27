#!/usr/bin/env python3
"""
Probar Circuito de Asimilación WRF
Script principal con interfaz Streamlit para ejecutar el circuito completo:
  1. Descargar GFS desde AWS
  2. Generar OBS_DOMAIN101 desde datos históricos
  3. Ejecutar WPS (geogrid, ungrib, metgrid)
  4. Correr WRF (nudged + control)
  5. Validar resultados

Uso:
    streamlit run probar_circuito.py
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CONTAINER = "teachme"
CONTAINER_WRF_DIR = "/wrf/WRF/test/em_real"
CONTAINER_WPS_DIR = "/wrf/WPS"

PROJECT_DIR = Path(__file__).parent
TESIS_DIR = PROJECT_DIR / "tesis_wrf_pgich"
HISTORICO_DIR = TESIS_DIR / "historico"
GFS_DIR = PROJECT_DIR / "gfs_data"
RESULTS_DIR = PROJECT_DIR / "results"
LOGS_DIR = PROJECT_DIR / "logs"

GFS_S3_BASE = "s3://noaa-gfs-bdp-pds"
GFS_FILES_TEMPLATE = [
    "gfs.t{hora}z.pgrb2.0p25.f000",
    "gfs.t{hora}z.pgrb2.0p25.f003",
    "gfs.t{hora}z.pgrb2.0p25.f006",
    "gfs.t{hora}z.pgrb2.0p25.f009",
    "gfs.t{hora}z.pgrb2.0p25.f012",
]

ESTACIONES_VALIDAS = [
    "INTA_POCITO",
    "ULLUM_EMBALSE",
    "ECOHUMUS",
    "PUNTA_NEGRA",
]

# ---------------------------------------------------------------------------
# Sistema de Logs
# ---------------------------------------------------------------------------


def setup_logging(fecha_str):
    """Configura logging para archivo y consola."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"circuit_{fecha_str}.log"

    logger = logging.getLogger("circuit")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def get_logger():
    """Retorna logger global o crea uno básico."""
    logger = logging.getLogger("circuit")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Funciones de verificación
# ---------------------------------------------------------------------------


def verificar_contenedor(nombre):
    """Verifica si el contenedor Docker está corriendo."""
    try:
        result = subprocess.run(
            ["docker", "exec", nombre, "echo", "ok"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, f"Contenedor '{nombre}' activo"
        else:
            return False, f"Contenedor '{nombre}' no responde"
    except FileNotFoundError:
        return False, "Docker no está instalado"
    except subprocess.TimeoutExpired:
        return False, f"Timeout al conectar con '{nombre}'"
    except Exception as e:
        return False, f"Error: {str(e)[:80]}"


def verificar_aws_cli():
    """Verifica si AWS CLI está instalado."""
    try:
        result = subprocess.run(
            ["aws", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, "AWS CLI instalado"
        else:
            return False, "AWS CLI no funciona"
    except FileNotFoundError:
        return False, "AWS CLI no instalado"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def verificar_gfs_disponible(fecha_str, hora):
    """Verifica si los archivos GFS están disponibles en AWS S3."""
    s3_path = f"{GFS_S3_BASE}/gfs.{fecha_str}/{hora}/atmos/"

    try:
        result = subprocess.run(
            ["aws", "s3", "ls", "--no-sign-request", "--summarize", s3_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and "Total Objects" in result.stdout:
            for f in GFS_FILES_TEMPLATE:
                if f.format(hora=hora) not in result.stdout:
                    return False, f"Archivos GFS incompletos", []
            return True, "GFS disponible en AWS", GFS_FILES_TEMPLATE
        else:
            return False, "GFS no disponible en AWS", []
    except FileNotFoundError:
        return False, "AWS CLI no instalado", []
    except Exception as e:
        return False, f"Error: {str(e)[:80]}", []


def verificar_historico(fecha_str):
    """Verifica si existe el CSV histórico para la fecha."""
    fecha_file = fecha_str.replace("-", "")
    csv_path = HISTORICO_DIR / f"ecowitt_historico_{fecha_file}.csv"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            estaciones = df["estacion"].nunique()
            registros = len(df)
            return True, f"CSV: {estaciones} estaciones, {registros} registros"
        except Exception as e:
            return False, f"Error leyendo CSV: {str(e)[:50]}"
    else:
        return False, f"CSV no encontrado: {csv_path.name}"


def verificar_obsdomain():
    """Verifica si OBS_DOMAIN101 existe en el directorio de procesados."""
    obs_path = TESIS_DIR / "data" / "processed" / "OBS_DOMAIN101"
    if obs_path.exists():
        size_kb = obs_path.stat().st_size / 1024
        return True, f"OBS_DOMAIN101: {size_kb:.0f} KB"
    else:
        return False, "OBS_DOMAIN101 no generado"


def verificar_contenedor_corriendo():
    """Verifica si el contenedor está corriendo y retorna estado."""
    ok, msg = verificar_contenedor(CONTAINER)
    return ok


# ---------------------------------------------------------------------------
# Funciones de ejecución
# ---------------------------------------------------------------------------


def docker_exec(cmd, container=CONTAINER, timeout=7200):
    """Ejecuta comando dentro del contenedor."""
    try:
        result = subprocess.run(
            ["docker", "exec", container, "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)


def docker_cp(src, dst, container=CONTAINER):
    """Copia archivo al contenedor."""
    try:
        result = subprocess.run(
            ["docker", "cp", str(src), f"{container}:{dst}"],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


def docker_cp_from(container_src, dst, container=CONTAINER):
    """Copia archivo desde el contenedor."""
    try:
        result = subprocess.run(
            ["docker", "cp", f"{container}:{container_src}", str(dst)],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


def descargar_gfs(fecha_str, hora, logger):
    """Descarga archivos GFS desde AWS S3."""
    gfs_dir = GFS_DIR / fecha_str
    gfs_dir.mkdir(parents=True, exist_ok=True)

    s3_path = f"{GFS_S3_BASE}/gfs.{fecha_str}/{hora}/atmos/"

    logger.info(f"Descargando GFS desde {s3_path}")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"  Intento {attempt + 1}/{max_retries}...")

            result = subprocess.run(
                ["aws", "s3", "cp", "--no-sign-request",
                 "--recursive", s3_path, str(gfs_dir),
                 "--exclude", "*",
                 "--include", f"gfs.t{hora}z.pgrb2.0p25.f0*"],
                capture_output=True, text=True, timeout=600
            )

            if result.returncode == 0:
                archivos = list(gfs_dir.glob(f"gfs.t{hora}z.pgrb2.0p25.f0*"))
                if len(archivos) >= 5:
                    logger.info(f"  GFS descargado: {len(archivos)} archivos")
                    return True, f"GFS descargado: {len(archivos)} archivos", len(archivos)
                else:
                    logger.warning(f"  Solo {len(archivos)}/5 archivos descargados")
            else:
                logger.error(f"  Error AWS: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            logger.warning(f"  Timeout en intento {attempt + 1}")
        except Exception as e:
            logger.error(f"  Error inesperado: {e}")

    return False, "Fallo la descarga de GFS después de 3 intentos", 0


def generar_obsdomain(fecha_str, logger):
    """Genera OBS_DOMAIN101 desde datos históricos."""
    logger.info("Generando OBS_DOMAIN101 desde datos históricos...")

    script_path = TESIS_DIR / "src" / "calidad" / "historico_a_obsnud.py"
    output_dir = TESIS_DIR / "data" / "processed"

    cmd = f"cd {TESIS_DIR} && python {script_path} --fecha {fecha_str} --no-docker"
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=120
    )

    if result.returncode == 0:
        obs_path = output_dir / "OBS_DOMAIN101"
        if obs_path.exists():
            logger.info(f"  OBS_DOMAIN101 generado: {obs_path}")
            return True, f"OBS_DOMAIN101 generado", 4
        else:
            logger.error("  OBS_DOMAIN101 no encontrado después de ejecutar script")
            return False, "OBS_DOMAIN101 no generado", 0
    else:
        logger.error(f"  Error: {result.stderr[:200]}")
        return False, f"Error generando OBS_DOMAIN101", 0


def preparar_namelist_wps(fecha_str, hora, logger):
    """Prepara namelist.wps con las fechas correctas."""
    logger.info("Preparando namelist.wps...")

    start_date = f"{fecha_str}_{hora}:00:00"
    end_dt = datetime.strptime(fecha_str, "%Y-%m-%d") + timedelta(hours=12)
    end_date = end_dt.strftime("%Y-%m-%d_00:00:00")

    namelist_template = PROJECT_DIR / "namelist.wps"

    with open(namelist_template) as f:
        content = f.read()

    content = re.sub(
        r"start_date\s*=\s*'[^']*'",
        f"start_date = '{start_date}'",
        content
    )
    content = re.sub(
        r"end_date\s*=\s*'[^']*'",
        f"end_date = '{end_date}'",
        content
    )

    output_path = TESIS_DIR / "data" / "processed" / "namelist.wps"
    with open(output_path, "w") as f:
        f.write(content)

    logger.info(f"  namelist.wps: {start_date} → {end_date}")
    return output_path


def preparar_namelist_input(fecha_str, hora, obs_nudge_opt, logger):
    """Prepara namelist.input con las fechas y opciones correctas."""
    logger.info(f"Preparando namelist.input (obs_nudge_opt={obs_nudge_opt})...")

    start_dt = datetime.strptime(f"{fecha_str} {hora}", "%Y-%m-%d %H")
    end_dt = start_dt + timedelta(hours=12)

    namelist_template = PROJECT_DIR / "namelist.input"

    with open(namelist_template) as f:
        content = f.read()

    # Fechas
    content = re.sub(r"start_year\s*=\s*\d+", f"start_year = {start_dt.year}", content)
    content = re.sub(r"start_month\s*=\s*\d+", f"start_month = {start_dt.month:02d}", content)
    content = re.sub(r"start_day\s*=\s*\d+", f"start_day = {start_dt.day:02d}", content)
    content = re.sub(r"start_hour\s*=\s*\d+", f"start_hour = {start_dt.hour}", content)

    content = re.sub(r"end_year\s*=\s*\d+", f"end_year = {end_dt.year}", content)
    content = re.sub(r"end_month\s*=\s*\d+", f"end_month = {end_dt.month:02d}", content)
    content = re.sub(r"end_day\s*=\s*\d+", f"end_day = {end_dt.day:02d}", content)
    content = re.sub(r"end_hour\s*=\s*\d+", f"end_hour = {end_dt.hour}", content)

    # Obs nudging
    content = re.sub(r"obs_nudge_opt\s*=\s*\d+", f"obs_nudge_opt = {obs_nudge_opt}", content)
    content = re.sub(r"fdda_end\s*=\s*\d+", f"fdda_end = 720", content)

    output_path = TESIS_DIR / "data" / "processed" / "namelist.input"
    with open(output_path, "w") as f:
        f.write(content)

    logger.info(f"  namelist.input: {start_dt} → {end_dt}")
    return output_path


def ejecutar_wps(fecha_str, hora, logger):
    """Ejecuta WPS (geogrid, ungrib, metgrid) en el contenedor."""
    logger.info("Ejecutando WPS...")

    # Verificar contenedor
    ok, _ = verificar_contenedor(CONTAINER)
    if not ok:
        return False, "Contenedor no disponible", "00:00"

    start_time = time.time()

    # Preparar namelist.wps
    namelist_wps = preparar_namelist_wps(fecha_str, hora, logger)

    # Copiar namelist.wps al contenedor
    docker_cp(namelist_wps, f"{CONTAINER_WPS_DIR}/namelist.wps")

    # Copiar GFS al contenedor
    gfs_dir = GFS_DIR / fecha_str
    if gfs_dir.exists():
        docker_exec(f"mkdir -p {CONTAINER_WPS_DIR}/gfs_data")
        for f in gfs_dir.glob("gfs.*"):
            docker_cp(f, f"{CONTAINER_WPS_DIR}/gfs_data/{f.name}")

    # geogrid.exe
    logger.info("  Ejecutando geogrid.exe...")
    ok, stdout, stderr = docker_exec(f"cd {CONTAINER_WPS_DIR} && ./geogrid.exe", timeout=300)
    if not ok:
        logger.error(f"  geogrid.exe falló: {stderr[:200]}")
        return False, f"geogrid.exe falló", elapsed_str(start_time)

    # ungrib.exe
    logger.info("  Ejecutando ungrib.exe...")
    ok, stdout, stderr = docker_exec(f"cd {CONTAINER_WPS_DIR} && ./ungrib.exe", timeout=600)
    if not ok:
        logger.error(f"  ungrib.exe falló: {stderr[:200]}")
        return False, f"ungrib.exe falló", elapsed_str(start_time)

    # metgrid.exe
    logger.info("  Ejecutando metgrid.exe...")
    ok, stdout, stderr = docker_exec(f"cd {CONTAINER_WPS_DIR} && ./metgrid.exe", timeout=600)
    if not ok:
        logger.error(f"  metgrid.exe falló: {stderr[:200]}")
        return False, f"metgrid.exe falló", elapsed_str(start_time)

    # Verificar archivos met_em*
    ok, stdout, _ = docker_exec(f"ls {CONTAINER_WPS_DIR}/met_em* | wc -l")
    n_met = int(stdout.strip()) if ok else 0

    elapsed = elapsed_str(start_time)
    logger.info(f"  WPS completado en {elapsed} ({n_met} archivos met_em)")

    return True, f"WPS completado: {n_met} archivos met_em", elapsed


def ejecutar_wrf_nudged(fecha_str, hora, logger):
    """Corre WRF con obs_nudge_opt=1."""
    logger.info("Ejecutando WRF (nudged)...")

    start_time = time.time()

    # Preparar namelist
    namelist = preparar_namelist_input(fecha_str, hora, 1, logger)

    # Copiar al contenedor
    docker_cp(namelist, f"{CONTAINER_WRF_DIR}/namelist.input")

    # Copiar OBS_DOMAIN101
    obs_path = TESIS_DIR / "data" / "processed" / "OBS_DOMAIN101"
    if obs_path.exists():
        docker_cp(obs_path, f"{CONTAINER_WRF_DIR}/OBS_DOMAIN101")

    # Limpiar archivos previos
    docker_exec(f"cd {CONTAINER_WRF_DIR} && rm -f rsl.* wrfout_d01*")

    # Ejecutar WRF
    logger.info("  Ejecutando wrf.exe (nudged)...")
    ok, stdout, stderr = docker_exec(
        f"cd {CONTAINER_WRF_DIR} && mpirun -np 4 ./wrf.exe",
        timeout=7200
    )

    if not ok:
        logger.error(f"  wrf.exe (nudged) falló")
        return False, "wrf.exe (nudged) falló", elapsed_str(start_time)

    # Verificar wrfout
    ok, stdout, _ = docker_exec(f"ls {CONTAINER_WRF_DIR}/wrfout_d01* | wc -l")
    n_wrfout = int(stdout.strip()) if ok else 0

    # Copiar wrfout a directorio local
    fecha_dt = datetime.strptime(f"{fecha_str} {hora}", "%Y-%m-%d %H")
    case_dir = RESULTS_DIR / f"{fecha_str}_{hora}00z" / f"hist_{fecha_str}"
    nudged_dir = case_dir / "nudged"
    nudged_dir.mkdir(parents=True, exist_ok=True)

    # Copiar wrfout desde contenedor
    ok, stdout, _ = docker_exec(f"ls {CONTAINER_WRF_DIR}/wrfout_d01*")
    if ok:
        for fname in stdout.strip().splitlines():
            fname = fname.strip()
            if fname:
                safe_name = Path(fname).name.replace(":", "_")
                docker_cp_from(fname, nudged_dir / safe_name)

    elapsed = elapsed_str(start_time)
    logger.info(f"  WRF nudged completado en {elapsed} ({n_wrfout} wrfout)")

    return True, f"WRF nudged: {n_wrfout} wrfout", elapsed


def ejecutar_wrf_control(fecha_str, hora, logger):
    """Corre WRF con obs_nudge_opt=0 (control)."""
    logger.info("Ejecutando WRF (control)...")

    start_time = time.time()

    # Preparar namelist
    namelist = preparar_namelist_input(fecha_str, hora, 0, logger)

    # Copiar al contenedor
    docker_cp(namelist, f"{CONTAINER_WRF_DIR}/namelist.input")

    # Limpiar archivos previos
    docker_exec(f"cd {CONTAINER_WRF_DIR} && rm -f rsl.* wrfout_d01*")

    # Ejecutar WRF
    logger.info("  Ejecutando wrf.exe (control)...")
    ok, stdout, stderr = docker_exec(
        f"cd {CONTAINER_WRF_DIR} && mpirun -np 4 ./wrf.exe",
        timeout=7200
    )

    if not ok:
        logger.error(f"  wrf.exe (control) falló")
        return False, "wrf.exe (control) falló", elapsed_str(start_time)

    # Verificar wrfout
    ok, stdout, _ = docker_exec(f"ls {CONTAINER_WRF_DIR}/wrfout_d01* | wc -l")
    n_wrfout = int(stdout.strip()) if ok else 0

    # Copiar wrfout a directorio local
    case_dir = RESULTS_DIR / f"{fecha_str}_{hora}00z" / f"hist_{fecha_str}"
    control_dir = case_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=True)

    ok, stdout, _ = docker_exec(f"ls {CONTAINER_WRF_DIR}/wrfout_d01*")
    if ok:
        for fname in stdout.strip().splitlines():
            fname = fname.strip()
            if fname:
                safe_name = Path(fname).name.replace(":", "_")
                docker_cp_from(fname, control_dir / safe_name)

    elapsed = elapsed_str(start_time)
    logger.info(f"  WRF control completado en {elapsed} ({n_wrfout} wrfout)")

    return True, f"WRF control: {n_wrfout} wrfout", elapsed


def validar_resultados(fecha_str, hora, logger):
    """Ejecuta validación WRF vs observaciones."""
    logger.info("Ejecutando validación...")

    case_dir = RESULTS_DIR / f"{fecha_str}_{hora}00z" / f"hist_{fecha_str}"
    nudged_dir = case_dir / "nudged"
    control_dir = case_dir / "control"

    # Verificar que existen wrfout
    if not nudged_dir.exists() or not list(nudged_dir.glob("wrfout_d01*")):
        return False, "No hay wrfout nudged para validar", {}
    if not control_dir.exists() or not list(control_dir.glob("wrfout_d01*")):
        return False, "No hay wrfout control para validar", {}

    # Copiar valida_wrf.py al contenedor
    container_tmp = f"{CONTAINER_WRF_DIR}/pipeline_validation"
    docker_exec(f"mkdir -p {container_tmp}")

    valida_script = TESIS_DIR / "src" / "calidad" / "valida_wrf.py"
    docker_cp(valida_script, f"{container_tmp}/valida_wrf.py")

    estaciones_json = TESIS_DIR / "config" / "estaciones.json"
    docker_cp(estaciones_json, f"{container_tmp}/estaciones.json")

    # Copiar wrfouts al contenedor para validación
    docker_exec(f"mkdir -p {CONTAINER_WRF_DIR}/nudged {CONTAINER_WRF_DIR}/control")
    docker_exec(f"cp {CONTAINER_WRF_DIR}/wrfout_d01* {CONTAINER_WRF_DIR}/nudged/")

    # Ejecutar validación
    valid_time = f"{fecha_str}_{hora}:00:00"
    cmd = (
        f"cd {container_tmp} && python3 {container_tmp}/valida_wrf.py"
        f" --nudged-dir {CONTAINER_WRF_DIR}/nudged"
        f" --control-dir {CONTAINER_WRF_DIR}/control"
        f" --output-dir {container_tmp}/output"
        f" --valid-time {valid_time}"
        f" --estaciones-json {container_tmp}/estaciones.json"
    )
    ok, stdout, stderr = docker_exec(cmd, timeout=300)

    # Copiar resultados al host
    output_dir = case_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    result_ok, result_list, _ = docker_exec(f"ls {container_tmp}/output/")
    if result_ok:
        for fname in result_list.strip().splitlines():
            fname = fname.strip()
            if fname:
                docker_cp_from(f"{container_tmp}/output/{fname}", output_dir / fname)

    # Leer métricas si existen
    metrics = {}
    metricas_file = output_dir / "metricas_resumen.txt"
    if metricas_file.exists():
        with open(metricas_file) as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    try:
                        metrics[key.strip()] = float(val.strip())
                    except ValueError:
                        metrics[key.strip()] = val.strip()

    # Limpiar
    docker_exec(f"rm -rf {container_tmp}")

    logger.info(f"  Validación completada: {len(metrics)} métricas")
    return True, "Validación completada", metrics


def elapsed_str(start_time):
    """Retorna string con tiempo transcurrido."""
    elapsed = time.time() - start_time
    return time.strftime("%H:%M:%S", time.gmtime(elapsed))


# ---------------------------------------------------------------------------
# Funciones de interfaz Streamlit
# ---------------------------------------------------------------------------


def mostrar_estado_paso(nombre, estado, mensaje, detalles=None):
    """Muestra el estado de un paso del circuito."""
    iconos = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "error": "❌"
    }

    col1, col2 = st.columns([1, 4])
    with col1:
        st.write(f"{iconos.get(estado, '❓')} **{nombre}**")
    with col2:
        if estado == "completed":
            st.success(mensaje)
        elif estado == "error":
            st.error(mensaje)
        elif estado == "running":
            st.info(mensaje)
        else:
            st.caption(mensaje)
        if detalles:
            st.caption(detalles)


def mostrar_graficos_validacion(results_dir):
    """Muestra gráficos de validación si existen."""
    if not results_dir.exists():
        st.warning("No hay resultados para mostrar")
        return

    tab1, tab2, tab3 = st.tabs(["📊 Métricas", "🔍 Scatter", "🗺️ Mapa Errores"])

    with tab1:
        img_path = results_dir / "tabla_metricas.png"
        if img_path.exists():
            st.image(str(img_path), caption="Tabla de Métricas", use_container_width=True)
        else:
            st.info("Gráfico de métricas no disponible")

    with tab2:
        img_path = results_dir / "scatter_4panels.png"
        if img_path.exists():
            st.image(str(img_path), caption="Scatter 4 Paneles", use_container_width=True)
        else:
            st.info("Gráfico de scatter no disponible")

    with tab3:
        img_path = results_dir / "mapa_errores_t2.png"
        if img_path.exists():
            st.image(str(img_path), caption="Mapa de Errores T2", use_container_width=True)
        else:
            st.info("Mapa de errores no disponible")


def mostrar_log_viewer(log_file):
    """Muestra el contenido del log."""
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        st.code(content, language="text")
    else:
        st.warning("No hay log disponible")


def mostrar_metricas(metrics):
    """Muestra métricas de validación."""
    if not metrics:
        st.info("No hay métricas disponibles")
        return

    cols = st.columns(4)
    metric_names = {
        "T2 RMSE": "🌡️",
        "RH2 RMSE": "💧",
        "U10 RMSE": "🌬️",
        "PSFC RMSE": "🔽"
    }

    for i, (key, icon) in enumerate(metric_names.items()):
        with cols[i]:
            if key in metrics:
                st.metric(f"{icon} {key}", f"{metrics[key]:.2f}")
            else:
                st.metric(f"{icon} {key}", "N/A")


# ---------------------------------------------------------------------------
# Ejecución del circuito completo
# ---------------------------------------------------------------------------


def ejecutar_circuito_completo(fecha, hora, container, logger):
    """Ejecuta todo el circuito secuencialmente."""
    fecha_str = fecha.strftime("%Y-%m-%d")

    try:
        logger.info("=" * 60)
        logger.info("INICIO DEL CIRCUITO DE ASIMILACIÓN WRF")
        logger.info(f"Fecha: {fecha_str} | Hora: {hora} UTC")
        logger.info("=" * 60)

        # Paso 1: GFS
        st.session_state.steps["gfs"]["status"] = "running"
        st.session_state.steps["gfs"]["message"] = "Descargando GFS..."
        st.rerun()

        ok, msg, n = descargar_gfs(fecha_str, hora, logger)
        st.session_state.steps["gfs"] = {
            "status": "completed" if ok else "error",
            "message": msg
        }
        if not ok:
            st.error(f"Fallo Paso 1: {msg}")
            return

        # Paso 2: OBS_DOMAIN101
        st.session_state.steps["obsdomain"]["status"] = "running"
        st.session_state.steps["obsdomain"]["message"] = "Generando OBS_DOMAIN101..."
        st.rerun()

        ok, msg, n = generar_obsdomain(fecha_str, logger)
        st.session_state.steps["obsdomain"] = {
            "status": "completed" if ok else "error",
            "message": msg
        }
        if not ok:
            st.error(f"Fallo Paso 2: {msg}")
            return

        # Paso 3: WPS
        st.session_state.steps["wps"]["status"] = "running"
        st.session_state.steps["wps"]["message"] = "Ejecutando WPS..."
        st.rerun()

        ok, msg, elapsed = ejecutar_wps(fecha_str, hora, logger)
        st.session_state.steps["wps"] = {
            "status": "completed" if ok else "error",
            "message": f"{msg} ({elapsed})"
        }
        if not ok:
            st.error(f"Fallo Paso 3: {msg}")
            return

        # Paso 4a: WRF Nudged
        st.session_state.steps["wrf_nudged"]["status"] = "running"
        st.session_state.steps["wrf_nudged"]["message"] = "Ejecutando WRF nudged..."
        st.rerun()

        ok, msg, elapsed = ejecutar_wrf_nudged(fecha_str, hora, logger)
        st.session_state.steps["wrf_nudged"] = {
            "status": "completed" if ok else "error",
            "message": f"{msg} ({elapsed})"
        }
        if not ok:
            st.error(f"Fallo Paso 4a: {msg}")
            return

        # Paso 4b: WRF Control
        st.session_state.steps["wrf_control"]["status"] = "running"
        st.session_state.steps["wrf_control"]["message"] = "Ejecutando WRF control..."
        st.rerun()

        ok, msg, elapsed = ejecutar_wrf_control(fecha_str, hora, logger)
        st.session_state.steps["wrf_control"] = {
            "status": "completed" if ok else "error",
            "message": f"{msg} ({elapsed})"
        }
        if not ok:
            st.error(f"Fallo Paso 4b: {msg}")
            return

        # Paso 5: Validación
        st.session_state.steps["validacion"]["status"] = "running"
        st.session_state.steps["validacion"]["message"] = "Ejecutando validación..."
        st.rerun()

        ok, msg, metrics = validar_resultados(fecha_str, hora, logger)
        st.session_state.steps["validacion"] = {
            "status": "completed" if ok else "error",
            "message": msg
        }
        st.session_state.metrics = metrics

        logger.info("=" * 60)
        logger.info("CIRCUITO COMPLETADO EXITOSAMENTE")
        logger.info("=" * 60)

        st.success("🎉 ¡Circuito completado exitosamente!")

    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        st.error(f"Error inesperado: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    st.set_page_config(
        page_title="Probar Circuito WRF",
        page_icon="🧪",
        layout="wide"
    )

    st.title("🧪 Probar Circuito de Asimilación WRF")

    # Fecha y hora fijas (misma configuración que namelist anterior)
    fecha_sim = date(2026, 7, 2)
    hora_sim = "12"

    st.markdown(f"""
    **Fecha de prueba:** {fecha_sim.strftime('%Y-%m-%d')} | 
    **Hora:** {hora_sim} UTC | 
    **Duración:** 12 horas | 
    **Simulación:** {fecha_sim.strftime('%Y-%m-%d')} 12:00 → {(fecha_sim + timedelta(days=1)).strftime('%Y-%m-%d')} 00:00 UTC
    """)

    # === SIDEBAR ===
    with st.sidebar:
        st.header("⚙️ Configuración")
        st.markdown(f"""
        **Fecha:** {fecha_sim}
        **Hora:** {hora_sim} UTC
        **Duración:** 12 horas
        **Contenedor:** {CONTAINER}
        """)

        st.markdown("---")
        if st.button("🔄 Reiniciar Estado"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # === VERIFICACIONES INICIALES ===
    st.markdown("### 🔍 Verificaciones Iniciales")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ok, msg = verificar_contenedor(CONTAINER)
        st.metric("🐳 Contenedor", "✅" if ok else "❌", msg)

    with col2:
        ok, msg = verificar_aws_cli()
        st.metric("☁️ AWS CLI", "✅" if ok else "❌", msg)

    with col3:
        ok, msg, archivos = verificar_gfs_disponible(fecha_sim.strftime("%Y-%m-%d"), hora_sim)
        st.metric("🌍 GFS AWS", "✅" if ok else "❌", msg)

    with col4:
        ok, msg = verificar_historico(fecha_sim.strftime("%Y-%m-%d"))
        st.metric("📊 Datos Históricos", "✅" if ok else "❌", msg)

    st.markdown("---")

    # === PASOS DEL CIRCUITO ===
    st.markdown("### 📋 Pasos del Circuito")

    # Inicializar estado
    if "steps" not in st.session_state:
        st.session_state.steps = {
            "gfs": {"status": "pending", "message": "Esperando..."},
            "obsdomain": {"status": "pending", "message": "Esperando..."},
            "wps": {"status": "pending", "message": "Esperando..."},
            "wrf_nudged": {"status": "pending", "message": "Esperando..."},
            "wrf_control": {"status": "pending", "message": "Esperando..."},
            "validacion": {"status": "pending", "message": "Esperando..."},
        }
    if "metrics" not in st.session_state:
        st.session_state.metrics = {}

    # Paso 1: GFS
    with st.expander("📥 **PASO 1: Descargar GFS**", expanded=True):
        mostrar_estado_paso(
            "Descargar GFS",
            st.session_state.steps["gfs"]["status"],
            st.session_state.steps["gfs"]["message"],
            f"Archivos: gfs.t{hora_sim}z.pgrb2.0p25.f000-f012"
        )
        if st.button("▶ Ejecutar Paso 1", key="run_gfs"):
            logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
            with st.spinner("Descargando GFS..."):
                ok, msg, n = descargar_gfs(fecha_sim.strftime("%Y-%m-%d"), hora_sim, logger)
                st.session_state.steps["gfs"] = {
                    "status": "completed" if ok else "error",
                    "message": msg
                }
                st.rerun()

    # Paso 2: OBS_DOMAIN101
    with st.expander("📊 **PASO 2: Generar OBS_DOMAIN101**", expanded=True):
        mostrar_estado_paso(
            "Generar OBS_DOMAIN101",
            st.session_state.steps["obsdomain"]["status"],
            st.session_state.steps["obsdomain"]["message"],
            f"Estaciones: {', '.join(ESTACIONES_VALIDAS)}"
        )
        if st.button("▶ Ejecutar Paso 2", key="run_obs"):
            logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
            with st.spinner("Generando OBS_DOMAIN101..."):
                ok, msg, n = generar_obsdomain(fecha_sim.strftime("%Y-%m-%d"), logger)
                st.session_state.steps["obsdomain"] = {
                    "status": "completed" if ok else "error",
                    "message": msg
                }
                st.rerun()

    # Paso 3: WPS
    with st.expander("🌐 **PASO 3: Ejecutar WPS**", expanded=True):
        mostrar_estado_paso(
            "Ejecutar WPS",
            st.session_state.steps["wps"]["status"],
            st.session_state.steps["wps"]["message"],
            "geogrid → ungrib → metgrid"
        )
        if st.button("▶ Ejecutar Paso 3", key="run_wps"):
            logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
            with st.spinner("Ejecutando WPS..."):
                ok, msg, elapsed = ejecutar_wps(fecha_sim.strftime("%Y-%m-%d"), hora_sim, logger)
                st.session_state.steps["wps"] = {
                    "status": "completed" if ok else "error",
                    "message": f"{msg} ({elapsed})"
                }
                st.rerun()

    # Paso 4: WRF
    with st.expander("🌀 **PASO 4: Correr WRF**", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            mostrar_estado_paso(
                "WRF Nudged",
                st.session_state.steps["wrf_nudged"]["status"],
                st.session_state.steps["wrf_nudged"]["message"],
                "obs_nudge_opt=1"
            )
        with col2:
            mostrar_estado_paso(
                "WRF Control",
                st.session_state.steps["wrf_control"]["status"],
                st.session_state.steps["wrf_control"]["message"],
                "obs_nudge_opt=0"
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶ Ejecutar WRF Nudged", key="run_nudged"):
                logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
                with st.spinner("Ejecutando WRF nudged..."):
                    ok, msg, elapsed = ejecutar_wrf_nudged(
                        fecha_sim.strftime("%Y-%m-%d"), hora_sim, logger
                    )
                    st.session_state.steps["wrf_nudged"] = {
                        "status": "completed" if ok else "error",
                        "message": f"{msg} ({elapsed})"
                    }
                    st.rerun()
        with col2:
            if st.button("▶ Ejecutar WRF Control", key="run_control"):
                logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
                with st.spinner("Ejecutando WRF control..."):
                    ok, msg, elapsed = ejecutar_wrf_control(
                        fecha_sim.strftime("%Y-%m-%d"), hora_sim, logger
                    )
                    st.session_state.steps["wrf_control"] = {
                        "status": "completed" if ok else "error",
                        "message": f"{msg} ({elapsed})"
                    }
                    st.rerun()

    # Paso 5: Validación
    with st.expander("📈 **PASO 5: Validar Resultados**", expanded=True):
        mostrar_estado_paso(
            "Validar Resultados",
            st.session_state.steps["validacion"]["status"],
            st.session_state.steps["validacion"]["message"],
            "T2, RH, Wind, PSFC"
        )
        if st.button("▶ Ejecutar Validación", key="run_valid"):
            logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
            with st.spinner("Ejecutando validación..."):
                ok, msg, metrics = validar_resultados(
                    fecha_sim.strftime("%Y-%m-%d"), hora_sim, logger
                )
                st.session_state.steps["validacion"] = {
                    "status": "completed" if ok else "error",
                    "message": msg
                }
                st.session_state.metrics = metrics
                st.rerun()

    # === BOTONES DE ACCIÓN GLOBAL ===
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶ EJECUTAR TODO", type="primary", use_container_width=True):
            logger = setup_logging(fecha_sim.strftime("%Y-%m-%d"))
            ejecutar_circuito_completo(fecha_sim, hora_sim, CONTAINER, logger)
            st.rerun()

    with col2:
        if st.button("📊 Ver Resultados", use_container_width=True):
            results_dir = RESULTS_DIR / f"{fecha_sim.strftime('%Y-%m-%d')}_1200z" / f"hist_{fecha_sim}"
            mostrar_graficos_validacion(results_dir)

    with col3:
        if st.button("📋 Ver Log", use_container_width=True):
            log_file = LOGS_DIR / f"circuit_{fecha_sim}.log"
            mostrar_log_viewer(log_file)

    # === MÉTRICAS DE VALIDACIÓN ===
    if st.session_state.metrics:
        st.markdown("---")
        st.markdown("### 📊 Métricas de Validación")
        mostrar_metricas(st.session_state.metrics)

    # === FOOTER ===
    st.markdown("---")
    st.markdown("**PGICH v0.2.0** - Probar Circuito de Asimilación WRF | 2026-07-02 12Z")


if __name__ == "__main__":
    main()
