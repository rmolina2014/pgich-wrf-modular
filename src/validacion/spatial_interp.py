"""Interpolación espacial rigurosa de variables WRF a coordenadas de estaciones meteorológicas."""

import math
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import xarray as xr

logger = logging.getLogger("validacion.spatial_interp")


class SpatialInterpolator:
    """Interpola los campos 2D/3D de salida de WRF a las coordenadas exactas de las estaciones."""

    @staticmethod
    def q2_a_humedad_relativa(q2: float, t2: float, psfc: float) -> float:
        """Calcula Humedad Relativa (%) a partir de Q2 (kg/kg), T2 (K) y PSFC (Pa)."""
        temp_c = t2 - 273.15
        # Presión de saturación de vapor de agua (Tetens / Magnus)
        es = 611.2 * math.exp((17.67 * temp_c) / (temp_c + 243.5))
        qs = 0.622 * es / (psfc - 0.378 * es)
        if qs <= 0:
            return 0.0
        rh = (q2 / qs) * 100.0
        return float(np.clip(rh, 0.0, 100.0))

    @staticmethod
    def u_v_a_velocidad_direccion(u: float, v: float) -> Tuple[float, float]:
        """Convierte componentes zonales y meridionales u, v (m/s) a velocidad (m/s) y dirección (°)."""
        speed = math.sqrt(u**2 + v**2)
        direction = (270.0 - math.degrees(math.atan2(v, u))) % 360.0
        return speed, direction

    def interpolar_4_nodos(self, ds: xr.Dataset, var_name: str, lat: float, lon: float) -> float:
        """Realiza una interpolación bilineal/IDW ponderada por distancia sobre los 4 nodos más cercanos."""
        lats = ds.XLAT.values[0] if ds.XLAT.ndim == 3 else ds.XLAT.values
        lons = ds.XLONG.values[0] if ds.XLONG.ndim == 3 else ds.XLONG.values
        data = ds[var_name].values[0] if ds[var_name].ndim >= 3 else ds[var_name].values

        # Localizar índices de malla
        j = np.searchsorted(lats[:, 0], lat) - 1
        i = np.searchsorted(lons[0, :], lon) - 1

        j = max(0, min(j, lats.shape[0] - 2))
        i = max(0, min(i, lats.shape[1] - 2))

        lat_sw, lat_se = lats[j, i], lats[j, i + 1]
        lat_nw, lat_ne = lats[j + 1, i], lats[j + 1, i + 1]
        lon_sw, lon_se = lons[j, i], lons[j, i + 1]
        lon_nw, lon_ne = lons[j + 1, i], lons[j + 1, i + 1]

        lat_ref = (lat_sw + lat_se + lat_nw + lat_ne) / 4.0
        lon_ref = (lon_sw + lon_se + lon_nw + lon_ne) / 4.0

        dlon = math.cos(math.radians(lat_ref))
        dlat = 1.0

        x_sw = (lon_sw - lon_ref) * dlon
        x_se = (lon_se - lon_ref) * dlon
        x_nw = (lon_nw - lon_ref) * dlon
        x_ne = (lon_ne - lon_ref) * dlon

        y_sw = (lat_sw - lat_ref) * dlat
        y_se = (lat_se - lat_ref) * dlat
        y_nw = (lat_nw - lat_ref) * dlat
        y_ne = (lat_ne - lat_ref) * dlat

        xp = (lon - lon_ref) * dlon
        yp = (lat - lat_ref) * dlat

        c = np.array([x_sw, x_se, x_nw, x_ne])
        r = np.array([y_sw, y_se, y_nw, y_ne])
        v = np.array([data[j, i], data[j, i + 1], data[j + 1, i], data[j + 1, i + 1]])

        dist2 = (c - xp) ** 2 + (r - yp) ** 2
        dist2 = np.maximum(dist2, 1e-12)
        pesos = 1.0 / dist2

        return float(np.sum(pesos * v) / np.sum(pesos))

    def extraer_variables_estacion(self, ds: xr.Dataset, lat: float, lon: float, elev_estacion: Optional[float] = None) -> Dict[str, float]:
        """Extrae e interpola todas las variables meteorológicas de superficie para una estación."""
        t2 = self.interpolar_4_nodos(ds, "T2", lat, lon)
        psfc = self.interpolar_4_nodos(ds, "PSFC", lat, lon)
        q2 = self.interpolar_4_nodos(ds, "Q2", lat, lon)
        u10 = self.interpolar_4_nodos(ds, "U10", lat, lon)
        v10 = self.interpolar_4_nodos(ds, "V10", lat, lon)
        hgt = self.interpolar_4_nodos(ds, "HGT", lat, lon)

        rh = self.q2_a_humedad_relativa(q2, t2, psfc)
        wspd, wdir = self.u_v_a_velocidad_direccion(u10, v10)

        # Corrección barométrica si se dispone de la elevación real vs orografía del modelo
        if elev_estacion is not None and not math.isnan(elev_estacion):
            delta_h = elev_estacion - hgt
            # Gradiente térmico estándar ~ 6.5 K / km
            t2_corregida = t2 - (0.0065 * delta_h)
            # Presión barométrica barométrica barométrica
            psfc_corregida = psfc * math.exp(-9.81 * 0.02896 / (8.314 * t2) * delta_h)
        else:
            t2_corregida = t2
            psfc_corregida = psfc

        return {
            "t2": t2,
            "t2_corregida": t2_corregida,
            "t2_c": t2 - 273.15,
            "psfc": psfc,
            "psfc_hpa": psfc / 100.0,
            "psfc_corregida_hpa": psfc_corregida / 100.0,
            "q2": q2,
            "rh": rh,
            "u10": u10,
            "v10": v10,
            "wspd": wspd,
            "wspd_kmh": wspd * 3.6,
            "wdir": wdir,
            "hgt_modelo": hgt,
        }
