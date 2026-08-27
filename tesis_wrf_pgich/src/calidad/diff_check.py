import xarray as xr
n = xr.open_dataset('/wrf/WRF/test/em_real/nudged/wrfout_d01_2026-05-25_21:00:00')
c = xr.open_dataset('/wrf/WRF/test/em_real/control/wrfout_d01_2026-05-25_21:00:00')
for v in ['T2','PSFC','Q2','U10','V10']:
    diff = (n[v] - c[v]).values
    print(f'{v}: max|diff| = {abs(diff).max():.6f}')
n.close()
c.close()
