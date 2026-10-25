# Fase 0 — Propuesta de arquitectura

**Proyecto:** Radar de oportunidades inmobiliarias con descuento
**Fecha:** 25/10/2026 · **Para:** Jesús · **Estado:** aprobada el 25/10/2026 (plan de Claude: Pro; respuesta del bot en ~1 min aceptada)

> Este documento resume cómo se va a construir el sistema. No hay código todavía.
> Cuando lo apruebes, aplico los cambios propuestos a SPEC.md y empiezo la Fase 1.

---

## 1. Tus decisiones (sección 16 del SPEC)

| # | Pregunta | Tu respuesta | Qué implica |
|---|---|---|---|
| 1 | Hosting | **0 €** | Todo sobre servicios gratuitos: GitHub Actions + Cloudflare Workers (ver §3). |
| 2 | Presupuesto API de Claude | **0 €** | No se usa la API de pago. Ver §2: cambio importante. |
| 3 | ¿Compran por sociedad? | No lo sé | ITP general del 7 %. Toda operación lleva "fiscalidad pendiente de verificar". |
| 4a | Margen sobre beneficio antes de impuestos | OK | El informe dirá "margen antes de impuestos". |
| 4b | Comisión de venta con IVA | OK | 3,63 %. |
| 4c | Coste de reforma | **Análisis real por ciudad y zona** | Se hace en la Fase 3 con fuentes citadas (ver §6.3). Mientras tanto, 300/550/850 €/m² como valor provisional. |
| 4d | Descuento 25 %, alquiler 7 % | OK | Sin cambios. |
| 5 | Avisos de Telegram | Solo Jesús | Un único chat autorizado. |
| 6 | Make.com | Sustituir | He revisado tu cuenta de Make (eu2.make.com) y **no hay ningún escenario del BOE**: solo "Agente Triaje Dental - WhatsApp". Puede que el del BOE esté en otra cuenta. No bloquea nada: el conector del BOE de la Fase 1 lo sustituye igualmente. |
| 7 | Buzón con Claude con navegador | Google Drive | Se implementa en la Fase 6. |
| 8 | GitHub | Sí | Falta que me digas el nombre del repositorio (ver §9). |
| 9 | Email de contacto | jesus20000220@gmail.com | Se usará en el "user-agent" con el que el sistema se identifica ante las webs. Los administradores de esas webs podrán verlo. |

---

## 2. Cambio importante: "0 € de API de Claude"

El SPEC usa la API de Claude (de pago por uso) para dos cosas: **leer textos** (edictos, fichas, PDFs) y **redactar** los textos de los informes. Con 0 € propongo esto:

1. **Lo estructurado se lee con código, sin IA.** La ficha del Portal de Subastas del BOE ya tiene campos separados: valor, tasación, puja mínima, depósito, referencia catastral, "situación posesoria", "visitable", cargas… Eso lo lee el código sin coste y sin errores de interpretación. Así se cubre la mayor parte de los datos de la Fase 1 y la Fase 2.
2. **Lo ambiguo (texto libre de cargas u ocupación) se clasifica en dos pasos:**
   - **Primero, reglas de palabras clave.** Por ejemplo, "se encuentra ocupado", "libre de ocupantes", "sin posesión". Cada resultado se guarda con su confianza y la cita literal.
   - **Lo que las reglas no resuelvan con seguridad** pasa a "pendiente de verificar", o a la cola de revisión con Claude.
3. **Redacción de los informes:** plantillas de texto rellenadas con los datos calculados. El resultado es sobrio, pero no se inventa nada.
4. **Si quieres textos redactados por Claude sin pagar API:** se puede usar tu **suscripción de Claude** (Pro o Max) desde GitHub Actions. Claude Code admite autenticarse con tu suscripción en lugar de con una clave de API. No cuesta dinero extra, pero **consume parte de tu uso** de la suscripción, igual que la tarea con navegador. Lo probaríamos en la Fase 2 y lo activas solo si te convence.
   - **Necesito saber qué plan de Claude tienes** (ver §9).

El principio "la IA nunca calcula" se mantiene: todos los números los hace el motor determinista.

---

## 3. Hosting: comparación y recomendación

