"""Grafica promedios horarios T2 de control, nudging y observaciones (00-12 UTC).

Usa los NetCDF archivados y observaciones obs_flat; no ejecuta WRF.
Dependencias: numpy, scipy, h5py, matplotlib. Ejecutar desde cualquier directorio.
"""
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import json

import numpy as np
import h5py
from scipy.io import netcdf_file
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
COLORS = {'control': '#d45c35', 'nudging': '#226ab3', 'observado': '#192e35'}


def interpolar(t2, lats, lons, lat, lon):
    # Replica bilinear_interp de valida_wrf_cli.py: IDW de cuatro vecinos.
    j = int(np.clip(np.searchsorted(lats[:, 0], lat) - 1, 0, lats.shape[0] - 2))
    i = int(np.clip(np.searchsorted(lons[0, :], lon) - 1, 0, lats.shape[1] - 2))
    ys = lats[j:j+2, i:i+2].ravel()
    xs = lons[j:j+2, i:i+2].ravel()
    coslat = np.cos(np.radians(float(np.mean(ys))))
    dist2 = ((xs.astype(float) - lon) * coslat)**2 + (ys.astype(float) - lat)**2
    weights = 1 / np.maximum(dist2, 1e-12)
    return float(np.sum(weights * t2[j:j+2, i:i+2].ravel()) / weights.sum()) - 273.15


def modelo(path, expected_time, names, catalog):
    if h5py.is_hdf5(path):
        with h5py.File(path, 'r') as ds:
            actual = ds['Times'][:].tobytes().decode('ascii').strip('\x00')
            t2, lats, lons = (ds[k][0] for k in ('T2', 'XLAT', 'XLONG'))
    else:
        with netcdf_file(path, mmap=True) as ds:
            actual = ds.variables['Times'][:].copy().tobytes().decode('ascii').strip('\x00')
            t2, lats, lons = (ds.variables[k][0].copy() for k in ('T2', 'XLAT', 'XLONG'))
    if actual != expected_time.strftime('%Y-%m-%d_%H:%M:%S'):
        raise ValueError(f'Tiempo interno inesperado en {path}: {actual}')
    return {name: interpolar(t2, lats, lons, catalog[name]['lat'], catalog[name]['lon'])
            for name in names}


def extraer(case, catalog):
    day = case['fecha'].replace('-', '')
    source = ROOT / 'data' / 'raw' / f'obs_flat_{day}.json'
    raw = json.loads(source.read_text(encoding='utf-8'))
    readings = []
    for row in raw:
        if 'error' in row or row.get('temp') is None or row.get('estacion') not in catalog:
            continue
        try:
            dt = datetime.fromisoformat(f"{row['fecha']} {row['hora']}")
            temp = float(row['temp'])
        except (ValueError, KeyError, TypeError):
            continue
        if np.isfinite(temp):
            readings.append((dt, row['estacion'], temp))
    folder = ROOT / case['resultados_dir']
    archived = json.loads((folder / 'tabla_evolutiva.json').read_text(encoding='utf-8'))
    reference = {e['tiempo']: e['rows'][0] for e in archived['por_tiempo']}
    hours = []
    checks = []
    for hour in range(13):
        dt = datetime.fromisoformat(case['fecha']) + timedelta(hours=hour)
        groups = {}
        for obs_dt, name, value in readings:
            if abs((obs_dt - dt).total_seconds()) <= 1800:
                groups.setdefault(name, []).append(value)
        names = sorted(groups)
        filename = f"wrfout_d01_{dt.strftime('%Y-%m-%d_%H_%M_%S')}"
        ctl = modelo(folder / 'control' / filename, dt, names, catalog)
        nud = modelo(folder / 'nudged' / filename, dt, names, catalog)
        pairs = [{'estacion': n, 'rol': catalog[n].get('rol'),
                  'observado': float(np.mean(groups[n])), 'control': ctl[n],
                  'nudging': nud[n], 'lecturas': len(groups[n])}
                 for n in names if np.isfinite(ctl[n]) and np.isfinite(nud[n])]
        if not pairs:
            raise ValueError(f"Sin pares validos: {case['id']} {hour:02d}Z")
        point = {'hora_utc': hour, 'n': len(pairs), 'estaciones': pairs}
        for key in COLORS:
            point[key] = float(np.mean([r[key] for r in pairs]))
        ref = reference.get(f'{hour:02d}Z')
        if ref:
            for key, prefix in [('control', 'control'), ('nudging', 'nudged')]:
                error = np.array([r[key] - r['observado'] for r in pairs])
                rmse = float(np.sqrt(np.mean(error**2)))
                bias = float(np.mean(error))
                # Tolerancia de 0.02 K frente a resultados archivados.
                for metric, value in [('rmse', rmse), ('bias', bias)]:
                    delta = abs(value - ref[f'{prefix}_{metric}'])
                    checks.append({'hora': hour, 'corrida': key, 'metrica': metric, 'diferencia': delta})
                    if delta > 0.02:
                        raise ValueError(f"Discrepancia con informe {case['id']} {hour} {key} {metric}: {delta}")
            if len(pairs) != ref['n']:
                raise ValueError(f"N no coincide en {case['id']} {hour}")
        hours.append(point)
    return {'caso': case['titulo'], 'fecha': case['fecha'], 'horas': hours,
            'fuente_observaciones': str(source.relative_to(ROOT)), 'verificaciones': checks}


