#!/usr/bin/env python3
"""Download full (unfiltered) GFS pgrb2 files from NOMADS for one time step."""
import urllib.request
import ssl
import os
from pathlib import Path

ctx = ssl.create_default_context()

fecha = "20260705"
hora = "12"
output_dir = Path("gfs_data/2026-07-05_full")
output_dir.mkdir(parents=True, exist_ok=True)

horas = ["f000", "f003", "f006", "f009", "f012"]

for fhr in horas:
    file_name = f"gfs.t{hora}z.pgrb2.0p25.{fhr}"
    local_path = output_dir / file_name

    if local_path.exists() and local_path.stat().st_size > 10_000_000:
        print(f"  Ya existe: {file_name} ({local_path.stat().st_size // (1024*1024)} MB)")
        continue

    # Full file, no subregion
    url = (
        f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
        f"?file={file_name}"
        f"&dir=%2Fgfs.{fecha}%2F{hora}%2Fatmos"
    )

    print(f"  Descargando: {file_name} (full)...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=600, context=ctx)
        data = resp.read()

        with open(local_path, "wb") as f:
            f.write(data)

        size_mb = len(data) / (1024 * 1024)
        print(f"    OK ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"    Error: {e}")

print("Done.")
