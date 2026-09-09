import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from math import radians, sin, cos, atan2, sqrt
from datetime import datetime
import json
import argparse

def ruta_estaciones_json(estaciones_json=None):
    """Devuelve la ruta al catálogo unificado de estaciones (config/estaciones.json)."""
    if estaciones_json:
        return Path(estaciones_json)
    return Path(__file__).parent.parent.parent / "config" / "estaciones.json"


def cargar_metadatos_estaciones(estaciones_json=None):
    """Carga la red completa de estaciones desde el catálogo (sin valores de obs)."""
    with open(ruta_estaciones_json(estaciones_json), encoding="utf-8") as f:
        metadatos = json.load(f)
    return [
        {"name": nombre, "lat": meta.get("lat"), "lon": meta.get("lon"),
         "elev": meta.get("elev"), "temp": None, "rh": None, "psfc": None,
         "speed": None, "dir": None}
        for nombre, meta in metadatos.items()
    ]


def _parse_obs_dt(obs):
    fecha = str(obs.get("fecha", ""))
    hora = str(obs.get("hora", ""))
    if not fecha or not hora:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{fecha} {hora}", fmt)
        except ValueError:
            continue
    return None

def cargar_estaciones_desde_json(ruta_json, estaciones_json=None, valid_time=None, ventana_min=30):
    with open(ruta_json, encoding="utf-8") as f:
        raw = json.load(f)

    valid_dt = None
    if valid_time:
        base = valid_time.replace("wrfout_d01_", "")
        for fmt in ("%Y-%m-%d_%H:%M:%S", "%Y-%m-%d_%H:%M"):
            try:
                valid_dt = datetime.strptime(base, fmt)
                break
            except ValueError:
                continue

    if estaciones_json:
        ruta_meta = Path(estaciones_json)
    else:
        ruta_meta = ruta_estaciones_json()
    with open(ruta_meta) as f:
        metadatos = json.load(f)

    estaciones = []
    for obs in raw:
        nombre = obs.get("estacion")
        if not nombre or "error" in obs:
            continue
        if valid_dt is not None:
            obs_dt = _parse_obs_dt(obs)
            if obs_dt is None or abs((obs_dt - valid_dt).total_seconds()) > ventana_min * 60:
                continue
        meta = metadatos.get(nombre, {})
        temp_c = obs.get("temp")
        rh = obs.get("humedad")
        psfc_hpa = obs.get("presion_absoluta")
        speed = obs.get("viento")
        direcc = obs.get("direcc")

        estaciones.append({
            "name": nombre,
            "lat": meta.get("lat", 0.0),
            "lon": meta.get("lon", 0.0),
            "elev": meta.get("elev", 0.0),
            "temp": float(temp_c) + 273.15 if temp_c is not None else None,
            "rh": float(rh) if rh is not None else None,
            "psfc": float(psfc_hpa) * 100 if psfc_hpa is not None else None,
            "speed": float(speed) if speed is not None else None,
            "dir": float(direcc) if direcc is not None else None,
        })
    return estaciones

def obs_u_v(speed, direction):
    if speed is None or direction is None:
        return None, None
    rad = radians(direction)
    u = -speed * sin(rad)
    v = -speed * cos(rad)
    return u, v

def model_u_v_to_speed_dir(u, v):
    speed = sqrt(u**2 + v**2)
    dir = (270 - np.degrees(atan2(v, u))) % 360
    return speed, dir

def q2_to_rh(q2, t2, psfc):
    es = 611.2 * np.exp(17.67 * (t2 - 273.15) / (t2 - 29.65))
    qs = 0.622 * es / (psfc - 0.378 * es)
    rh = (q2 / qs) * 100
    return np.clip(rh, 0, 100)

