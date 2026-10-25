import json
from datetime import date

from comun.http import ClientePrudente
from comun.territorio import provincia_de_sede, provincia_en_texto
from fuentes.boe_sumario import BoeSumario, analizar_texto, clasificar, items_del_sumario
from tests.conftest import FIXTURES


def test_sedes_judiciales_con_nombres_abreviados_del_boe():
    assert provincia_de_sede("PEÑARROYA PUEBLONUEVO") == 14
    assert provincia_de_sede("CORDOBA") == 14
    assert provincia_de_sede("LORA RIO") == 41
    assert provincia_de_sede("PALMA CONDADO") == 21
    assert provincia_de_sede("SANLUCAR MAYOR") == 41
    assert provincia_de_sede("SANLUCAR BARRAMEDA") is None   # Cádiz
    assert provincia_de_sede("CORIA") is None                # Cáceres, no Coria del Río
    assert provincia_de_sede("ESTEPA") == 41 and provincia_de_sede("ESTEPONA") == 29


def test_provincia_en_titulo():
    assert provincia_en_texto("Resolución de la Delegación de Economía y Hacienda en Córdoba por la que") == 14
    assert provincia_en_texto("Delegación de Economía y Hacienda en Granada") is None


def test_items_y_clasificacion_de_un_sumario_real():
    datos = json.loads((FIXTURES / "sumario_20261019.json").read_text(encoding="utf-8"))
    items = items_del_sumario(datos)
    assert len(items) == 259
    cordoba = [i["identificador"] for i in items if clasificar(i, {14})]
    assert cordoba == ["BOE-B-2026-33903", "BOE-B-2026-33925"]


def test_aeat_andalucia_queda_con_provincia_por_confirmar():
    item = {"seccion": "5B", "titulo": "U.R. SUBASTAS ANDALUCÍA 41", "departamento": "MINISTERIO DE HACIENDA"}
    assert clasificar(item, {14}) == (None, "desconocida", "Andalucía (AEAT U.R. 41)")
    otra = {"seccion": "5B", "titulo": "U.R. SUBASTAS MADRID", "departamento": "MINISTERIO DE HACIENDA"}
    assert clasificar(otra, {14}) is None


def test_analizar_texto_judicial():
    texto = ("Sección Civil TI Córdoba. Plz.n 9.- Anuncio de subasta judicial en vía de apremio con número de "
             "identificación 5150000006094122. Dirección electrónica: https://subastas.boe.es/ds.php?id=SUB-JA-2026-266512 "
             "Cordoba, 17 de septiembre de 2026.- El Letrado de la Administración de Justicia.")
    datos = analizar_texto(texto)
    assert datos == {
        "id_externo": "SUB-JA-2026-266512",
        "tipo": "JA",
        "url_portal": "https://subastas.boe.es/ds.php?id=SUB-JA-2026-266512",
        "tipo_texto": "judicial en vía de apremio",
        "autoridad": "Sección Civil TI Córdoba. Plz.n 9",
        "num_expediente": "5150000006094122",
    }


def test_descubrir_un_dia_real(cfg_red, transporte, tmp_path):
    conector = BoeSumario(ClientePrudente(cfg_red, tmp_path, transporte=transporte), {14})
    anuncios = conector.descubrir(date(2026, 10, 19))
    assert [a.id_externo for a in anuncios] == ["SUB-JA-2026-267476", anuncios[1].id_externo]
    assert all(a.provincia == 14 and a.provincia_origen == "partido_judicial" for a in anuncios)
    assert anuncios[1].id_externo.startswith("SUB-")


def test_dia_sin_boe_devuelve_vacio(cfg_red, transporte, tmp_path):
    conector = BoeSumario(ClientePrudente(cfg_red, tmp_path, transporte=transporte), {14})
    assert conector.descubrir(date(2026, 10, 18)) == []   # domingo
