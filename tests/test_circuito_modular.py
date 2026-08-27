"""Suite de pruebas unitarias y de integración para la arquitectura modular PGICH-WRF."""

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.calidad.qc_rules import validar_limites_fisicos, aplicar_control_calidad, LIMITES_FISICOS
from src.calidad.cleaner import ObservacionesCleaner
from src.asimilacion.littler_writer import LittleRWriter
from src.asimilacion.obsnud_writer import ObsNudWriter
from src.modelo.namelist_manager import NamelistManager
from src.validacion.metrics import MetricsCalculator
from src.validacion.spatial_interp import SpatialInterpolator
from src.reporting.report_builder import ReportBuilder
from src.reporting.plot_generator import PlotGenerator
from src.reporting.experiment_registry import ExperimentRegistry


class TestCalidadYReglas(unittest.TestCase):
    def test_limites_fisicos_temp(self):
        valido, msg = validar_limites_fisicos(25.0, "temp")
        self.assertTrue(valido)

        invalido, msg = validar_limites_fisicos(99.0, "temp")
        self.assertFalse(invalido)
        self.assertIn("Fuera de rango", msg)

    def test_aplicar_qc_dataframe(self):
        df_raw = pd.DataFrame({
            "estacion": ["POCITO", "ULLUM"],
            "temp": [22.5, 120.0],  # 120 C es espurio
            "humedad": [45.0, -10.0],  # -10% es espurio
            "presion_absoluta": [940.0, 935.0],
        })
        df_limpio = aplicar_control_calidad(df_raw)
        self.assertEqual(df_limpio.loc[0, "temp"], 22.5)
        self.assertTrue(pd.isna(df_limpio.loc[1, "temp"]))
        self.assertEqual(df_limpio.loc[0, "humedad"], 45.0)
        self.assertTrue(pd.isna(df_limpio.loc[1, "humedad"]))


