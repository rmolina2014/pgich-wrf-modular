#!/usr/bin/env python3
"""Producto de pronóstico de los campos WRF (mejora 3.11 del informe_mejoras_f4).

El flujo automatizado llegaba hasta la validación; este script transforma los wrfout
de una corrida (nudged) en un producto visual de pronóstico: mapas por tiempo válido
de T2, RH, PSFC y viento a 10 m, con overlay de las observaciones de estaciones.

Uso:
    python scripts/generar_producto.py \
        --nudged-dir results/2026-07-31_0000z/caso1_zonda/nudged \
        --output results/2026-07-31_0000z/caso1_zonda/productos \
        [--obs-json data/raw/obs_flat_20260731.json] \
        [--estaciones-json config/estaciones.json] \
        [--valid-time 2026-07-31_12:00:00]   # opcional; default: todos los wrfout
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

README = """
Productos de pronóstico generados por scripts/generar_producto.py (mejora 3.11).
Por tiempo válido se genera una lámina con T2 (C), RH (%), PSFC (hPa) y viento a 10 m
(c) con barbs/densidad. Cuando se pasa --obs-json se superponen las observaciones de
las estaciones con su valor numerico.
"""


def _leer_primer_time(ds, var):
    data = ds[var].values
    if data.ndim == 3:
        data = data[0]
    if var in ("T2", "PSFC", "Q2"):
        data = np.squeeze(data)
    return data


def _t2_c(t2_k):
    return t2_k - 273.15


def _rh(ds, valid):
    q2 = ds["Q2"].values[0]
    t2 = ds["T2"].values[0]
    psfc = ds["PSFC"].values[0]
    es = 611.2 * np.exp(17.67 * (t2 - 273.15) / (t2 - 29.65))
    qs = 0.622 * es / (psfc - 0.378 * es)
    rh = (q2 / qs) * 100.0
    return np.clip(rh, 0, 100)


def _viento(ds):
    u = ds["U10"].values[0]
    v = ds["V10"].values[0]
    wspd = np.sqrt(u ** 2 + v ** 2)
    return u, v, wspd


def _cargar_obs(obs_json, estaciones_json, valid_time, ventana_min=30):
    if not obs_json or not valid_time:
        return []
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        from src.validacion.valida_wrf_cli import cargar_estaciones_desde_json
    except ImportError:
        from validacion.valida_wrf_cli import cargar_estaciones_desde_json
    stations = cargar_estaciones_desde_json(obs_json, estaciones_json,
                                            valid_time=valid_time, ventana_min=ventana_min)
    return [
        {"name": s["name"], "lat": s["lat"], "lon": s["lon"], "elev": s["elev"],
         "temp": s["temp"], "rh": s["rh"], "psfc": s["psfc"] / 100.0 if s["psfc"] else None,
         "speed": s["speed"], "dir": s["dir"]}
        for s in stations
    ]


def _panel_t2(ax, ds, obs_list, vt):
    t2 = _t2_c(ds["T2"].values[0])
    lon2d, lat2d = ds["XLONG"].values[0], ds["XLAT"].values[0]
    hgt = ds["HGT"].values[0]
    cf = ax.contourf(lon2d, lat2d, t2, levels=40, cmap="RdYlBu_r")
    ax.contour(lon2d, lat2d, hgt, levels=10, colors="grey", linewidths=0.4, alpha=0.5)
    ax.set_title(f"T2 (C) - {vt}", fontsize=11)
    for o in obs_list:
        if o["temp"] is not None:
            ax.plot(o["lon"], o["lat"], "ko", ms=6, mfc="none", zorder=5)
            ax.annotate(f"{o['temp'] - 273.15:.1f}", (o["lon"], o["lat"]),
                        textcoords="offset points", xytext=(6, 6), fontsize=7, zorder=6)
    _formato_ejes(ax, lon2d, lat2d)
    return cf


def _panel_rh(ax, ds, obs_list, vt):
    rh = _rh(ds, vt)
    lon2d, lat2d = ds["XLONG"].values[0], ds["XLAT"].values[0]
    cf = ax.contourf(lon2d, lat2d, rh, levels=20, cmap="BrBG")
    ax.set_title(f"RH (%) - {vt}", fontsize=11)
    for o in obs_list:
        if o["rh"] is not None:
            ax.plot(o["lon"], o["lat"], "ko", ms=6, mfc="none", zorder=5)
            ax.annotate(f"{o['rh']:.0f}", (o["lon"], o["lat"]),
                        textcoords="offset points", xytext=(6, 6), fontsize=7, zorder=6)
    _formato_ejes(ax, lon2d, lat2d)
    return cf


def _panel_psfc(ax, ds, obs_list, vt):
    psfc = ds["PSFC"].values[0] / 100.0
    lon2d, lat2d = ds["XLONG"].values[0], ds["XLAT"].values[0]
    cf = ax.contourf(lon2d, lat2d, psfc, levels=30, cmap="YlGnBu")
    ax.set_title(f"PSFC (hPa) - {vt}", fontsize=11)
    for o in obs_list:
        if o["psfc"] is not None:
            ax.plot(o["lon"], o["lat"], "ko", ms=6, mfc="none", zorder=5)
            ax.annotate(f"{o['psfc']:.1f}", (o["lon"], o["lat"]),
                        textcoords="offset points", xytext=(6, 6), fontsize=7, zorder=6)
    _formato_ejes(ax, lon2d, lat2d)
    return cf


def _panel_viento(ax, ds, obs_list, vt):
    u, v, wspd = _viento(ds)
    lon2d, lat2d = ds["XLONG"].values[0], ds["XLAT"].values[0]
    cf = ax.contourf(lon2d, lat2d, wspd, levels=25, cmap="Purples")
    stride = 7
    ax.barbs(lon2d[::stride, ::stride], lat2d[::stride, ::stride],
             u[::stride, ::stride], v[::stride, ::stride],
             length=4.5, alpha=0.8, linewidth=0.6)
    ax.set_title(f"Viento 10m (m/s) - {vt}", fontsize=11)
    for o in obs_list:
        if o["speed"] is not None:
            ax.plot(o["lon"], o["lat"], "ko", ms=6, mfc="none", zorder=5)
            ax.annotate(f"{o['speed']:.1f}", (o["lon"], o["lat"]),
                        textcoords="offset points", xytext=(6, 6), fontsize=7, zorder=6)
    _formato_ejes(ax, lon2d, lat2d)
    return cf


def _formato_ejes(ax, lon2d, lat2d):
    ax.set_xlim(lon2d.min(), lon2d.max())
    ax.set_ylim(lat2d.min(), lat2d.max())
    ax.set_xlabel("Longitud", fontsize=8)
    ax.set_ylabel("Latitud", fontsize=8)
    ax.tick_params(labelsize=7)


def principal():
    p = argparse.ArgumentParser(description="Producto de pronóstico a partir de wrfout (mejora 3.11).")
    p.add_argument("--nudged-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--obs-json", default=None)
    p.add_argument("--estaciones-json", default=None)
    p.add_argument("--valid-time", default=None,
                   help="Un tiempo válido (YYYY-MM-DD_HH:MM:SS); default: todos los wrfout.")
    args = p.parse_args()

    nudged = Path(args.nudged_dir)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "LEEME.txt").write_text(README, encoding="utf-8")

    wrfouts = sorted(nudged.glob("wrfout_d01_*"))
    if not wrfouts:
        print(f"No hay wrfout en {nudged}")
        return 1
    if args.valid_time:
        wrfouts = [Path(nudged) / f"wrfout_d01_{args.valid_time}" for w in [args.valid_time]
                   if (nudged / f"wrfout_d01_{args.valid_time}").exists()]
        if not wrfouts:
            print(f"No existe wrfout para {args.valid_time}")
            return 1

    for wrfout in wrfouts:
        vt = wrfout.name.replace("wrfout_d01_", "")
        obs = _cargar_obs(args.obs_json, args.estaciones_json, vt) if args.obs_json else []
        ds = xr.open_dataset(str(wrfout))
        fig, axes = plt.subplots(2, 2, figsize=(13, 10))
        fig.suptitle(f"WRF - San Juan 15 km - {vt}  [{'obs superpuestas' if obs else 'sin obs'}]",
                     fontsize=13, y=0.98)
        cf1 = _panel_t2(axes[0, 0], ds, obs, vt)
        cf2 = _panel_rh(axes[0, 1], ds, obs, vt)
        cf3 = _panel_psfc(axes[1, 0], ds, obs, vt)
        cf4 = _panel_viento(axes[1, 1], ds, obs, vt)
        for ax, cf in zip(axes.ravel(), (cf1, cf2, cf3, cf4)):
            fig.colorbar(cf, ax=ax, shrink=0.75, pad=0.03)
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        sub = out / vt.replace(":", "").replace("-", "")
        sub.mkdir(parents=True, exist_ok=True)
        dest = sub / f"producto_{vt.replace(':', '')}.png"
        fig.savefig(str(dest), dpi=140, bbox_inches="tight")
        plt.close(fig)
        ds.close()
        print(f"-> {dest}  (obs: {len(obs)})")

    (out / "indice.html").write_text(
        "<html><head><meta charset='utf-8'></head><body style='font-family:sans-serif'>"
        "<h1>Productos WRF - San Juan</h1><ul>"
        + "".join(f"<li><a href='{p.stem.replace(chr(95), chr(95))}.png'>ver</a> {p.name}</li>"
                  for p in sorted(out.glob("*/producto_*.png")))
        + "</ul></body></html>", encoding="utf-8")
    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())