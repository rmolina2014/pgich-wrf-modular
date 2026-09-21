"""Cálculo de métricas estadísticas objetivas para evaluación y validación de simulaciones."""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("validacion.metrics")

METRICAS_VARIABLES = ["t2", "rh", "wspd", "psfc"]


def correlacion_pearson(
    modelado: np.ndarray, observado: np.ndarray, n_min: int = 3
) -> Dict[str, float]:
    """Correlación de Pearson compartida (mejora 3.8: evitar r duplicado entre
    metrics.py y valida_wrf_cli.py).

    Devuelve {'r': float, 'p_value': float}, con NaN cuando la muestra es demasiado
    chica o la varianza es nula (en lugar de emitir warnings de scipy)."""
    m = np.asarray(modelado, dtype=float)
    o = np.asarray(observado, dtype=float)
    r = float("nan")
    p = float("nan")
    if len(m) >= n_min and np.cov(m, o)[0, 0] > 1e-6 and np.cov(m, o)[1, 1] > 1e-6:
        r_val, p_val = stats.pearsonr(m, o)
        r = float(r_val)
        p = float(p_val)
    return {"r": r, "p_value": p}


def _percentil(valores: np.ndarray, q: float) -> float:
    if len(valores) == 0:
        return float("nan")
    return float(np.nanpercentile(valores, q))


def metricas_par(
    modelado: np.ndarray,
    observado: np.ndarray,
    n_bootstrap: int = 1000,
    semilla: int = 42,
    alpha: float = 0.95,
) -> Dict[str, Any]:
    """Bias, MAE, RMSE, Pearson r y N para un par de series coincidentes, con
    intervalos de confianza por bootstrap (mejora 3.3 del informe_mejoras_f4).

    Los IC (lo-hi) se calculan para bias/mae/rmse remuestreando los errores
    (modelado-observado) con reemplazo. Devuelve NaN donde no es computable."""
    mask = (~np.isnan(modelado)) & (~np.isnan(observado))
    m = np.asarray(modelado, dtype=float)[mask]
    o = np.asarray(observado, dtype=float)[mask]
    n = len(m)
    nan = float("nan")

    if n == 0:
        return {
            "bias": nan, "mae": nan, "rmse": nan, "r": nan, "n": 0,
            "bias_ci": [nan, nan], "mae_ci": [nan, nan], "rmse_ci": [nan, nan],
        }

    err = m - o
    bias = float(np.mean(err))
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))

    corr = correlacion_pearson(m, o)

    # El bootstrap necesita al menos 2 puntos para tener sentido: con n=1,
    # cualquier remuestreo con reemplazo devuelve siempre el mismo valor, lo
    # que da un IC de ancho cero — no es "maxima precision", es ausencia total
    # de informacion sobre la incertidumbre. Se deja bias/mae/rmse (validos
    # con un solo punto) pero el IC queda en NaN en ese caso.
    if n < 2:
        bias_ci = [nan, nan]
        mae_ci = [nan, nan]
        rmse_ci = [nan, nan]
    else:
        ci_lo = (1.0 - alpha) / 2.0 * 100
        ci_hi = (1.0 + alpha) / 2.0 * 100
        rng = np.random.default_rng(semilla)
        bias_b, mae_b, rmse_b = [], [], []
        for _ in range(n_bootstrap):
            muestra = err[rng.integers(0, n, size=n)]
            bias_b.append(float(np.mean(muestra)))
            mae_b.append(float(np.mean(np.abs(muestra))))
            rmse_b.append(float(np.sqrt(np.mean(muestra ** 2))))
        bias_ci = [_percentil(bias_b, ci_lo), _percentil(bias_b, ci_hi)]
        mae_ci = [_percentil(mae_b, ci_lo), _percentil(mae_b, ci_hi)]
        rmse_ci = [_percentil(rmse_b, ci_lo), _percentil(rmse_b, ci_hi)]

    return {
        "bias": bias,
        "mae": mae,
        "rmse": rmse,
        "r": corr["r"],
        "p_value": corr["p_value"],
        "n": int(n),
        "bias_ci": bias_ci,
        "mae_ci": mae_ci,
        "rmse_ci": rmse_ci,
    }


class MetricsCalculator:
    """Calculador de estadísticas de rendimiento de modelos meteorológicos."""

    @staticmethod
    def calcular_metricas_par(modelado: np.ndarray, observado: np.ndarray) -> Dict[str, Optional[float]]:
        """Calcula Bias, MAE, RMSE, Pearson r y N para un par de series coincidentes
        (r vía la función compartida `correlacion_pearson`, mejora 3.8)."""
        mask = (~np.isnan(modelado)) & (~np.isnan(observado))
        m = np.asarray(modelado, dtype=float)[mask]
        o = np.asarray(observado, dtype=float)[mask]
        n = len(m)

        if n == 0:
            return {"bias": None, "mae": None, "rmse": None, "r": None, "p_value": None, "n": 0}

        bias = float(np.mean(m - o))
        mae = float(np.mean(np.abs(m - o)))
        rmse = float(np.sqrt(np.mean((m - o) ** 2)))

        corr = correlacion_pearson(m, o)
        r = corr["r"] if corr["r"] == corr["r"] else None
        p = corr["p_value"] if corr["p_value"] == corr["p_value"] else None

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
