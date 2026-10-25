"""Listado de subastas activas de la zona, en Markdown y CSV.

Uso:
    python -m tareas.listado                    # escribe en data/salidas/
    python -m tareas.listado --salida docs/fase1

"Activa" = anuncio publicado en el BOE dentro de la ventana de config.yaml
(una subasta judicial dura 20 días naturales desde su apertura).
"""

import argparse
import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from comun.config import DIR_DATOS, cargar_config
from comun.territorio import PROVINCIAS
from comun.texto import clave_lugar
from db import repositorio

NOMBRES_TIPO = {
    "JA": "Judicial (apremio)", "JC": "Judicial (concursal)", "JV": "Judicial (voluntaria)",
    "AT": "Agencia Tributaria", "SS": "Seguridad Social", "PE": "Patrimonio del Estado", "NO": "Notarial",
}

COLUMNAS = ["id_externo", "tipo", "provincia", "autoridad", "fecha_publicacion_boe", "url_portal", "boe_id"]


def subastas_activas(conexion: sqlite3.Connection, provincias: list[int], desde: date) -> tuple[list, list]:
    """Devuelve (subastas con provincia de la zona, subastas con provincia por confirmar)."""
    consulta = """
        SELECT s.*, (SELECT MIN(boe_id) FROM anuncio_boe a WHERE a.subasta_id = s.id) AS boe_id
        FROM subasta s
        WHERE s.fecha_publicacion_boe >= ? AND {condicion}
        ORDER BY s.fecha_publicacion_boe DESC, s.id_externo
    """
    huecos = ",".join("?" for _ in provincias)
    confirmadas = conexion.execute(consulta.format(condicion=f"s.provincia IN ({huecos})"),
                                   (desde.isoformat(), *provincias)).fetchall()
    pendientes = conexion.execute(consulta.format(condicion="s.provincia IS NULL"),
                                  (desde.isoformat(),)).fetchall()
    return confirmadas, pendientes


def _fila(s: sqlite3.Row) -> dict:
    autoridad = s["autoridad"] or ""
    localidad = s["localidad_autoridad"]
    if localidad and clave_lugar(localidad) not in clave_lugar(autoridad):
        autoridad = f"{autoridad} ({localidad.title()})"
    return {
        "id_externo": s["id_externo"],
        "tipo": NOMBRES_TIPO.get(s["tipo"], s["tipo"] or "?"),
        "provincia": PROVINCIAS.get(s["provincia"], s["ambito"] or "por confirmar"),
        "autoridad": autoridad,
        "fecha_publicacion_boe": s["fecha_publicacion_boe"],
        "url_portal": s["url_portal"] or "",
        "boe_id": s["boe_id"] or "",
    }


def _tabla_md(filas: list[dict]) -> str:
    cabecera = "| # | Identificador | Tipo | Autoridad | Publicado en BOE | Anuncio BOE |\n|---|---|---|---|---|---|\n"
    lineas = [
        f"| {i} | [{f['id_externo']}]({f['url_portal']}) | {f['tipo']} | {f['autoridad']} | "
        f"{f['fecha_publicacion_boe']} | [{f['boe_id']}](https://www.boe.es/diario_boe/txt.php?id={f['boe_id']}) |"
        if f["url_portal"] else
        f"| {i} | {f['id_externo']} | {f['tipo']} | {f['autoridad']} | {f['fecha_publicacion_boe']} | "
        f"[{f['boe_id']}](https://www.boe.es/diario_boe/txt.php?id={f['boe_id']}) |"
        for i, f in enumerate(filas, 1)
    ]
    return cabecera + "\n".join(lineas) + "\n"


def generar(conexion: sqlite3.Connection, cfg: dict, hoy: date, dir_salida: Path) -> Path:
    provincias = cfg["zonas"]["provincias_activas"]
    desde = hoy - timedelta(days=cfg["descubrimiento"]["ventana_activa_dias"])
    confirmadas, pendientes = subastas_activas(conexion, provincias, desde)
    filas_c = [_fila(s) for s in confirmadas]
    filas_p = [_fila(s) for s in pendientes]

    nombre_zona = ", ".join(PROVINCIAS[p] for p in provincias)
    dir_salida.mkdir(parents=True, exist_ok=True)
    base = dir_salida / f"listado_{'_'.join(map(str, provincias))}_{hoy:%Y%m%d}"

    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas_c + filas_p)

    md = [
        f"# Subastas activas — {nombre_zona}",
        "",
        f"Generado el {hoy:%d/%m/%Y} a partir de la API de datos abiertos del BOE. "
        f"Ventana: anuncios publicados desde el {desde:%d/%m/%Y}.",
        "",
        "**Importante:** el anuncio del BOE no dice qué se subasta (puede ser un piso, un coche o "
        "maquinaria). Eso se sabe al abrir la ficha del portal (revisión asistida, Fase 2).",
        "",
        f"## 1. Provincia confirmada por el juzgado o el título del anuncio ({len(filas_c)})",
        "",
        _tabla_md(filas_c),
        f"## 2. Agencia Tributaria en Andalucía: provincia por confirmar ({len(filas_p)})",
        "",
        "La AEAT anuncia desde su oficina regional sin indicar la provincia del bien. "
        "Hay que abrir la ficha para saber si está en la zona.",
        "",
        _tabla_md(filas_p),
    ]
    base.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    return base.with_suffix(".md")


def main() -> None:
    cfg = cargar_config()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--salida", type=Path, default=DIR_DATOS / "salidas")
    p.add_argument("--fecha", type=date.fromisoformat, default=date.today())
    args = p.parse_args()
    conexion = repositorio.conectar(DIR_DATOS / "radar.sqlite")
    print(generar(conexion, cfg, args.fecha, args.salida))


if __name__ == "__main__":
    main()
