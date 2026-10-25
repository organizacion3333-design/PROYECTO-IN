"""Fuente 1: API de datos abiertos del BOE (sumario diario).

Qué se busca en cada sumario:
- Sección IV (Administración de Justicia): anuncios de subastas judiciales.
  El título es la localidad del juzgado → provincia por partido judicial.
- Sección V-B (Otros anuncios oficiales):
  - "U.R. SUBASTAS ANDALUCÍA …": subastas de la Agencia Tributaria en Andalucía.
    El anuncio no dice la provincia del bien → queda "por confirmar".
  - Subastas de la Seguridad Social, Patrimonio del Estado, etc. cuyo título
    menciona una provincia de la zona.

De cada anuncio interesante se descarga su texto (página HTML del BOE, permitida
por su robots.txt) y se extraen el identificador SUB-…, el tipo y el juzgado.
"""

import json
import re
from datetime import date

from comun.http import ClientePrudente
from comun.territorio import provincia_de_sede, provincia_en_texto
from comun.texto import html_a_texto
from fuentes.base import Anuncio, Conector

URL_SUMARIO = "https://www.boe.es/datosabiertos/api/boe/sumario/{:%Y%m%d}"

RE_SUB = re.compile(r"SUB-([A-Z]{2})-(\d{4})-([0-9A-Z]+)")
RE_URL_PORTAL = re.compile(r"https?://subastas\.boe\.es/\S+?(?=\s|$)")
RE_TEXTO = re.compile(r'<div id="textoxslt">(.*?)</div>', re.S)
RE_SUBASTA_TITULO = re.compile(r"subasta|enajenaci[oó]n", re.I)
RE_AEAT_ANDALUCIA = re.compile(r"SUBASTAS\s+ANDALUC[IÍ]A\s*(\d+)?", re.I)

# Tipo de subasta según el texto del anuncio (por si el SUB-… no aparece).
TIPOS_TEXTO = [
    (re.compile(r"v[ií]a de apremio", re.I), "JA"),
    (re.compile(r"concursal|concurso", re.I), "JC"),
    (re.compile(r"voluntaria", re.I), "JV"),
    (re.compile(r"Agencia Estatal de Administraci[oó]n Tributaria", re.I), "AT"),
    (re.compile(r"Seguridad Social", re.I), "SS"),
    (re.compile(r"Econom[ií]a y Hacienda|Patrimonio del Estado", re.I), "PE"),
    (re.compile(r"notar", re.I), "NO"),
]


def _como_lista(valor) -> list:
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def items_del_sumario(datos: dict) -> list[dict]:
    """Aplana el sumario: una entrada por anuncio, con su sección y departamento."""
    resultado = []
    for diario in _como_lista(datos["data"]["sumario"].get("diario")):
        for seccion in _como_lista(diario.get("seccion")):
            for depto in _como_lista(seccion.get("departamento")):
                entradas = _como_lista(depto.get("item"))
                for epigrafe in _como_lista(depto.get("epigrafe")):
                    entradas += _como_lista(epigrafe.get("item"))
                for item in entradas:
                    url_pdf = item.get("url_pdf")
                    resultado.append({
                        "seccion": seccion.get("codigo"),
                        "departamento": depto.get("nombre", ""),
                        "identificador": item["identificador"],
                        "titulo": item["titulo"],
                        "url_html": item.get("url_html"),
                        "url_pdf": url_pdf.get("texto") if isinstance(url_pdf, dict) else url_pdf,
                    })
    return resultado


def clasificar(item: dict, provincias: set[int]) -> tuple[int | None, str, str | None] | None:
    """Decide si un anuncio interesa. Devuelve (provincia, origen_provincia, ámbito) o None."""
    titulo = item["titulo"]
    if item["seccion"] == "4":
        prov = provincia_de_sede(titulo)
        if prov in provincias:
            return prov, "partido_judicial", None
        return None
    if item["seccion"] == "5B":
        aeat = RE_AEAT_ANDALUCIA.search(titulo)
        if aeat:
            unidad = aeat.group(1)
            return None, "desconocida", f"Andalucía (AEAT U.R. {unidad})" if unidad else "Andalucía (AEAT)"
        if RE_SUBASTA_TITULO.search(titulo):
            prov = provincia_en_texto(titulo)
            if prov in provincias:
                return prov, "titulo_anuncio", None
    return None


def extraer_texto_anuncio(html: str) -> str:
    m = RE_TEXTO.search(html)
    return html_a_texto(m.group(1) if m else html)


def analizar_texto(texto: str) -> dict:
    """Saca del texto del anuncio: SUB-…, tipo, autoridad, expediente y URL del portal."""
    datos: dict = {}
    sub = RE_SUB.search(texto)
    if sub:
        datos["id_externo"] = sub.group(0)
        datos["tipo"] = sub.group(1)
    url = RE_URL_PORTAL.search(texto)
    if url:
        datos["url_portal"] = url.group(0)
    if "tipo" not in datos:
        for patron, codigo in TIPOS_TEXTO:
            if patron.search(texto):
                datos["tipo"] = codigo
                break
    m = re.search(r"Anuncio de subasta ([^,.]+?)(?: con n[uú]mero| de la Agencia|\.|,)", texto)
    if m:
        datos["tipo_texto"] = m.group(1).strip()
    # Autoridad judicial: lo que va antes de ".- Anuncio de subasta".
    m = re.match(r"\s*(.+?)\.-\s*Anuncio de subasta", texto)
    if m:
        datos["autoridad"] = m.group(1).strip()
    m = re.search(r"n[uú]mero de (?:identificaci[oó]n|referencia) ([0-9A-Z]+)", texto)
    if m:
        datos["num_expediente"] = m.group(1)
    return datos


class BoeSumario(Conector):
    nombre = "boe_sumario"

    def __init__(self, cliente: ClientePrudente, provincias: set[int]):
        self.cliente = cliente
        self.provincias = provincias

    def sumario(self, dia: date) -> dict | None:
        """Sumario del día, o None si ese día no hubo BOE (domingos)."""
        r = self.cliente.obtener(URL_SUMARIO.format(dia), aceptar="application/json",
                                 usar_cache=dia < date.today())
        if r.estado == 404:
            return None
        if r.estado != 200:
            raise RuntimeError(f"El sumario del BOE del {dia} devolvió HTTP {r.estado}")
        return json.loads(r.contenido)

    def descubrir(self, dia: date) -> list[Anuncio]:
        datos = self.sumario(dia)
        if datos is None:
            return []
        anuncios = []
        for item in items_del_sumario(datos):
            clasificacion = clasificar(item, self.provincias)
            if clasificacion is None:
                continue
            provincia, origen, ambito = clasificacion
            texto = extraer_texto_anuncio(self.cliente.obtener(item["url_html"]).texto)
            info = analizar_texto(texto)
            anuncios.append(Anuncio(
                fuente=self.nombre,
                id_externo=info.get("id_externo", item["identificador"]),
                tipo=info.get("tipo"),
                tipo_texto=info.get("tipo_texto"),
                autoridad=info.get("autoridad") or item["departamento"],
                localidad_autoridad=item["titulo"] if item["seccion"] == "4" else None,
                num_expediente=info.get("num_expediente"),
                provincia=provincia,
                provincia_origen=origen,
                ambito=ambito,
                url_portal=info.get("url_portal"),
                fecha_publicacion=dia,
                boe_id=item["identificador"],
                seccion=item["seccion"],
                titulo=item["titulo"],
                texto=texto,
                url_html=item["url_html"],
                url_pdf=item["url_pdf"],
            ))
        return anuncios
