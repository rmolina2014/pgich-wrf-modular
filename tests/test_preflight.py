"""Pruebas unitarias del módulo preflight (Sección 2.2 de chequeos_previso_ejecucionWRF.md)."""

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.preflight.preflight import (
    Estado,
    InformePreflight,
    _parsear_obsdomain,
    correr_preflight_observaciones,
)


def _namelist(p=" max_obs = 10000,\n run_hours = 12,\n") -> Path:
    nl = Path(tempfile.mkdtemp()) / "namelist.input"
    nl.write_text(p, encoding="utf-8")
    return nl


def _obs_json(n=5) -> Path:
    obs = Path(tempfile.mkdtemp()) / "obs.json"
    obs.write_text(json.dumps(
        [{"estacion": "A", "lat": -31.65, "lon": -68.3, "temp": 20.0,
          "humedad": 50.0, "presion_absoluta": 940.0, "fecha": "2026-08-06", "hora": "00:00"}] * n
    ), encoding="utf-8")
    return obs


def _bloque_obs(ts="20260806000000") -> str:
    return (
        f" {ts}\n"
        "   -31.65  -68.30 \n"
        "  ESTACION_A  SURFACE                            \n"
        "  FM-12 SYNOP  ESTACION_A         600  F  F  1\n"
        #                    slp       qc     ref_p     qc      height    qc     temp      qc
        " -888888.000 -888888.000 -888888.000 -888888.000     300.000       0.000     293.150       0.000"
        #                u        qc       v         qc       rh         qc      psfc        qc
        "      -1.000       0.000      -2.000       0.000     100.000       0.000   90000.000       0.000"
        #             precip     qc
        " -888888.000 -888888.000\n"
    )


def _obsdomain(bloques: list) -> Path:
    od = Path(tempfile.mkdtemp()) / "OBS_DOMAIN101"
    od.write_text("".join(bloques), encoding="utf-8")
    return od


class TestParseoObsdomain(unittest.TestCase):
    def test_parsea_9_pares(self):
        bloques = [_bloque_obs() for _ in range(3)]
        regs = _parsear_obsdomain(_obsdomain(bloques))
        self.assertEqual(len(regs), 3)
        self.assertEqual({r["n_pares"] for r in regs}, {9})
        self.assertEqual(regs[0]["timestamp"], "20260806000000")

    def test_tolera_lineas_en_blanco(self):
        od = _obsdomain([_bloque_obs(), ""])
        od.write_text(od.read_text() + "\n\n", encoding="utf-8")
        self.assertEqual(len(_parsear_obsdomain(od)), 1)


class TestChequeosPreflight(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 8, 6, 0, 0)
        self.obs = _obs_json(5)

    def test_chequeos_ok(self):
        od = _obsdomain([_bloque_obs() for _ in range(5)])
        inf = correr_preflight_observaciones(self.obs, od, _namelist(), self.start, caso="ok")
        self.assertTrue(inf.puede_ejecutar, inf.resumen_log())
        estados = {c.id: c.estado for c in inf.chequeos}
        self.assertEqual({i: estados[i] for i in ["2.2.1", "2.2.2", "2.2.3", "2.2.4", "2.2.5"]},
                         {i: Estado.OK for i in ["2.2.1", "2.2.2", "2.2.3", "2.2.4", "2.2.5"]})

    def test_formato104_bloquea(self):
        # 6 pares (FORMAT 104 de sondeos) en lugar de 9
        datos_104 = (
            #            slp     qc     ref_p     qc    height    qc     temp      qc    u        qc      v        qc
            " -888888.000 -888888.000 -888888.000 -888888.000     300.000       0.000     293.150       0.000"
            "      -1.000       0.000      -2.000       0.000\n"
        )
        od = _obsdomain([
            f" 20260806000000\n   -31.65  -68.30 \n  ESTACION_A  SURFACE                            \n"
            f"  FM-12 SYNOP  ESTACION_A         600  F  F  1\n" + datos_104
        ])
        inf = correr_preflight_observaciones(self.obs, od, _namelist(), self.start, caso="fmt104")
        c = next(c for c in inf.chequeos if c.id == "2.2.2")
        self.assertEqual(c.estado, Estado.BLOQUEANTE)
        self.assertIn("FORMAT 104", c.detalle)

    def test_timestamp_sintetico_bloquea(self):
        temp = Path(tempfile.mkdtemp())
        od = temp / "OBS_DOMAIN101"
        lineas = []
        for i in (0, 1, 2, 3, 4):
            lineas.append(_bloque_obs(ts=f"2026080600000{i}"))
        od.write_text("".join(lineas), encoding="utf-8")
        inf = correr_preflight_observaciones(self.obs, od, _namelist(), self.start, caso="synthetic")
        c = next(c for c in inf.chequeos if c.id == "2.2.4")
        self.assertEqual(c.estado, Estado.BLOQUEANTE)
        self.assertIn("desfase sintético", c.detalle)

    def test_max_obs_cero_bloquea(self):
        od = _obsdomain([_bloque_obs() for _ in range(2)])
        inf = correr_preflight_observaciones(self.obs, od, _namelist(" max_obs = 0,\n run_hours = 12,\n"), self.start, caso="maxobs0")
        c = next(c for c in inf.chequeos if c.id == "2.2.5")
        self.assertEqual(c.estado, Estado.BLOQUEANTE)
        self.assertIn("NIOBF=0", c.detalle)

    def test_cobertura_tercios_advertencia(self):
        od = _obsdomain([_bloque_obs(f"20260806{hh}0000") for hh in ["000000", "010000", "020000"]])
        inf = correr_preflight_observaciones(self.obs, od, _namelist(), self.start, caso="cobertura")
        c = next(c for c in inf.chequeos if c.id == "2.2.6")
        self.assertEqual(c.estado, Estado.ADVERTENCIA)

    def test_archivo_json_inexistente_bloquea(self):
        od = _obsdomain([_bloque_obs()])
        inf = correr_preflight_observaciones(Path("/no/existe.json"), od, _namelist(), self.start, caso="nojson")
        c = next(c for c in inf.chequeos if c.id == "2.2.1")
        self.assertEqual(c.estado, Estado.BLOQUEANTE)

    def test_guardar_informe_json(self):
        informe = InformePreflight(caso="test")
        informe.agregar("2.2.1", "x", Estado.OK, "5 registros")
        out = Path(tempfile.mkdtemp()) / "preflight_test.json"
        informe.guardar(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(data["ejecutar_wrf"])
        self.assertEqual(data["chequeos"][0]["estado"], "OK")


if __name__ == "__main__":
    unittest.main()