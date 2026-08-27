import urllib.request
import os
import ssl

# Try NOMADS direct download for standard GFS pgrb2
# Format: https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=...&dir=/gfs.YYYYMMDD/HH/atmos

date = '20260702'
hour = '12'
fhour = 'f000'
file_name = f'gfs.t{hour}z.pgrb2.0p25.{fhour}'
dir_path = f'/gfs.{date}/{hour}/atmos'

# Create filtered URL (subregion around San Juan)
url = (
    f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
    f"?file={file_name}"
    f"&lev_10_m_above_ground=on"
    f"&lev_2_m_above_ground=on"
    f"&lev_surface=on"
    f"&var_TMP=on&var_UGRD=on&var_VGRD=on&var_SPFH=on&var_HGT=on"
    f"&var_HLCY=on&var_PRES=on&var_PRATE=on"
    f"&subregion="
    f"&leftlon=-70&rightlon=-66"
    f"&toplat=-30&bottomlat=-33"
    f"&dir={dir_path}"
)

print("Testing NOMADS URL:")
print(url[:150])
print()

# Try HTTP instead of HTTPS
try:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30, context=ctx)
    data = resp.read(500)
    print(f"HTTPS Status: {resp.status}")
    print(f"Content-Length header: {resp.headers.get('Content-Length', 'N/A')}")
    print(f"First 20 bytes: {data[:20]}")
    print(f"Is GRIB2: {'GRIB' in data[:4].decode('latin-1')}")
except Exception as e:
    print(f"HTTPS Error: {e}")

# Also try without subregion (full file)
url2 = (
    f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
    f"?file={file_name}"
    f"&dir={dir_path}"
)
print(f"\nFull file URL test:")
try:
    req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
    resp2 = urllib.request.urlopen(req2, timeout=30)
    print(f"Status: {resp2.status}")
    cl = resp2.headers.get('Content-Length', 'N/A')
    print(f"Content-Length: {cl}")
except Exception as e:
    print(f"Error: {e}")
