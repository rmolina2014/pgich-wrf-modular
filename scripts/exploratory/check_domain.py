import netCDF4 as nc
ds = nc.Dataset('/wrf/WPS/geo_em.d01.nc')
lat = ds['XLAT'][:].flatten()
lon = ds['XLONG'][:].flatten()
print('XLAT min/max:', lat.min(), lat.max())
print('XLONG min/max:', lon.min(), lon.max())
ds.close()
