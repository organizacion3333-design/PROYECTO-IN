"""Provincias y partidos judiciales de la zona de trabajo.

Los anuncios judiciales del BOE se titulan con la localidad del juzgado
(sede del partido judicial). De ahí se deduce la provincia.

Ojo: un juzgado puede subastar un inmueble situado en otra provincia
(sobre todo los de lo mercantil en concursos). Esa provincia "deducida"
se confirma después con la ficha del portal.
"""

from comun.texto import clave_lugar

PROVINCIAS = {
    14: "Córdoba",
    41: "Sevilla",
    29: "Málaga",
    21: "Huelva",
}

# Sedes de partido judicial por provincia.
PARTIDOS_JUDICIALES = {
    14: [
        "Aguilar de la Frontera", "Baena", "Cabra", "Córdoba", "Lucena",
        "Montilla", "Montoro", "Peñarroya-Pueblonuevo", "Posadas",
        "Pozoblanco", "Priego de Córdoba", "Puente Genil",
    ],
    41: [
        "Alcalá de Guadaíra", "Carmona", "Cazalla de la Sierra",
        "Coria del Río", "Dos Hermanas", "Écija", "Estepa", "Lebrija",
        "Lora del Río", "Marchena", "Morón de la Frontera", "Osuna",
        "Sanlúcar la Mayor", "Sevilla", "Utrera",
    ],
    29: [
        "Antequera", "Archidona", "Coín", "Estepona", "Fuengirola",
        "Málaga", "Marbella", "Ronda", "Torremolinos", "Torrox",
        "Vélez-Málaga",
    ],
    21: [
        "Aracena", "Ayamonte", "Huelva", "La Palma del Condado", "Moguer",
        "Valverde del Camino",
    ],
}

_SEDE_A_PROVINCIA = {
    clave_lugar(sede): prov
    for prov, sedes in PARTIDOS_JUDICIALES.items()
    for sede in sedes
}


def provincia_de_sede(localidad: str) -> int | None:
    """Código INE de la provincia de una sede judicial, o None si no es de la zona."""
    return _SEDE_A_PROVINCIA.get(clave_lugar(localidad))


def provincia_en_texto(texto: str) -> int | None:
    """Busca el nombre de una provincia de la zona dentro de un texto (p. ej. un título)."""
    palabras = set(clave_lugar(texto).split())
    for prov, nombre in PROVINCIAS.items():
        if clave_lugar(nombre) in palabras:
            return prov
    return None
