#!/usr/bin/env python3
"""Install cfgrib in container and inspect goessimpgrb2 file"""
import subprocess
import sys

# Install cfgrib
print("Installing cfgrib...")
subprocess.run([sys.executable, "-m", "pip", "install", "cfgrib", "eccodes", "--quiet"], check=True)

# Inspect the file
print("\nInspecting goessimpgrb2 file...")
code = """
import xarray as xr
try:
    ds = xr.open_dataset('/wrf/WPS/gfs_data/gfs.t12z.goessimpgrb2.0p25.f000', engine='cfgrib')
    print("Variables:", list(ds.data_vars))
    for var in ds.data_vars:
        v = ds[var]
        print(f"  {var}: shape={v.shape}, attrs={dict(v.attrs)}")
except Exception as e:
    print(f"Error with cfgrib: {e}")
    # Try direct read
    try:
        ds = xr.open_dataset('/wrf/WPS/gfs_data/gfs.t12z.goessimpgrb2.0p25.f000')
        print("Variables (default):", list(ds.data_vars))
    except Exception as e2:
        print(f"Error with default: {e2}")
"""
result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-500:])
