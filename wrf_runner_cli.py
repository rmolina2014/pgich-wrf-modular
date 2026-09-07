"""Runner CLI aislado para la corrida WRF desde la app Streamlit.

Ejecutar la corrida WRF (prepare -> real -> nudged -> control) en un proceso
Python limpio y separado del servidor Streamlit. Esto evita el segfault
intermitente de wrf.exe con obs nudging observable cuando corre dentro del
proceso streamlit persistente (en un proceso fresco la corrida es estable).

Uso:
    python wrf_runner_cli.py --json data/raw/obs_flat_20260813.json \
        --fecha 2026-08-13 --hora 00:00 --caso base \
        [--namelist ...] [--run-real] [--skip-control]

Salida: el progreso se escribe a stdout con marcadores de estado:
    __NUDGED_OK__ / __NUDGED_FAIL__
    __CONTROL_OK__ / __CONTROL_FAIL__
Codigo de salida != 0 si la corrida nudged o control falla.
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_wrf as pw

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("wrf_runner_cli")


def argumentos():
    p = argparse.ArgumentParser(description="Runner aislado de corrida WRF")
    p.add_argument("--json", required=True, help="Ruta al JSON crudo de observaciones")
    p.add_argument("--fecha", required=True, help="Fecha YYYY-MM-DD (inicio de corrida)")
    p.add_argument("--hora", default="00:00", help="Hora UTC HH:MM")
    p.add_argument("--caso", default="base", help="Nombre del caso")
    p.add_argument("--namelist", default=str(pw.PROJECT_DIR.parent / "namelist.input"),
                   help="Ruta al namelist.input base")
    p.add_argument("--run-real", action="store_true",
                   help="Regenerar wrfinput/wrfbdy con real.exe antes de wrf.exe")
    p.add_argument("--skip-control", action="store_true",
                   help="Saltar la corrida control (obs_nudge_opt=0)")
    return p.parse_args()


def main():
    args = argumentos()

    try:
        start_dt = datetime.strptime(f"{args.fecha} {args.hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        start_dt = None
        logger.warning("No se pudo parsear la fecha de inicio; se usan las fechas del namelist")

    run_dir = pw.LOCAL_WRF_DIR
    case_dir = pw.RESULTS_DIR / f"{args.fecha}_{args.hora.replace(':', '')}z" / args.caso
    obsdomain_dir = case_dir / "input"
    nudged_dir = case_dir / "nudged"
    control_dir = case_dir / "control"
    obsdomain_dir.mkdir(parents=True, exist_ok=True)

    # PASOS 1-3: Little_R + OBS_DOMAIN101
    try:
        littler_path, timestamp, df = pw.generar_littler_desde_json(args.json, obsdomain_dir)
        obsdomain = pw.generar_obsdomain(df, obsdomain_dir, run_dir, False)
        if obsdomain is None:
            print("__PREP_FAIL__")
            return 1
        print(f"__PREP_OK__ Little_R={littler_path} OBS={obsdomain}", flush=True)
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo la preparacion de OBS_DOMAIN101: %s", exc)
        print("__PREP_FAIL__")
        return 1

    # PASO: real.exe (opcional) - solo si faltan wrfinput/wrfbdy validos
    if args.run_real:
        wi = run_dir / "wrfinput_d01"
        wb = run_dir / "wrfbdy_d01"
        tienen_inputs = (
            wi.exists() and wb.exists()
            and wi.stat().st_size > 0 and wb.stat().st_size > 0
        )
        if tienen_inputs:
            logger.info(
                "Paso: wrfinput_d01/wrfbdy_d01 ya existen y son validos; "
                "se reutilizan (se omite real.exe)."
            )
            print("__REAL_OK__ (reusados)", flush=True)
        else:
            logger.info("Paso: real.exe (regenera wrfinput/wrfbdy)...")
            if not pw.ejecutar_real(run_dir):
                print("__REAL_FAIL__")
                return 1
            print("__REAL_OK__", flush=True)

    # PASO: NUDGED (obs_nudge_opt=1)
    namelist_nudged = case_dir / "namelist_nudged.input"
    pw.preparar_namelist(args.namelist, 1, str(namelist_nudged), start_dt=start_dt)
    pw.copiar_namelist(str(namelist_nudged), run_dir)
    logger.info("Paso: wrf.exe nudged...")
    ok_nudged = pw.ejecutar_wrf(run_dir, "nudged", reintentos=5)
    if ok_nudged:
        pw.copiar_wrfout(run_dir, nudged_dir, f"{args.fecha}_{args.hora}:00")
        print("__NUDGED_OK__", flush=True)
    else:
        print("__NUDGED_FAIL__", flush=True)
        return 1

    # PASO: CONTROL (obs_nudge_opt=0)
    if not args.skip_control:
        namelist_control = case_dir / "namelist_control.input"
        pw.preparar_namelist(args.namelist, 0, str(namelist_control), start_dt=start_dt)
        pw.copiar_namelist(str(namelist_control), run_dir)
        logger.info("Paso: wrf.exe control...")
        ok_control = pw.ejecutar_wrf(run_dir, "control", reintentos=5)
        if ok_control:
            pw.copiar_wrfout(run_dir, control_dir, f"{args.fecha}_{args.hora}:00")
            print("__CONTROL_OK__", flush=True)
        else:
            print("__CONTROL_FAIL__", flush=True)
            return 1

    print("__RUNNER_DONE__", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
