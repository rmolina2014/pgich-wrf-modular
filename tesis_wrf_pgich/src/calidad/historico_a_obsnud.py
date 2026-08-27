#!/usr/bin/env python3
"""
Convierte datos historicos de EcoWitt a OBS_DOMAIN101 para WRF.

Uso:
    python historico_a_obsnud.py --fecha 2026-07-02
    python historico_a_obsnud.py --csv historico/ecowitt_historico_20260702.csv
    python historico_a_obsnud.py --fecha 2026-07-02 --wrf

Genera:
    - data/processed/littler_YYYY-MM-DD.txt (formato Little_R)
    - data/processed/OBS_DOMAIN101 (formato WRF obs nudging)
"""

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ESTACIONES_VALIDAS = [
    "INTA_POCITO",
    "ULLUM_EMBALSE",
    "ECOHUMUS",
    "PUNTA_NEGRA",
]

COLUMNAS_MAP = {
    "temp_c": "temp",
    "humedad_pct": "humedad",
    "viento_kmh": "viento",
    "viento_rafaga_kmh": "viento_rafaga",
    "direcc_grados": "direcc",
    "presion_relativa_hpa": "presion_relativa",
    "presion_absoluta_hpa": "presion_absoluta",
    "lluvia_diaria_mm": "rain_daily",
    "solar_wm2": "solar",
}

CONTAINER = "teachme"
CONTAINER_WRF_DIR = "/wrf/WRF/test/em_real"

# ---------------------------------------------------------------------------
# Funciones de generacion Little_R (adaptadas de generador_littler.py)
# ---------------------------------------------------------------------------


def cargar_metadatos() -> dict:
    """Carga metadatos de estaciones desde config/estaciones.json"""
    search_paths = [
        Path("config/estaciones.json"),
        Path(__file__).parent.parent.parent / "config" / "estaciones.json",
    ]
    for config_path in search_paths:
        if config_path.exists():
            with open(config_path, "r") as f:
                return json.load(f)
    return {}


def formatear_linea(estacion, lat, lon, elev, fecha, hora, nivel=1):
    """Formatea linea de encabezado con espaciado exacto Fortran"""
    hora_con_segundos = hora + ":00" if len(hora) == 5 else hora
    linea = f"{estacion:40s}" + f"{lat:12.5f}" + f"{lon:12.5f}" + f"{elev:12.5f}"
    linea += " " + fecha + " " + hora_con_segundos
    linea += f"{nivel:>6d}"
    return linea


def formatear_datos(nivel, num_niveles, temp_k, humedad, presion_pa,
                    u, v, direcc, rocio_k):
    """Formatea linea de datos con espaciado exacto Fortran"""
    linea = f"{nivel:6d}" + f"{num_niveles:6d}"
    linea += f"{temp_k:15.5f}" + f"{humedad:15.5f}" + f"{presion_pa:15.5f}"
    linea += f"{u:15.5f}" + f"{v:15.5f}" + f"{direcc:15.5f}" + f"{rocio_k:15.5f}"
    return linea


def formatear_null():
    """Formatea linea de nulos/marcador de cierre"""
    linea = ""
    for _ in range(8):
        linea += f"{-999999.00000:15.5f}"
    return linea


def formatear_tailer():
    """Formatea registro de fin de archivo (tailer)"""
    resultado = ""
    for _ in range(7):
        resultado += f"{-999999.00000:15.5f}" + "\n"
    resultado += "0" * 15 + "0" * 15 + "0" * 15 + "0" * 15
    resultado += "0" * 15 + "0" * 15 + "0" * 15 + "0" * 15
    return resultado


# ---------------------------------------------------------------------------
# Funciones de conversion a OBS_DOMAIN101 (adaptadas de littler_a_obsnud.py)
# ---------------------------------------------------------------------------


