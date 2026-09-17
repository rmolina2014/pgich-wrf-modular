"""Pruebas de la validación multi-temporal (informe de evolución del nudging)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.validacion.valida_wrf_cli import (
    build_tables,
    cargar_estaciones_desde_json,
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


class TestPromedioPorEstacionYHoldout(unittest.TestCase):
    """Promedio de lecturas repetidas por estacion + rol de hold-out espacial."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config_est = self.tmp / "estaciones.json"
        self.config_est.write_text(json.dumps({
            "INTA_POCITO": {"lat": -31.65, "lon": -68.58, "elev": 615, "rol": "asimilacion"},
            "ULLUM_EMBALSE": {"lat": -31.47, "lon": -68.67, "elev": 768, "rol": "evaluacion"},
        }))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _obs_json(self, registros):
        p = self.tmp / "obs.json"
        p.write_text(json.dumps(registros))
        return p

    def test_lecturas_repetidas_se_promedian_en_una_fila(self):
        # 3 lecturas de la misma estacion en la ventana (simula EcoWitt cada 5 min)
        registros = [
            {"estacion": "INTA_POCITO", "fecha": "2026-08-12", "hora": "05:50:00", "temp": 14.0},
            {"estacion": "INTA_POCITO", "fecha": "2026-08-12", "hora": "05:55:00", "temp": 16.0},
            {"estacion": "INTA_POCITO", "fecha": "2026-08-12", "hora": "06:00:00", "temp": 18.0},
        ]
        ruta = self._obs_json(registros)
        est = cargar_estaciones_desde_json(
            str(ruta), str(self.config_est),
            valid_time="2026-08-12_06:00:00", ventana_min=30,
        )
        self.assertEqual(len(est), 1)  # una fila, no tres (evita pseudo-replicacion)
        self.assertEqual(est[0]["n_lecturas"], 3)
        self.assertAlmostEqual(est[0]["temp"], (14.0 + 16.0 + 18.0) / 3 + 273.15, places=3)

    def test_viento_se_promedia_por_vector_no_por_escalar(self):
        # Dos lecturas con la misma velocidad y direcciones opuestas: el promedio
        # vectorial (u,v) debe dar viento ~0, no el promedio simple de las direcciones
        # (que daria una direccion intermedia enganosa).
        registros = [
            {"estacion": "INTA_POCITO", "fecha": "2026-08-12", "hora": "05:55:00",
             "viento": 36.0, "direcc": 0.0},
            {"estacion": "INTA_POCITO", "fecha": "2026-08-12", "hora": "06:00:00",
             "viento": 36.0, "direcc": 180.0},
        ]
        ruta = self._obs_json(registros)
        est = cargar_estaciones_desde_json(
            str(ruta), str(self.config_est),
            valid_time="2026-08-12_06:00:00", ventana_min=30,
        )
        self.assertEqual(len(est), 1)
        self.assertAlmostEqual(est[0]["speed"], 0.0, places=3)

    def test_rol_evaluacion_se_propaga(self):
        registros = [
            {"estacion": "INTA_POCITO", "fecha": "2026-08-12", "hora": "06:00:00", "temp": 15.0},
            {"estacion": "ULLUM_EMBALSE", "fecha": "2026-08-12", "hora": "06:00:00", "temp": 16.0},
        ]
        ruta = self._obs_json(registros)
        est = cargar_estaciones_desde_json(
            str(ruta), str(self.config_est),
            valid_time="2026-08-12_06:00:00", ventana_min=30,
        )
        roles = {e["name"]: e["rol"] for e in est}
        self.assertEqual(roles["INTA_POCITO"], "asimilacion")
        self.assertEqual(roles["ULLUM_EMBALSE"], "evaluacion")


if __name__ == "__main__":
    unittest.main()