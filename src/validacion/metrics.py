"""Cálculo de métricas estadísticas objetivas para evaluación y validación de simulaciones."""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("validacion.metrics")

METRICAS_VARIABLES = ["t2", "rh", "wspd", "psfc"]


class MetricsCalculator:
    """Calculador de estadísticas de rendimiento de modelos meteorológicos."""

    @staticmethod
    def calcular_metricas_par(modelado: np.ndarray, observado: np.ndarray) -> Dict[str, Optional[float]]:
        """Calcula Bias, MAE, RMSE, Pearson r y N para un par de series coincidentes."""
        mask = (~np.isnan(modelado)) & (~np.isnan(observado))
        m = modelado[mask]
        o = observado[mask]
        n = len(m)

        if n == 0:
            return {"bias": None, "mae": None, "rmse": None, "r": None, "p_value": None, "n": 0}

        bias = float(np.mean(m - o))
        mae = float(np.mean(np.abs(m - o)))
        rmse = float(np.sqrt(np.mean((m - o) ** 2)))

        if n >= 3 and np.std(m) > 1e-6 and np.std(o) > 1e-6:
            r_val, p_val = stats.pearsonr(m, o)
            r = float(r_val)
            p = float(p_val)
        else:
            r = None
            p = None

        return {
            "bias": round(bias, 3),
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r": round(r, 3) if r is not None else None,
            "p_value": round(p, 4) if p is not None else None,
            "n": int(n),
        }

    @staticmethod
    def calcular_mejora_rmse(rmse_control: Optional[float], rmse_nudged: Optional[float]) -> Optional[float]:
        """Calcula el porcentaje de mejora en RMSE respecto a la corrida de control."""
        if rmse_control is None or rmse_nudged is None or rmse_control <= 1e-6:
            return None
        mejora = ((rmse_control - rmse_nudged) / rmse_control) * 100.0
        return round(mejora, 2)

    def comparar_corridas(
        self,
        df_evaluacion: pd.DataFrame,
        col_obs_prefix: str = "obs_",
        col_nudged_prefix: str = "nudged_",
        col_control_prefix: str = "control_",
    ) -> Dict[str, Dict[str, Any]]:
        """Genera un reporte comparativo completo de métricas para todas las variables."""
        resultados = {}

        for var in METRICAS_VARIABLES:
            col_obs = f"{col_obs_prefix}{var}"
            col_nudged = f"{col_nudged_prefix}{var}"
            col_control = f"{col_control_prefix}{var}"

            if col_obs not in df_evaluacion.columns:
                continue

            obs_vals = df_evaluacion[col_obs].to_numpy(dtype=float)
            nud_vals = df_evaluacion[col_nudged].to_numpy(dtype=float) if col_nudged in df_evaluacion.columns else np.array([])
            ctl_vals = df_evaluacion[col_control].to_numpy(dtype=float) if col_control in df_evaluacion.columns else np.array([])

            m_nudged = self.calcular_metricas_par(nud_vals, obs_vals) if len(nud_vals) > 0 else {}
            m_control = self.calcular_metricas_par(ctl_vals, obs_vals) if len(ctl_vals) > 0 else {}

            mejora_rmse = self.calcular_mejora_rmse(m_control.get("rmse"), m_nudged.get("rmse"))

            resultados[var] = {
                "control": m_control,
                "nudged": m_nudged,
                "mejora_rmse_pct": mejora_rmse,
            }

        return resultados
