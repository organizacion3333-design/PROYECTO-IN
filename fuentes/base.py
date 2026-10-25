"""Forma común de todos los conectores de fuentes (SPEC.md §13)."""

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel


class Anuncio(BaseModel):
    """Una subasta o venta descubierta en una fuente, antes de leer su ficha completa."""

    fuente: str
    id_externo: str                    # SUB-JA-2026-267476, o el id del BOE si no hay SUB
    tipo: str | None = None            # JA, JC, JV, AT, SS, PE...
    tipo_texto: str | None = None
    autoridad: str | None = None
    localidad_autoridad: str | None = None
    num_expediente: str | None = None
    provincia: int | None = None       # código INE, None si aún no se sabe
    provincia_origen: str              # partido_judicial | titulo_anuncio | desconocida
    ambito: str | None = None
    url_portal: str | None = None
    fecha_publicacion: date
    # Datos del anuncio original en el BOE
    boe_id: str
    seccion: str
    titulo: str
    texto: str
    url_html: str | None = None
    url_pdf: str | None = None


class Conector(ABC):
    nombre: str

    @abstractmethod
    def descubrir(self, dia: date) -> list[Anuncio]:
        """Anuncios publicados ese día que interesan a la zona de trabajo."""
