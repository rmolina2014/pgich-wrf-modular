#!/usr/bin/env python3
"""Download GFS with variable filters but NO subregion."""
import urllib.request
import ssl
import time
from pathlib import Path

ctx = ssl.create_default_context()

fecha = "20260705"
hora = "12"
output_dir = Path("gfs_data/2026-07-05_nosub")
output_dir.mkdir(parents=True, exist_ok=True)

horas = ["f000", "f003", "f006", "f009", "f012"]

# Variables needed for WPS GFS Vtable
var_filter = "var_TMP=on&var_UGRD=on&var_VGRD=on&var_SPFH=on&var_HGT=on&var_PRES=on&var_PRATE=on&var_HLCY=on&var_HGSF=on&var_VVEL=on&var_USHR=on&var_VWSH=on"
lev_filter = (
    "lev_surface=on&lev_2_m_above_ground=on&lev_10_m_above_ground=on"
    "&lev_3000-0_m_above_ground=on"
    "&lev_1000_mb=on&lev_975_mb=on&lev_950_mb=on&lev_925_mb=on"
    "&lev_900_mb=on&lev_850_mb=on&lev_800_mb=on&lev_750_mb=on"
    "&lev_700_mb=on&lev_650_mb=on&lev_600_mb=on&lev_550_mb=on"
    "&lev_500_mb=on&lev_450_mb=on&lev_400_mb=on&lev_350_mb=on"
    "&lev_300_mb=on&lev_275_mb=on&lev_250_mb=on&lev_225_mb=on"
    "&lev_200_mb=on&lev_175_mb=on&lev_150_mb=on&lev_125_mb=on"
    "&lev_100_mb=on&lev_75_mb=on&lev_50_mb=on&lev_30_mb=on"
    "&lev_20_mb=on&lev_15_mb=on&lev_10_mb=on&lev_7_mb=on"
    "&lev_5_mb=on&lev_3_mb=on&lev_2_mb=on&lev_1_mb=on"
)

for fhr in horas:
    file_name = f"gfs.t{hora}z.pgrb2.0p25.{fhr}"
    local_path = output_dir / file_name

    if local_path.exists() and local_path.stat().st_size > 10000:
        print(f"  Ya existe: {file_name} ({local_path.stat().st_size // 1024} KB)")
        continue

    url = (
        f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
        f"?file={file_name}"
        f"&{lev_filter}"
        f"&{var_filter}"
        f"&dir=%2Fgfs.{fecha}%2F{hora}%2Fatmos"
    )

    print(f"  Descargando: {file_name} (vars+levels only, no subregion)...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=300, context=ctx)
        data = resp.read()

        if len(data) < 100:
            print(f"    Archivo muy pequeno ({len(data)} bytes)")
            continue

        with open(local_path, "wb") as f:
            f.write(data)

        size_mb = len(data) / (1024 * 1024)
        print(f"    OK ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"    Error: {e}")

    time.sleep(1)

print("Done.")
