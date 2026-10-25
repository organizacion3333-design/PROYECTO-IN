from datetime import date

from comun.http import ClientePrudente
from db import repositorio
from fuentes.boe_sumario import BoeSumario


def test_guardar_dos_veces_no_duplica(cfg_red, transporte, tmp_path):
    conexion = repositorio.conectar(":memory:")
    conector = BoeSumario(ClientePrudente(cfg_red, tmp_path, conexion, transporte=transporte), {14})
    anuncios = conector.descubrir(date(2026, 10, 19))
    nuevas = [repositorio.guardar_anuncio(conexion, a)[1] for a in anuncios]
    otra_vez = [repositorio.guardar_anuncio(conexion, a)[1] for a in anuncios]
    assert nuevas == [True, True] and otra_vez == [False, False]
    assert conexion.execute("SELECT COUNT(*) FROM subasta").fetchone()[0] == 2
    assert conexion.execute("SELECT COUNT(*) FROM anuncio_boe").fetchone()[0] == 2
    # Cada anuncio queda enlazado con su evidencia original.
    assert conexion.execute("SELECT COUNT(*) FROM anuncio_boe WHERE documento_id IS NOT NULL").fetchone()[0] == 2


def test_dedup_por_referencia_catastral():
    c = repositorio.conectar(":memory:")
    a, nuevo = repositorio.registrar_activo(c, ref_catastral="1234567UG4913S0001AB", direccion="C/ Mayor 1")
    b, otro = repositorio.registrar_activo(c, ref_catastral="1234567 UG4913S 0001 AB", direccion="Otra 5")
    assert nuevo and not otro and a == b


def test_dedup_por_finca_registral():
    c = repositorio.conectar(":memory:")
    a, _ = repositorio.registrar_activo(c, finca_registral="12345", registro="Córdoba nº 3")
    assert repositorio.buscar_activo_existente(c, finca_registral="12345", registro="Córdoba nº 3") == (a, "finca_registral")
    assert repositorio.buscar_activo_existente(c, finca_registral="12345", registro="Córdoba nº 1") is None


def test_dedup_por_direccion_y_superficie_con_tolerancia():
    c = repositorio.conectar(":memory:")
    a, _ = repositorio.registrar_activo(c, direccion="C/ Gran Capitán, nº 12, 3º B", sup_construida_m2=90)
    assert repositorio.buscar_activo_existente(c, direccion="Calle Gran Capitan 12 3 B", superficie_m2=91) == (
        a, "direccion_superficie")
    assert repositorio.buscar_activo_existente(c, direccion="Calle Gran Capitan 12 3 B", superficie_m2=120) is None
    assert repositorio.buscar_activo_existente(c, direccion="Calle Gran Capitan 12 3 C", superficie_m2=90) is None


def test_el_orden_de_criterios_es_el_del_spec():
    c = repositorio.conectar(":memory:")
    por_ref, _ = repositorio.registrar_activo(c, ref_catastral="1111111AA1111A0001AA")
    por_finca, _ = repositorio.registrar_activo(c, finca_registral="999", registro="Sevilla nº 2")
    encontrado = repositorio.buscar_activo_existente(
        c, ref_catastral="1111111AA1111A0001AA", finca_registral="999", registro="Sevilla nº 2")
    assert encontrado == (por_ref, "ref_catastral")
    assert por_ref != por_finca
