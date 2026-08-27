"""Cliente HTTP robusto para la adquisición de datos de estaciones meteorológicas EcoWitt."""

import os
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("ingesta.ecowitt")

ESTACIONES_PGICH = {
    "INTA_POCITO": "30:83:98:A7:43:1B",
    "ULLUM_EMBALSE": "30:83:98:A5:CB:17",
    "PUNTA_NEGRA": "30:83:98:A6:BB:72",
}

ECOHUMUS_MAC = "BC:FF:4D:F7:DF:DA"


class EcowittIngestor:
    """Cliente para la API de EcoWitt (v3) con control de rate limit y manejo de errores."""

    _ultima_peticion = 0.0
    _min_intervalo = 1.0  # segundos entre peticiones

    def __init__(
        self,
        app_key: Optional[str] = None,
        api_key: Optional[str] = None,
        app_key_ecohumus: Optional[str] = None,
        api_key_ecohumus: Optional[str] = None,
    ):
        self.base_url_rt = "https://api.ecowitt.net/api/v3/device/real_time"
        self.base_url_hist = "https://api.ecowitt.net/api/v3/device/history"
        self.app_key = app_key or os.getenv("ECOWITT_APP_KEY")
        self.api_key = api_key or os.getenv("ECOWITT_API_KEY")
        self.app_key_ecohumus = app_key_ecohumus or os.getenv("ECOWITT_APP_KEY_ECOHUMUS")
        self.api_key_ecohumus = api_key_ecohumus or os.getenv("ECOWITT_API_KEY_ECOHUMUS")

    def tiene_credenciales(self) -> bool:
        """Verifica si las credenciales principales están presentes."""
        return bool(self.app_key and self.api_key and len(self.app_key) >= 10 and len(self.api_key) >= 10)

    def _esperar_rate_limit(self):
        ahora = time.time()
        tiempo_transcurrido = ahora - self._ultima_peticion
        if tiempo_transcurrido < self._min_intervalo:
            time.sleep(self._min_intervalo - tiempo_transcurrido)
        self._ultima_peticion = time.time()

    def obtener_datos_tiempo_real(self, mac_address: str, app_key: Optional[str] = None, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Consulta datos de tiempo real para una MAC específica."""
        self._esperar_rate_limit()
        ak = app_key or self.app_key
        sk = api_key or self.api_key

        if not ak or not sk:
            logger.error("No hay credenciales configuradas para consultar EcoWitt.")
            return None

        params = {
            "application_key": ak,
            "api_key": sk,
            "mac": mac_address,
            "call_back": "all",
            "temp_unitid": "1",          # Celsius
            "pressure_unitid": "3",      # hPa
            "wind_speed_unitid": "7",    # km/h
            "rainfall_unitid": "12",     # mm
            "solar_irradiance_unitid": "16", # W/m2
        }

        try:
            response = requests.get(self.base_url_rt, params=params, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            if res_json.get("code") == 0:
                return res_json
            logger.warning(f"EcoWitt API code {res_json.get('code')}: {res_json.get('msg')}")
            return None
        except Exception as e:
            logger.error(f"Error consultando MAC {mac_address}: {e}")
            return None

    def extraer_datos_estacion(self, data: Optional[Dict[str, Any]], nombre_estacion: str) -> Dict[str, Any]:
        """Normaliza la respuesta JSON de EcoWitt a un diccionario plano estandarizado."""
        if not data or "data" not in data:
            return {"estacion": nombre_estacion, "error": "Sin datos"}

        raw_data = data["data"]
        if isinstance(raw_data, list):
            if not raw_data:
                return {"estacion": nombre_estacion, "error": "Sin datos (lista vacía)"}
            raw_data = raw_data[0]

        timestamp = int(data.get("time", time.time()))
        dt = datetime.fromtimestamp(timestamp)

        return {
            "estacion": nombre_estacion,
            "time_unix": timestamp,
            "fecha": dt.strftime("%Y-%m-%d"),
            "hora": dt.strftime("%H:%M"),
            "temp": raw_data.get("outdoor", {}).get("temperature", {}).get("value"),
            "humedad": raw_data.get("outdoor", {}).get("humidity", {}).get("value"),
            "viento": raw_data.get("wind", {}).get("wind_speed", {}).get("value"),
            "viento_rafaga": raw_data.get("wind", {}).get("wind_gust", {}).get("value"),
            "direcc": raw_data.get("wind", {}).get("wind_direction", {}).get("value"),
            "presion_relativa": raw_data.get("pressure", {}).get("relative", {}).get("value"),
            "presion_absoluta": raw_data.get("pressure", {}).get("absolute", {}).get("value"),
            "rain_daily": raw_data.get("rainfall", {}).get("daily", {}).get("value"),
            "rain_monthly": raw_data.get("rainfall", {}).get("monthly", {}).get("value"),
            "solar": raw_data.get("solar_and_uvi", {}).get("solar", {}).get("value"),
            "termica": raw_data.get("outdoor", {}).get("feels_like", {}).get("value"),
            "rocio": raw_data.get("outdoor", {}).get("dew_point", {}).get("value"),
        }

    def consultar_todas_las_estaciones(self) -> List[Dict[str, Any]]:
        """Consulta todas las estaciones PGICH incluyendo ECOHUMUS."""
        resultados = []

        # 1. Estaciones con credenciales estándar
        for nombre, mac in ESTACIONES_PGICH.items():
            data = self.obtener_datos_tiempo_real(mac, self.app_key, self.api_key)
            if data:
                resultados.append(self.extraer_datos_estacion(data, nombre))
            else:
                resultados.append({"estacion": nombre, "error": "Sin respuesta"})

        # 2. ECOHUMUS
        if self.app_key_ecohumus and self.api_key_ecohumus:
            data_eco = self.obtener_datos_tiempo_real(ECOHUMUS_MAC, self.app_key_ecohumus, self.api_key_ecohumus)
            if data_eco:
                resultados.append(self.extraer_datos_estacion(data_eco, "ECOHUMUS"))
            else:
                resultados.append({"estacion": "ECOHUMUS", "error": "Sin respuesta"})

        return resultados

    def guardar_json_crudo(self, resultados: List[Dict[str, Any]], output_dir: str = "data/raw") -> str:
        """Guarda la lista de observaciones crudas en formato JSON."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        archivo = os.path.join(output_dir, f"ecowitt_todos_{ts}.json")
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)
        logger.info(f"Observaciones guardadas en: {archivo}")
        return archivo
