#!/usr/bin/env python3
"""Check GFS file format"""
import sys

# Read first 100 bytes
with open('/wrf/WPS/gfs_data/gfs.t12z.goessimpgrb2.0p25.f000', 'rb') as f:
    data = f.read(100)
    print('First 50 bytes:', data[:50])
    print('Is GRIB2:', b'GRIB' in data[:10])
    print('File size:', len(data), 'bytes (first 100)')
