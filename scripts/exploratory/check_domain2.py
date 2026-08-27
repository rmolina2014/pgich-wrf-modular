import netCDF4 as nc
ds = nc.Dataset('/wrf/WPS/geo_em.d01.nc')
print(list(ds.variables.keys())[:20])
for v in ['XLAT', 'XLONG', 'XLAT_M', 'XLONG_M']:
    if v in ds.variables:
        data = ds[v][:].flatten()
        print(v, 'min/max:', data.min(), data.max())
ds.close()
