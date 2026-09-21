#!/usr/bin/env python3
"""Barrido automático de coeficientes de nudging (mejora 3.10 del informe_mejoras_f4).

Ejecuta el pipeline WRF para una serie de combinaciones de obs_coef_wind/temp/mois
(nudged + control la primera vez; luego reutiliza el control) y agrega un resumen
comparativo de RMSE T2/RH vs la combinación base.

Uso:
    python scripts/barrido_coefs.py -d 2026-07-31 -t 00:00 \\
        --json data/raw/obs_flat_20260731.json \\
        --valores 0.0001 0.0002 0.00005 \\
        --npm 2 --mpirun /usr/bin/mpirun

Opciones:
    --obs-coef-wind/temp/mois: listas separadas por coma (si todas tienen la misma
        longitud se combinan posición a posición; si no, producto cartesiano).
    --valores: aplicar la misma lista a los tres coeficientes (atajo).
    --dry-run: solo imprime los comandos.
"""

import argparse
import itertools
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
PIPELINE = ROOT / "pipeline_wrf.py"
RESULTADOS = ROOT / "results"
ESTADO_DIR = RESULTADOS / "casos_estudio"


def _pars_lista(s):
    return [v.strip() for v in s.split(",") if v.strip()]


def _combos(wind, temp, mois):
    if len(wind) == len(temp) == len(mois) and len(wind) > 1:
        return list(zip(wind, temp, mois))
    return [(w, t, m) for (w, t, m) in itertools.product(wind, temp, mois)]


def _leer_rmse_tabla(tabla_path, variable, tiempo_eta="Z"):
    """Extrae {nudged_rmse, control_rmse} de la última fila de la variable dada."""
    if not tabla_path.exists():
        return None
    with open(tabla_path, "r", encoding="utf-8") as f:
        tabla = json.load(f)
    for t in reversed(tabla.get("por_tiempo", [])):
        for r in t.get("rows", []):
            if r.get("var") == variable:
                return {"tiempo": t["tiempo"], "nudged_rmse": r.get("nudged_rmse"),
                        "control_rmse": r.get("control_rmse")}
    return None


def principal():
    p = argparse.ArgumentParser(description="Barrido de coeficientes de obs nudging.")
    p.add_argument("-d", "--date", required=True)
    p.add_argument("-t", "--hour", default="00:00")
    p.add_argument("-j", "--json", required=True)
    p.add_argument("--namelist", default=str(ROOT / "namelist.input"))
    p.add_argument("--caso-base", default="barrido")
    p.add_argument("--obs-coef-wind", default=None)
    p.add_argument("--obs-coef-temp", default=None)
    p.add_argument("--obs-coef-mois", default=None)
    p.add_argument("--valores", nargs="*", default=None,
                   help="Misma lista de coeficientes para los tres (atajo).")
    p.add_argument("--np", default="2")
    p.add_argument("--mpirun", default="/usr/bin/mpirun")
    p.add_argument("--run-real", action="store_true", help="Correr real.exe en el primer combo.")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.valores:
        wind = temp = mois = args.valores
    else:
        wind = _pars_lista(args.obs_coef_wind or "0.0001")
        temp = _pars_lista(args.obs_coef_temp or "0.0001")
        mois = _pars_lista(args.obs_coef_mois or "0.0001")

    combos = _combos(wind, temp, mois)
    if not combos:
        p.error("No hay combinaciones de coeficientes.")
    print(f"Combinaciones a evaluar: {len(combos)}")

    resumen = []
    for i, (w, t, m) in enumerate(combos):
        case = f"{args.caso_base}_w{w}_t{t}_m{m}"
        base_dir = RESULTADOS / f"{args.date}_{args.hour.replace(':', '')}z" / case
        cmd = [
            "python", str(PIPELINE),
            "-d", args.date, "-t", args.hour,
            "--json", args.json,
            "--case", case,
            "--namelist", args.namelist,
            "--obs-coef-wind", str(w),
            "--obs-coef-temp", str(t),
            "--obs-coef-mois", str(m),
            "--np", args.np,
            "--mpirun", args.mpirun,
            "--valid-times", "00:00:00,06:00:00,12:00:00",
            "--label", f"barrido_{i + 1}",
        ]
        if args.run_real and i == 0:
            cmd.append("--run-real")
        control_dir = base_dir / "control"
        if control_dir.exists() and any(control_dir.glob("wrfout_d01_*")):
            cmd.append("--skip-control")

        print(f"\n[{i + 1}/{len(combos)}] {case}  w={w} t={t} m={m}")
        if args.dry_run:
            print("  " + " ".join(cmd))
            continue

        log = ESTADO_DIR / f"barrido_{case}.log"
        ESTADO_DIR.mkdir(parents=True, exist_ok=True)
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run(cmd, cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT)
        print(f"  pipeline rc={r.returncode}  (log: {log})")
        if r.returncode != 0:
            resumen.append({"combo": [w, t, m], "rc": r.returncode, "t2": None})
            continue

        tabla = base_dir / "tabla_evolutiva.json"
        t2 = _leer_rmse_tabla(tabla, "T2 (K)")
        rh = _leer_rmse_tabla(tabla, "RH (%)")
        fila = {"combo": [w, t, m], "rc": 0, "t2": t2, "rh": rh}
        resumen.append(fila)
        print(f"  T2 @ {t2['tiempo'] if t2 else '-'}: nudged {t2['nudged_rmse'] if t2 else '-'}")

    if args.dry_run:
        return 0

    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    json_path = ESTADO_DIR / f"barrido_coefs_{args.date.replace('-', '')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"date": args.date, "hour": args.hour, "coefs": combos,
                   "resultados": resumen}, f, ensure_ascii=False, indent=2)

    L = []
    L.append("# Barrido de coeficientes de nudging")
    L.append("")
    L.append(f"Fecha: {args.date} {args.hour}Z | Coefs evaluados: {len(combos)}")
    L.append("")
    L.append("RMSE de T2 y RH en el último tiempo de validación, Nudged (N) vs Control (C):")
    L.append("")
    L.append("| combo (w/t/m) | tiempo | RMSE T2 N | RMSE T2 C | RMSE RH N | RMSE RH C |")
    L.append("|---------------|--------|-----------|-----------|-----------|-----------|")
    for fila in resumen:
        c = "/".join(fila["combo"])
        t2 = fila.get("t2") or {}
        rh = fila.get("rh") or {}
        t = t2.get("tiempo") or rh.get("tiempo") or "-"
        L.append(f"| {c} | {t} | {t2.get('nudged_rmse', '-'):.2f if isinstance(t2.get('nudged_rmse'), float) else '-'}"
                 f" | {t2.get('control_rmse', '-'):.2f if isinstance(t2.get('control_rmse'), float) else '-'}"
                 f" | {rh.get('nudged_rmse', '-'):.2f if isinstance(rh.get('nudged_rmse'), float) else '-'}"
                 f" | {rh.get('control_rmse', '-'):.2f if isinstance(rh.get('control_rmse'), float) else '-'} |")
    L.append("")
    md = ESTADO_DIR / f"barrido_coefs_{args.date.replace('-', '')}.md"
    md.write_text("\n".join(L), encoding="utf-8")
    print(f"\nResumen: {json_path}\n        {md}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())