# Fase 1: comprobación contra el Portal de Subastas

**Criterio de aceptación (SPEC §14):** el listado de subastas de inmuebles activas en Córdoba que genera el sistema coincide con una búsqueda manual en el portal: ninguna omisión en una muestra de 20.

Como el portal no permite programas automáticos, la búsqueda la haces tú o Claude in Chrome en tu ordenador. Elige una de las dos opciones.

## Opción A: tú, a mano (unos 10 minutos)

1. Entra en https://subastas.boe.es y pulsa **Búsqueda avanzada**.
2. Rellena:
   - **Estado:** Celebrándose.
   - **Tipo de bien:** Inmuebles.
   - **Provincia:** Córdoba.
   - Deja **todos los tipos de subasta** (judicial, administrativa, notarial…).
3. Pulsa **Buscar**.
4. Copia los identificadores (`SUB-JA-2026-…`, `SUB-AT-2026-…`) de los 20 primeros resultados y pégamelos en el chat. Si hay menos de 20, copia todos.

## Opción B: Claude in Chrome

Pega esto en Claude in Chrome:

```
Abre https://subastas.boe.es → Búsqueda avanzada. Solo lectura: no inicies sesión,
no te registres, no pujes ni envíes formularios distintos del de búsqueda. Si aparece
un captcha o un login, para y avísame.

Busca: Estado = Celebrándose, Tipo de bien = Inmuebles, Provincia = Córdoba, todos
los tipos de subasta.

Devuélveme una lista con los primeros 20 resultados (o todos, si hay menos), una línea
por subasta: identificador SUB-…, tipo de subasta, órgano gestor y fecha de conclusión.
Nada más.
```

## Qué haré con esa lista

Cruzaré cada identificador con el listado del sistema y te diré cuáles aparecen y cuáles faltan. De los que falten, explicaré por qué.

Ya sé de dos casos en los que el BOE no basta para detectar una subasta:
- **Juzgado de otra provincia:** por ejemplo, un concurso tramitado en Madrid con un inmueble en Córdoba. El anuncio sale con la localidad del juzgado, no la del inmueble.
- **Agencia Tributaria de fuera de Andalucía:** la AEAT anuncia desde su oficina regional sin decir la provincia del bien.

Si aparecen omisiones de este tipo, se cubren con la búsqueda semanal asistida por provincia en el portal (Fase 2), que es la que da la lista completa.
