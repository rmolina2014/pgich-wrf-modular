"""Generador de figuras científicas para validación de simulaciones meteorológicas."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger("reporting.plots")


class PlotGenerator:
    """Generador de gráficos estadísticos y espaciales."""

    def __init__(self, style_dark: bool = False):
        plt.style.use("default")
        self.color_nudged = "#1f77b4"  # Azul
        self.color_control = "#d62728" # Rojo
        self.color_obs = "#2ca02c"     # Verde

    def generar_scatter_4panels(
        self,
        df_eval: pd.DataFrame,
        output_path: str = "plots/scatter_4panels.png",
        titulo: str = "Dispersión Observado vs Modelado",
    ) -> Path:
        """Genera un gráfico 2x2 comparando T2, RH, WSPD y PSFC."""
        dst = Path(output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        vars_config = [
            ("t2", "Temperatura 2m (K)", axes[0, 0]),
            ("rh", "Humedad Relativa (%)", axes[0, 1]),
            ("wspd", "Viento 10m (m/s)", axes[1, 0]),
            ("psfc", "Presión Superficie (hPa)", axes[1, 1]),
        ]

        for var, label, ax in vars_config:
            col_obs = f"obs_{var}"
            col_nud = f"nudged_{var}"
            col_ctl = f"control_{var}"

            if col_obs in df_eval.columns:
                obs = df_eval[col_obs].dropna()
                if col_ctl in df_eval.columns:
                    ax.scatter(df_eval[col_obs], df_eval[col_ctl], color=self.color_control, alpha=0.6, label="Control", edgecolors="none")
                if col_nud in df_eval.columns:
                    ax.scatter(df_eval[col_obs], df_eval[col_nud], color=self.color_nudged, alpha=0.7, label="Nudged (Asimilado)", marker="^")

                # Línea 1:1
                val_min = min(df_eval[col_obs].min(), df_eval.get(col_nud, obs).min())
                val_max = max(df_eval[col_obs].max(), df_eval.get(col_nud, obs).max())
                if pd.notna(val_min) and pd.notna(val_max):
                    ax.plot([val_min, val_max], [val_min, val_max], "k--", alpha=0.5, label="1:1 Ideal")

            ax.set_title(label, fontsize=12, fontweight="bold")
            ax.set_xlabel("Observado", fontsize=10)
            ax.set_ylabel("Modelado", fontsize=10)
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.legend(fontsize=9)

        fig.suptitle(titulo, fontsize=14, fontweight="bold")
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])
        fig.savefig(dst, dpi=200)
        plt.close(fig)

        logger.info(f"Scatter plot 4 paneles guardado en {dst}")
        return dst

    def generar_mapa_errores(
        self,
        estaciones_metrics: List[Dict[str, Any]],
        output_path: str = "plots/mapa_errores_t2.png",
        variable_error: str = "bias_t2",
    ) -> Path:
        """Genera un mapa espacial de San Juan con los errores por estación."""
        dst = Path(output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(9, 8))

        lats = [e["lat"] for e in estaciones_metrics if "lat" in e]
        lons = [e["lon"] for e in estaciones_metrics if "lon" in e]
        nombres = [e["name"] for e in estaciones_metrics if "name" in e]
        errores = [e.get(variable_error, 0.0) for e in estaciones_metrics]

        sc = ax.scatter(lons, lats, c=errores, cmap="coolwarm", s=250, edgecolors="black", linewidth=1.5, zorder=5)
        cbar = plt.colorbar(sc, ax=ax, shrink=0.8)
        cbar.set_label(f"Error {variable_error.upper()}", fontsize=10)

        for lon, lat, nom, err in zip(lons, lats, nombres, errores):
            ax.annotate(
                f"{nom}\n({err:+.2f})",
                (lon, lat),
                textcoords="offset points",
                xytext=(0, 12),
                ha="center",
                fontsize=9,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8, ec="gray"),
            )

        ax.set_title(f"Distribución Espacial de Errores - {variable_error.upper()}", fontsize=13, fontweight="bold")
        ax.set_xlabel("Longitud (°W)", fontsize=10)
        ax.set_ylabel("Latitud (°S)", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.5)

        fig.tight_layout()
        fig.savefig(dst, dpi=200)
        plt.close(fig)

        logger.info(f"Mapa de errores guardado en {dst}")
        return dst