def parse_littler_custom(filepath):
    """Parsea el formato Little_R generado por este script"""
    estaciones = []
    with open(filepath) as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("0000000") or stripped == "":
            i += 1
            continue
        if len(line) < 90:
            i += 1
            continue
        if (stripped.replace(".", "").replace("-", "").replace(" ", "").isdigit()
                and len(stripped) > 50):
            i += 1
            continue
        try:
            estacion = line[:40].strip()
            lat = float(line[40:52].strip())
            lon = float(line[52:64].strip())
            elev = float(line[64:76].strip())
            fecha = line[77:87].strip()
            hora = line[88:96].strip()
        except (ValueError, IndexError):
            i += 1
            continue

        if i + 1 >= len(lines):
            break
        data_line = lines[i + 1]
        try:
            nivel = float(data_line[0:6].strip())
            n_niv = float(data_line[6:12].strip())
            temp_k = float(data_line[12:27].strip()) if len(data_line) >= 27 else -999999.0
            humedad = float(data_line[27:42].strip()) if len(data_line) >= 42 else -999999.0
            presion = float(data_line[42:57].strip()) if len(data_line) >= 57 else -999999.0
            u_val = float(data_line[57:72].strip()) if len(data_line) >= 72 else -999999.0
            speed = float(data_line[72:87].strip()) if len(data_line) >= 87 else -999999.0
            direcc = float(data_line[87:102].strip()) if len(data_line) >= 102 else -999999.0
            rocio = float(data_line[102:117].strip()) if len(data_line) >= 117 else -999999.0
        except (ValueError, IndexError):
            i += 3
            continue

        estaciones.append({
            "nombre": estacion,
            "lat": lat,
            "lon": lon,
            "elev": elev,
            "fecha": fecha,
            "hora": hora,
            "temp_k": temp_k,
            "humedad": humedad,
            "presion": presion,
            "speed": speed,
            "direcc": direcc,
            "rocio": rocio,
        })
        i += 3
    return estaciones


def convertir_a_obsnud(estaciones, output_path):
    """Convierte a formato .obsnud que WRF lee (wrf_fddaobs_in.F format 105)"""
    fmt_h1 = " {:<14s}\n"
    fmt_h2 = "  {:<9.4f} {:<9.4f}\n"
    fmt_h3 = "  {:<40s}   {:<40s}   \n"
    fmt_h4 = "  {:<16s}  {:<16s}  {:8.0f}  F     F       1\n"

    with open(output_path, "w") as f:
        for obs in estaciones:
            temp = obs["temp_k"]
            rh = obs["humedad"]
            psfc = obs["presion"]
            elev = obs["elev"]
            speed = obs["speed"]
            direcc = obs["direcc"]
            lat = obs["lat"]
            lon = obs["lon"]
            nombre = obs["nombre"]

            fecha_str = obs["fecha"].replace("-", "")
            hora_str = obs["hora"][:5].replace(":", "") + "00"

            tiene_viento = (speed > -888888 and direcc > -888888
                           and speed >= 0 and direcc >= 0)

            if tiene_viento:
                rad = math.radians(direcc)
                u_met = -speed * math.sin(rad)
                v_met = -speed * math.cos(rad)
                u_qc = 129.0
                v_qc = 129.0
            else:
                u_met = -888888.0
                v_met = -888888.0
                u_qc = -888888.0
                v_qc = -888888.0

            def qc(val):
                return 0.0 if val > -888888 else -888888.0

            date_char = f"{fecha_str}{hora_str}"
            f.write(fmt_h1.format(date_char))
            f.write(fmt_h2.format(lat, lon))

            id_str = f"{nombre:<40s}"
            namef_str = f"{'SURFACE':<40s}"
            f.write(fmt_h3.format(id_str, namef_str))

            platform = f"{'SYNOP':<16s}"
            source = f"{nombre:<16s}"
            f.write(fmt_h4.format(platform, source, elev))

            pares = [
                (-888888.0, -888888.0),
                (-888888.0, -888888.0),
                (elev, qc(elev)),
                (temp, qc(temp)),
                (u_met, u_qc),
                (v_met, v_qc),
                (rh, qc(rh)),
                (psfc, qc(psfc)),
                (-888888.0, -888888.0),
            ]
            linea = ""
            for val, qc_val in pares:
                linea += f"{val:11.3f} {qc_val:11.3f} "
            f.write(" " + linea.rstrip() + "\n")

    return output_path


# ---------------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------------


def cargar_historico(csv_path, fecha=None):
    """Carga CSV historico y filtra estaciones validas."""
    print(f"Leyendo: {csv_path}")
    df = pd.read_csv(csv_path)

    total_registros = len(df)
    total_estaciones = df["estacion"].nunique()
    print(f"  CSV original: {total_registros} registros, {total_estaciones} estaciones")

    # Filtrar estaciones validas
    df = df[df["estacion"].isin(ESTACIONES_VALIDAS)]
    estaciones_filtradas = df["estacion"].unique().tolist()
    estaciones_no_validas = [e for e in df["estacion"].unique()
                            if e not in ESTACIONES_VALIDAS]

    if estaciones_no_validas:
        print(f"  Estaciones descartadas: {', '.join(estaciones_no_validas)}")

    # Filtrar por fecha si se especifica
    if fecha:
        df = df[df["fecha"] == fecha]
        if df.empty:
            print(f"  ERROR: No hay datos para la fecha {fecha}")
            return None

    # Mapear columnas
    df = df.rename(columns=COLUMNAS_MAP)

    # Extraer fecha y hora de fecha_hora
    if "fecha_hora" in df.columns:
        dt = pd.to_datetime(df["fecha_hora"])
        df["fecha"] = dt.dt.strftime("%Y-%m-%d")
        df["hora"] = dt.dt.strftime("%H:%M")

    print(f"  Despues de filtrar: {len(df)} registros, {df['estacion'].nunique()} estaciones")
    return df


