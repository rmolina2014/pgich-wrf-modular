#!/usr/bin/env python3
"""
Pipeline WRF - Ciclo completo: Little_R -> OBS_DOMAIN101 -> wrf.exe -> Validacion.
Version nativa (sin Docker): usa el WRF instalado en esta PC.

Uso:
    python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \\
        --json data/raw/ecowitt_todos_20260525_2059.json \\
        --case base --namelist namelist.input

    python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \\
        --json data/raw/ecowitt_todos_20260525_2059.json \\
        --case sens_coef0001 --namelist namelist_sens_coef0001.input

    # Solo preparar archivos de entrada (no correr WRF)
    python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \\
        --json data/raw/ecowitt_todos_20260525_2059.json \\
        --case base --namelist namelist.input --prepare-only

    # Correr real.exe antes de wrf.exe (si faltan wrfinput/wrfbdy)
    python pipeline_wrf.py --date 2026-05-25 --hour 21:00 \\
        --json data/raw/ecowitt_todos_20260525_2059.json \\
        --case base --run-real
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde .env (rutas WRF, credenciales EcoWitt, etc.)
load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("pipeline_wrf")

# Rutas fijas del proyecto
DATA_RAW = Path(__file__).parent / "data" / "raw"
DATA_PROCESSED = Path(__file__).parent / "data" / "processed"
RESULTS_DIR = Path(__file__).parent / "results"
# Metadatos de estaciones (archivo compartido por los modulares)
ESTACIONES_JSON = Path(__file__).parent / "config" / "estaciones.json"

# === Configuracion nativa (WRF local) ===
# Este proyecto se usa en dos PCs Linux con rutas distintas. El default de cada
# variable es el de la PC activa; el de la otra PC queda comentado al lado para
# no perderlo. Si hace falta, tambien se puede overridear con la env var
# correspondiente (LOCAL_WRF_DIR, WRF_ENV_BASH, MPIRUN, VALIDATION_PYTHON) sin
# tocar el codigo (ver documentacion_proyecto/info_pc_linux.md para el detalle
# completo de la PC pgich, y un .env local ahi es la forma recomendada de
# fijar estas rutas sin volver a tocar estas lineas).
#
# OJO version de WRF: PC pgich corre WRF-Chem 4.5 (/home/pgich/Build_WRF/WRF).
# Esta PC corria WRF 4.0 hasta 2026-09-12; se compilo WRF-4.5 propio (misma
# version que pgich, ver documentacion_proyecto/ y memoria "wrf45-upgrade")
# y se revalido el fix de OBS_DOMAIN101 contra wrf_fddaobs_in.F de 4.5 (corrida
# nudged completa, NSTA>0, metricas nudged vs control consistentes con 4.0).
# WRF-4.0 queda instalado sin usarse por si hace falta volver atras.
# Directorio de corrida de WRF (debe contener wrf.exe, wrfinput, wrfbdy)
LOCAL_WRF_DIR = Path(os.environ.get(
    "LOCAL_WRF_DIR",
    # "/home/pgich/wrf-operativo/ejecutables/WRF",  # PC pgich
    # "/home/roberto/opencode/wrf/WRF-4.0/run",  # PC roberto (WRF 4.0, en desuso)
    "/home/roberto/opencode/wrf/WRF-4.5/run",  # PC roberto
))
# Script que carga el entorno operativo (LD_LIBRARY_PATH, MPICH, etc.).
# En la PC roberto WRF enlaza las librerias del sistema, por lo que este
# archivo puede no existir; ejecutar_comando lo carga solo si esta presente.
WRF_ENV_BASH = os.environ.get(
    "WRF_ENV_BASH",
    # "/home/pgich/wrf-operativo/ejecutables/env.bash",  # PC pgich
    "/home/roberto/opencode/wrf/WRF-4.5/run/env.bash",  # PC roberto
)
# mpirun de la instalacion MPI local
MPIRUN = os.environ.get(
    "MPIRUN",
    # "/home/pgich/Build_WRF/libraries/MPICH/bin/mpirun",  # PC pgich
    "/usr/bin/mpirun",  # PC roberto
)
# Numero de procesos MPI para wrf.exe (1 = ejecucion directa, como el setup operativo)
WRF_NP = os.environ.get("WRF_NP", "1")
# Python con xarray/netCDF4 para la validacion
VALIDATION_PYTHON = os.environ.get(
    "VALIDATION_PYTHON",
    # "/home/pgich/anaconda3/envs/wrf-operativo-p3/bin/python",  # PC pgich
    "/usr/bin/python3",  # PC roberto
)

# Importar modulos modulares del proyecto
from src.calidad.cleaner import ObservacionesCleaner
from src.asimilacion.littler_writer import LittleRWriter
from src.asimilacion.obsnud_writer import ObsNudWriter
from src.modelo.namelist_manager import NamelistManager
from src.modelo.wrf_runner import WRFRunner
from src.preflight.preflight import InformePreflight, correr_preflight_observaciones


def check_run_dir(run_dir=None):
    """Verifica que el directorio de corrida local tenga wrf.exe."""
    run_dir = Path(run_dir or LOCAL_WRF_DIR)
    if not run_dir.exists():
        logger.error(f"Directorio de corrida no existe: {run_dir}")
        return False
    if not (run_dir / "wrf.exe").exists():
        logger.error(f"No se encuentra wrf.exe en {run_dir}")
        return False
    return True


def copiar_archivo(src, dst, timeout=60):
    """Copia un archivo local a otra ruta local."""
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        logger.error(f"No existe el archivo: {src}")
        return False
    try:
        shutil.copy2(src, dst)
        logger.info(f"  Copiado: {src} -> {dst}")
        return True
    except OSError as e:
        logger.error(f"Error copiando {src} a {dst}: {e}")
        return False


def preparar_namelist(namelist_src, obs_nudge_opt, output_path, start_dt=None, **kwargs):
    """
    Prepara un namelist final delegando en src/modelo/namelist_manager.py.
    - Parchea las fechas de inicio/fin si se pasa start_dt (run_hours se lee del namelist).
    - Fija obs_nudge_opt y parametros de sensibilidad (obs_coef_*, obs_twindo).
    - Fuerza fdda_end=720 (12h) para que el obs nudging funcione.
    """
    mgr = NamelistManager(template_path=str(namelist_src))
    if start_dt is not None:
        m = re.search(r'run_hours\s*=\s*(\d+)', mgr.contenido)
        run_hours = int(m.group(1)) if m else 12
        end_dt = start_dt + timedelta(hours=run_hours)
        mgr.actualizar_fechas(
            start_year=start_dt.year, start_month=start_dt.month,
            start_day=start_dt.day, start_hour=start_dt.hour,
            end_year=end_dt.year, end_month=end_dt.month,
            end_day=end_dt.day, end_hour=end_dt.hour,
            run_hours=run_hours,
        )
    # fdda_end siempre 720 (12h) para que funcione obs nudging
    mgr.contenido = re.sub(r'fdda_end\s*=\s*\d+', 'fdda_end = 720', mgr.contenido)
    mgr.configurar_fdda(obs_nudge_opt=obs_nudge_opt, **kwargs)
    mgr.guardar(output_path)
    logger.info(f"Namelist preparado: {output_path} (obs_nudge_opt={obs_nudge_opt})")
    return Path(output_path)


def generar_littler_desde_json(json_path, output_dir):
    """Ejecuta el pipeline de limpieza + generacion Little_R (modulos modulares)."""
    logger.info(f"Paso 1: Procesando JSON: {json_path}")

    cleaner = ObservacionesCleaner(str(output_dir))
    df = cleaner.procesar_json(str(json_path))
    fecha = df["fecha"].iloc[0].replace("-", "")
    hora = df["hora"].iloc[0].replace(":", "")
    timestamp = f"{fecha}_{hora}"

    # Guardar CSV
    csv_path = str(output_dir / f"datos_validados_{timestamp}.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"  CSV generado: {csv_path}")

    logger.info("Paso 2: Generando Little_R...")
    output_littler = str(output_dir / f"littler_{timestamp}.txt")
    writer = LittleRWriter(config_estaciones_path=str(ESTACIONES_JSON))
    littler_path, num_obs = writer.generar_littler(df, output_path=output_littler)
    logger.info(f"  Little_R generado: {littler_path} ({num_obs} observaciones)")

    return littler_path, timestamp, df


def generar_obsdomain(df, output_dir, run_dir, no_copiar=False):
    """Convierte el DataFrame validado a OBS_DOMAIN101 y lo copia al directorio de corrida."""
    logger.info("Paso 3: Generando OBS_DOMAIN101...")
    obsdomain_path = str(output_dir / "OBS_DOMAIN101")

    writer = ObsNudWriter(config_estaciones_path=str(ESTACIONES_JSON))
    writer.generar_desde_dataframe(df, output_path=obsdomain_path)
    logger.info(f"  OBS_DOMAIN101 generado: {obsdomain_path}")

    if not no_copiar:
        # Copiar al directorio de corrida de WRF
        run_dir = Path(run_dir or LOCAL_WRF_DIR)
        run_dir.mkdir(parents=True, exist_ok=True)
        ok = copiar_archivo(obsdomain_path, run_dir / "OBS_DOMAIN101")
        if ok:
            logger.info(f"  Copiado a {run_dir / 'OBS_DOMAIN101'}")
        else:
            logger.warning("  No se pudo copiar el OBS_DOMAIN101")
            return None

    return obsdomain_path


def copiar_namelist(namelist_path, run_dir):
    """Copia namelist.input al directorio de corrida local."""
    run_dir = Path(run_dir or LOCAL_WRF_DIR)
    logger.info(f"  Copiando namelist a {run_dir / 'namelist.input'}")
    return copiar_archivo(namelist_path, run_dir / "namelist.input")


def ejecutar_preflight(obs_json, obsdomain, namelist, start_dt=None, caso="", config_path=None):
    """Ejecuta los chequeos previos a WRF (Sección 2.2) y los registra en el log.

    Devuelve (informe, ok): ok=False si existe algún chequeo BLOQUEANTE,
    en cuyo caso el pipeline debe detenerse sin ejecutar wrf.exe."""
    informe = correr_preflight_observaciones(
        obs_json=Path(obs_json),
        obsdomain=Path(obsdomain),
        namelist=Path(namelist),
        start_dt=start_dt,
        caso=caso,
        config_path=Path(config_path) if config_path else None,
    )
    logger.info("=== PREFLIGHT ===")
    for line in informe.resumen_log().splitlines():
        logger.info(f"  {line}")
    return informe, informe.puede_ejecutar


def ejecutar_real(run_dir=None, timeout=7200, mpirun=None, np=None):
    """Ejecuta real.exe delegando en WRFRunner (src/modelo/wrf_runner.py).

    np=1 (default) ejecuta el binario directo (un solo proceso, como el setup operativo)."""
    runner = WRFRunner(run_dir=run_dir or LOCAL_WRF_DIR,
                       env_bash=WRF_ENV_BASH, mpirun=mpirun or MPIRUN,
                       np=np or WRF_NP, timeout=timeout)
    return runner.ejecutar_real()


def ejecutar_wrf(run_dir=None, run_label="nudged", timeout=7200, mpirun=None, np=None, reintentos=5):
    """Ejecuta wrf.exe delegando en WRFRunner (src/modelo/wrf_runner.py).

    run_label: etiqueta 'nudged'/'control' (solo informativa).
    reintentos: si wrf.exe aborta (SIGSEGV intermitente con obs nudging), se limpia
    el run dir y se reintenta; 0 = un solo intento."""
    runner = WRFRunner(run_dir=run_dir or LOCAL_WRF_DIR,
                       env_bash=WRF_ENV_BASH, mpirun=mpirun or MPIRUN,
                       np=np or WRF_NP, timeout=timeout, reintentos=reintentos)
    return runner.ejecutar_wrf(nudged=(run_label != "control"), run_label=run_label)


def copiar_wrfout(run_dir, dest_dir, valid_time):
    """Copia wrfouts locales del directorio de corrida a un directorio de resultados."""
    run_dir = Path(run_dir or LOCAL_WRF_DIR)
    logger.info(f"  Copiando wrfout desde {run_dir} a {dest_dir}")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    wrfouts = sorted(run_dir.glob("wrfout_d01_*"))
    if not wrfouts:
        logger.warning("  No se encontraron wrfout en el directorio de corrida")
        return False

    for src in wrfouts:
        dest_path = dest_dir / src.name
        shutil.copy2(src, dest_path)
        logger.info(f"    {src.name}")
    return True


def run_valida_wrf(nudged_dir, control_dir, output_dir, valid_time, obs_json, label="",
                   run_dir=None, valid_times=None):
    """Ejecuta valida_wrf.py localmente con el python del entorno de validacion.

    Si valid_times tiene mas de un tiempo, genera el informe de evolucion del
    nudging (gráfico 00Z-06Z-12Z) ademas de las tablas por horario."""
    logger.info("Paso: Ejecutando validacion (local)...")

    valida_script_local = str(Path(__file__).parent / "src" / "validacion" / "valida_wrf_cli.py")
    estaciones_json_local = str(ESTACIONES_JSON)

    cmd = [
        VALIDATION_PYTHON, valida_script_local,
        "--nudged-dir", str(nudged_dir),
        "--control-dir", str(control_dir),
        "--output-dir", str(output_dir),
        "--estaciones-json", estaciones_json_local,
    ]
    if valid_times and len(valid_times) > 1:
        cmd += ["--valid-times", ",".join(valid_times)]
    else:
        cmd += ["--valid-time", valid_time]
    if obs_json:
        cmd += ["--obs-json", str(obs_json)]
    if label:
        cmd += ["--label", label]

    logger.info(f"  Ejecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        # valida_wrf_cli.py imprime sus errores controlados (ej. sin obs en
        # la ventana) por stdout, no por stderr; mostrar ambos para no
        # perder el mensaje.
        detalle = result.stderr.strip() or result.stdout.strip()
        logger.error(f"  Error en validacion (codigo {result.returncode}): {detalle[-500:]}")
        return False
    for line in result.stdout.splitlines()[-15:]:
        logger.info(f"  {line}")
    return True


def pipeline(args):
    """Ejecuta el pipeline completo."""
    case = args.case
    date_str = args.date
    hour_str = args.hour
    valid_time = f"{date_str}_{hour_str}:00"
    run_dir = Path(args.run_dir)
    try:
        start_dt = datetime.strptime(f"{date_str} {hour_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        start_dt = None
        logger.warning("No se pudo parsear la fecha de inicio, se usan fechas del namelist")

    # Directorios
    case_dir = RESULTS_DIR / f"{date_str}_{hour_str.replace(':', '')}z" / case
    nudged_dir = case_dir / "nudged"
    control_dir = case_dir / "control"
    obsdomain_dir = case_dir / "input"
    case_dir.mkdir(parents=True, exist_ok=True)
    obsdomain_dir.mkdir(parents=True, exist_ok=True)

    # Verificar directorio de corrida local
    run_ok = check_run_dir(run_dir)
    if not run_ok and not args.prepare_only and not args.validate_only:
        logger.error(f"Directorio de corrida no disponible: {run_dir}")
        return 1
    if run_ok:
        logger.info(f"Directorio de corrida OK: {run_dir}")

    # === PASOS 1-3: Generar OBS_DOMAIN101 ===
    if not args.validate_only:
        littler_path, timestamp, df = generar_littler_desde_json(args.json, obsdomain_dir)
        obsdomain = generar_obsdomain(df, obsdomain_dir, run_dir, args.prepare_only)

        if obsdomain is None and not args.prepare_only:
            logger.error("Fallo la generacion de OBS_DOMAIN101")
            return 1

        if args.prepare_only:
            logger.info(f"Material listo en {obsdomain_dir}")
            logger.info(f"  Little_R: {littler_path}")
            logger.info(f"  OBS_DOMAIN101: {obsdomain}")
            logger.info("Modo --prepare-only: fin.")
            return 0

    # === PASOS 4-7: Corrida NUDGED ===
    if not args.skip_wrf and not args.validate_only:
        logger.info("=" * 60)
        logger.info("CORRIDA NUDGED (obs_nudge_opt=1)")
        logger.info("=" * 60)

        namelist_nudged = case_dir / "namelist_nudged.input"
        coefs = {}
        if args.obs_coef_wind is not None:
            coefs["obs_coef_wind"] = args.obs_coef_wind
        if args.obs_coef_temp is not None:
            coefs["obs_coef_temp"] = args.obs_coef_temp
        if args.obs_coef_mois is not None:
            coefs["obs_coef_mois"] = args.obs_coef_mois
        if args.obs_twindo is not None:
            coefs["obs_twindo"] = args.obs_twindo

        preparar_namelist(args.namelist, 1, namelist_nudged, start_dt=start_dt, **coefs)

        # === PREFLIGHT: validar OBS_DOMAIN101 y namelist antes de ejecutar wrf.exe ===
        if not args.skip_preflight:
            informe_preflight, preflight_ok = ejecutar_preflight(
                args.json, obsdomain_dir / "OBS_DOMAIN101", namelist_nudged,
                start_dt=start_dt, caso=case,
                config_path=args.preflight_config,
            )
            informe_preflight.guardar(case_dir / f"preflight_{case}.json")
            if not preflight_ok:
                logger.error("PREFLIGHT BLOQUEANTE: no se ejecuta wrf.exe. Corregir los chequeos indicados.")
                return 1
            logger.info("PREFLIGHT OK: se procede con la corrida nudgeada.")
        else:
            logger.warning("PREFLIGHT omitido (--skip-preflight)")

        copiar_namelist(namelist_nudged, run_dir)

        if args.run_real:
            if not ejecutar_real(run_dir, args.wrf_timeout, args.mpirun, args.np):
                logger.error("real.exe fallido")
                return 1

        if not ejecutar_wrf(run_dir, "nudged", args.wrf_timeout, args.mpirun, args.np):
            logger.error("Corrida nudged fallida")
            return 1
        copiar_wrfout(run_dir, nudged_dir, valid_time)

        # Copiar wrfout al subdirectorio nudged/ del directorio de corrida para validacion
        subprocess.run(
            ["bash", "-lc",
             f"mkdir -p {run_dir}/nudged && cp {run_dir}/wrfout_d01* {run_dir}/nudged/"],
            capture_output=True, text=True, timeout=60,
        )

    # === PASOS 8-11: Corrida CONTROL ===
    if not args.skip_wrf and not args.validate_only and not args.skip_control:
        logger.info("=" * 60)
        logger.info("CORRIDA CONTROL (obs_nudge_opt=0)")
        logger.info("=" * 60)

        # Si ya existe control de este caso, preguntar
        if control_dir.exists() and list(control_dir.glob("wrfout_d01*")):
            logger.info(f"  Control ya existe en {control_dir}, reutilizando")
        else:
            namelist_control = case_dir / "namelist_control.input"
            preparar_namelist(args.namelist, 0, namelist_control, start_dt=start_dt)
            copiar_namelist(namelist_control, run_dir)

            # Si venimos de nudged, reiniciar con wrfinput (sin nudging previo)
            # Limpiar rsl* para no confundir
            subprocess.run(
                ["bash", "-lc", f"cd {run_dir} && rm -f rsl.*"],
                capture_output=True, text=True, timeout=30,
            )

            if not ejecutar_wrf(run_dir, "control", args.wrf_timeout, args.mpirun, args.np):
                logger.error("Corrida control fallida")
                return 1
            copiar_wrfout(run_dir, control_dir, valid_time)
            # Copiar wrfout al subdirectorio control/ del directorio de corrida
            subprocess.run(
                ["bash", "-lc",
                 f"mkdir -p {run_dir}/control && cp {run_dir}/wrfout_d01* {run_dir}/control/"],
                capture_output=True, text=True, timeout=60,
            )

    # === PASO 12: Validacion ===
    if args.validate_only:
        # Verificar que hay wrfout locales
        n_nudged = len(list((run_dir / "nudged").glob("wrfout_d01*"))) if (run_dir / "nudged").exists() else 0
        n_control = len(list((run_dir / "control").glob("wrfout_d01*"))) if (run_dir / "control").exists() else 0
        if n_nudged == 0:
            logger.error(f"No hay wrfout en {run_dir}/nudged/")
            return 1
        if n_control == 0:
            logger.error(f"No hay wrfout en {run_dir}/control/")
            return 1
        logger.info(f"  Local: {n_nudged} nudged / {n_control} control wrfout encontrados")

    # Para validar necesitamos el python con xarray
    if not Path(VALIDATION_PYTHON).exists():
        logger.error(f"Python de validacion no encontrado: {VALIDATION_PYTHON}")
        logger.error("Ajusta VALIDATION_PYTHON (env var) o crea el entorno con xarray.")
        return 1
    else:
        # Validacion multi-temporal (00Z, 06Z, 12Z) si se pidio; si no, solo valid_time
        valid_times = None
        if args.valid_times:
            tiempos = [t.strip() for t in args.valid_times.split(",") if t.strip()]
            # Completar con fecha si vienen como solo hora (HH:MM:SS)
            if date_str := getattr(args, "date", None):
                tiempos = [
                    t if "_" in t else f"{date_str}_{t}" for t in tiempos
                ]
            valid_times = tiempos
        valid_ok = run_valida_wrf(
            nudged_dir, control_dir, case_dir,
            valid_time, args.json, args.label, run_dir, valid_times,
        )
    if valid_ok:
        logger.info(f"Pipeline completo. Resultados en {case_dir}")
    else:
        logger.warning(f"Validacion con errores. Resultados parciales en {case_dir}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline WRF: Little_R -> OBS_DOMAIN101 -> wrf.exe -> Validacion (nativo, sin Docker)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Ciclo completo
  python pipeline_wrf.py --date 2026-05-25 --hour 21:00 --json data/raw/ecowitt_todos_20260525_2059.json --case base

  # Sensibilidad
  python pipeline_wrf.py --date 2026-05-25 --hour 21:00 --json data/raw/ecowitt_todos_20260525_2059.json --case coef0001 --obs-coef-wind 0.0001 --obs-coef-temp 0.0001 --obs-coef-mois 0.0001

  # Solo preparar archivos (sin WRF)
  python pipeline_wrf.py --date 2026-05-25 --hour 21:00 --json ... --case base --prepare-only

  # Solo validar corridas existentes
  python pipeline_wrf.py --date 2026-05-25 --hour 21:00 --case base --validate-only

  # Con real.exe (genera wrfinput/wrfbdy desde met_em)
  python pipeline_wrf.py --date 2026-05-25 --hour 21:00 --json ... --case base --run-real
        """
    )

    parser.add_argument("--date", "-d", required=True,
                        help="Fecha en formato YYYY-MM-DD")
    parser.add_argument("--hour", "-t", default="21:00",
                        help="Hora UTC en formato HH:MM (default: 21:00)")
    parser.add_argument("--json", "-j", default=None,
                        help="Ruta al JSON crudo de estaciones (en data/raw/)")
    parser.add_argument("--case", "-c", default="default",
                        help="Nombre del caso (ej: base, coef0001, twindo05)")
    parser.add_argument("--namelist", "-n",
                        default=Path(__file__).parent / "namelist.input",
                        help="Ruta al namelist.input base (default: ./namelist.input)")
    parser.add_argument("--label", default="",
                        help="Etiqueta opcional para graficos")

    # Modos
    parser.add_argument("--prepare-only", action="store_true",
                        help="Solo generar OBS_DOMAIN101, no correr WRF")
    parser.add_argument("--skip-wrf", action="store_true",
                        help="Saltar corridas WRF (solo validar si ya existen)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Solo ejecutar validacion sobre datos existentes")
    parser.add_argument("--skip-control", action="store_true",
                        help="Saltar corrida control (si ya existe)")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Omitir los chequeos previos a WRF (preflight)")
    parser.add_argument("--preflight-config", default=None,
                        help="Ruta al JSON de umbrales del preflight (default: config/preflight_config.json)")

    # Configuracion nativa
    parser.add_argument("--run-dir", default=str(LOCAL_WRF_DIR),
                        help=f"Directorio de corrida de WRF (default: {LOCAL_WRF_DIR})")
    parser.add_argument("--mpirun", default=MPIRUN,
                        help=f"Ruta a mpirun (default: {MPIRUN})")
    parser.add_argument("--np", default=WRF_NP,
                        help=f"Procesos MPI para real/wrf.exe; 1 = un proceso (default: {WRF_NP})")
    parser.add_argument("--run-real", action="store_true",
                        help="Ejecutar real.exe antes de wrf.exe (si faltan wrfinput/wrfbdy)")

    # Parametros de sensibilidad
    parser.add_argument("--obs-coef-wind", type=float, default=None,
                        help="obs_coef_wind (default: usar valor del namelist)")
    parser.add_argument("--obs-coef-temp", type=float, default=None,
                        help="obs_coef_temp (default: usar valor del namelist)")
    parser.add_argument("--obs-coef-mois", type=float, default=None,
                        help="obs_coef_mois (default: usar valor del namelist)")
    parser.add_argument("--obs-twindo", type=float, default=None,
                        help="obs_twindo en horas (default: usar valor del namelist)")

    # Timeout
    parser.add_argument("--wrf-timeout", type=int, default=7200,
                        help="Timeout para wrf.exe en segundos (default: 7200 = 2h)")

    # Validacion multi-temporal
    parser.add_argument("--valid-times", default=None,
                        help="Tiempos de validacion separados por coma (default: solo el tiempo final). "
                             "Ej: 00:00:00,06:00:00,12:00:00 genera informe de evolucion del nudging.")

    args = parser.parse_args()

    # Validar
    if args.validate_only and args.prepare_only:
        parser.error("--validate-only y --prepare-only son mutuamente excluyentes")
    if args.skip_wrf and args.prepare_only:
        parser.error("--skip-wrf y --prepare-only son mutuamente excluyentes")

    # Si se paso --json y es ruta relativa, resolver contra CWD
    if args.json:
        p = Path(args.json)
        if not p.is_absolute():
            p = Path.cwd() / args.json
            args.json = str(p)
        if not Path(args.json).exists():
            parser.error(f"No se encuentra --json: {args.json}")

    if not args.validate_only and not args.json:
        parser.error("Se requiere --json (a menos que se use --validate-only)")

    return pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
