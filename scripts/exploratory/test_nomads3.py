import urllib.request
import ssl

ctx = ssl.create_default_context()

# Test various dates and URLs
tests = [
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&dir=%2Fgfs.20260705%2F12%2Fatmos",
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&dir=%2Fgfs.20260704%2F12%2Fatmos",
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&dir=%2Fgfs.20260703%2F12%2Fatmos",
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&dir=%2Fgfs.20260706%2F12%2Fatmos",
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&dir=%2Fgfs.20260706%2F06%2Fatmos",
]

for url in tests:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        data = resp.read(100)
        is_grib = b"GRIB" in data[:4]
        print(f"OK ({len(data)} bytes, GRIB={is_grib}): {url.split('dir=')[1]}")
    except Exception as e:
        print(f"ERROR ({e}): {url.split('dir=')[1]}")
