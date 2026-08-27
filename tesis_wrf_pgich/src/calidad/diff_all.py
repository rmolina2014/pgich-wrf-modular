import xarray as xr
from pathlib import Path
base = Path('/wrf/WRF/test/em_real')
t2 = base / 'wrfout_d01_2026-05-25_21:00:00'
for f in sorted((base / 'nudged').glob('wrfout_d01*')):
    fname = f.name
    n = xr.open_dataset(str(base / 'nudged' / fname))
    c = xr.open_dataset(str(base / 'control' / fname))
    timestr = str(n.Times.values[0], 'utf-8') if hasattr(n.Times.values[0], 'decode') else str(n.Times.values[0])
    diffs = []
    for v in ['T2','PSFC','Q2','U10','V10']:
        d = abs(n[v] - c[v]).values.max()
        diffs.append(d)
    md = max(diffs)
    marker = ' <-- DIFF' if md > 0 else ''
    print(f'{timestr:>20s}  T2={diffs[0]:.6e}  PSFC={diffs[1]:.6e}  Q2={diffs[2]:.6e}  U10={diffs[3]:.6e}  V10={diffs[4]:.6e}{marker}')
    n.close()
    c.close()
