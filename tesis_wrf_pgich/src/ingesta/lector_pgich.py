import requests
import json
import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ESTACIONES = {
    "INTA_POCITO": "30:83:98:A7:43:1B",
    "ULLUM_EMBALSE": "30:83:98:A5:CB:17",
    "PUNTA_NEGRA": "30:83:98:A6:BB:72",
}

# ECOHUMUS usa API keys separadas - se maneja por separado en guardar_todos_con_ecohumus()


class EcowittIngestor:
    _ultima_peticion = 0
    _min_intervalo = 1.0

    def __init__(self, app_key=None, api_key=None):
        self.base_url = "https://api.ecowitt.net/api/v3/device/real_time"
        self.app_key = app_key or os.getenv("ECOWITT_APP_KEY")
        self.api_key = api_key or os.getenv("ECOWITT_API_KEY")
        self._validar_credenciales()

    def _validar_credenciales(self):
        if not self.app_key or not self.api_key:
            raise ValueError("Faltan credenciales: APP_KEY o API_KEY no configuradas")
        if len(self.app_key) < 10 or len(self.api_key) < 10:
            raise ValueError("Credenciales inválidas: longitud insuficiente")
        logger.info("Credenciales validadas correctamente")

    def _esperar_rate_limit(self):
        ahora = time.time()
        tiempo_transcurrido = ahora - self._ultima_peticion
        if tiempo_transcurrido < self._min_intervalo:
            time.sleep(self._min_intervalo - tiempo_transcurrido)
        self._ultima_peticion = time.time()

    def obtener_datos_estacion(self, mac_address):
        self._esperar_rate_limit()

        params = {
            "application_key": self.app_key,
            "api_key": self.api_key,
            "mac": mac_address,
            "call_back": "all",
            "temp_unitid": "1",
            "pressure_unitid": "3",
            "wind_speed_unitid": "7",
            "rainfall_unitid": "12",
            "solar_irradiance_unitid": "16",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al conectar con MAC {mac_address}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP {e.response.status_code} para MAC {mac_address}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexion con MAC {mac_address}: {type(e).__name__}")
            return None

    def extraer_datos_meteorologicos(self, data, estacion):
        if not data or "data" not in data:
            return None

        raw_data = data["data"]
        if isinstance(raw_data, list):
            if not raw_data:
                return {"estacion": estacion, "error": "Sin datos (lista vacia)"}
            raw_data = raw_data[0]

        return {
            "estacion": estacion,
            "time_unix": data.get("time"),
            "fecha": datetime.fromtimestamp(int(data["time"])).strftime("%Y-%m-%d"),
            "hora": datetime.fromtimestamp(int(data["time"])).strftime("%H:%M"),
            "temp": raw_data.get("outdoor", {}).get("temperature", {}).get("value"),
            "humedad": raw_data.get("outdoor", {}).get("humidity", {}).get("value"),
            "viento": raw_data.get("wind", {}).get("wind_speed", {}).get("value"),
            "viento_rafaga": raw_data.get("wind", {}).get("wind_gust", {}).get("value"),
            "direcc": raw_data.get("wind", {}).get("wind_direction", {}).get("value"),
            "presion_relativa": raw_data.get("pressure", {})
            .get("relative", {})
            .get("value"),
            "presion_absoluta": raw_data.get("pressure", {})
            .get("absolute", {})
            .get("value"),
            "rain_daily": raw_data.get("rainfall", {}).get("daily", {}).get("value"),
            "rain_monthly": raw_data.get("rainfall", {})
            .get("monthly", {})
            .get("value"),
            "solar": raw_data.get("solar_and_uvi", {}).get("solar", {}).get("value"),
            "termica": raw_data.get("outdoor", {}).get("feels_like", {}).get("value"),
            "rocio": raw_data.get("outdoor", {}).get("dew_point", {}).get("value"),
        }

    def formatear_linea(self, datos):
        lineas = []
        for key, value in datos.items():
            lineas.append(f"{key}: {value if value is not None else 'N/A'}")
        return "\n".join(lineas)

    def obtener_todas_estaciones(self, estaciones_dict):
        resultados = []
        logger.info(f"Iniciando consulta de {len(estaciones_dict)} estaciones")
        for nombre, mac in estaciones_dict.items():
            logger.debug(f"Consultando estacion: {nombre} ({mac})")
            data = self.obtener_datos_estacion(mac)
            if data:
                datos = self.extraer_datos_meteorologicos(data, nombre)
                resultados.append(datos)
            else:
                resultados.append({"estacion": nombre, "error": "Sin datos"})
        logger.info(f"Consulta completada: {len(resultados)} resultados")
        return resultados

    def guardar_raw(self, datos, nombre_estacion):
        if not datos:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"data/raw/ecowitt_{nombre_estacion}_{timestamp}.json"

        os.makedirs("data/raw", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        logger.info(f"Datos guardados: {filename}")

    def guardar_todos(self, estaciones_dict):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"data/raw/ecowitt_todos_{timestamp}.json"

        os.makedirs("data/raw", exist_ok=True)
        resultados = self.obtener_todas_estaciones(estaciones_dict)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)
        logger.info(f"Datos guardados: {filename}")
        return resultados

    def guardar_todos_con_ecohumus(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"data/raw/ecowitt_todos_{timestamp}.json"
        
        os.makedirs("data/raw", exist_ok=True)
        resultados = []
        
        # Estaciones regulares
        app_key = os.getenv("ECOWITT_APP_KEY")
        api_key = os.getenv("ECOWITT_API_KEY")
        
        ingestor = EcowittIngestor(app_key, api_key)
        resultados_regulares = ingestor.obtener_todas_estaciones(ESTACIONES)
        resultados.extend(resultados_regulares)
        
        # ECOHUMUS con API keys separadas
        app_key_eco = os.getenv("ECOWITT_APP_KEY_ECOHUMUS")
        api_key_eco = os.getenv("ECOWITT_API_KEY_ECOHUMUS")
        
        if app_key_eco and api_key_eco:
            ingestor_eco = EcowittIngestor(app_key_eco, api_key_eco)
            mac_eco = "BC:FF:4D:F7:DF:DA"
            data_eco = ingestor_eco.obtener_datos_estacion(mac_eco)
            if data_eco:
                datos_eco = ingestor_eco.extraer_datos_meteorologicos(data_eco, "ECOHUMUS")
                resultados.append(datos_eco)
            else:
                resultados.append({"estacion": "ECOHUMUS", "error": "Sin datos"})
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=4, ensure_ascii=False)
        logger.info(f"Datos guardados: {filename}")
        return resultados


if __name__ == "__main__":
    try:
        APP_KEY = os.getenv("ECOWITT_APP_KEY")
        API_KEY = os.getenv("ECOWITT_API_KEY")

        if not APP_KEY or not API_KEY:
            print("Error: Faltan credenciales en .env")
            exit(1)

        ingestor = EcowittIngestor(APP_KEY, API_KEY)
        resultados = ingestor.guardar_todos_con_ecohumus()

        for datos in resultados:
            if "error" not in datos:
                print(f"\n{'-' * 40}")
                print(f"ESTACION: {datos['estacion']}")
                print(f"{'-' * 40}")
                print(ingestor.formatear_linea(datos))
    except ValueError as e:
        print(f"Error de configuracion: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {type(e).__name__}")
        exit(1)