def generar_littler_desde_historico(df, output_path):
    """Genera archivo Little_R desde DataFrame historico."""
    metadatos = cargar_metadatos()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Sort by datetime to ensure chronological order (WRF requires this)
    if "fecha_hora" in df.columns:
        df = df.sort_values("fecha_hora").reset_index(drop=True)

    num_observaciones = 0

    with open(output_path, "w") as f:
        for idx, row in df.iterrows():
            estacion = row.get("estacion", "UNKNOWN")

            meta = metadatos.get(estacion, {})
            lat = meta.get("lat", 0.0)
            lon = meta.get("lon", 0.0)
            elev = meta.get("elev", 0.0)

            temp = row.get("temp")
            humedad = row.get("humedad")
            presion = row.get("presion_absoluta")
            viento = row.get("viento")
            direcc = row.get("direcc")
            rocio = row.get("rocio")

            temp_k = float(temp) + 273.15 if pd.notna(temp) else -999999.0
            humedad_pct = float(humedad) if pd.notna(humedad) else -999999.0
            presion_pa = float(presion) * 100 if pd.notna(presion) else -999999.0
            v_sp = float(viento) if pd.notna(viento) else -999999.0
            u_sp = -999999.0
            direcc_val = float(direcc) if pd.notna(direcc) else -999999.0
            rocio_k = float(rocio) + 273.15 if pd.notna(rocio) else -999999.0

            date_str = row.get("fecha", datetime.now().strftime("%Y-%m-%d"))
            time_str = row.get("hora", "00:00")

            f.write(formatear_linea(estacion, lat, lon, elev, date_str, time_str, 1) + "\n")
            f.write(formatear_datos(1, 1, temp_k, humedad_pct, presion_pa,
                                    u_sp, v_sp, direcc_val, rocio_k) + "\n")
            f.write(formatear_null() + "\n")

            num_observaciones += 1

        f.write(formatear_tailer())

    return str(output_path), num_observaciones


def generar_obsdomain(littler_path, output_path):
    """Convierte Little_R a OBS_DOMAIN101."""
    estaciones = parse_littler_custom(str(littler_path))
    if not estaciones:
        print("Error: no se pudieron parsear estaciones del Little_R")
        return None
    convertir_a_obsnud(estaciones, str(output_path))
    return str(output_path)


