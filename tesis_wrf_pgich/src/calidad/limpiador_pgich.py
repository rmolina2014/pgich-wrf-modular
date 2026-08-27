import pandas as pd
import json
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def procesar_json_ecowitt(ruta_archivo):
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Procesando {len(data)} registros del archivo JSON")

    valid_data = [obs for obs in data if "error" not in obs]
    logger.info(f"Estaciones validas: {len(valid_data)} de {len(data)}")

    if not valid_data:
        raise ValueError("No hay estaciones con datos validos")

    df = pd.DataFrame(valid_data)

    cols_numericas = [
        "temp",
        "humedad",
        "viento",
        "viento_rafaga",
        "direcc",
        "presion_relativa",
        "presion_absoluta",
        "rain_daily",
        "rain_monthly",
        "solar",
        "termica",
        "rocio",
    ]
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["timestamp"] = pd.to_datetime(df["fecha"] + " " + df["hora"])
    df["time_unix"] = pd.to_numeric(df["time_unix"], errors="coerce")

    logger.info(f"DataFrame creado con {len(df)} filas y {len(df.columns)} columnas")

    return df


def generar_resumen_estadistico(df):
    cols_numericas = df.select_dtypes(include=["float64", "int64"]).columns
    return df[cols_numericas].describe()


def guardar_procesado(df, nombre_base=None):
    nombre_base = nombre_base or datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs("data/processed", exist_ok=True)

    csv_path = f"data/processed/datos_validados_{nombre_base}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    logger.info(f"CSV guardado: {csv_path}")

    excel_path = f"data/processed/datos_validados_{nombre_base}.xlsx"
    df.to_excel(excel_path, index=False, engine="openpyxl")
    logger.info(f"Excel guardado: {excel_path}")

    return csv_path, excel_path


if __name__ == "__main__":
    try:
        archivos = sorted(
            [f for f in os.listdir("data/raw") if f.startswith("ecowitt_todos")],
            reverse=True,
        )

        if not archivos:
            print("No se encontraron archivos JSON en data/raw")
            exit(1)

        archivo_mas_reciente = os.path.join("data/raw", archivos[0])
        logger.info(f"Procesando archivo: {archivo_mas_reciente}")

        df_limpio = procesar_json_ecowitt(archivo_mas_reciente)

        print("\n" + "=" * 50)
        print("RESUMEN DE ESTACIONES ACTIVAS")
        print("=" * 50)
        print(df_limpio[["estacion", "temp", "humedad", "presion_absoluta", "viento"]])

        print("\n" + "=" * 50)
        print("ESTADISTICAS DESCRIPTIVAS")
        print("=" * 50)
        print(generar_resumen_estadistico(df_limpio))

        guardar_procesado(df_limpio)

    except FileNotFoundError as e:
        logger.error(f"Archivo no encontrado: {e}")
        exit(1)
    except ValueError as e:
        logger.error(f"Error de validacion: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {type(e).__name__} - {e}")
        exit(1)