def bilinear_interp(ds, var, lat, lon):
    lats = ds.XLAT.values[0]
    lons = ds.XLONG.values[0]
    data = ds[var].values[0]

    j = np.searchsorted(lats[:, 0], lat) - 1
    i = np.searchsorted(lons[0, :], lon) - 1

    j = max(0, min(j, lats.shape[0] - 2))
    i = max(0, min(i, lats.shape[1] - 2))

    lat_sw, lat_se = lats[j, i], lats[j, i+1]
    lat_nw, lat_ne = lats[j+1, i], lats[j+1, i+1]
    lon_sw, lon_se = lons[j, i], lons[j, i+1]
    lon_nw, lon_ne = lons[j+1, i], lons[j+1, i+1]

    lat_avg = (lat_sw + lat_se + lat_nw + lat_ne) / 4
    lon_avg = (lon_sw + lon_se + lon_nw + lon_ne) / 4

    lon_ref = lon_avg
    lat_ref = lat_avg
    dlon = np.cos(radians(lat_ref))
    dlat = 1.0

    x_sw = (lon_sw - lon_ref) * dlon
    x_se = (lon_se - lon_ref) * dlon
    x_nw = (lon_nw - lon_ref) * dlon
    x_ne = (lon_ne - lon_ref) * dlon
    y_sw = (lat_sw - lat_ref) * dlat
    y_se = (lat_se - lat_ref) * dlat
    y_nw = (lat_nw - lat_ref) * dlat
    y_ne = (lat_ne - lat_ref) * dlat
    xp = (lon - lon_ref) * dlon
    yp = (lat - lat_ref) * dlat

    c = np.array([x_sw, x_se, x_nw, x_ne])
    r = np.array([y_sw, y_se, y_nw, y_ne])
    v = np.array([data[j, i], data[j, i+1], data[j+1, i], data[j+1, i+1]])

    dist2 = (c - xp)**2 + (r - yp)**2
    dist2 = np.maximum(dist2, 1e-12)
    w = 1.0 / dist2
    return np.sum(w * v) / np.sum(w)

def interp_station(ds, s):
    lat, lon = s["lat"], s["lon"]
    t2 = bilinear_interp(ds, "T2", lat, lon)
    psfc = bilinear_interp(ds, "PSFC", lat, lon)
    q2 = bilinear_interp(ds, "Q2", lat, lon)
    u10 = bilinear_interp(ds, "U10", lat, lon)
    v10 = bilinear_interp(ds, "V10", lat, lon)
    hgt = bilinear_interp(ds, "HGT", lat, lon)
    rh = q2_to_rh(q2, t2, psfc)
    wspd, wdir = model_u_v_to_speed_dir(u10, v10)
    return {
        "t2": t2, "psfc": psfc, "q2": q2, "rh": rh,
        "u10": u10, "v10": v10, "wspd": wspd, "wdir": wdir, "hgt": hgt
    }

def load_run(subdir, valid_time, stations):
    path = subdir / valid_time
    if not path.exists():
        alt = subdir / f"{valid_time}:00"
        if alt.exists():
            path = alt
        else:
            print(f"  ERROR: No se encuentra wrfout para {valid_time} en {subdir}")
            return None
    print(f"  Leyendo {path}")
    ds = xr.open_dataset(str(path))
    results = []
    for s in stations:
        m = interp_station(ds, s)
        results.append(m)
    ds.close()
    return results

def metrics(obs, mod, name):
    mask = ~np.isnan(obs) & ~np.isnan(mod)
    if mask.sum() < 2:
        return {"n": 0, "bias": np.nan, "mae": np.nan, "rmse": np.nan, "r": np.nan}
    o = obs[mask]
    m = mod[mask]
    bias = np.mean(m - o)
    mae = np.mean(np.abs(m - o))
    rmse = np.sqrt(np.mean((m - o)**2))
    if np.std(o) > 0 and np.std(m) > 0:
        r = np.corrcoef(o, m)[0, 1]
    else:
        r = np.nan
    return {"n": int(mask.sum()), "bias": bias, "mae": mae, "rmse": rmse, "r": r}

