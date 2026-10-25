"""Cruza una lista de identificadores del portal con lo que ha encontrado el sistema.

Uso:
    python -m tareas.verificar SUB-JA-2026-267484 SUB-AT-2026-26R4186001478 ...
    python -m tareas.verificar --fichero lista.txt     # cualquier texto que contenga SUB-…

Sirve para el criterio de aceptación de la Fase 1: ninguna omisión en una muestra de 20.
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

from comun.config import DIR_DATOS
from comun.territorio import PROVINCIAS
from db import repositorio

RE_SUB = re.compile(r"SUB-[A-Z]{2}-\d{4}-[0-9A-Z]+")


def verificar(conexion: sqlite3.Connection, identificadores: list[str]) -> tuple[list[dict], list[str]]:
    """Devuelve (encontrados con sus datos, identificadores que faltan)."""
    encontrados, faltan = [], []
    for ident in dict.fromkeys(identificadores):  # sin repetidos, en el mismo orden
        fila = conexion.execute(
            "SELECT id_externo, tipo, provincia, ambito, fecha_publicacion_boe FROM subasta WHERE id_externo = ?",
            (ident,),
        ).fetchone()
        if fila:
            encontrados.append(dict(fila))
        else:
            faltan.append(ident)
    return encontrados, faltan


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("identificadores", nargs="*")
    p.add_argument("--fichero", type=Path)
    args = p.parse_args()
    texto = " ".join(args.identificadores)
    if args.fichero:
        texto += " " + args.fichero.read_text(encoding="utf-8")
    identificadores = RE_SUB.findall(texto)
    if not identificadores:
        sys.exit("No he encontrado ningún identificador SUB-… en la entrada.")

    encontrados, faltan = verificar(repositorio.conectar(DIR_DATOS / "radar.sqlite"), identificadores)
    print(f"Muestra: {len(encontrados) + len(faltan)} · Encontradas: {len(encontrados)} · Faltan: {len(faltan)}\n")
    for e in encontrados:
        provincia = PROVINCIAS.get(e["provincia"], e["ambito"] or "por confirmar")
        print(f"  ✔ {e['id_externo']}  ({provincia}, BOE {e['fecha_publicacion_boe']})")
    for f in faltan:
        print(f"  ✘ {f}  NO está en el listado")


if __name__ == "__main__":
    main()
