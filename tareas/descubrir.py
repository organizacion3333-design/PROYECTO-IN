"""Descubre subastas nuevas en el BOE y las guarda en la base de datos.

Uso:
    python -m tareas.descubrir                 # revisa los últimos N días (config.yaml)
    python -m tareas.descubrir --dias 10
    python -m tareas.descubrir --desde 2026-10-01 --hasta 2026-10-24

Se puede ejecutar tantas veces como se quiera: nunca duplica nada.
"""

import argparse
import logging
from datetime import date, timedelta

from comun.config import DIR_DATOS, cargar_config
from comun.http import AccesoProhibido, ClientePrudente
from db import repositorio
from fuentes.boe_sumario import BoeSumario

log = logging.getLogger("descubrir")


def ejecutar(desde: date, hasta: date, cfg: dict, ruta_db=None) -> dict:
    conexion = repositorio.conectar(ruta_db or DIR_DATOS / "radar.sqlite")
    cliente = ClientePrudente(cfg["red"], DIR_DATOS, conexion)
    conector = BoeSumario(cliente, set(cfg["zonas"]["provincias_activas"]))
    ejecucion = repositorio.iniciar_ejecucion(conexion, "descubrir")
    resumen = {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias_revisados": 0,
               "anuncios": 0, "subastas_nuevas": 0, "errores": []}
    dia = desde
    while dia <= hasta:
        try:
            anuncios = conector.descubrir(dia)
            resumen["dias_revisados"] += 1
            for anuncio in anuncios:
                _, nueva = repositorio.guardar_anuncio(conexion, anuncio)
                resumen["anuncios"] += 1
                resumen["subastas_nuevas"] += int(nueva)
            conexion.commit()
            log.info("%s: %d anuncios de interés", dia, len(anuncios))
        except AccesoProhibido as e:
            resumen["errores"].append(f"{dia}: bloqueado por robots.txt: {e}")
            log.error("%s", e)
        except Exception as e:  # una fuente caída no debe tumbar toda la ejecución
            resumen["errores"].append(f"{dia}: {e}")
            log.exception("Error procesando el %s", dia)
        dia += timedelta(days=1)

    resultado = "ok" if not resumen["errores"] else "aviso"
    repositorio.registrar_salud(conexion, ejecucion, conector.nombre, resumen["anuncios"],
                                len(resumen["errores"]), detalle="; ".join(resumen["errores"]) or None)
    resumen["peticiones_red"] = cliente.peticiones_red
    repositorio.cerrar_ejecucion(conexion, ejecucion, resultado, resumen)
    conexion.commit()
    cliente.cerrar()
    conexion.close()
    return resumen


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = cargar_config()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dias", type=int, default=cfg["descubrimiento"]["dias_hacia_atras"])
    p.add_argument("--desde", type=date.fromisoformat)
    p.add_argument("--hasta", type=date.fromisoformat)
    args = p.parse_args()
    hasta = args.hasta or date.today()
    desde = args.desde or hasta - timedelta(days=args.dias)
    resumen = ejecutar(desde, hasta, cfg)
    log.info("Resumen: %s", resumen)


if __name__ == "__main__":
    main()
