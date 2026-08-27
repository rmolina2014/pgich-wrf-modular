"""Registro inmutable y gobernanza de experimentos meteorológicos (experiments/experiment_registry.jsonl)."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("reporting.registry")


class ExperimentRegistry:
    """Administra el índice maestro de experimentos realizados en el proyecto."""

    def __init__(self, registry_file: str = "experiments/experiment_registry.jsonl"):
        self.registry_path = Path(registry_file)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.touch()

    def registrar(self, exp_record: Dict[str, Any]) -> None:
        """Registra un experimento de forma atómica e inmutable en el archivo JSONL."""
        exp_id = exp_record.get("experiment_id")
        if not exp_id:
            raise ValueError("El registro del experimento debe contener 'experiment_id'")

        # Verificar si ya existe para actualizar o agregar
        existentes = self.listar_todos()
        actualizado = False

        for i, reg in enumerate(existentes):
            if reg.get("experiment_id") == exp_id:
                existentes[i] = exp_record
                actualizado = True
                break

        if not actualizado:
            existentes.append(exp_record)

        # Escribir de forma limpia
        with open(self.registry_path, "w", encoding="utf-8") as f:
            for item in existentes:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logger.info(f"Experimento '{exp_id}' registrado exitosamente en {self.registry_path.name}")

    def listar_todos(self) -> List[Dict[str, Any]]:
        """Lee y retorna todos los experimentos registrados."""
        if not self.registry_path.exists():
            return []

        registros = []
        with open(self.registry_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea_clean = linea.strip()
                if linea_clean:
                    try:
                        registros.append(json.loads(linea_clean))
                    except json.JSONDecodeError:
                        continue
        return registros

    def obtener_por_id(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """Busca y retorna los metadatos de un experimento por su identificador."""
        for reg in self.listar_todos():
            if reg.get("experiment_id") == exp_id:
                return reg
        return None
