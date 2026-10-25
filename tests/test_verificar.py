from datetime import date

from db import repositorio
from fuentes.base import Anuncio
from tareas.verificar import verificar


def test_verificar_separa_encontradas_y_omisiones():
    c = repositorio.conectar(":memory:")
    repositorio.guardar_anuncio(c, Anuncio(
        fuente="boe_sumario", id_externo="SUB-JA-2026-267476", tipo="JA", provincia=14,
        provincia_origen="partido_judicial", fecha_publicacion=date(2026, 10, 19), boe_id="BOE-B-2026-33903",
        seccion="4", titulo="PEÑARROYA PUEBLONUEVO", texto="..."))
    encontrados, faltan = verificar(c, ["SUB-JA-2026-267476", "SUB-JA-2026-999999", "SUB-JA-2026-267476"])
    assert [e["id_externo"] for e in encontrados] == ["SUB-JA-2026-267476"]
    assert faltan == ["SUB-JA-2026-999999"]
