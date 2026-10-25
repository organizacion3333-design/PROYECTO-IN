# Radar de oportunidades inmobiliarias

Sistema que detecta cada semana inmuebles con descuento (subastas y ventas especiales) en Córdoba, Sevilla, Málaga y Huelva, los valora con números trazables y te los manda por Telegram para que decidas.

- **Qué hace y por qué:** [`SPEC.md`](SPEC.md). Es la fuente de verdad del proyecto.
- **Arquitectura aprobada:** [`docs/FASE0.md`](docs/FASE0.md).

## Estado actual: Fase 1 (descubrimiento de subastas en el BOE, Córdoba)

| Pieza | Estado |
|---|---|
| Descubrir subastas en el BOE (API de datos abiertos) | ✅ |
| Base de datos y detección de duplicados | ✅ |
| Guardar el original de cada anuncio como evidencia | ✅ |
| Respetar robots.txt automáticamente | ✅ |
| Fichas completas del portal (revisión asistida) | Fase 2 |
| Valoración, informes, Telegram | Fases 3–5 |

## Cómo se usa (por ahora, desde la terminal)

> No hace falta hacerlo a mano: en la Fase 5 todo se ejecuta solo en GitHub cada semana.

1. Instalar (una sola vez). Hace falta Python 3.12 o superior:
   ```
   python -m venv .venv
   .venv/bin/pip install -e ".[dev]"
   ```
2. Buscar subastas de los últimos 45 días:
   ```
   .venv/bin/python -m tareas.descubrir
   ```
   Tarda unos minutos porque espera 4 segundos entre cada petición a la web del BOE (es lo que pide el SPEC para no molestar). Se puede repetir sin problema: nunca duplica nada.
3. Generar el listado de subastas activas:
   ```
   .venv/bin/python -m tareas.listado
   ```
   Escribe un `.md` (para leer) y un `.csv` (para abrir con Excel) en `data/salidas/`.
4. Comprobar que todo funciona:
   ```
   .venv/bin/python -m pytest
   ```

## Cómo cambiar parámetros

Todo está en [`config/config.yaml`](config/config.yaml), con un comentario en cada línea. Por ejemplo:

- **Añadir provincias:** cambia `provincias_activas: [14]` por `[14, 41, 29, 21]`.
- **Revisar más días hacia atrás:** cambia `dias_hacia_atras`.

## Dónde se guarda cada cosa

| Carpeta | Contenido |
|---|---|
| `config/` | Parámetros |
| `fuentes/` | Un conector por cada web de la que se leen datos |
| `db/` | Esquema y acceso a la base de datos |
| `tareas/` | Lo que se ejecuta: descubrir, listado… |
| `comun/` | Piezas compartidas (cliente web prudente, nombres de lugares…) |
| `tests/` | Comprobaciones automáticas con páginas reales guardadas |
| `data/` | Base de datos, evidencias y salidas. No se sube al repositorio. |
| `docs/` | Documentos del proyecto |

## Reglas que el sistema cumple siempre

- Nunca entra en una web que lo prohíba en su robots.txt. Lo comprueba automáticamente antes de cada descarga.
- Nunca se salta captchas ni logins. Nunca puja ni se registra en ninguna plataforma.
- Nunca envía nada a terceros. Todo pasa primero por Jesús.
- Los secretos (tokens) nunca van en el repositorio.