class TestFormatosAsimilacion(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_est = self.test_dir / "estaciones.json"
        self.config_est.write_text(json.dumps({
            "INTA_POCITO": {"lat": -31.6500, "lon": -68.5833, "elev": 615.0},
            "ULLUM_EMBALSE": {"lat": -31.4667, "lon": -68.6667, "elev": 768.0},
        }))

        self.df_sample = pd.DataFrame([
            {
                "estacion": "INTA_POCITO",
                "fecha": "2026-08-12",
                "hora": "00:00",
                "temp": 15.0,
                "humedad": 50.0,
                "presion_absoluta": 940.0,
                "viento": 10.0,
                "direcc": 180.0,
            }
        ])

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_littler_writer(self):
        writer = LittleRWriter(config_estaciones_path=str(self.config_est))
        out_file = self.test_dir / "littler_test.txt"
        out_path, count = writer.generar_littler(self.df_sample, output_path=str(out_file))

        self.assertTrue(out_file.exists())
        self.assertEqual(count, 1)
        content = out_file.read_text(encoding="utf-8")
        self.assertIn("INTA_POCITO", content)
        self.assertIn("2026-08-12 00:00:00", content)

    def test_obsnud_writer_format105(self):
        writer = ObsNudWriter(config_estaciones_path=str(self.config_est))
        out_file = self.test_dir / "OBS_DOMAIN101"
        out_path = writer.generar_desde_dataframe(self.df_sample, output_path=str(out_file))

        self.assertTrue(out_file.exists())
        content = out_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        self.assertGreaterEqual(len(lines), 5)
        # Verificar plataforma SYNOP
        self.assertTrue(any("SYNOP" in l for l in lines))
        # Verificar fin de archivo con marcador -777777.000
        self.assertIn("-777777.000", lines[-1])


class TestNamelistManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.template = self.test_dir / "namelist.template"
        self.template.write_text("""
&time_control
 start_year = 2020, start_month = 01, start_day = 01, start_hour = 00,
 end_year = 2020, end_month = 01, end_day = 01, end_hour = 12,
 run_hours = 12,
/
&fdda
 obs_nudge_opt = 0,
 obs_coef_temp = 0.0001,
 obs_coef_wind = 0.0001,
 obs_coef_mois = 0.0001,
 obs_twindo = 0.5,
 obs_rinxy = 30.0,
/
""")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_actualizar_fechas_y_fdda(self):
        mgr = NamelistManager(template_path=str(self.template))
        mgr.actualizar_fechas(
            start_year=2026, start_month=8, start_day=12, start_hour=0,
            end_year=2026, end_month=8, end_day=12, end_hour=12, run_hours=12
        )
        mgr.configurar_fdda(
            obs_nudge_opt=1,
            obs_coef_temp=0.0005,
            obs_coef_wind=0.0005,
            obs_coef_mois=0.0005,
            obs_twindo=1.0,
            obs_rinxy=50.0,
        )
        out_nl = self.test_dir / "namelist.input"
        mgr.guardar(str(out_nl))

        saved = out_nl.read_text()
        self.assertIn("start_year = 2026", saved)
        self.assertIn("obs_nudge_opt = 1", saved)
        self.assertIn("obs_coef_temp = 0.0005", saved)
        self.assertIn("obs_twindo = 1.", saved)


class TestValidacionYMétricas(unittest.TestCase):
    def test_calcular_metricas_par(self):
        obs = np.array([10.0, 20.0, 30.0, 40.0])
        mod = np.array([11.0, 21.0, 29.0, 42.0])  # errores: +1, +1, -1, +2 (bias = 0.75)

        m = MetricsCalculator.calcular_metricas_par(mod, obs)
        self.assertAlmostEqual(m["bias"], 0.75, places=2)
        self.assertAlmostEqual(m["mae"], 1.25, places=2)
        self.assertIsNotNone(m["rmse"])
        self.assertGreater(m["r"], 0.95)

    def test_mejora_rmse(self):
        mejora = MetricsCalculator.calcular_mejora_rmse(rmse_control=4.0, rmse_nudged=3.0)
        self.assertEqual(mejora, 25.0)  # (4-3)/4 * 100 = 25%

    def test_spatial_interp_formulas(self):
        # Q2 a HR
        rh = SpatialInterpolator.q2_a_humedad_relativa(q2=0.005, t2=293.15, psfc=100000.0)
        self.assertGreater(rh, 0.0)
        self.assertLessEqual(rh, 100.0)

        # U/V a velocidad y dirección
        spd, direcc = SpatialInterpolator.u_v_a_velocidad_direccion(u=0.0, v=-5.0)
        self.assertAlmostEqual(spd, 5.0)
        self.assertAlmostEqual(direcc, 0.0)  # Viento de Norte (hacia el sur)


class TestReportingYRegistro(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_manifiesto_e_informe(self):
        builder = ReportBuilder()
        manifest_path = self.test_dir / "manifest.json"
        manifest = builder.crear_manifiesto(
            experiment_id="EXP-TEST-001",
            name="Experimento Unit Test",
            output_path=str(manifest_path),
        )
        self.assertTrue(manifest_path.exists())
        self.assertEqual(manifest["experiment_id"], "EXP-TEST-001")

        metricas_fake = {
            "t2": {"control": {"bias": 1.2, "rmse": 2.5}, "nudged": {"bias": 0.3, "rmse": 1.5, "r": 0.96}, "mejora_rmse_pct": 40.0},
            "rh": {"control": {"bias": -5.0, "rmse": 12.0}, "nudged": {"bias": -1.0, "rmse": 6.0, "r": 0.91}, "mejora_rmse_pct": 50.0},
            "wspd": {"control": {"bias": 0.8, "rmse": 2.1}, "nudged": {"bias": 0.2, "rmse": 1.1, "r": 0.88}, "mejora_rmse_pct": 47.6},
            "psfc": {"control": {"bias": 2.0, "rmse": 3.0}, "nudged": {"bias": 0.5, "rmse": 1.2, "r": 0.99}, "mejora_rmse_pct": 60.0},
        }

        report_path = self.test_dir / "INFORME.md"
        builder.renderizar_informe_markdown(
            manifest=manifest,
            metricas=metricas_fake,
            output_path=str(report_path),
        )
        self.assertTrue(report_path.exists())
        report_content = report_path.read_text(encoding="utf-8")
        self.assertIn("EXP-TEST-001", report_content)
        self.assertIn("40.0%", report_content)

    def test_experiment_registry(self):
        reg_file = self.test_dir / "registry.jsonl"
        reg = ExperimentRegistry(registry_file=str(reg_file))

        reg.registrar({"experiment_id": "EXP-01", "name": "Run 1", "status": "SUCCESS"})
        reg.registrar({"experiment_id": "EXP-02", "name": "Run 2", "status": "FAILED"})

        todos = reg.listar_todos()
        self.assertEqual(len(todos), 2)
        exp1 = reg.obtener_por_id("EXP-01")
        self.assertIsNotNone(exp1)
        self.assertEqual(exp1["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
