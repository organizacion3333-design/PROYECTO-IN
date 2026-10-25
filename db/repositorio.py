"""Acceso a la base de datos: guardar sin duplicar y buscar duplicados."""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from comun.texto import sin_acentos
from fuentes.base import Anuncio

ESQUEMA = Path(__file__).with_name("esquema.sql")


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def conectar(ruta: Path | str) -> sqlite3.Connection:
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.executescript(ESQUEMA.read_text(encoding="utf-8"))
    return conexion


# --- subastas -----------------------------------------------------------------

def guardar_anuncio(conexion: sqlite3.Connection, anuncio: Anuncio) -> tuple[int, bool]:
    """Guarda un anuncio y su subasta. Devuelve (id de la subasta, ¿es nueva?).

    Volver a guardar el mismo anuncio no crea nada nuevo (idempotente): solo
    actualiza la fecha de última comprobación.
    """
    momento = ahora()
    fila = conexion.execute("SELECT id FROM subasta WHERE id_externo = ?", (anuncio.id_externo,)).fetchone()
    if fila:
        subasta_id, nueva = fila["id"], False
        conexion.execute("UPDATE subasta SET ultima_comprobacion = ? WHERE id = ?", (momento, subasta_id))
    else:
        cursor = conexion.execute(
            """INSERT INTO subasta (id_externo, fuente, tipo, tipo_texto, autoridad, localidad_autoridad,
                   num_expediente, provincia, provincia_origen, ambito, url_portal, fecha_publicacion_boe,
                   fecha_deteccion, ultima_comprobacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (anuncio.id_externo, anuncio.fuente, anuncio.tipo, anuncio.tipo_texto, anuncio.autoridad,
             anuncio.localidad_autoridad, anuncio.num_expediente, anuncio.provincia, anuncio.provincia_origen,
             anuncio.ambito, anuncio.url_portal, anuncio.fecha_publicacion.isoformat(), momento, momento),
        )
        subasta_id, nueva = cursor.lastrowid, True

    conexion.execute(
        """INSERT INTO anuncio_boe (boe_id, subasta_id, fecha_publicacion, seccion, titulo, texto, url_html, url_pdf,
                                    documento_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, (SELECT id FROM documento WHERE url = ?))
           ON CONFLICT(boe_id) DO NOTHING""",
        (anuncio.boe_id, subasta_id, anuncio.fecha_publicacion.isoformat(), anuncio.seccion, anuncio.titulo,
         anuncio.texto, anuncio.url_html, anuncio.url_pdf, anuncio.url_html),
    )
    return subasta_id, nueva


# --- deduplicación de activos (SPEC.md §5) ------------------------------------

# Tipo de vía: solo se traduce si es la primera palabra ("3º C" no es "calle").
_TIPOS_VIA = {
    "C": "CALLE", "CL": "CALLE",
    "AV": "AVENIDA", "AVDA": "AVENIDA",
    "PZ": "PLAZA", "PL": "PLAZA", "PLZA": "PLAZA",
    "PS": "PASEO", "PSO": "PASEO",
    "CTRA": "CARRETERA", "CR": "CARRETERA",
    "URB": "URBANIZACION",
}
# Palabras que se ignoran en cualquier posición.
_IGNORADAS = {"N", "NUM", "NUMERO", "NO", "DE", "DEL", "LA", "EL", "LOS", "LAS"}


def normalizar_direccion(direccion: str) -> str:
    """'C/ Gran Capitán, nº 12, 3º B' → 'CALLE GRAN CAPITAN 12 3 B'."""
    texto = sin_acentos(direccion).upper()
    texto = re.sub(r"(\d+)\s*[ºª°]", r"\1", texto)
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    palabras = texto.split()
    if palabras:
        palabras[0] = _TIPOS_VIA.get(palabras[0], palabras[0])
    return " ".join(p for p in palabras if p not in _IGNORADAS)


def normalizar_catastral(ref: str | None) -> str | None:
    if not ref:
        return None
    limpia = re.sub(r"[^0-9A-Z]", "", ref.upper())
    return limpia or None


def buscar_activo_existente(conexion: sqlite3.Connection, *, ref_catastral: str | None = None,
                            finca_registral: str | None = None, registro: str | None = None,
                            direccion: str | None = None, superficie_m2: float | None = None,
                            tolerancia_superficie: float = 0.03) -> tuple[int, str] | None:
    """Busca si el inmueble ya está en la base de datos, en el orden del SPEC:

    1. referencia catastral;
    2. finca registral + registro;
    3. dirección normalizada + superficie (con una tolerancia del 3 %).

    Devuelve (id del activo, criterio que ha coincidido) o None.
    """
    ref = normalizar_catastral(ref_catastral)
    if ref:
        fila = conexion.execute("SELECT id FROM activo WHERE ref_catastral = ?", (ref,)).fetchone()
        if fila:
            return fila["id"], "ref_catastral"

    if finca_registral and registro:
        fila = conexion.execute(
            "SELECT id FROM activo WHERE finca_registral = ? AND registro = ?",
            (finca_registral.strip(), registro.strip()),
        ).fetchone()
        if fila:
            return fila["id"], "finca_registral"

    if direccion and superficie_m2:
        filas = conexion.execute(
            """SELECT id, COALESCE(sup_construida_m2, sup_catastro_m2, sup_nota_simple_m2, sup_util_m2) AS sup
               FROM activo WHERE direccion_normalizada = ?""",
            (normalizar_direccion(direccion),),
        ).fetchall()
        for fila in filas:
            if fila["sup"] and abs(fila["sup"] - superficie_m2) <= tolerancia_superficie * superficie_m2:
                return fila["id"], "direccion_superficie"
    return None


def registrar_activo(conexion: sqlite3.Connection, **datos) -> tuple[int, bool]:
    """Crea el activo, o devuelve el existente si es un duplicado. Devuelve (id, ¿es nuevo?)."""
    existente = buscar_activo_existente(
        conexion,
        ref_catastral=datos.get("ref_catastral"),
        finca_registral=datos.get("finca_registral"),
        registro=datos.get("registro"),
        direccion=datos.get("direccion"),
        superficie_m2=datos.get("sup_construida_m2") or datos.get("sup_catastro_m2"),
    )
    if existente:
        return existente[0], False
    datos = dict(datos)
    datos["ref_catastral"] = normalizar_catastral(datos.get("ref_catastral"))
    if datos.get("direccion"):
        datos["direccion_normalizada"] = normalizar_direccion(datos["direccion"])
    datos["creado"] = ahora()
    columnas = ", ".join(datos)
    huecos = ", ".join("?" for _ in datos)
    cursor = conexion.execute(f"INSERT INTO activo ({columnas}) VALUES ({huecos})", tuple(datos.values()))
    return cursor.lastrowid, True


# --- ejecuciones y salud de fuentes -------------------------------------------

def iniciar_ejecucion(conexion: sqlite3.Connection, tipo: str) -> int:
    return conexion.execute("INSERT INTO ejecucion (tipo, inicio) VALUES (?, ?)", (tipo, ahora())).lastrowid


def cerrar_ejecucion(conexion: sqlite3.Connection, ejecucion_id: int, resultado: str, resumen: dict) -> None:
    conexion.execute(
        "UPDATE ejecucion SET fin = ?, resultado = ?, resumen = ? WHERE id = ?",
        (ahora(), resultado, json.dumps(resumen, ensure_ascii=False), ejecucion_id),
    )


def registrar_salud(conexion: sqlite3.Connection, ejecucion_id: int, fuente: str, n_resultados: int,
                    n_errores: int = 0, bloqueos: str | None = None, detalle: str | None = None) -> None:
    conexion.execute(
        """INSERT INTO salud_fuente (ejecucion_id, fuente, n_resultados, n_errores, bloqueos, detalle)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ejecucion_id, fuente, n_resultados, n_errores, bloqueos, detalle),
    )
