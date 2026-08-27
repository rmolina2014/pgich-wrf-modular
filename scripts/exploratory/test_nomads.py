import urllib.request
import os

# Try NOMADS for standard GFS pgrb2 files
base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
test_url = base_url + "?file=gfs.t12z.pgrb2.0p25.f000&lev_10_m_above_ground=on&var_TMP=on&subregion=&leftlon=-70&rightlon=-66&toplat=-30&bottomlat=-33&dir=%2Fgfs.20260702%2F12%2Fatmos"

print("Testing NOMADS URL...")
print(test_url[:120] + "...")
try:
    req = urllib.request.Request(test_url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=15)
    print("Status:", resp.status)
    print("Content-Type:", resp.headers.get('Content-Type'))
    data = resp.read(100)
    print("First bytes:", data[:20])
except Exception as e:
    print("Error:", str(e)[:200])
