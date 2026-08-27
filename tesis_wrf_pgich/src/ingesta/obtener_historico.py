#!/usr/bin/env python3
"""
Obtiene datos historicos de EcoWitt para una fecha especifica.

Uso:
    python obtener_historico.py --fecha 2026-07-02

Genera:
    - JSON con datos raw de la API
    - CSV con datos tabulados por estacion
"""

import requests
import json
import csv
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

APP_KEY_REG = os.getenv("ECOWITT_APP_KEY")
API_KEY_REG = os.getenv("ECOWITT_API_KEY")
APP_KEY_ECO = os.getenv("ECOWITT_APP_KEY_ECOHUMUS")
API_KEY_ECO = os.getenv("ECOWITT_API_KEY_ECOHUMUS")

ESTACIONES = {
    "INTA_POCITO": "30:83:98:A7:43:1B",
    "ULLUM_EMBALSE": "30:83:98:A5:CB:17",
    "PUNTA_NEGRA": "30:83:98:A6:BB:72",
}

# ECOHUMUS usa API keys separadas - se maneja por separado en main()


def _fetch_group(mac, app_key, api_key, fecha, call_back):
    """Fetch a single group from the history API."""
    url = "https://api.ecowitt.net/api/v3/device/history"
    params = {
        "application_key": app_key,
        "api_key": api_key,
        "mac": mac,
        "start_date": f"{fecha} 00:00:00",
        "end_date": f"{fecha} 23:59:59",
        "cycle_type": "5min",
        "call_back": call_back,
        "temp_unitid": "1",
        "pressure_unitid": "3",
        "wind_speed_unitid": "7",
        "rainfall_unitid": "12",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 0:
            return data.get("data", {})
        logger.warning(f"API code {data.get('code')}: {data.get('msg', '?')}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout para MAC {mac} group={call_back}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error para MAC {mac}: {e}")
        return None


def _clean_value(val):
    """Return float if valid, else None."""
    if val is None or val == "-" or val == "" or val == "N/A":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _merge_lists(lists):
    """Merge multiple {timestamp: value} dicts, keeping valid values."""
    merged = {}
    for lst in lists:
        for ts, val in lst.items():
            if _clean_value(val) is not None:
                merged[ts] = val
    return merged


def obtener_historico_estacion(mac, app_key, api_key, fecha):
    """Obtiene datos historicos de 1 estacion para 1 dia (por grupo separado)."""
    groups = ["outdoor", "wind", "pressure", "rainfall"]
    all_data = {}

    for grp in groups:
        data = _fetch_group(mac, app_key, api_key, fecha, grp)
        if data:
            all_data.update(data)
        time.sleep(0.34)

    if not all_data:
        return None

    return {"code": 0, "data": all_data}


def _get_list(data, *keys):
    """Navigate nested dict to get a 'list' dict."""
    d = data
    for k in keys:
        d = d.get(k, {})
    if isinstance(d, dict) and "list" in d:
        return d.get("list", {})
    return {}


def _safe_str(val):
    """Convert value to string, return empty string if None or dash."""
    if val is None or val == "-" or val == "":
        return ""
    return str(val)


def convertir_a_csv(respuestas, fecha):
    """Convierte las respuestas a formato CSV tabular."""
    filas = []

    for nombre, data in respuestas.items():
        if not data or data.get("code") != 0:
            logger.warning(f"Sin datos para {nombre}")
            continue

        datos = data.get("data", {})

        temp_list = _get_list(datos, "outdoor", "temperature")
        hum_list = _get_list(datos, "outdoor", "humidity")
        wind_list = _get_list(datos, "wind", "wind_speed")
        gust_list = _get_list(datos, "wind", "wind_gust")
        dir_list = _get_list(datos, "wind", "wind_direction")
        pres_rel_list = _get_list(datos, "pressure", "relative")
        pres_abs_list = _get_list(datos, "pressure", "absolute")
        rain_list = _get_list(datos, "rainfall", "daily")
        solar_list = _get_list(datos, "solar_and_uvi", "solar")

        all_sources = [temp_list, hum_list, wind_list, pres_rel_list]
        all_ts = sorted(set().union(*(s.keys() for s in all_sources if s)))

        for ts in all_ts:
            fecha_hora = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
            filas.append({
                "estacion": nombre,
                "fecha": fecha,
                "hora_unix": ts,
                "fecha_hora": fecha_hora,
                "temp_c": _safe_str(temp_list.get(ts)),
                "humedad_pct": _safe_str(hum_list.get(ts)),
                "viento_kmh": _safe_str(wind_list.get(ts)),
                "viento_rafaga_kmh": _safe_str(gust_list.get(ts)),
                "direcc_grados": _safe_str(dir_list.get(ts)),
                "presion_relativa_hpa": _safe_str(pres_rel_list.get(ts)),
                "presion_absoluta_hpa": _safe_str(pres_abs_list.get(ts)),
                "lluvia_diaria_mm": _safe_str(rain_list.get(ts)),
                "solar_wm2": _safe_str(solar_list.get(ts)),
            })

    return filas


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Obtener datos historicos EcoWitt")
    parser.add_argument("--fecha", required=True, help="Fecha YYYY-MM-DD")
    args = parser.parse_args()

    fecha = args.fecha
    fecha_file = fecha.replace("-", "")
    output_dir = Path(__file__).parent.parent.parent / "historico"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Consultando datos historicos para {fecha}")

    respuestas = {}

    # Estaciones regulares
    for nombre, mac in ESTACIONES.items():
        logger.info(f"Consultando {nombre} ({mac})...")
        data = obtener_historico_estacion(mac, APP_KEY_REG, API_KEY_REG, fecha)
        respuestas[nombre] = data

        if data:
            datos = data.get("data", {})
            temp_list = datos.get("outdoor", {}).get("temperature", {}).get("list", {})
            n_valid = sum(1 for v in temp_list.values() if _clean_value(v) is not None)
            logger.info(f"  {nombre}: {n_valid} registros validos de {len(temp_list)}")
        else:
            logger.warning(f"  {nombre}: Sin datos")

        time.sleep(0.34)

    # ECOHUMUS con API keys separadas
    if APP_KEY_ECO and API_KEY_ECO:
        mac_eco = "BC:FF:4D:F7:DF:DA"
        logger.info(f"Consultando ECOHUMUS ({mac_eco})...")
        data = obtener_historico_estacion(mac_eco, APP_KEY_ECO, API_KEY_ECO, fecha)
        respuestas["ECOHUMUS"] = data

        if data:
            datos = data.get("data", {})
            temp_list = datos.get("outdoor", {}).get("temperature", {}).get("list", {})
            n_valid = sum(1 for v in temp_list.values() if _clean_value(v) is not None)
            logger.info(f"  ECOHUMUS: {n_valid} registros validos de {len(temp_list)}")
        else:
            logger.warning(f"  ECOHUMUS: Sin datos")

    json_path = output_dir / f"ecowitt_historico_{fecha_file}.json"
    json_completo = {
        "fechaconsulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fechadatos": fecha,
        "estaciones": {}
    }

    # Combined MAC lookup for all stations
    macs = dict(ESTACIONES)
    macs["ECOHUMUS"] = "BC:FF:4D:F7:DF:DA"

    for nombre, data in respuestas.items():
        if data and data.get("code") == 0:
            datos = data.get("data", {})
            temp_list = datos.get("outdoor", {}).get("temperature", {}).get("list", {})
            n_valid = sum(1 for v in temp_list.values() if _clean_value(v) is not None)
            json_completo["estaciones"][nombre] = {
                "mac": macs.get(nombre, ""),
                "registros_validos": n_valid,
                "registros_total": len(temp_list),
                "datos": datos,
            }
        else:
            json_completo["estaciones"][nombre] = {
                "mac": macs.get(nombre, ""),
                "registros_validos": 0,
                "registros_total": 0,
                "error": "Sin datos",
            }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_completo, f, indent=2, ensure_ascii=False)
    logger.info(f"JSON guardado: {json_path}")

    csv_path = output_dir / f"ecowitt_historico_{fecha_file}.csv"
    filas = convertir_a_csv(respuestas, fecha)

    if filas:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=filas[0].keys())
            writer.writeheader()
            writer.writerows(filas)
        logger.info(f"CSV guardado: {csv_path} ({len(filas)} filas)")
    else:
        logger.warning("No hay datos para guardar en CSV")

    est_ok = sum(1 for d in respuestas.values() if d and d.get("code") == 0)
    logger.info(f"Resumen: {est_ok}/{len(ESTACIONES)} estaciones con datos")


if __name__ == "__main__":
    main()