def graficar(data, out, selected_hour):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.3), sharey=True)
    for ax, case in zip(axes, data):
        points = case['horas']
        for key, label, marker, style in [('control', 'Control', 's', '--'),
                ('nudging', 'Nudging', 'o', '-'), ('observado', 'Promedio observado', 'D', '-')]:
            ax.plot(range(13), [p[key] for p in points], label=label, color=COLORS[key],
                    marker=marker, ms=4, lw=2, linestyle=style)
        title = case['caso'].replace(' - ', ' · ').replace(' (Año Nuevo)', '')
        ax.set_title(f"{title}\n{case['fecha']}", loc='left', fontsize=12, pad=15)
        ax.set_xticks(range(0, 13, 2), [f'{h:02d}Z' for h in range(0, 13, 2)])
        ax.set_xlim(-0.25, 12.25)
        ax.set_xlabel('Hora UTC', labelpad=10)
        ax.grid(axis='y', alpha=.18)
        ax.text(0, -.21, 'Estaciones por hora (00Z → 12Z):\n' +
                ' · '.join(str(p['n']) for p in points), transform=ax.transAxes,
                fontsize=8.5, color='#536570', va='top')
    axes[0].set_ylabel('Temperatura a 2 m (°C)')
    fig.suptitle('Temperatura media de la red · evolución de 00Z a 12Z',
                 x=.06, y=.98, ha='left', fontsize=19, fontweight='bold')
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper left',
               bbox_to_anchor=(.055, .90), ncol=3, frameon=False)
    fig.text(.06, .035, 'Observaciones: media por estación en ±30 min; luego media de estaciones con igual peso.\n'
             'Control y nudging: misma red disponible en cada hora. La composición puede variar. 00Z–12Z = 21–09 h de Argentina.',
             fontsize=9, color='#536570')
    fig.subplots_adjust(left=.06, right=.98, top=.74, bottom=.30, wspace=.16)
    for ext in ('png', 'svg'):
        fig.savefig(out / f'temperatura_media_00a12Z.{ext}', dpi=180, facecolor='white')
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(12, 11))
    for ax, case in zip(axes, data):
        p = case['horas'][selected_hour]
        rows = p['estaciones']
        x = np.arange(len(rows))
        for key, label, marker in [('control', 'Control', 's'), ('nudging', 'Nudging', 'o')]:
            ax.plot(x, [r[key] for r in rows], marker=marker, lw=2, label=label, color=COLORS[key])
        ax.scatter(x, [r['observado'] for r in rows], color=COLORS['observado'],
                   label='Observado por estación', zorder=4, s=30)
        ax.axhline(p['observado'], color=COLORS['observado'], ls='--',
                   label=f"Promedio observado: {p['observado']:.2f} °C")
        ax.set_xticks(x, [r['estacion'].replace('_', '\n') for r in rows], fontsize=8)
        ax.set_ylabel('Temperatura (°C)')
        ax.set_title(f"{case['caso']} · {case['fecha']} · {selected_hour:02d}Z", loc='left', fontsize=12)
        ax.grid(axis='y', alpha=.18)
        ax.legend(fontsize=8, loc='best', ncol=2)
    fig.suptitle(f'Temperatura por estación · {selected_hour:02d}Z', fontsize=18, fontweight='bold', y=.99)
    fig.text(.08, .012, 'Observado por estación: promedio en ±30 min. Línea horizontal: media de esas estaciones con igual peso.', fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, .97), h_pad=2.2)
    fig.savefig(out / f'temperatura_estaciones_{selected_hour:02d}Z.png', dpi=180, facecolor='white')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hora', type=int, choices=range(13), default=6)
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/casos_estudio.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT / 'config/estaciones.json').read_text(encoding='utf-8'))
    data = [extraer(case, catalog) for case in config['casos']]
    out = ROOT / 'results/comparacion_temperatura'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'datos_graficos.json').write_text(json.dumps({'unidad': '°C', 'ventana_observacion_min': 30,
        'ponderacion': 'igual por estacion; red comun entre las tres series por hora', 'casos': data},
        ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    graficar(data, out, args.hora)
    for case in data:
        max_delta = max(c['diferencia'] for c in case['verificaciones'])
        print(f"{case['caso']}: 13 horas; diferencia maxima frente a metricas archivadas {max_delta:.6f} K")
    print(out)


if __name__ == '__main__':
    main()