| | **A. GitHub Actions + Cloudflare Worker (recomendada)** | B. VPS gratuito (Google Cloud e2-micro) | C. VPS de pago (el del SPEC) |
|---|---|---|---|
| Coste mensual | **0 €** | 0 € (pide tarjeta; riesgo de pequeños cargos si se configura mal) | ~4–6 € |
| Ejecución semanal y diaria | GitHub Actions (programado) | cron | cron |
| Bot de Telegram | Un mini-programa gratuito en Cloudflare recibe cada pulsación y lanza una tarea en GitHub | Siempre escuchando | Siempre escuchando |
| Tiempo de respuesta del bot | **30–90 segundos** | Inmediato | Inmediato |
| Mantenimiento | Ninguno (no hay servidor que actualizar) | Hay que mantener el servidor | Hay que mantener el servidor |
| Si algo falla | GitHub te avisa por email y el bot por Telegram | Depende de que el servidor siga vivo | Igual |

**Recomiendo la A.** Cumple tu presupuesto de 0 €, no hay ningún servidor que cuidar y todo queda guardado en GitHub.

**El único inconveniente:** cuando pulses "Aprobar" o pidas `/ficha 123`, la respuesta tarda alrededor de un minuto. El bot contesta al instante "⏳ Procesando…" para que sepas que lo ha recibido. Si esto te molesta, más adelante se puede pasar a la B o la C sin rehacer nada.

### Cómo funciona la opción A, en sencillo

```
Cada lunes 07:00 y cada día (chequeo de cierres)
        │
        ▼
GitHub Actions ──► consulta las fuentes ──► actualiza la base de datos
        │                                        (archivo guardado en el propio repositorio)
        ▼
calcula valoración y score ──► genera PDF ──► te lo manda por Telegram

Tú pulsas un botón en Telegram
        │
        ▼
Cloudflare Worker (gratis) ── comprueba que eres tú ──► lanza una tarea en GitHub Actions
                                                              │
                                                              ▼
                                               actualiza estado / genera teaser / responde
```

- **Base de datos:** un único archivo SQLite que se guarda en una rama aparte del repositorio privado (`datos`) después de cada ejecución. Cada ejecución queda como una versión, así que si algo sale mal se puede volver atrás.
- **Una cosa a la vez:** las tareas se ponen en fila para que dos ejecuciones nunca escriban en la base de datos al mismo tiempo.
- **Evidencias (HTML y PDF originales):** se comprimen y se suben cada semana como un paquete adjunto en GitHub ("Releases"). No engordan el repositorio y no tienen coste.

### Coste mensual estimado (opción A)

| Concepto | Uso estimado | Límite gratuito | Coste |
|---|---|---|---|
| GitHub (repositorio privado + Actions) | ~400 min/mes (ejecución semanal ~10 min, diaria ~3 min, botones ~1 min cada uno) | 2.000 min/mes | 0 € |
| Cloudflare Workers | Unas pocas pulsaciones al día | 100.000 peticiones/día | 0 € |
| Telegram | — | Gratis | 0 € |
| Claude | Plantillas, o tu suscripción si la activas | — | 0 € extra |
| **Total** | | | **0 €/mes** |

### Riesgo a comprobar en la Fase 1
GitHub Actions se ejecuta desde ordenadores de centros de datos. Algunas webs bloquean ese tipo de conexión. El primer día de la Fase 1 compruebo que el BOE responde desde GitHub. Si no responde, te lo digo y elegimos entre la B y la C.

---

## 4. Librerías (piezas de software ya hechas que usaremos)

| Pieza | Para qué | Por qué |
|---|---|---|
| Python 3.12 | Lenguaje principal | El que pide el SPEC; el más usado para este tipo de tareas. |
| httpx | Descargar páginas y APIs | Moderno y fiable. Le añadimos la pausa de 3–5 s entre peticiones y la caché. |
| selectolax | Leer el HTML de las fichas | Rápido y sencillo. Playwright (navegador automático) solo si alguna web lo exige. |
| Pydantic | Validar que cada dato tiene la forma correcta | Si un dato llega raro, se detecta en lugar de colarse en el informe. |
| SQLite | Base de datos | Un único archivo, sin servidor, sin coste. Suficiente para decenas de miles de registros. |
| Jinja2 + WeasyPrint | Generar los PDF a partir de plantillas HTML | La marca (logo, colores, tipografías) queda en un solo archivo, como pide el SPEC. |
| python-telegram-bot | Enviar mensajes, PDFs y botones | Estándar de facto. |
| pytest | Tests automáticos | Para los casos calculados a mano y el test del teaser ciego. |
| Cloudflare Worker (JavaScript, ~50 líneas) | Recibir las pulsaciones de Telegram | La única pieza que no es Python: es lo que admite el plan gratuito. |

