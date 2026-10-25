"""Utilidades de normalización de texto."""

import html
import re
import unicodedata

# Palabras que se ignoran al comparar nombres de lugares ("Lora del Río" = "LORA RIO").
_PALABRAS_VACIAS = {"DE", "DEL", "LA", "EL", "LOS", "LAS", "L", "I", "Y"}


def sin_acentos(texto: str) -> str:
    # También convierte la Ñ en N, así "PEÑARROYA" y "PENARROYA" coinciden.
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def clave_lugar(nombre: str) -> str:
    """Clave para comparar nombres de localidades escritos de formas distintas.

    'Lora del Río', 'LORA RIO' y 'Lora  del rio' dan la misma clave.
    'EJIDO(EL)' y 'El Ejido' también.
    """
    texto = sin_acentos(nombre).upper()
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    palabras = [p for p in texto.split() if p not in _PALABRAS_VACIAS]
    return " ".join(sorted(palabras))


def html_a_texto(fragmento: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", fragmento)
    return re.sub(r"\s+", " ", html.unescape(texto)).strip()