def build_tables(nudged_data, control_data, stations):
    var_defs = [
        ("t2",      "T2 (K)",        lambda s: s["temp"]),
        ("psfc",    "PSFC (hPa)",    lambda s: s["psfc"] / 100.0 if s["psfc"] is not None else None),
        ("rh",      "RH (%)",        lambda s: s["rh"]),
        ("wspd",    "Wind (m/s)",    lambda s: s["speed"]),
    ]
    rows = []
    for key, label, obs_fun in var_defs:
        obs_vals = np.array([obs_fun(s) if obs_fun(s) is not None else np.nan for s in stations], dtype=float)
        ngt = np.array([d[key] for d in nudged_data], dtype=float)
        ctl = np.array([d[key] for d in control_data], dtype=float)
        if key == "psfc":
            ngt = ngt / 100.0
            ctl = ctl / 100.0
        m_n = metrics(obs_vals, ngt, f"Nudged {label}")
        m_c = metrics(obs_vals, ctl, f"Control {label}")
        rows.append({
            "var": label,
            "n": m_n["n"],
            "nudged_bias": m_n["bias"], "nudged_mae": m_n["mae"],
            "nudged_rmse": m_n["rmse"], "nudged_r": m_n["r"],
            "control_bias": m_c["bias"], "control_mae": m_c["mae"],
            "control_rmse": m_c["rmse"], "control_r": m_c["r"],
        })
    return rows