---

## 5. Esquema de base de datos

Explicado en sencillo: es una **colección de tablas, como hojas de Excel enlazadas entre sí**.

### Una mejora sobre el SPEC: subasta → lote → bien
Una misma subasta del BOE puede tener **varios lotes**, cada uno con su propio valor y su propia puja. Y un lote puede incluir **varios bienes**, por ejemplo vivienda + garaje + trastero. Por eso:
- **evento_venta** se guarda por lote. Una subasta con 3 lotes son 3 eventos.
- Una tabla de enlace une cada lote con sus bienes.

Así un garaje que va "dentro de un lote" con una vivienda no se descarta, como pide §6.

### Tablas

| Tabla | Qué guarda (una fila = …) | Campos principales |
|---|---|---|
| **activo** | Un inmueble físico | id, tipo, provincia, municipio, dirección, dirección normalizada, CP, referencia catastral, finca registral, registro, superficie (catastro / nota simple / útil / construida, cada una con su fuente), año, estado de conservación estimado, coordenadas, fotos |
| **evento_venta** | Una vez que ese inmueble sale a la venta (un lote de una subasta, una venta directa…) | id, fuente, identificador externo (SUB-…), nº de lote, tipo (JA/JC/JV/AT/notarial/venta directa/servicer…), autoridad, administrador concursal (nombre y contacto profesional), valor de subasta, tasación, puja mínima, depósito, comisión de plataforma, fecha de inicio, fecha de fin, estado, puja máxima, participación (%), URL, fecha de detección, última comprobación |
| **evento_activo** | El enlace entre un lote y sus bienes | evento_id, activo_id |
| **dato_verificable** | Cada dato jurídico por separado (cargas, ocupación, posesión, deuda de comunidad, IBI, visitas…) | activo_id / evento_id, campo, valor, **fuente, confianza** (verificado / extraído / estimado / desconocido), **cita literal**, fecha |
| **referencia_mercado** | Un dato de precio de una zona | fuente, ámbito (municipio / CP / barrio), tipología, tipo (escriturado / oferta / alquiler), periodo, €/m², nº de operaciones, fecha de descarga |
| **coste_reforma** | El coste de reforma de una ciudad o zona | ciudad, zona, nivel (ligera / media / integral), €/m², fuente, fecha |
| **parametros** | Cada versión de config.yaml | versión, contenido, fecha. Así cada valoración sabe con qué números se calculó. |
| **valoracion** | Un cálculo del motor para un evento | evento_id, versión de parámetros, valor conservador/base/optimista, P_max, inversión total, margen, rentabilidad de alquiler, TIR, sensibilidad, score, semáforos, **explicación de cada cifra** (fórmula + origen), confianza |
| **oportunidad** | Una operación que sigue su ciclo (§10) | id, activo_id, evento_id, estado actual, motivo de descarte |
| **historial_estado** | Cada cambio de estado | oportunidad_id, de → a, fecha, motivo, quién (sistema o Jesús) |
| **envio** | Qué se ha mandado | oportunidad_id, versión (teaser / completo), destinatario, fecha, archivo |
| **documento** | Cada HTML o PDF original guardado como evidencia | URL, tipo, huella digital (hash), dónde está guardado, fecha |
| **ejecucion** | Cada vez que corre el sistema | tipo (semanal / diaria / botón), inicio, fin, resultado, resumen |
| **salud_fuente** | El estado de cada fuente en cada ejecución | ejecucion_id, fuente, nº de resultados, errores, bloqueos (captcha/login) |
| **alerta_enviada** | Cada aviso de Telegram enviado | clave única. Garantiza que **nunca se repite un aviso** aunque se vuelva a ejecutar. |

