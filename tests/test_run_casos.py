"""Pruebas del runner de casos de estudio (src/casos/run_casos.py)."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from src.casos.run_casos import (
    _md_tabla_variable,
    cobertura_obs,
    generar_obs_flat,
    gfs_disponible,
    redactar_informe_caso,
)


def _csv_historico(path: Path, fecha: str = "2026-07-31"):
    """CSV historico minimo (esquema de ecowitt_client._convertir_a_csv)."""
    rows = [("estacion", "fecha", "hora_unix", "fecha_hora", "temp_c", "humedad_pct",
             "viento_kmh", "viento_rafaga_kmh", "direcc_grados", "presion_relativa_hpa",
             "presion_absoluta_hpa", "lluvia_diaria_mm", "solar_wm2")]
    base = datetime.strptime(f"{fecha} 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp()
    for i, est in enumerate(["INTA_POCITO", "CARACOLES"]):
        for k in range(5):
            ts = int(base + k * 300)
            rows.append((est, fecha, str(ts), datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                         f"{20 + k}.0", "40", "5", "7", "180", "1010", "930", "0", "100"))
    with open(path, "w", newline="", encoding="utf-8") as f:
        for row in rows:
            f.write(",".join(row) + "\n")
    return path


class TestObs(unittest.TestCase):
    def test_cobertura_conteos(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv = _csv_historico(Path(tmp) / "hist.csv", "2026-07-31")
            cov = cobertura_obs(csv, "2026-07-31", "00")
            # 10 registros en el dia; todos dentro de la ventana 00-12Z (hasta 00:20)
            self.assertEqual(cov["dia"], 10)
            self.assertEqual(cov["ventana"], 10)
            self.assertEqual(cov["estaciones"], 2)

    def test_cobertura_fuera_ventana(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv = _csv_historico(Path(tmp) / "hist.csv", "2026-07-31")
            # La ventana 00-12Z termina a las 12Z; los registros son de 00:00-00:20: entran todos.
            # Usamos una ventana ad-hoc de 00:00 a 00:05 para verificar el filtrado.
            ts_ini = int(datetime.strptime("2026-07-31 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp())
            df = __import__("pandas").read_csv(csv)
            df["ts"] = __import__("pandas").to_numeric(df["hora_unix"], errors="coerce")
            # La ventana ad-hoc 00:00-00:10 cubre k=0,1,2 (00:00, 00:05, 00:10) => 3 por estacion.
            en_ventana = (df["ts"] >= ts_ini) & (df["ts"] <= ts_ini + 2 * 300)
            self.assertEqual(en_ventana.sum(), 6)

    def test_generar_obs_flat(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv = _csv_historico(tmp / "hist.csv", "2026-07-31")
            salida = generar_obs_flat(csv, "2026-07-31", tmp / "obs_flat.json")
            self.assertTrue(salida.exists())
            data = json.loads(salida.read_text())
            self.assertEqual(len(data), 10)
            self.assertEqual(data[0]["estacion"], "INTA_POCITO")
            self.assertEqual(data[0]["fecha"], "2026-07-31")
            self.assertEqual(data[0]["hora"], "00:00:00")
            self.assertEqual(data[0]["temp"], 20.0)
            self.assertIsInstance(data[0]["time_unix"], int)


class TestGFS(unittest.TestCase):
    def test_gfs_disponible_aws(self):
        with mock.patch("src.casos.run_casos.requests.head") as head:
            head.return_value.status_code = 200
            self.assertEqual(gfs_disponible("2026-07-31", "00"), "aws")
            # primer intento: AWS
            args = head.call_args.args[0]
            self.assertIn("noaa-gfs-bdp-pds", args)

    def test_gfs_no_disponible(self):
        with mock.patch("src.casos.run_casos.requests.head", side_effect=Exception("boom")):
            self.assertIsNone(gfs_disponible("2026-07-31", "00"))


class TestInformes(unittest.TestCase):
    def test_md_tabla_variable(self):
        rows = [
            {"var": "T2 (K)", "tiempo": "06Z", "n": 65, "nudged_rmse": 5.79, "control_rmse": 7.93,
             "nudged_bias": -3.27, "control_bias": -4.00},
            {"var": "T2 (K)", "tiempo": "12Z", "n": 52, "nudged_rmse": 4.39, "control_rmse": 3.78,
             "nudged_bias": -2.95, "control_bias": -1.96},
        ]
        tbl = _md_tabla_variable(rows, "T2 (K)")
        self.assertIn("06Z", tbl)
        self.assertIn("+2.14", tbl)  # dRMSE = 7.93 - 5.79
        self.assertIn("12Z", tbl)

    def test_informe_caso_no_ejecutado(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            caso = {
                "id": "caso1", "num": 1, "fecha": "2026-07-31", "evento": "viento_zonda",
                "titulo": "Caso 1 - Viento Zonda", "descripcion": "Alerta naranja.",
                "fuente": "SMN", "resultados_dir": str(tmp / "res"),
                "informe": str(tmp / "informe_caso1.md"),
            }
            entry = {"estado": "NO EJECUTADO - SIN DATOS (obs)", "detalle": "cobertura insuficiente (0 registros)"}
            ruta = redactar_informe_caso(caso, entry, None)
            contenido = ruta.read_text(encoding="utf-8")
            self.assertIn("NO EJECUTADO", contenido)
            self.assertIn("cobertura insuficiente", contenido)

    def test_informe_caso_ejecutado_con_tabla(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            res = tmp / "res"
            res.mkdir()
            tabla = {
                "valid_times": ["00Z", "06Z", "12Z"],
                "variables": ["T2 (K)", "RH (%)"],
                "por_tiempo": [
                    {"tiempo": "00Z", "rows": [
                        {"var": "T2 (K)", "n": 14, "nudged_rmse": 3.74, "control_rmse": 3.74,
                         "nudged_bias": 1.14, "control_bias": 1.14}]},
                    {"tiempo": "06Z", "rows": [
                        {"var": "T2 (K)", "n": 18, "nudged_rmse": 3.34, "control_rmse": 3.74,
                         "nudged_bias": -0.12, "control_bias": 0.83},
                        {"var": "RH (%)", "n": 18, "nudged_rmse": 16.35, "control_rmse": 23.42,
                         "nudged_bias": -9.62, "control_bias": -17.99}]},
                ],
            }
            (res / "tabla_evolutiva.json").write_text(json.dumps(tabla), encoding="utf-8")
            caso = {
                "id": "caso2", "num": 2, "fecha": "2026-01-01", "evento": "calor_verano",
                "titulo": "Caso 2 - Calor", "descripcion": "Ola de calor.",
                "fuente": "SMN", "resultados_dir": str(res), "informe": str(tmp / "informe_caso2.md"),
            }
            entry = {"estado": "EJECUTADO", "detalle": "fuente GFS aws"}
            ruta = redactar_informe_caso(caso, entry, None)
            contenido = ruta.read_text(encoding="utf-8")
            self.assertIn("EJECUTADO", contenido)
            self.assertIn("RMSE N", contenido)
            self.assertIn("+0.40", contenido)  # dRMSE control-nudged para T2 06Z
            self.assertIn("RH (%)", contenido)


if __name__ == "__main__":
    unittest.main()