import xarray as xr
n = xr.open_dataset('/wrf/WRF/test/em_real/wrfout_d01_2026-05-25_21:00:00')
c = xr.open_dataset('/wrf/WRF/test/em_real/control/wrfout_d01_2026-05-25_21:00:00')
print('Nudged (fdda_end=720) vs Control (fdda_end=0) at 21:00z:')
for v in ['T2','PSFC','Q2','U10','V10','T','U','V','QVAPOR']:
    d = abs(n[v] - c[v]).values.max()
    print(f'  {v:>8s}: max|diff| = {d:.6e}')
n.close()
c.close()

print()
print('Also check 20:00z:')
n2 = xr.open_dataset('/wrf/WRF/test/em_real/wrfout_d01_2026-05-25_20:00:00')
c2 = xr.open_dataset('/wrf/WRF/test/em_real/control/wrfout_d01_2026-05-25_20:00:00')
for v in ['T2','PSFC','Q2','U10','V10']:
    d = abs(n2[v] - c2[v]).values.max()
    print(f'  {v:>8s}: max|diff| = {d:.6e}')
n2.close()
c2.close()

print()
print('Also check 22:00z:')
n3 = xr.open_dataset('/wrf/WRF/test/em_real/wrfout_d01_2026-05-25_22:00:00')
c3 = xr.open_dataset('/wrf/WRF/test/em_real/control/wrfout_d01_2026-05-25_22:00:00')
for v in ['T2','PSFC','Q2','U10','V10']:
    d = abs(n3[v] - c3[v]).values.max()
    print(f'  {v:>8s}: max|diff| = {d:.6e}')
n3.close()
c3.close()
