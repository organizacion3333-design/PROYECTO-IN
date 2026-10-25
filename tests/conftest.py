import sys
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

FIXTURES = Path(__file__).parent / "fixtures" / "boe"

# Qué fichero real responde a cada dirección en los tests (sin salir a internet).
RUTAS = {
    "https://www.boe.es/robots.txt": "robots_boe.txt",
    "https://subastas.boe.es/robots.txt": "robots_subastas.txt",
    "https://www.boe.es/datosabiertos/api/boe/sumario/20261019": "sumario_20261019.json",
}


def _responder(peticion: httpx.Request) -> httpx.Response:
    url = str(peticion.url)
    if url in RUTAS:
        return httpx.Response(200, content=(FIXTURES / RUTAS[url]).read_bytes())
    if "txt.php?id=" in url:
        fichero = FIXTURES / f"{peticion.url.params['id']}.html"
        if fichero.exists():
            return httpx.Response(200, content=fichero.read_bytes(), headers={"content-type": "text/html"})
    if "/sumario/" in url:
        return httpx.Response(404, content=b"<response><status><code>404</code></status></response>")
    return httpx.Response(404)


@pytest.fixture
def cfg_red():
    return {"user_agent": "RadarInmobiliario/test (+contacto: test@example.com)",
            "pausa_segundos": 0, "timeout_segundos": 5, "reintentos": 1}


@pytest.fixture
def transporte():
    return httpx.MockTransport(_responder)
