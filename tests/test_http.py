import pytest

from comun.http import AccesoProhibido, ClientePrudente, parsear_robots, ruta_permitida
from tests.conftest import FIXTURES


def test_portal_de_subastas_prohibe_todo():
    reglas = parsear_robots((FIXTURES / "robots_subastas.txt").read_text(), "RadarInmobiliario")
    assert not ruta_permitida(reglas, "/ds.php?id=SUB-JA-2026-267476")
    assert not ruta_permitida(reglas, "/")


def test_boe_permite_api_y_texto_de_anuncios_pero_no_xml():
    reglas = parsear_robots((FIXTURES / "robots_boe.txt").read_text(encoding="utf-8"), "RadarInmobiliario")
    assert ruta_permitida(reglas, "/datosabiertos/api/boe/sumario/20261019")
    assert ruta_permitida(reglas, "/diario_boe/txt.php?id=BOE-B-2026-33903")
    assert not ruta_permitida(reglas, "/diario_boe/xml.php?id=BOE-B-2026-33903")
    assert not ruta_permitida(reglas, "/diario_boe/txt.php?id=BOE-B-2026-33903&lang=en")


def test_regla_mas_especifica_gana():
    reglas = parsear_robots("User-agent: *\nDisallow: /privado/\nAllow: /privado/publico\n", "x")
    assert ruta_permitida(reglas, "/privado/publico/1")
    assert not ruta_permitida(reglas, "/privado/otro")
    assert ruta_permitida(reglas, "/otra")


def test_cliente_no_descarga_lo_prohibido(cfg_red, transporte, tmp_path):
    cliente = ClientePrudente(cfg_red, tmp_path, transporte=transporte)
    with pytest.raises(AccesoProhibido):
        cliente.obtener("https://subastas.boe.es/ds.php?id=SUB-JA-2026-267476")


def test_cliente_guarda_evidencia_y_usa_cache(cfg_red, transporte, tmp_path):
    cliente = ClientePrudente(cfg_red, tmp_path, transporte=transporte)
    url = "https://www.boe.es/diario_boe/txt.php?id=BOE-B-2026-33903"
    primera = cliente.obtener(url)
    peticiones = cliente.peticiones_red
    segunda = cliente.obtener(url)
    assert primera.estado == 200 and not primera.desde_cache
    assert segunda.desde_cache and segunda.contenido == primera.contenido
    assert cliente.peticiones_red == peticiones  # la segunda vez no sale a internet
    assert list((tmp_path / "documentos").rglob("*.gz"))
