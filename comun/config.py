"""Carga de config/config.yaml y rutas del proyecto."""

import hashlib
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONFIG = RAIZ / "config" / "config.yaml"
DIR_DATOS = RAIZ / "data"


def cargar_config(ruta: Path = RUTA_CONFIG) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def version_config(ruta: Path = RUTA_CONFIG) -> str:
    """Huella corta del contenido de config.yaml: identifica la versión de parámetros."""
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:12]
