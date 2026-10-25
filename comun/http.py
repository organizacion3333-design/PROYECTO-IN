"""Cliente web "prudente" (SPEC.md §4, reglas de acceso).

Todas las descargas del proyecto pasan por aquí, que se encarga de:
- respetar robots.txt (si una web lo prohíbe, se lanza AccesoProhibido y no se descarga);
- esperar al menos `pausa_segundos` entre peticiones al mismo dominio;
- identificarse con un user-agent con email de contacto;
- guardar cada original descargado (comprimido) como evidencia y caché.
"""

import gzip
import hashlib
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx


class AccesoProhibido(Exception):
    """La web no permite el acceso automático a esa dirección (robots.txt)."""


@dataclass
class Respuesta:
    url: str
    estado: int
    contenido: bytes
    tipo: str
    desde_cache: bool

    @property
    def texto(self) -> str:
        return self.contenido.decode("utf-8", errors="replace")


# --- robots.txt ---------------------------------------------------------------

def _patron_a_regex(patron: str) -> re.Pattern:
    # Comodines estándar de robots.txt: "*" = cualquier cosa, "$" = fin de la dirección.
    regex = re.escape(patron).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.compile(regex)


Regla = tuple[bool, str, re.Pattern]  # (permitir, patrón, patrón compilado)


def parsear_robots(texto: str, agente: str) -> list[Regla]:
    """Devuelve las reglas (permitir, patrón) que aplican a nuestro agente.

    Si hay un grupo con nuestro nombre se usa ese; si no, el grupo "*".
    """
    grupos: dict[str, list[Regla]] = {}
    agentes_actuales: list[str] = []
    leyendo_reglas = False
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        campo, valor = (p.strip() for p in linea.split(":", 1))
        campo = campo.lower()
        if campo == "user-agent":
            if leyendo_reglas:
                agentes_actuales, leyendo_reglas = [], False
            agentes_actuales.append(valor.lower())
            for a in agentes_actuales:
                grupos.setdefault(a, [])
        elif campo in ("allow", "disallow"):
            leyendo_reglas = True
            if campo == "disallow" and not valor:
                continue  # "Disallow:" vacío = todo permitido
            for a in agentes_actuales:
                grupos[a].append((campo == "allow", valor, _patron_a_regex(valor)))
    agente = agente.lower()
    for nombre, reglas in grupos.items():
        if nombre != "*" and nombre in agente:
            return reglas
    return grupos.get("*", [])


def ruta_permitida(reglas: list[Regla], ruta: str) -> bool:
    """Gana la regla más específica (la más larga); a igualdad, gana "Allow"."""
    mejor: tuple[int, bool] | None = None
    for permitir, patron, regex in reglas:
        if regex.match(ruta):
            candidato = (len(patron), permitir)
            if mejor is None or candidato > mejor:
                mejor = candidato
    return True if mejor is None else mejor[1]


# --- cliente ------------------------------------------------------------------

class ClientePrudente:
    def __init__(self, cfg_red: dict, dir_datos: Path, conexion: sqlite3.Connection | None = None,
                 transporte: httpx.BaseTransport | None = None):
        self.pausa = float(cfg_red["pausa_segundos"])
        self.reintentos = int(cfg_red["reintentos"])
        self.agente = cfg_red["user_agent"]
        self.dir_documentos = dir_datos / "documentos"
        self.conexion = conexion
        self._http = httpx.Client(
            headers={"User-Agent": self.agente},
            timeout=float(cfg_red["timeout_segundos"]),
            follow_redirects=True,
            transport=transporte,
        )
        self._ultima_peticion: dict[str, float] = {}
        self._robots: dict[str, list[Regla]] = {}
        self.peticiones_red = 0

    def cerrar(self) -> None:
        self._http.close()

    # Rutas de la evidencia: data/documentos/<dominio>/<xx>/<sha256 de la url>.gz
    def _ruta_documento(self, url: str) -> Path:
        h = hashlib.sha256(url.encode()).hexdigest()
        return self.dir_documentos / urlsplit(url).netloc / h[:2] / f"{h}.gz"

    def _esperar_turno(self, dominio: str) -> None:
        ultima = self._ultima_peticion.get(dominio)
        if ultima is not None:
            falta = self.pausa - (time.monotonic() - ultima)
            if falta > 0:
                time.sleep(falta)
        self._ultima_peticion[dominio] = time.monotonic()

    def _peticion(self, url: str, cabeceras: dict | None = None) -> httpx.Response:
        dominio = urlsplit(url).netloc
        error: Exception | None = None
        for intento in range(self.reintentos):
            self._esperar_turno(dominio)
            try:
                self.peticiones_red += 1
                r = self._http.get(url, headers=cabeceras)
                if r.status_code < 500:
                    return r
                error = httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
            except httpx.TransportError as e:
                error = e
            time.sleep(self.pausa * (2 ** intento))
        raise error  # type: ignore[misc]

    def permitido(self, url: str) -> bool:
        partes = urlsplit(url)
        base = f"{partes.scheme}://{partes.netloc}"
        if base not in self._robots:
            r = self._peticion(f"{base}/robots.txt")
            # Sin robots.txt (404) = sin restricciones declaradas.
            self._robots[base] = parsear_robots(r.text, self.agente) if r.status_code == 200 else []
        ruta = partes.path + (f"?{partes.query}" if partes.query else "")
        return ruta_permitida(self._robots[base], ruta or "/")

    def obtener(self, url: str, aceptar: str | None = None, usar_cache: bool = True) -> Respuesta:
        """Descarga una dirección respetando robots.txt. Solo se guardan las respuestas 200."""
        ruta = self._ruta_documento(url)
        if usar_cache and ruta.exists():
            return Respuesta(url, 200, gzip.decompress(ruta.read_bytes()), self._tipo_guardado(url), True)

        if not self.permitido(url):
            raise AccesoProhibido(f"robots.txt no permite acceder a {url}")

        r = self._peticion(url, {"Accept": aceptar} if aceptar else None)
        tipo = r.headers.get("content-type", "")
        if r.status_code == 200:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(gzip.compress(r.content))
            self._registrar_documento(url, tipo, r.content, ruta)
        return Respuesta(url, r.status_code, r.content, tipo, False)

    def _registrar_documento(self, url: str, tipo: str, contenido: bytes, ruta: Path) -> None:
        if self.conexion is None:
            return
        self.conexion.execute(
            """INSERT INTO documento (url, tipo, hash, ruta, fecha) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(url) DO UPDATE SET tipo=excluded.tipo, hash=excluded.hash,
                                              ruta=excluded.ruta, fecha=excluded.fecha""",
            (url, tipo, hashlib.sha256(contenido).hexdigest(),
             str(ruta.relative_to(self.dir_documentos.parent)), datetime.now().isoformat(timespec="seconds")),
        )

    def _tipo_guardado(self, url: str) -> str:
        if self.conexion is None:
            return ""
        fila = self.conexion.execute("SELECT tipo FROM documento WHERE url = ?", (url,)).fetchone()
        return fila[0] if fila else ""

    def id_documento(self, url: str) -> int | None:
        if self.conexion is None:
            return None
        fila = self.conexion.execute("SELECT id FROM documento WHERE url = ?", (url,)).fetchone()
        return fila[0] if fila else None
