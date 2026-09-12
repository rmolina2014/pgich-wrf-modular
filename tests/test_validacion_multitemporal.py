"""Pruebas de la validación multi-temporal (informe de evolución del nudging)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.validacion.valida_wrf_cli import (
    build_tables,
    plot_evolucion,
    write_tabla_evolutiva,
)


class TestEvolucionNudging(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.stations = [
            {"name": "A", "temp": 295.0, "psfc": 94000.0, "rh": 50.0, "speed": 5.0},
            {"name": "B", "temp": 300.0, "psfc": 90000.0, "rh": 55.0, "speed": 6.0},
        ]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _datos(self, time):
        # Nudged converge hacia obs con el tiempo (error grande en 00Z, chico en 12Z)
        error = {"00Z": 2.0, "06Z": 1.0, "12Z": 0.4}[time]
        return [
            {"t2": 295.0 + error, "psfc": 94000 + error * 10,
             "rh": 50.0 + error, "wspd": 5.0 + error},
            {"t2": 300.0 + error, "psfc": 90000 + error * 10,
             "rh": 55.0 + error, "wspd": 6.0 + error},
        ]

    def _datos_control(self, time):
        # Control se mantiene alejado de obs (error fijo grande)
        return [
            {"t2": 294.0, "psfc": 93900, "rh": 60.0, "wspd": 7.0},
            {"t2": 302.0, "psfc": 89900, "rh": 45.0, "wspd": 3.0},
        ]

    def test_evolucion_genera_informes(self):
        evolution = []
        for time in ("00Z", "06Z", "12Z"):
            rows = build_tables(self._datos(time), self._datos_control(time), self.stations)
            evolution.append({"tiempo": time, "full": time, "rows": rows})

        plot_evolucion(evolution, self.tmp, label="test")
        write_tabla_evolutiva(evolution, self.tmp, label="test")

        self.assertTrue((self.tmp / "informe_evolucion_nudging.png").exists())
        self.assertTrue((self.tmp / "informe_evolucion_nudging.txt").exists())
        self.assertTrue((self.tmp / "tabla_evolutiva.json").exists())

        data = json.loads((self.tmp / "tabla_evolutiva.json").read_text(encoding="utf-8"))
        self.assertEqual(data["valid_times"], ["00Z", "06Z", "12Z"])
        self.assertEqual(len(data["variables"]), 4)  # T2, PSFC, RH, Wind
        self.assertEqual(len(data["por_tiempo"]), 3)

    def test_report_nudging_no_empobrece(self):
        # El RMSE nudged de T2 debe mejorar en 12Z vs 00Z (factor converge)
        ev00 = build_tables(self._datos("00Z"), self._datos_control("00Z"), self.stations)
        ev12 = build_tables(self._datos("12Z"), self._datos_control("12Z"), self.stations)
        r00 = next(r for r in ev00 if r["var"] == "T2 (K)")
        r12 = next(r for r in ev12 if r["var"] == "T2 (K)")
        self.assertLess(r12["nudged_rmse"], r00["nudged_rmse"])


if __name__ == "__main__":
    unittest.main()