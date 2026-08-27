"""Generador de archivos OBS_DOMAIN101 (Formato 105 de WRF) para asimilación FDDA de superficie."""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger("asimilacion.obsnud")


class ObsNudWriter:
    """Convierte observaciones procesadas al formato OBS_DOMAIN101 (Surface FORMAT 105) de WRF."""

    def __init__(self, config_estaciones_path: Optional[str] = None):
        self.config_path = Path(config_estaciones_path or "config/estaciones.json")

    def _u_v(self, wspd_kmh: Optional[float], wdir_deg: Optional[float]):
        if wspd_kmh is None or wdir_deg is None or pd.isna(wspd_kmh) or pd.isna(wdir_deg):
            return -888888.0, -888888.0, 0.0, 0.0
        vel_ms = float(wspd_kmh) / 3.6
        rad = math.radians(float(wdir_deg))
        u = -vel_ms * math.sin(rad)
        v = -vel_ms * math.cos(rad)
        return u, v, 129.0, 129.0

    def escribir_obsnud(self, observaciones: List[Dict[str, Any]], output_path: str = "data/processed/OBS_DOMAIN101") -> Path:
        """Escribe la lista de observaciones en el archivo destino con formato estricto FORMAT 105."""
        dst_path = Path(output_path)
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        escritas = 0
        with open(dst_path, "w", encoding="utf-8") as f:
            for obs in observaciones:
                nombre = obs.get("estacion", "UNKNOWN")
                lat = float(obs.get("lat", 0.0))
                lon = float(obs.get("lon", 0.0))
                elev = float(obs.get("elev", 0.0))

                dt_str = obs.get("datetime_str")
                if not dt_str:
                    fecha = str(obs.get("fecha", "2026-01-01")).replace("-", "")
                    hora = str(obs.get("hora", "00:00")).replace(":", "")
                    if len(hora) == 4:
                        hora += "00"
                    dt_str = f"{fecha}{hora}"
                else:
                    dt_str = dt_str.replace("-", "").replace(":", "").replace(" ", "")

                # Variables físicas
                t_c = obs.get("temp")
                if t_c is not None and pd.notna(t_c):
                    t_k = float(t_c) + 273.15
                    t_qc = 0.0
                else:
                    t_k = -999999.0
                    t_qc = -888888.0

                rh_val = obs.get("humedad")
                if rh_val is not None and pd.notna(rh_val):
                    rh = float(rh_val)
                    rh_qc = 0.0
                else:
                    rh = -999999.0
                    rh_qc = -888888.0

                p_val = obs.get("presion_absoluta")
                if p_val is None or pd.isna(p_val):
                    p_val = obs.get("presion_relativa")

                if p_val is not None and pd.notna(p_val):
                    psfc_pa = float(p_val) * 100.0
                    psfc_qc = 0.0
                else:
                    psfc_pa = -888888.0
                    psfc_qc = -888888.0

                wspd = obs.get("viento")
                wdir = obs.get("direcc")
                u, v, u_qc, v_qc = self._u_v(wspd, wdir)

                # 1. Timestamp
                f.write(f" {dt_str}\n")
                # 2. Coordenadas
                f.write(f"  {lat:7.4f}  {lon:7.4f} \n")
                # 3. Identificador
                f.write(f"  {nombre:40s}  {'SURFACE':40s}\n")
                # 4. Plataforma y elevación (SYNOP platform, plfo=4)
                f.write(f"        {'SYNOP':>5s}       {nombre:15s}  {int(elev):10d}  F     F       1\n")
                # 5. Formato 105 (9 pares: slp, ref_p, height, t_k, u, v, rh, psfc, precip)
                linea_datos = (
                    f" -888888.000 -888888.000 -888888.000 -888888.000"
                    f"     {elev:7.3f}       0.000"
                    f"     {t_k:7.3f}     {t_qc:7.3f}"
                    f"     {u:7.3f}     {u_qc:7.3f}"
                    f"     {v:7.3f}     {v_qc:7.3f}"
                    f"     {rh:7.3f}     {rh_qc:7.3f}"
                    f"   {psfc_pa:9.3f}     {psfc_qc:7.3f}"
                    f" -888888.000 -888888.000\n"
                )
                f.write(linea_datos)
                escritas += 1

            # Marcador de fin de archivo
            f.write(" -777777.000 -777777.000 -777777.000 -777777.000       0.000       0.000 -777777.000 -777777.000       0.000       0.000       0.000       0.000       0.000       0.000       0.000       0.000 -888888.000 -888888.000\n")

        logger.info(f"OBS_DOMAIN101 generado en {dst_path} con {escritas} observaciones.")
        return dst_path

    def generar_desde_dataframe(self, df: pd.DataFrame, config_estaciones: Optional[Dict[str, Any]] = None, output_path: str = "data/processed/OBS_DOMAIN101") -> Path:
        """Convierte directamente un DataFrame validado a OBS_DOMAIN101."""
        if config_estaciones is None and self.config_path.exists():
            import json
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_estaciones = json.load(f)
        config_estaciones = config_estaciones or {}

        obs_list = []
        for _, row in df.iterrows():
            nombre = str(row.get("estacion", "UNKNOWN"))
            meta = config_estaciones.get(nombre, {})
            obs_list.append({
                "estacion": nombre,
                "lat": meta.get("lat", row.get("lat", 0.0)),
                "lon": meta.get("lon", row.get("lon", 0.0)),
                "elev": meta.get("elev", row.get("elev", 0.0)),
                "fecha": row.get("fecha"),
                "hora": row.get("hora"),
                "temp": row.get("temp"),
                "humedad": row.get("humedad"),
                "presion_absoluta": row.get("presion_absoluta"),
                "presion_relativa": row.get("presion_relativa"),
                "viento": row.get("viento"),
                "direcc": row.get("direcc"),
            })

        return self.escribir_obsnud(obs_list, output_path)
