import xarray as xr
n = xr.open_dataset('/wrf/WRF/test/em_real/wrfout_d01_2026-05-25_21:00:00')
c = xr.open_dataset('/wrf/WRF/test/em_real/control/wrfout_d01_2026-05-25_21:00:00')
print("Latest run vs control at 21:00z:")
for v in ['T2','PSFC','Q2','U10','V10','U','V','T','QVAPOR']:
    d = abs(n[v] - c[v]).values.max()
    print(f"  {v:>8s}: max|diff| = {d:.6e}")
n.close(); c.close()
