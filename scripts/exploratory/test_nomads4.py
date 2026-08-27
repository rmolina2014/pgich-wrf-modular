import urllib.request
import ssl

ctx = ssl.create_default_context()

# Try direct raw URL without the filter CGI
urls = [
    # Raw file access (no filter)
    "https://nomads.ncep.noaa.gov/pub/gfs/gyre/gfs.20260705/12/atmos/gfs.t12z.pgrb2.0p25.f000",
    "https://nomads.ncep.noaa.gov/pub/gfs/gfs.20260705/12/atmos/gfs.t12z.pgrb2.0p25.f000",
    # NCEP NOMADS direct paths
    "https://nomads.ncep.noaa.gov/data/gfs/gfs.20260705/12/atmos/gfs.t12z.pgrb2.0p25.f000",
    # Filter URL but checking what file type it gives
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl?file=gfs.t12z.pgrb2.0p25.f000&dir=%2Fgfs.20260705%2F12%2Fatmos",
]

for i, url in enumerate(urls):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        data = resp.read(100)
        header = data[:4].decode("latin-1")
        print(f"URL {i+1}: OK ({len(data)} bytes, header={header})")
        print(f"  URL: {url[:100]}")
    except Exception as e:
        print(f"URL {i+1}: ERROR - {str(e)[:100]}")
        print(f"  URL: {url[:100]}")