def docker_cp(src, dst, container=CONTAINER):
    """Copia archivo al contenedor."""
    result = subprocess.run(
        ["docker", "cp", str(src), f"{container}:{dst}"],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0


def docker_exec(cmd, container=CONTAINER, timeout=60):
    """Ejecuta comando dentro del contenedor."""
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode == 0


def copiar_al_wrf(obsdomain_path, container=CONTAINER):
    """Copia OBS_DOMAIN101 al contenedor WRF."""
    print(f"\nCopiando al contenedor {container}...")
    ok = docker_exec(f"mkdir -p {CONTAINER_WRF_DIR}", timeout=15)
    if not ok:
        print(f"  ERROR: Contenedor '{container}' no disponible")
        return False

    ok = docker_cp(obsdomain_path, f"{CONTAINER_WRF_DIR}/OBS_DOMAIN101", container)
    if ok:
        print(f"  Copiado: {container}:{CONTAINER_WRF_DIR}/OBS_DOMAIN101")
    else:
        print(f"  ERROR: No se pudo copiar al contenedor")
    return ok


def imprimir_resumen(df, littler_path, obsdomain_path, num_obs):
    """Imprime resumen de la conversion."""
    print("\n" + "=" * 60)
    print("RESUMEN DE CONVERSION")
    print("=" * 60)

    # Informacion general
    fecha = df["fecha"].iloc[0] if not df.empty else "N/A"
    hora_min = df["hora"].min() if not df.empty else "N/A"
    hora_max = df["hora"].max() if not df.empty else "N/A"

    print(f"\nFecha: {fecha}")
    print(f"Horas cubiertas: {hora_min} - {hora_max}")
    print(f"Total registros: {len(df)}")
    print(f"Observaciones Little_R: {num_obs}")

    # Registros por estacion
    print("\nRegistros por estacion:")
    print("-" * 40)
    for estacion in ESTACIONES_VALIDAS:
        df_est = df[df["estacion"] == estacion]
        if not df_est.empty:
            n = len(df_est)
            t_min = df_est["temp"].min() if "temp" in df_est.columns else None
            t_max = df_est["temp"].max() if "temp" in df_est.columns else None
            temp_str = f"  T: {t_min:.1f}-{t_max:.1f}°C" if t_min is not None else ""
            print(f"  {estacion:<18} {n:>4} registros{temp_str}")
        else:
            print(f"  {estacion:<18}    0 registros (sin datos)")

    # Archivos generados
    print("\nArchivos generados:")
    print("-" * 40)
    if littler_path:
        size_kb = os.path.getsize(littler_path) / 1024
        print(f"  Little_R:    {littler_path} ({size_kb:.1f} KB)")
    if obsdomain_path:
        size_kb = os.path.getsize(obsdomain_path) / 1024
        print(f"  OBS_DOMAIN1: {obsdomain_path} ({size_kb:.1f} KB)")

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Convierte datos historicos EcoWitt a OBS_DOMAIN101 para WRF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Por fecha (busca en historico/)
  python historico_a_obsnud.py --fecha 2026-07-02

  # Por CSV especifico
  python historico_a_obsnud.py --csv historico/ecowitt_historico_20260702.csv

  # Copiar al contenedor WRF
  python historico_a_obsnud.py --fecha 2026-07-02 --wrf

  # Salida personalizada sin docker
  python historico_a_obsnud.py --fecha 2026-07-02 --output-dir results/obs --no-docker
        """
    )

    parser.add_argument("--fecha", "-f",
                        help="Fecha YYYY-MM-DD (busca en historico/)")
    parser.add_argument("--csv", "-c",
                        help="Ruta al CSV historico")
    parser.add_argument("--output-dir", "-o", default="data/processed",
                        help="Directorio de salida (default: data/processed)")
    parser.add_argument("--wrf", "-w", action="store_true",
                        help="Copiar OBS_DOMAIN101 al contenedor WRF")
    parser.add_argument("--container", default=CONTAINER,
                        help=f"Nombre del contenedor Docker (default: {CONTAINER})")
    parser.add_argument("--no-docker", action="store_true",
                        help="No copiar al contenedor")

    args = parser.parse_args()

    # Determinar CSV de entrada
    if args.csv:
        csv_path = args.csv
    elif args.fecha:
        fecha_file = args.fecha.replace("-", "")
        csv_path = f"historico/ecowitt_historico_{fecha_file}.csv"
    else:
        # Usar el mas reciente
        historico_dir = Path("historico")
        if not historico_dir.exists():
            print("ERROR: Directorio historico/ no encontrado")
            return 1
        csvs = sorted(historico_dir.glob("ecowitt_historico_*.csv"))
        if not csvs:
            print("ERROR: No hay CSVs en historico/")
            return 1
        csv_path = str(csvs[-1])
        print(f"Usando CSV mas reciente: {csv_path}")

    if not Path(csv_path).exists():
        print(f"ERROR: No se encuentra {csv_path}")
        return 1

    # Paso 1: Cargar datos historicos
    print("\nPaso 1: Cargando datos historicos...")
    df = cargar_historico(csv_path, args.fecha)
    if df is None or df.empty:
        print("ERROR: No hay datos para procesar")
        return 1

    # Paso 2: Generar Little_R
    print("\nPaso 2: Generando Little_R...")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fecha_label = args.fecha or datetime.now().strftime("%Y-%m-%d")
    littler_path = output_dir / f"littler_{fecha_label}.txt"
    littler_path, num_obs = generar_littler_desde_historico(df, littler_path)
    print(f"  Little_R generado: {littler_path} ({num_obs} observaciones)")

    # Paso 3: Generar OBS_DOMAIN101
    print("\nPaso 3: Generando OBS_DOMAIN101...")
    obsdomain_path = output_dir / "OBS_DOMAIN101"
    obsdomain_path = generar_obsdomain(littler_path, obsdomain_path)
    if not obsdomain_path:
        print("ERROR: Fallo la generacion de OBS_DOMAIN101")
        return 1
    print(f"  OBS_DOMAIN101 generado: {obsdomain_path}")

    # Paso 4: Copiar al contenedor (opcional)
    if args.wrf and not args.no_docker:
        print("\nPaso 4: Copiando al contenedor WRF...")
        copiar_al_wrf(obsdomain_path, args.container)

    # Resumen
    imprimir_resumen(df, littler_path, obsdomain_path, num_obs)

    return 0


if __name__ == "__main__":
    sys.exit(main())
