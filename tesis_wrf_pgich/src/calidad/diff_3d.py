import xarray as xr
from pathlib import Path
import numpy as np

base = Path('/wrf/WRF/test/em_real')
fname = 'wrfout_d01_2026-05-25_21:00:00'
n = xr.open_dataset(str(base / 'nudged' / fname))
c = xr.open_dataset(str(base / 'control' / fname))

print("=== 2D variables ===")
for v in ['T2','PSFC','Q2','U10','V10','TH2','TSK']:
    diff = (n[v] - c[v]).values
    print(f"{v:>8s}: max|diff|={abs(diff).max():.6e}  mean={np.nanmean(diff):.6e}")

print("\n=== 3D variables (k=0, surface level) ===")
for v in ['T','U','V','QVAPOR','P']:
    diff = (n[v][0,0] - c[v][0,0]).values
    print(f"{v:>8s} k=0: max|diff|={abs(diff).max():.6e}  mean={np.nanmean(diff):.6e}")

print("\n=== 3D variables (all levels) ===")
for v in ['T','U','V','QVAPOR']:
    diff = (n[v] - c[v]).values
    print(f"{v:>8s}: max|diff|={abs(diff).max():.6e}  mean={np.nanmean(diff):.6e}")

print("\n=== Station 1 (INTA_POCITO, lat~-31.57, lon~-67.89) ===")
lat_idx = abs(n.XLAT[0,:,0] - (-31.5678)).argmin().values
lon_idx = abs(n.XLONG[0,0,:] - (-67.8901)).argmin().values
print(f"Grid point: j={lat_idx}, i={lon_idx}")
for v in ['T2','PSFC','Q2','U10','V10']:
    nv = n[v][0,lat_idx,lon_idx].values
    cv = c[v][0,lat_idx,lon_idx].values
    print(f"{v:>8s}: nudged={nv:.6f}  control={cv:.6f}  diff={nv-cv:.6e}")

print("\n=== T at station grid point, k=0 ===")
for k in [0, 1, 2, 3, 4, 5]:
    nv = n['T'][0,k,lat_idx,lon_idx].values
    cv = c['T'][0,k,lat_idx,lon_idx].values
    print(f"T k={k}: nudged={nv:.6f}  control={cv:.6f}  diff={nv-cv:.6e}")

n.close()
c.close()