**Detección de duplicados**, en el orden del SPEC: referencia catastral → finca registral + registro → dirección normalizada + superficie. Cuando hay coincidencia, el sistema no crea un activo nuevo: añade un evento de venta al activo existente. Así se detecta la alerta 4 ("reaparece más barato").

**Datos personales:** no hay ningún campo para nombres de deudores ni de ocupantes. Si aparecen en un texto, se eliminan de la cita antes de guardarla. Los eventos cerrados se limpian a los 12 meses.

---

## 6. Cambios propuestos al SPEC (se aplican cuando apruebes)

### 6.1 Fuente principal para detectar subastas (§4)
La **búsqueda avanzada del Portal de Subastas** por provincia pasa a ser la fuente principal. El sumario del BOE queda como complemento y como control cruzado. Motivo: el criterio de aceptación de la Fase 1 se comprueba contra el portal.

### 6.2 Valor de mercado (§7.1)
El Portal Estadístico del Notariado da **medias por zona**, no ventas sueltas. No se pueden calcular percentiles ni exigir 5 comparables. Nueva regla:
- **Base:** €/m² escriturado de la zona más pequeña disponible (CP mejor que municipio) y de la tipología más parecida, últimos 12 meses.
- **Conservador:** base −10 % (configurable).
- **Optimista:** base +10 %, solo después de reformar (configurable).
- **Contraste:** precio de oferta de la zona −10 %.
- **Confianza baja** si: solo hay dato de municipio, el dato tiene más de 12 meses, hay menos de 10 operaciones en la zona, o el escriturado y la oferta difieren más de un 25 %.

### 6.3 Coste de reforma por ciudad y zona (tu respuesta 4c)
En la Fase 3 preparo una tabla de €/m² por ciudad (las 4 capitales y los municipios prioritarios) y nivel de reforma, con estas fuentes citadas:
- **BCCA** (Base de Costes de la Construcción de Andalucía, publicada por la Junta).
- **Generador de precios de CYPE** (por provincia).
- Informes públicos de precios de reformas.
- Un recargo por zona donde esté justificado, por ejemplo en cascos históricos con protección patrimonial, donde las licencias y los materiales son más caros.

Te la presento para que la valides. Si consigues presupuestos reales, tienen prioridad sobre todo lo demás.

### 6.4 Comisión de plataforma
Es 0 en el Portal del BOE. Solo se aplica en plataformas privadas, leída de sus condiciones.

### 6.5 Fórmula del precio máximo (§7.2)
Si el inmueble está ocupado, se suman los meses de desocupación a los meses del coste financiero:
`f = coste_financiero × (meses_posesión + meses_desocupación + meses_reforma_y_venta) / 12`

### 6.6 Riesgo fiscal del ITP
En Andalucía, Hacienda puede calcular el ITP sobre el **valor de referencia del Catastro** en lugar de sobre el precio pagado. Si se compra barato, se puede pagar más impuesto del previsto. El informe lo muestra como riesgo ámbar y la pregunta queda anotada para tu asesor.

### 6.7 Nuevas fuentes gratuitas
- **Catastro** (servicio oficial): da la superficie y el año a partir de la referencia catastral, y ayuda a detectar duplicados.
- **Sistema Estatal de Referencia del Precio del Alquiler** (Ministerio de Vivienda): sirve para estimar la renta en el cálculo de alquiler (§7.3), que el SPEC no decía de dónde sacar.

### 6.8 API de Claude
Ver §2: plantillas y reglas por defecto; suscripción de Claude como opción.

### 6.9 Hosting
Ver §3: GitHub Actions + Cloudflare Worker.

### 6.10 El Portal de Subastas prohíbe el acceso automático (descubierto el 25/10/2026)
El archivo de reglas para robots de `subastas.boe.es` (robots.txt) dice `Disallow: /`. Eso significa que no admite ningún programa automático en ninguna de sus páginas. Según §4, una fuente así **pasa a revisión asistida o se descarta**. Lo que sí está permitido es la **API de datos abiertos del BOE**. He comprobado que cada día publica, en la sección IV, un anuncio por cada subasta judicial con esta información: juzgado y localidad, tipo (apremio / concursal / voluntaria), identificador SUB-… y enlace.

