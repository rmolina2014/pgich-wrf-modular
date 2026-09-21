"""Corrección aditiva por estación del sesgo sistemático de PSFC (mejora 3.5).

El informe_mejoras_f4 (hallazgo 3.5) documenta un sesgo sistemático de PSFC de
~-30 a -40 hPa entre WRF y las estaciones (con r estable 0.86-0.88 en todos los
casos). Como el sesgo es predecible por estación, se corrige en post-proceso:

  1. Se estima el bias medio (modelo - obs) de PSFC por estación sobre el ciclo.
  2. Se resta ese bias a los valores modelados (nudged y control) en las estaciones.
  3. Se recalculan las métricas de PSFC antes/después de la corrección.

Uso como script:
    python src/validacion/correccion_psfc.py \
        --nudged-dir results/<ciclo>/<caso>/nudged \
        --control-dir results/<ciclo>/<caso>/control \
        --obs-json data/raw/obs_flat_<fecha>.json \
        --output results/<ciclo>/<caso> \
        [--estaciones-json config/estaciones.json] [--ventana-min 30]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    from .valida_wrf_cli import cargar_estaciones_desde_json, load_run
    from .metrics import metricas_par
except ImportError:  # invocación como script
    from valida_wrf_cli import cargar_estaciones_desde_json, load_run
    from metrics import metricas_par


def _interp_psfc_por_estacion(wrfout_data, stations):
    """Devuelve {estacion: psfc_pa} interpolando PSFC para cada estación."""
    return {s["name"]: s["psfc"] for s in wrfout_data} if wrfout_data else {}


def estimar_bias_psfc(nudged_dir, obs_json, estaciones_json=None, ventana_min=30):
    """Estima el bias por estación (modelo nudged - obs) de PSFC sobre el ciclo.

    Devuelve (bias_por_estacion, detalles) donde bias_por_estacion es
    {estacion: {"bias_pa": float, "n": int}}."""
    nudged_dir = Path(nudged_dir)
    wrfouts = sorted(nudged_dir.glob("wrfout_d01_*"))
    acum = {}
    detalles = []
    for wrfout in wrfouts:
        vt_full = wrfout.name
        vt_clean = vt_full.replace("wrfout_d01_", "")
        stations = cargar_estaciones_desde_json(obs_json, estaciones_json,
                                                valid_time=vt_full, ventana_min=ventana_min)
        if not stations:
            continue
        data = load_run(nudged_dir, vt_full, stations)
        if data is None:
            continue
        for s in stations:
            if s["psfc"] is None:
                continue
            mod = next((d["psfc"] for d in data if d), None) if data else None
            # load_run devuelve una lista en el mismo orden que stations
            for i, st in enumerate(stations):
                if st["name"] != s["name"]:
                    continue
                mod = data[i]["psfc"]
                break
            if mod is None or mod != mod:
                continue
            bias = mod - s["psfc"]  # Pa
            e = acum.setdefault(s["name"], {"bias_pa": 0.0, "n": 0})
            e["bias_pa"] += bias
            e["n"] += 1
            detalles.append({"estacion": s["name"], "tiempo": vt_clean,
                             "obs_pa": s["psfc"], "mod_pa": mod, "bias_pa": bias})
    for e in acum.values():
        e["bias_pa"] = e["bias_pa"] / e["n"] if e["n"] else 0.0
    return acum, detalles


def metricas_psfc_pre_post(nudged_dir, control_dir, obs_json, bias_por_estacion,
                           estaciones_json=None, ventana_min=30):
    """Métricas de PSFC (nudged y control) antes/después de la corrección aditiva.

    Devuelve dict con agregado por grupo: {"nudged_raw": {...}, "nudged_corregido": {...},
    "control_raw": {...}, "control_corregido": {...}} usando pares obs-modelo de
    todas las estaciones y tiempos."""
    nudged_dir = Path(nudged_dir)
    control_dir = Path(control_dir)
    wrfouts = sorted(nudged_dir.glob("wrfout_d01_*"))

    grupos = {"nudged_raw": [], "nudged_corregido": [],
              "control_raw": [], "control_corregido": []}
    for wrfout in wrfouts:
        vt_full = wrfout.name
        stations = cargar_estaciones_desde_json(obs_json, estaciones_json,
                                                valid_time=vt_full, ventana_min=ventana_min)
        if not stations:
            continue
        d_n = load_run(nudged_dir, vt_full, stations)
        d_c = load_run(control_dir, vt_full, stations)
        if d_n is None or d_c is None:
            continue
        for i, s in enumerate(stations):
            if s["psfc"] is None:
                continue
            obs = s["psfc"]
            mod_n = d_n[i]["psfc"]
            mod_c = d_c[i]["psfc"]
            b = bias_por_estacion.get(s["name"], {}).get("bias_pa", 0.0)
            grupos["nudged_raw"].append((obs, mod_n))
            grupos["nudged_corregido"].append((obs, mod_n - b))
            if mod_c == mod_c:
                grupos["control_raw"].append((obs, mod_c))
                grupos["control_corregido"].append((obs, mod_c - b))

    resultado = {}
    for nombre, pares in grupos.items():
        if len(pares) < 2:
            resultado[nombre] = {"n": 0}
            continue
        obs = np.array([p[0] for p in pares], dtype=float)
        mod = np.array([p[1] for p in pares], dtype=float)
        m = metricas_par(mod, obs)
        resultado[nombre] = {
            "n": m["n"], "bias_hpa": m["bias"] / 100.0,
            "mae_hpa": m["mae"] / 100.0, "rmse_hpa": m["rmse"] / 100.0,
            "r": m["r"],
            "bias_ci_hpa": [v / 100.0 if v == v else float("nan") for v in m["bias_ci"]],
            "rmse_ci_hpa": [v / 100.0 if v == v else float("nan") for v in m["rmse_ci"]],
        }
    return resultado


def principal():
    p = argparse.ArgumentParser(description="Corrección aditiva de sesgo de PSFC por estación (mejora 3.5).")
    p.add_argument("--nudged-dir", required=True)
    p.add_argument("--control-dir", required=True)
    p.add_argument("--obs-json", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--estaciones-json", default=None)
    p.add_argument("--ventana-min", type=int, default=30)
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    bias, detalles = estimar_bias_psfc(args.nudged_dir, args.obs_json,
                                       args.estaciones_json, args.ventana_min)
    bias_path = out / "bias_psfc_por_estacion.json"
    with open(bias_path, "w", encoding="utf-8") as f:
        json.dump(bias, f, ensure_ascii=False, indent=2)
    print(f"-> {bias_path}")

    resumen = metricas_psfc_pre_post(args.nudged_dir, args.control_dir, args.obs_json,
                                     bias, args.estaciones_json, args.ventana_min)
    resumen_path = out / "correccion_psfc.json"
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump({"bias_por_estacion": bias, "metricas": resumen,
                   "n_pares": len(detalles)}, f, ensure_ascii=False, indent=2)
    print(f"-> {resumen_path}")

    L = []
    L.append("=" * 78)
    L.append("CORRECCION ADITIVA DE PSFC POR ESTACION (mejora 3.5 informe_mejoras_f4)")
    L.append("=" * 78)
    L.append("")
    L.append("Bias medio estimado (modelo nudged - obs), en hPa:")
    L.append(f"{'Estación':<20}{'bias_hPa':>10}{'n':>6}")
    L.append("-" * 36)
    for nombre in sorted(bias, key=lambda k: -abs(bias[k]["bias_pa"])):
        b = bias[nombre]
        L.append(f"{nombre:<20}{b['bias_pa'] / 100.0:>10.1f}{b['n']:>6}")
    L.append("")
    L.append("Metricas de PSFC (hPa), antes y despues de restar el bias por estacion:")
    L.append(f"{'Grupo':<20}{'n':>5}{'RMSE':>8}{'MAE':>8}{'Bias':>8}{'r':>7}")
    L.append("-" * 56)
    for nombre in ("nudged_raw", "nudged_corregido", "control_raw", "control_corregido"):
        m = resumen.get(nombre, {})
        n = m.get("n", 0)
        if n == 0:
            L.append(f"{nombre:<20}{0:>5}   (sin pares)")
            continue
        L.append(f"{nombre:<20}{n:>5}{m['rmse_hpa']:>8.2f}{m['mae_hpa']:>8.2f}"
                 f"{m['bias_hpa']:>8.2f}{m['r']:>7.3f}")
    L.append("")
    L.append("La correccion es aditiva y por estacion; se aplica solo en post-proceso")
    L.append("(no re-corta el modelo).")

    txt = out / "informe_correccion_psfc.txt"
    txt.write_text("\n".join(L), encoding="utf-8")
    print(f"-> {txt}")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(principal())