def plot_scatter(nudged_data, control_data, stations, output_dir, valid_time, label=""):
    def _obs_val(s, key):
        v = {"t2": s["temp"], "psfc": s["psfc"]/100.0 if s.get("psfc") is not None else None, "rh": s["rh"], "wspd": s["speed"]}[key]
        return np.nan if v is None else v

    var_defs = [("t2", "T2 (K)"), ("psfc", "PSFC (hPa)"), ("rh", "RH (%)"), ("wspd", "Wind (m/s)")]
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    suffix = f" {label}" if label else ""
    fig.suptitle(f"WRF vs Observaciones - San Juan {valid_time}{suffix}", fontsize=13, y=0.98)

    colors = ['#1f77b4', '#d62728']
    markers = ['Nudged', 'Control']

    for ax, (key, label_var) in zip(axes.flat, var_defs):
        obs = np.array([_obs_val(s, key) for s in stations], dtype=float)
        ngt = np.array([d[key] for d in nudged_data], dtype=float)
        ctl = np.array([d[key] for d in control_data], dtype=float)
        if key == "psfc":
            ngt = ngt / 100.0
            ctl = ctl / 100.0

        vmin = min(obs.min(), ngt.min(), ctl.min()) - 0.05 * abs(obs.min())
        vmax = max(obs.max(), ngt.max(), ctl.max()) + 0.05 * abs(obs.max())
        ax.plot([vmin, vmax], [vmin, vmax], 'k--', lw=0.8, alpha=0.5, label='1:1')

        ax.scatter(obs, ngt, c=colors[0], edgecolors='k', s=50, alpha=0.8, zorder=3)
        ax.scatter(obs, ctl, c=colors[1], edgecolors='k', s=50, alpha=0.8, zorder=3, marker='s')

        ax.set_xlabel(f"Observado {label_var}")
        ax.set_ylabel(f"WRF {label_var}")
        ax.set_title(label_var, fontsize=11)
        ax.grid(True, alpha=0.3)

    axes[0, 0].legend(loc='upper left', fontsize=8)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(str(output_dir / "scatter_4panels.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  -> {output_dir / 'scatter_4panels.png'}")

def plot_map(nudged_data, control_data, stations, output_dir, valid_time, nudged_dir, label=""):
    path = nudged_dir / valid_time
    if not path.exists():
        alt = nudged_dir / f"{valid_time}:00"
        if alt.exists():
            path = alt
        else:
            print("  Saltando mapa de errores (no se encuentra wrfout)")
            return
    ds = xr.open_dataset(str(path))
    hgt = ds.HGT.values[0]
    lat2d = ds.XLAT.values[0]
    lon2d = ds.XLONG.values[0]
    ds.close()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    suffix = f" {label}" if label else ""
    fig.suptitle(f"Error de Temperatura 2m - WRF vs Estaciones ({valid_time}){suffix}", fontsize=13, y=0.98)

    titles = ["Nudged", "Control"]
    data_sets = [nudged_data, control_data]

    lat_obs = np.array([s["lat"] for s in stations])
    lon_obs = np.array([s["lon"] for s in stations])
    obs_t = np.array([s["temp"] if s["temp"] is not None else np.nan for s in stations])

    for ax, title, mod_data in zip(axes, titles, data_sets):
        mod_t = np.array([d["t2"] for d in mod_data])
        err = mod_t - obs_t

        cf = ax.contourf(lon2d, lat2d, hgt, levels=20, cmap='terrain', alpha=0.6)
        ax.contour(lon2d, lat2d, hgt, levels=10, colors='grey', linewidths=0.3, alpha=0.4)

        sc = ax.scatter(lon_obs, lat_obs, c=err, cmap='RdBu_r', s=100,
                        vmin=-5, vmax=5, edgecolors='k', linewidths=1, zorder=5)

        for s, e in zip(stations, err):
            if not np.isnan(e):
                ax.annotate(f"{e:+.1f}K", (s["lon"], s["lat"]),
                           textcoords="offset points", xytext=(8, 8), fontsize=7, zorder=6)

        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
        ax.set_title(title, fontsize=11)
        ax.set_xlim(lon2d.min(), lon2d.max())
        ax.set_ylim(lat2d.min(), lat2d.max())

        cbar = plt.colorbar(sc, ax=ax, shrink=0.7)
        cbar.set_label("T2 error (K)")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(str(output_dir / "mapa_errores_t2.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  -> {output_dir / 'mapa_errores_t2.png'}")

def plot_metrics_table(rows, output_dir, valid_time, label=""):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('off')

    col_labels = ["Variable", "N",
                  "Bias N", "MAE N", "RMSE N", "r N",
                  "Bias C", "MAE C", "RMSE C", "r C"]

    fmt = lambda r: [
        r["var"], str(r["n"]),
        f"{r['nudged_bias']:+.2f}" if not np.isnan(r['nudged_bias']) else "-",
        f"{r['nudged_mae']:.2f}"   if not np.isnan(r['nudged_mae']) else "-",
        f"{r['nudged_rmse']:.2f}"  if not np.isnan(r['nudged_rmse']) else "-",
        f"{r['nudged_r']:.3f}"     if not np.isnan(r['nudged_r']) else "-",
        f"{r['control_bias']:+.2f}" if not np.isnan(r['control_bias']) else "-",
        f"{r['control_mae']:.2f}"   if not np.isnan(r['control_mae']) else "-",
        f"{r['control_rmse']:.2f}"  if not np.isnan(r['control_rmse']) else "-",
        f"{r['control_r']:.3f}"     if not np.isnan(r['control_r']) else "-",
    ]

    cell_text = [fmt(r) for r in rows]
    table = ax.table(cellText=cell_text, colLabels=col_labels,
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)

    suffix = f" {label}" if label else ""
    ax.set_title(f"Metricas de Validacion - Nudged (N) vs Control (C)\n{valid_time}{suffix}",
                 fontsize=12, pad=20)

    plt.tight_layout()
    plt.savefig(str(output_dir / "tabla_metricas.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  -> {output_dir / 'tabla_metricas.png'}")

def write_summary(rows, stations, output_dir, valid_time, label=""):
    lines = []
    lines.append("=" * 80)
    suffix = f" {label}" if label else ""
    lines.append(f"VALIDACION WRF vs OBSERVACIONES - {valid_time}{suffix}")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"{'Variable':<15} {'N':>4} {'Bias N':>10} {'MAE N':>10} {'RMSE N':>10} {'r N':>8} "
                 f"{'Bias C':>10} {'MAE C':>10} {'RMSE C':>10} {'r C':>8}")
    lines.append("-" * 105)
    for r in rows:
        def v(x):
            return f"{x:+.2f}" if not np.isnan(x) else "-"
        def f(x):
            return f"{x:.2f}" if not np.isnan(x) else "-"
        def rv(x):
            return f"{x:.3f}" if not np.isnan(x) else "-"
        lines.append(f"{r['var']:<15} {r['n']:>4} "
                     f"{v(r['nudged_bias']):>10} {f(r['nudged_mae']):>10} {f(r['nudged_rmse']):>10} {rv(r['nudged_r']):>8} "
                     f"{v(r['control_bias']):>10} {f(r['control_mae']):>10} {f(r['control_rmse']):>10} {rv(r['control_r']):>8}")
    lines.append("-" * 105)
    lines.append("")
    lines.append("N = Nudged (obs_nudge_opt=1), C = Control (obs_nudge_opt=0)")
    lines.append("")

    for s in stations:
        lines.append(f"  {s['name']:<20s}  lat={s['lat']:>8.4f}  lon={s['lon']:>8.4f}  elev={s['elev']:>5.0f}m")
    lines.append("")

    with open(str(output_dir / "metricas_resumen.txt"), 'w') as f:
        f.write('\n'.join(lines))
    print(f"  -> {output_dir / 'metricas_resumen.txt'}")
    print('\n'.join(lines))

def main():
    parser = argparse.ArgumentParser(description="Valida WRF vs observaciones de estaciones")
    parser.add_argument("--nudged-dir", required=True,
                        help="Directorio con wrfout de la corrida nudged")
    parser.add_argument("--control-dir", required=True,
                        help="Directorio con wrfout de la corrida control")
    parser.add_argument("--output-dir", required=True,
                        help="Directorio para gráficos y tabla de salida")
    parser.add_argument("--valid-time", required=True,
                        help="Tiempo valido en formato YYYY-MM-DD_HH:MM:SS (ej: 2026-05-25_21:00:00)")
    parser.add_argument("--obs-json", default=None,
                        help="Opcional: JSON de observaciones EcoWitt para extraer datos de estaciones")
    parser.add_argument("--label", default="",
                        help="Etiqueta opcional para los graficos")
    parser.add_argument("--estaciones-json", default=None,
                        help="Ruta a config/estaciones.json (opcional, busca por defecto)")
    parser.add_argument("--ventana-min", type=int, default=30,
                        help="Ventana temporal (± minutos) para filtrar observaciones (default: 30)")

    args = parser.parse_args()

    nudged_dir = Path(args.nudged_dir)
    control_dir = Path(args.control_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_time = args.valid_time

    if args.obs_json:
        stations = cargar_estaciones_desde_json(
            args.obs_json, args.estaciones_json,
            valid_time=valid_time, ventana_min=args.ventana_min)
    else:
        stations = cargar_metadatos_estaciones(args.estaciones_json)
    if not valid_time.startswith("wrfout_d01_"):
        valid_time = f"wrfout_d01_{valid_time}"

    print(f"Validando: {valid_time}")
    print(f"Nudged: {nudged_dir}")
    print(f"Control: {control_dir}")
    print(f"Salida: {output_dir}")
    print(f"Estaciones: {len(stations)}")

    if not stations:
        print(f"ERROR: Ninguna estacion tiene observaciones dentro de la ventana "
              f"(+/-{args.ventana_min} min) alrededor de {valid_time}. "
              "Nada que validar (revisar --valid-time u --obs-json).")
        return 1

    nudged_data = load_run(nudged_dir, valid_time, stations)
    control_data = load_run(control_dir, valid_time, stations)

    if nudged_data is None or control_data is None:
        print("ERROR: No se pudieron cargar los datos WRF")
        return 1

    print(f"  {len(nudged_data)} estaciones procesadas en cada corrida")

    rows = build_tables(nudged_data, control_data, stations)

    plot_scatter(nudged_data, control_data, stations, output_dir, valid_time, args.label)
    plot_map(nudged_data, control_data, stations, output_dir, valid_time, nudged_dir, args.label)
    plot_metrics_table(rows, output_dir, valid_time, args.label)
    write_summary(rows, stations, output_dir, valid_time, args.label)

    print("Validacion completa.")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())