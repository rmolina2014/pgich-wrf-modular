"""Ejecutor y supervisor de real.exe y wrf.exe para simulaciones Control y Nudged."""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("modelo.wrf")


class WRFRunner:
    """Orquestador de simulaciones WRF (local o vía contenedor Docker)."""

    def __init__(self, run_dir: Optional[str] = None):
        self.run_dir = Path(run_dir or os.environ.get("LOCAL_WRF_DIR", "/home/roberto/opencode/wrf/WRF-4.0/run"))

    def verificar_entorno(self) -> Dict[str, bool]:
        """Verifica la presencia de ejecutables y archivos base de WRF."""
        if not self.run_dir.exists():
            return {"run_dir": False, "wrf_exe": False, "real_exe": False}

        return {
            "run_dir": True,
            "wrf_exe": (self.run_dir / "wrf.exe").exists(),
            "real_exe": (self.run_dir / "real.exe").exists(),
            "wrfinput_d01": (self.run_dir / "wrfinput_d01").exists(),
            "wrfbdy_d01": (self.run_dir / "wrfbdy_d01").exists(),
        }

    def ejecutar_comando_seguro(self, cmd: str, log_file: Path, env_vars: Optional[Dict[str, str]] = None) -> bool:
        """Ejecuta un comando redirigiendo salida estándar y error directamente al archivo de log."""
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"  # Vital para evitar SIGSEGV en builds smpar
        if env_vars:
            env.update(env_vars)

        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ejecutando: {cmd} (Log: {log_file.name})")

        with open(log_file, "w", encoding="utf-8") as f_out:
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.run_dir),
                    stdout=f_out,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
                return proc.returncode == 0
            except Exception as e:
                logger.error(f"Fallo al ejecutar '{cmd}': {e}")
                return False

    def ejecutar_real(self, log_path: Path) -> bool:
        """Ejecuta real.exe para generar wrfinput_d01 y wrfbdy_d01."""
        cmd = "./real.exe"
        exito = self.ejecutar_comando_seguro(cmd, log_path)
        if exito:
            logger.info("real.exe finalizado exitosamente.")
        else:
            logger.error("Error en ejecución de real.exe. Revisar log.")
        return exito

    def ejecutar_wrf(self, nudged: bool = True, log_path: Optional[Path] = None) -> bool:
        """Ejecuta wrf.exe para simulación asimilada (nudged) o corrida de control."""
        tipo = "Nudged" if nudged else "Control"
        log = log_path or (self.run_dir / f"wrf_{tipo.lower()}.log")

        cmd = "./wrf.exe"
        logger.info(f"Iniciando corrida WRF ({tipo})...")
        exito = self.ejecutar_comando_seguro(cmd, log)
        if exito:
            logger.info(f"WRF {tipo} completado exitosamente.")
        else:
            logger.error(f"Error en ejecución de WRF {tipo}. Revisar log.")
        return exito
