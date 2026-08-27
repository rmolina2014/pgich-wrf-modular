#!/usr/bin/env python3
"""
Descarga archivos GFS desde NOMADS (pgrb2.0p25 estandar).

Uso:
    python descargar_gfs.py [--fecha YYYY-MM-DD] [--hora HH] [--output-dir DIR]

Notas:
    - Descarga archivos pgrb2.0p25 estandar desde NOMADS.
    - Subregion amplia (-75 a -60 lon, -35 a -25 lat) para evitar missing values.
    - Intervalo de 3h: f000, f003, f006, f009, f012.
"""
import argparse
import os
import sys
import urllib.request
import ssl
import time
from pathlib import Path


def download_gfs_nomads(fecha, hora, output_dir):
    """Descarga archivos GFS pgrb2 desde NOMADS con subregion amplia."""
    fecha_str = fecha.replace("-", "")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Subregion: WRF domain is lat -35.3 to -27.5, lon -74.7 to -62.3
    # Use generous padding (5+ deg each side)
    leftlon, rightlon = -80, -58
    toplat, bottomlat = -22, -40

    horas_fcst = ["f000", "f003", "f006", "f009", "f012"]
    downloaded = 0

    ctx = ssl.create_default_context()

    for fhr in horas_fcst:
        file_name = f"gfs.t{hora}z.pgrb2.0p25.{fhr}"
        local_path = output_path / file_name

        if local_path.exists() and local_path.stat().st_size > 10000:
            print(f"  Ya existe: {file_name} ({local_path.stat().st_size // 1024} KB)")
            downloaded += 1
            continue

        url = (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
            f"?file={file_name}"
            f"&subregion=&leftlon={leftlon}&rightlon={rightlon}"
            f"&toplat={toplat}&bottomlat={bottomlat}"
            f"&dir=%2Fgfs.{fecha_str}%2F{hora}%2Fatmos"
        )

        print(f"  Descargando: {file_name}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=300, context=ctx)
            data = resp.read()

            if len(data) < 1000:
                print(f"    Archivo muy pequeno ({len(data)} bytes), posible error")
                continue

            header = data[:4].decode("latin-1")
            if header != "GRIB":
                print(f"    No es GRIB2 (header={header})")
                continue

            with open(local_path, "wb") as f:
                f.write(data)

            size_mb = len(data) / (1024 * 1024)
            print(f"    OK ({size_mb:.1f} MB)")
            downloaded += 1

        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(0.5)

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Descargar archivos GFS")
    parser.add_argument("--fecha", default="2026-07-05", help="Fecha YYYY-MM-DD")
    parser.add_argument("--hora", default="12", help="Hora UTC (00 o 12)")
    parser.add_argument("--output-dir", default=None, help="Directorio de salida")
    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = f"gfs_data/{args.fecha}"

    print(f"Descargando GFS para {args.fecha} {args.hora} UTC (subregion amplia)...")
    n = download_gfs_nomads(args.fecha, args.hora, args.output_dir)
    print(f"\nDescargados: {n}/5 archivos")


if __name__ == "__main__":
    main()
