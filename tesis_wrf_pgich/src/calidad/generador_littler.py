"""Generador LITTLE_R - Convierte datos al formato para WRFDA
Este script convierte los datos de las estaciones meteorologicas al formato LITTLE_R
que es compatible con el sistema de asimilacion de datos WRF.

Formato exacto basado en especificación Fortran:
- Station ID: 40 caracteres
- Lat/Lon/Elev: 12 caracteres cada uno
- Fecha: 20 caracteres
- Hora: 5 caracteres
- Nivel: 6 caracteres
- Numero de niveles: 6 caracteres
- Variables: 15 caracteres cada una
"""

import pandas as pd
import os
import json
from datetime import datetime
from pathlib import Path


def cargar_metadatos() -> dict:
    """Carga metadatos de estaciones desde config/estaciones.json"""
    # Buscar en varios lugares: CWD, script_dir, y PROJECT_DIR
    search_paths = [
        Path("config/estaciones.json"),
        Path(__file__).parent.parent.parent / "config" / "estaciones.json",
    ]
    for config_path in search_paths:
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
    return {}


def formatear_linea(
    estacion: str,
    lat: float,
    lon: float,
    elev: float,
    fecha: str,
    hora: str,
    nivel: int = 1,
) -> str:
    """Formatea linea de encabezado con espaciado exacto Fortran"""
    hora_con_segundos = hora + ":00" if len(hora) == 5 else hora
    linea = f"{estacion:40s}" + f"{lat:12.5f}" + f"{lon:12.5f}" + f"{elev:12.5f}"
    linea += " " + fecha + " " + hora_con_segundos
    linea += f"{nivel:>6d}"
    return linea


def formatear_datos(
    nivel: int,
    num_niveles: int,
    temp_k: float,
    humedad: float,
    presion_pa: float,
    u: float,
    v: float,
    direcc: float,
    rocio_k: float,
) -> str:
    """Formatea linea de datos con espaciado exacto Fortran"""
    # Formato: nivel(6) num_niveles(6) temp(15) humedad(15) presion(15) u(15) v(15) direcc(15) rocio(15)
    linea = f"{nivel:6d}" + f"{num_niveles:6d}"
    linea += f"{temp_k:15.5f}" + f"{humedad:15.5f}" + f"{presion_pa:15.5f}"
    linea += f"{u:15.5f}" + f"{v:15.5f}" + f"{direcc:15.5f}" + f"{rocio_k:15.5f}"
    return linea


def formatear_null() -> str:
    """Formatea linea de nulos/marcador de cierre"""
    # 8 valores de -999999.00000
    linea = ""
    for _ in range(8):
        linea += f"{-999999.00000:15.5f}"
    return linea


def formatear_tailer() -> str:
    """Formatea registro de fin de archivo (tailer)"""
    # 7 lineas de -999999.00000 + 1 linea de ceros
    resultado = ""
    for _ in range(7):
        resultado += f"{-999999.00000:15.5f}" + "\n"
    resultado += "0" * 15 + "0" * 15 + "0" * 15 + "0" * 15
    resultado += "0" * 15 + "0" * 15 + "0" * 15 + "0" * 15
    return resultado


def generar_littler(df: pd.DataFrame, output_path: str = None) -> str:
    """Genera archivo en formato LITTLE_R desde un DataFrame."""
    metadatos = cargar_metadatos()

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = f"data/processed/littler_{timestamp}.txt"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    num_observaciones = 0

    with open(output_path, "w") as f:
        for idx, row in df.iterrows():
            estacion = row.get("estacion", "UNKNOWN")

            # Obtener metadatos
            meta = metadatos.get(estacion, {})
            lat = meta.get("lat", 0.0)
            lon = meta.get("lon", 0.0)
            elev = meta.get("elev", 0.0)

            # Obtener datos
            temp = row.get("temp")
            humedad = row.get("humedad")
            presion = row.get("presion_absoluta")
            viento = row.get("viento")
            direcc = row.get("direcc")
            rocio = row.get("rocio")

            # Convertir a unidades WRF - usar pd.notna() porque NaN no es None
            temp_k = float(temp) + 273.15 if pd.notna(temp) else -999999.0
            humedad_pct = float(humedad) if pd.notna(humedad) else -999999.0
            presion_pa = float(presion) * 100 if pd.notna(presion) else -999999.0
            v_sp = float(viento) if pd.notna(viento) else -999999.0
            u_sp = -999999.0

            direcc_val = float(direcc) if pd.notna(direcc) else -999999.0
            rocio_k = float(rocio) + 273.15 if pd.notna(rocio) else -999999.0

            date_str = row.get("fecha", datetime.now().strftime("%Y-%m-%d"))
            time_str = row.get("hora", "00:00")

            # Escribir linea de encabezado
            f.write(
                formatear_linea(estacion, lat, lon, elev, date_str, time_str, 1) + "\n"
            )

            # Escribir linea de datos
            f.write(
                formatear_datos(
                    1,
                    1,
                    temp_k,
                    humedad_pct,
                    presion_pa,
                    u_sp,
                    v_sp,
                    direcc_val,
                    rocio_k,
                )
                + "\n"
            )

            # Escribir marcador de cierre
            f.write(formatear_null() + "\n")

            num_observaciones += 1

        # Escribir registro de cierre de archivo (tailer)
        f.write(formatear_tailer())

    return output_path, num_observaciones


def _read_last_processed() -> str | None:
    files = sorted(
        Path("data/processed").glob("datos_validados_*.csv"),
        key=os.path.getmtime,
        reverse=True,
    )
    return str(files[0]) if files else None


def main():
    """Ejecutar generador LITTLE_R"""
    csv_path = _read_last_processed()

    if not csv_path:
        print("No hay datos procesados. Ejecuta primero el limpiador.")
        return

    print(f"Procesando: {csv_path}")
    df = pd.read_csv(csv_path)

    output, num_obs = generar_littler(df)
    print(f"Archivo LITTLE_R generado: {output}")
    print(f"Total de observaciones: {num_obs}")
    print("Registro de cierre agregado correctamente.")


if __name__ == "__main__":
    main()