Nuevo reparto:
- **Código (automático, legal y gratis):** descubre todas las subastas nuevas a través de la API del BOE. De cada una guarda el identificador, el tipo, el juzgado y la fecha. La provincia se deduce del partido judicial del juzgado. Se descartan las que no son de las 4 provincias.
- **Claude con navegador (revisión asistida):** cada lunes recibe la lista de subastas nuevas de las 4 provincias, abre cada ficha en modo solo lectura y deja los datos (valor, tasación, puja mínima, bienes, cargas, ocupación…) en JSON en la carpeta de Google Drive. Después, el código los importa, valora y puntúa. **Esta pieza pasa de la Fase 6 a las Fases 1–2** y necesita tu ordenador encendido con la app de Claude abierta el lunes por la mañana.
- **En paralelo:** se pide al BOE autorización por escrito para consultar las fichas de forma automática y a ritmo lento. Si la conceden, se sustituye la revisión asistida por un conector de código sin tocar nada más.
- Pendiente de verificar en la Fase 1: si las subastas de la Agencia Tributaria, la Seguridad Social y las notariales también se anuncian en el BOE, y en qué sección.

---

## 7. Estructura de carpetas

```
radar/                         ← repositorio privado de GitHub
├── SPEC.md                    ← la fuente de verdad
├── README.md                  ← manual para no programadores
├── config/
│   ├── config.yaml            ← todos los parámetros que puedes tocar
│   └── marca.css              ← logo, colores y tipografías (fase de diseño)
├── fuentes/                   ← un archivo por fuente, todos con la misma forma
│   ├── base.py                ← la "forma común" (interfaz)
│   ├── boe_sumario.py
│   ├── boe_subastas.py
│   ├── catastro.py
│   └── notariado.py
├── extraccion/                ← reglas para leer cargas y ocupación; esquemas de datos
├── valoracion/                ← el motor de §7 (fórmulas, TIR, sensibilidad)
├── scoring/                   ← el score de §8 y los semáforos
├── informes/
│   ├── plantillas/            ← teaser, completo, resumen semanal (HTML)
│   └── generar.py
├── bot/
│   ├── telegram.py            ← mensajes, botones y comandos
│   └── worker/                ← el mini-programa de Cloudflare
├── db/
│   └── esquema.sql            ← las tablas de §5
├── tareas/                    ← lo que ejecuta GitHub: semanal, diaria, botón
├── tests/
│   ├── fixtures/              ← HTML y PDF reales guardados
│   ├── test_valoracion.py     ← casos calculados a mano
│   └── test_teaser_ciego.py   ← que no se cuele ningún dato identificativo
├── .github/workflows/         ← los horarios de ejecución
└── data/                      ← (rama aparte "datos") base de datos y caché
```

Los secretos (token de Telegram, token de GitHub para el Worker) van en el gestor de secretos de GitHub y Cloudflare, **nunca** en el código.

---

## 8. Qué verás al final de la Fase 1

- Un listado de las subastas de inmuebles activas en la provincia de Córdoba, generado por el sistema.
- Una comparación con 20 búsquedas manuales en el portal, que haremos juntos, con cero omisiones.
- La base de datos con duplicados resueltos y la evidencia original guardada de cada ficha.

**Requisito previo:** permitir el acceso a la red desde el entorno donde trabajo. Ahora mismo `boe.es` está bloqueado. Dominios: `boe.es`, `subastas.boe.es`, `ovc.catastro.meh.es`, `api.telegram.org`, `github.com`. Más adelante, también los del Notariado. Se cambia en el menú del entorno (barra de título de la sesión → Edit → Network access). Pasos: https://code.claude.com/docs/en/cloud-environments#network-access

---

## 9. Lo que necesito de ti para aprobar y arrancar

1. **¿Apruebas esta Fase 0?** Incluye los cambios de §6 (sobre todo el 6.10) y el hosting de §3.
2. **Nombre del repositorio privado de GitHub.** Créalo vacío, por ejemplo `radar-inmobiliario`, y dime `usuario/nombre`.
3. **¿Qué plan de Claude tienes** (Pro, Max u otro)? Solo importa para la opción de textos redactados con tu suscripción (§2.4).
4. **¿Te vale que el bot tarde ~1 minuto en responder** a los botones (§3)?
5. Ampliar el acceso a la red del entorno (§8), cuando vayamos a empezar la Fase 1.
