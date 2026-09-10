#!/usr/bin/env python3
"""CLI independiente para correr el preflight de WRF (Sección 2.2 observaciones).

Uso:
    python src/preflight/cli.py \
        --obs-json data/raw/obs_flat_20260806.json \
        --obsdomain results/2026-08-06_0000z/sens_coef0001/input/OBS_DOMAIN101 \
        --namelist results/2026-08-06_0000z/sens_coef0001/namelist_nudged.input \
        --date 2026-08-06 --hour 00:00 --caso sens_coef0001
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.preflight.preflight import correr_preflight_observaciones

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("preflight.cli")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight de WRF: chequeos sobre las observaciones y OBS_DOMAIN101")
    parser.add_argument("--obs-json", required=True, help="JSON crudo de observaciones")
    parser.add_argument("--obsdomain", required=True, help="OBS_DOMAIN101 generado")
    parser.add_argument("--namelist", required=True, help="namelist.input preparado para la corrida")
    parser.add_argument("--date", "-d", help="Fecha de inicio en formato YYYY-MM-DD")
    parser.add_argument("--hour", "-t", default="00:00", help="Hora de inicio en HH:MM")
    parser.add_argument("--caso", default="", help="Nombre del caso (para el informe)")
    parser.add_argument("--config", default=None, help="Ruta al JSON de umbrales (config/preflight_config.json)")
    parser.add_argument("--output", "-o", default=None,
                        help="Ruta donde guardar el informe JSON (default: ./preflight_<caso>.json)")
    args = parser.parse_args()

    start_dt = None
    if args.date:
        try:
            start_dt = datetime.strptime(f"{args.date} {args.hour}", "%Y-%m-%d %H:%M")
        except ValueError:
            logger.warning("Fecha de inicio no parseable; se omite la cobertura temporal")

    informe = correr_preflight_observaciones(
        obs_json=Path(args.obs_json),
        obsdomain=Path(args.obsdomain),
        namelist=Path(args.namelist),
        start_dt=start_dt,
        caso=args.caso,
        config_path=Path(args.config) if args.config else None,
    )

    print(informe.resumen_log())

    output = Path(args.output) if args.output else Path(f"preflight_{args.caso or 'default'}.json")
    informe.guardar(output)

    if not informe.puede_ejecutar:
        logger.error("Preflight BLOQUEADO: no se debe ejecutar wrf.exe sin corregir los chequeos bloqueantes.")
        return 2
    logger.info("Preflight OK: se puede lanzar wrf.exe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())