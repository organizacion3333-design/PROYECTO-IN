# SPEC.md — Radar de oportunidades inmobiliarias con descuento

**Versión 1.0 · 25/10/2026 · Responsable: Jesús**
Nombre y marca provisionales: se definen en la fase de diseño.

---

## 0. Cómo usar este documento

- Guárdalo en la raíz del repositorio como `SPEC.md`.
- Es la fuente de verdad del proyecto. Si algo cambia, se cambia aquí primero.
- Claude Code debe leerlo entero antes de proponer nada y trabajar por fases (sección 14).
- El prompt de arranque está en el Anexo A. El prompt de la tarea programada con navegador está en el Anexo B.

---

## 1. Objetivo

Construir un sistema que cada semana, sin intervención:

1. Detecte inmuebles con descuento real en Córdoba, Sevilla, Málaga y Huelva.
2. Los filtre y valore con criterio de inversor profesional y con números trazables.
3. Genere un dossier por operación (versión teaser ciega y versión completa) y un resumen semanal.
4. Me los envíe por Telegram para revisarlos y aprobarlos antes de presentarlos al grupo de inversores.

**Modelo de negocio:** presento operaciones a un grupo de inversores privados y cobro comisión por cada operación cerrada. El sistema debe proteger esa comisión (teaser ciego, §11.2) y mi credibilidad (nada se envía sin revisión y nada se inventa).

**Principio rector: el sistema propone y Jesús decide.** Nada sale hacia los inversores sin mi aprobación explícita.

---

## 2. Alcance

### 2.1 Zonas
- Provincias: Córdoba (14), Sevilla (41), Málaga (29), Huelva (21).
- Prioridad inicial: capitales y municipios de más de 20.000 habitantes (configurable).

### 2.2 Activos
- Viviendas para reformar, para vender o alquilar.
- Edificios completos y lotes de viviendas.
- Suelos y solares urbanos y urbanizables.
- Locales convertibles en vivienda o en apartamento turístico. Marcar siempre "cambio de uso pendiente de verificar con la normativa municipal".
- Cualquier inmueble con una causa de descuento identificable.

### 2.3 Causas de descuento a detectar
| Causa | Ejemplos |
|---|---|
| Subasta judicial | Apremio (JA), voluntaria (JV), concursal (JC) |
| Subasta administrativa | Agencia Tributaria (AT), Seguridad Social, otras administraciones |
| Subasta notarial | Ejecuciones extrajudiciales |
| Liquidación concursal | Entidades especializadas (ActCon, Escrapalia…), venta directa del administrador concursal |
| Tras subasta desierta | Venta directa, nueva subasta sin mínimo, relistado más barato |
| Situación jurídica | Ocupado, sin posesión, nuda propiedad, proindiviso, herencia, cesión de remate |
| Activo bancario | Servicers y bancos |

### 2.4 Tickets
Todos los importes. Cada operación se clasifica en un tramo:
**A** < 100.000 € · **B** 100.000–300.000 € · **C** 300.000 €–1 M€ · **D** > 1 M€.

---

## 3. Arquitectura: híbrida (código + Claude con navegador)

**Decisión de diseño:** lo masivo y repetitivo lo hace el código. Claude con navegador se usa solo donde el código no llega.

```
[Fuentes]
   │
   ▼
A. Ingesta automática (código, programada)
   │
   ▼
B. Base de datos (histórico, deduplicación, estados)
   │        ▲
   │        │ datos enriquecidos (JSON con esquema fijo)
   ▼        │
C. Cola de revisión asistida ──► Claude con navegador (tarea programada o a demanda, Anexo B)
   │
   ▼
D. Motor de valoración y scoring (código determinista)
   │
   ▼
E. Extracción y redacción con Claude (API)
   │
   ▼
F. Informes (HTML → PDF)
   │
   ▼
G. Telegram: aviso a Jesús + aprobación
```

### Reparto de trabajo y por qué
- **Código (A, B, D, F, G):** es barato, repetible semana a semana, guarda el histórico y no depende de que mi ordenador esté encendido.
- **Claude API (E):** lee edictos, fichas y PDFs de condiciones, los convierte en datos estructurados y redacta los textos. No hace cálculos.
- **Claude con navegador (C):** para webs que el código no puede leer de forma permitida o estable, y para revisar a fondo las fichas de las mejores candidatas. Solo funciona con la app de escritorio de Claude abierta y el ordenador encendido. Consume bastante uso por ejecución, así que se reserva para pocas tareas de alto valor.
- **Buzón de intercambio entre C y B:** una carpeta compartida (p. ej. Google Drive) donde Claude con navegador deja ficheros JSON con el esquema de §5, y la ingesta los importa. Claude Code puede proponer una alternativa más simple.

### Hosting
- **Recomendación:** un VPS pequeño (unos 5 €/mes), con cron para las ejecuciones y el bot de Telegram siempre activo. Los botones de Telegram necesitan un proceso escuchando.
- **Alternativa:** GitHub Actions para la ejecución semanal y una función serverless para el webhook del bot. En ese caso la base de datos tiene que persistir entre ejecuciones.
- Claude Code compara ambas opciones en la Fase 0, con el coste estimado de cada una.

---

## 4. Fuentes

| # | Fuente | Qué aporta | Método | Fase |
|---|---|---|---|---|
| 1 | API de datos abiertos del BOE (sumario diario, sección IV "Administración de Justicia") | Descubre anuncios nuevos de subasta con su identificador SUB-XX-AAAA-NNNNNN y su enlace | API oficial | F1 |
| 2 | Portal de Subastas del BOE (subastas.boe.es) | Ficha completa: valor, tasación, puja mínima, depósito, bienes, cargas, autoridad gestora, administrador concursal, estado y pujas | Búsqueda avanzada por tipo y provincia + ficha HTML | F1 |
| 3 | Registro Público Concursal (publicidadconcursal.es) | Alerta temprana: empresas de las 4 provincias en fase de liquidación | HTML | F6 |
| 4 | ActCon (subastas y ventas concursales) | Activos concursales | HTML | F6 |
| 5 | Escrapalia / Surus Inmuebles | Activos concursales y de empresas | HTML | F6 |
| 6 | Subastas de Procuradores (CGPE) | Subastas encargadas a procuradores | HTML | F6 |
| 7 | eactivos, IAG, Valoralia, Baratura | Liquidaciones | HTML | F6+ |
| 8 | Servicers y bancos (Altamira, Solvia, Haya, Servihabitat, Aliseda) | Ocupados, sin posesión, descuentos | HTML | F7 |
| 9 | Portales (Idealista, Fotocasa) | Ocupados, nuda propiedad, cesiones de remate | Solo con la API oficial si se consigue acceso, o por revisión asistida. **No hacer scraping contra sus condiciones de uso.** | F7 |
| 10 | Datos de mercado: Portal Estadístico del Notariado (€/m² escriturado por municipio o CP), estadística registral, precios de oferta solo como contraste | Comparables y valor de mercado | API, HTML o descarga | F3 |

### Reglas de acceso (obligatorias)
- Orden de preferencia: API o datos abiertos, luego HTML público y, por último, navegador asistido.
- Respetar robots.txt y las condiciones de uso. Si una fuente prohíbe el acceso automatizado, pasa a revisión asistida o se descarta.
- Ritmo prudente: al menos 3-5 segundos entre peticiones al mismo dominio, caché local y un user-agent identificable con email de contacto.
- **Nunca** saltarse captchas, logins ni bloqueos. Si ocurre, se registra y se avisa por Telegram.
- Guardar el HTML o PDF original de cada ficha, como evidencia y para depurar.

---

## 5. Modelo de datos (mínimo)

- **activo:** id interno, tipo, provincia, municipio, dirección, CP, referencia catastral, finca registral y registro, superficies (catastro, nota simple, útil o construida), año, estado de conservación estimado, coordenadas, fotos.
- **evento_venta:** id, activo_id, fuente, identificador externo (SUB-…), tipo (JC/JA/JV/AT/notarial/venta directa/servicer…), autoridad (juzgado, AEAT…), administrador concursal (nombre y contacto profesional), valor de subasta, tasación, puja mínima, depósito, comisión de la plataforma, fechas de inicio y fin, estado, puja actual o máxima, URL, fecha de detección y última comprobación.
- **situacion_juridica:** cargas anteriores y posteriores, cuáles se cancelan, ocupación (libre / ocupado / desconocido), posesión, deuda conocida de comunidad e IBI, posibilidad de visita. **Cada campo lleva `fuente` y `confianza`** (verificado / extraído / estimado / desconocido) y, si viene de un texto, la cita literal.
- **comparable:** fuente, fecha, €/m², superficie, distancia, tipo (escriturado / oferta).
- **valoracion:** versión de parámetros, escenarios, precio máximo de oferta, márgenes, TIR, score y semáforos.
- **oportunidad:** estado actual e historial de estados (§10).
- **envio:** qué se envió, a quién, cuándo y en qué versión (teaser o completo).

**Deduplicación,** en este orden: referencia catastral; finca registral + registro; dirección normalizada + superficie. Un mismo activo puede tener varios eventos de venta (p. ej. subasta desierta y después aparece en otra plataforma).

**Datos personales:** no guardar nombres de deudores ni de ocupantes que sean personas físicas más allá de lo imprescindible. Nunca aparecen en los informes (§12).

---

## 6. Configuración (`config.yaml`)

Todos los valores son supuestos iniciales y se validan conmigo en la Fase 0.

```yaml
zonas:
  provincias: [14, 41, 29, 21]        # Córdoba, Sevilla, Málaga, Huelva
  municipios_prioritarios: [Córdoba, Sevilla, Málaga, Huelva]   # ampliable

filtros:
  descuento_minimo: 0.25              # sobre valor de mercado conservador
  margen_neto_minimo_flip: 0.20       # beneficio neto / inversión total
  rentabilidad_bruta_min_alquiler: 0.07
  participacion_minima: 0.50          # excluir cuotas < 50 %
  dias_minimos_hasta_cierre: 5        # tiempo mínimo para due diligence
  excluir_sueltos: [garaje, trastero] # salvo que formen parte de un lote

costes:
  itp: 0.07                           # Andalucía, tipo general. Posible tipo reducido
                                      # para sociedades que revenden: verificar con asesor
  iva_si_vendedor_empresa: verificar  # marcar "fiscalidad pendiente de verificar"
  notaria_registro: 0.015
  comision_plataforma: leer_de_condiciones   # si no consta → "pendiente"
  comision_venta: 0.03
  plusvalia_municipal_venta: 0.005    # estimación, varía por municipio
  reforma_eur_m2: {ligera: 300, media: 550, integral: 850}   # ajustar con presupuestos reales
  imprevistos_reforma: 0.15
  deuda_comunidad: "año en curso + 3 anteriores (si se conoce)"
  desocupacion: {coste: 6000, meses: 12}     # supuesto, ajustar
  coste_financiero_anual: 0.06
  meses_hasta_posesion: {subasta_judicial: 6, concursal: 4, venta_directa: 3}
  meses_reforma_y_venta: 6
  descuento_oferta_a_cierre: 0.10     # cuando solo hay precios de oferta

scoring:
  pesos: {descuento: 30, margen: 25, riesgo: 20, liquidez: 15, plazo: 10}
  umbral_dossier: 65

ejecucion:
  semanal: "lunes 07:00 Europe/Madrid"
  chequeo_diario_cierres_y_estados: true

api_claude:
  modelo: configurable
  presupuesto_mensual_eur: 30         # a confirmar

telegram:
  chats_autorizados: [jesus]
```

---

## 7. Motor de valoración (código determinista; nunca lo calcula el LLM)

### 7.1 Valor de mercado: tres escenarios
- **Conservador:** percentil 25 de los comparables escriturados, o la mediana escriturada −5 %.
- **Base:** mediana escriturada, o precio de oferta menos `descuento_oferta_a_cierre`.
- **Optimista:** percentil 75, solo después de reformar.
- Mínimo 5 comparables. Si hay menos, la valoración se marca como de **baja confianza**.
- Se distingue el valor en el estado actual del valor después de la reforma.

### 7.2 Precio máximo de oferta (comprar, reformar y vender)

Definiciones:
- `V_neto = V_conservador × (1 − comision_venta − plusvalia_municipal_venta)`
- `t = itp + notaria_registro + comision_plataforma`
- `f = coste_financiero_anual × (meses_hasta_posesion + meses_reforma_y_venta) / 12`
- `R = reforma = m² × €/m² según estado × (1 + imprevistos)`
- `D = deudas que no se cancelan (comunidad, IBI)`
- `O = coste de desocupación (si está ocupado)`
- `m = margen_neto_minimo_flip`

Inversión total: `I = P × (1 + t + f) + R × (1 + f) + D + O`

Condición: `(V_neto − I) / I ≥ m`

**Precio máximo de oferta:**
`P_max = [ V_neto / (1 + m) − R × (1 + f) − D − O ] / (1 + t + f)`

### 7.3 Alquiler
- Rentabilidad bruta = renta anual estimada / I.
- Rentabilidad neta = (renta − IBI − comunidad − seguro − mantenimiento − vacío) / I.

### 7.4 TIR y plazo
- Flujos mensuales: compra, reforma y venta en el mes N. Se calcula la TIR anualizada.

### 7.5 Sensibilidad
- Tabla del precio de compra (−10 % / 0 / +10 %) frente al precio de venta (−10 % / 0 / +10 %), mostrando el margen resultante.

### 7.6 Trazabilidad
- Cada cifra del informe se puede rastrear hasta su origen: una fuente, o una fórmula con sus parámetros.
- Los parámetros se versionan, y cada valoración guarda la versión que usó.

---

## 8. Scoring (0–100)

| Factor | Peso | Criterio |
|---|---|---|
| Descuento | 30 | Sobre el valor conservador |
| Margen o rentabilidad | 25 | Flip o alquiler, el que sea mejor |
| Riesgo (inverso) | 20 | Ocupación, cargas, posesión, urbanismo, estado, competencia esperada |
| Liquidez de la zona | 15 | Rotación y número de comparables |
| Plazo | 10 | Tiempo suficiente para hacer la due diligence |

- Semáforo verde, ámbar o rojo por cada riesgo, con el criterio documentado.
- **Penalizaciones duras:** participación < 50 %, o desconocer a la vez la ocupación y las cargas, limitan el score a 60. Sin dossier: pasa a vigilancia o a revisión asistida.
- Solo se genera dossier si el score es ≥ `umbral_dossier`.

---

## 9. Uso de Claude (API): qué hace y qué no

**Hace:**
- Extraer a JSON los datos de edictos, fichas y PDFs de condiciones, con un esquema validado con Pydantic.
- Clasificar la ocupación, las cargas y el tipo de activo cuando el texto es ambiguo, con su nivel de confianza y la cita literal del fragmento.
- Redactar el resumen ejecutivo, la tesis de inversión, los riesgos y la estrategia a partir de datos ya calculados.

**No hace:**
- Cálculos financieros. Los hace el motor de §7.
- Rellenar huecos. Si falta un dato, se pone "pendiente de verificar".
- Decidir envíos.

**Control de coste:**
- Solo se llama a la API para los candidatos que pasan un prefiltro barato.
- Se registran los tokens y el coste de cada ejecución, con un límite mensual configurable.

---

## 10. Ciclo de vida y alertas

**Estados:**
`detectada → descartada_auto | candidata → analizada → pendiente_revision → aprobada → teaser_enviado → nda_firmado → completo_enviado → negociacion → cerrada | perdida | descartada`

**Alertas por Telegram:**
1. Nueva oportunidad con score ≥ umbral.
2. Cierre próximo (≤ 7 días) de una oportunidad en vigilancia.
3. **Subasta concursal concluida sin adjudicación o desierta.** Se crea una oportunidad de "venta directa" con el contacto del administrador concursal, el último precio y el precio máximo de oferta recomendado. En la F1 hay que verificar qué información de resultado muestra el portal.
4. **El mismo activo reaparece** (en otra plataforma o en una nueva subasta) con un precio menor.
5. Cambio de estado: suspendida o cancelada.
6. Fallo de una fuente, o 0 resultados cuando lo normal es tener alguno.

---

## 11. Entregables

### 11.1 Resumen semanal (1–2 páginas)
- Oportunidades nuevas ordenadas por score.
- En vigilancia y cierres próximos.
- Desiertas y candidatas a venta directa.
- Estado de salud de cada fuente.

### 11.2 Dossier por operación, en dos versiones
- **Teaser ciego:** se envía primero a los inversores.
  - Sin dirección exacta (solo barrio o zona), sin referencia catastral, sin finca registral, sin identificador de subasta ni plataforma, sin fotos de fachada identificables.
  - Incluye tipología, superficie aproximada, tramo de inversión, tesis, números clave, riesgos y plazo.
  - Pie con aviso de confidencialidad y mi contacto.
  - **Test automático** que verifica que el teaser no contiene ningún dato identificativo.
- **Completo:** solo después de que el inversor firme el NDA y el acuerdo de honorarios (estado `nda_firmado`).
  - Estructura de contenido:
    1. Portada.
    2. Resumen ejecutivo.
    3. El activo.
    4. Situación jurídica: cargas, ocupación y posesión.
    5. Mercado y comparables.
    6. Números: escenarios, precio máximo de oferta, sensibilidad y TIR.
    7. Riesgos y mitigantes.
    8. Estrategia y calendario: pujar hasta X / esperar a que quede desierta y ofertar en venta directa / negociar / descartar.
    9. Checklist de due diligence pendiente: nota simple, visita, certificado de deuda de comunidad, consulta urbanística, edicto completo.
    10. Fuentes y aviso legal.

**Diseño visual: fuera de alcance en esta fase.**
- Se usa una plantilla HTML/CSS neutra y sobria.
- Las variables de marca (logo, colores, tipografías) están centralizadas en un único archivo, para sustituirlas en la fase de diseño.
- La estructura de contenido sí es definitiva.

### 11.3 Telegram
- Bot privado. Solo atiende a los chats autorizados.
- Por cada oportunidad, el bot envía un resumen de 5 líneas con el PDF completo para mí y estos botones:
  - **Aprobar:** genera el teaser listo para reenviar.
  - **Vigilar.**
  - **Descartar,** con motivo.
  - **Ver ficha.**
- Comandos: `/semana`, `/ficha <id>`, `/vigilancia`, `/cierres`, `/estado` (salud de las fuentes), `/parametros`.
- WhatsApp queda para una fase posterior.

---

## 12. Cumplimiento, privacidad y riesgos

- Scraping responsable según las reglas de §4.
- **RGPD:**
  - Minimizar los datos personales.
  - Los informes nunca llevan nombres de deudores ni de ocupantes.
  - Los datos personales de eventos cerrados se borran a los 12 meses.
  - El repositorio es privado.
- Los secretos (tokens de Telegram, API key) van en `.env` o en un gestor de secretos, nunca en el repositorio.
- **Aviso legal en cada informe:** análisis orientativo que no constituye asesoramiento. Los datos están sujetos a verificación (nota simple, visita, edicto).
- Nada se envía a terceros de forma automática.
- **Nunca** se puja de forma automática ni se registra nada automáticamente en plataformas.

---

## 13. Requisitos técnicos

- **Stack sugerido** (se puede cambiar justificándolo):
  - Python 3.12, Pydantic, httpx.
  - BeautifulSoup o selectolax para leer HTML; Playwright solo si es imprescindible.
  - SQLite; Jinja2 + WeasyPrint para los PDF.
  - python-telegram-bot y el SDK de Anthropic.
- **Estructura:** `fuentes/` (un conector por fuente, con una interfaz común), `extraccion/`, `valoracion/`, `scoring/`, `informes/`, `bot/`, `config/`, `data/`.
- **Tests:**
  - Fixtures con HTML y PDF reales guardados, para cada conector.
  - Tests unitarios del motor de valoración, con casos calculados a mano.
- **Idempotencia:** volver a ejecutar no duplica activos ni reenvía avisos.
- **Logs** de cada ejecución, y alerta si algo falla.
- **README** para alguien que no programa: instalar, configurar, ejecutar y cambiar parámetros.

---

## 14. Fases y criterios de aceptación

| Fase | Qué se entrega | Criterio de aceptación |
|---|---|---|
| **F0 Arquitectura** | Propuesta escrita: hosting, librerías, esquema de base de datos, estructura de carpetas y coste mensual estimado. Decisiones de §16 resueltas conmigo. | Mi aprobación. **No se programa nada antes.** |
| **F1 BOE Córdoba** | Conectores de la API del BOE y del Portal de Subastas, base de datos y deduplicación. | El listado de subastas de inmuebles activas en Córdoba coincide con una búsqueda manual en el portal: ninguna omisión en una muestra de 20. |
| **F2 Extracción** | Fichas completas y extracción con Claude de bienes, cargas y ocupación. | 10 fichas revisadas conmigo sin errores críticos; cada dato con su fuente y su confianza. |
| **F3 Valoración y scoring** | Motor de §7 y §8, con comparables. | 3 casos reales calculados a mano coinciden con el motor (±1 %), con una explicación legible de cada cifra. |
| **F4 Informes (plantilla provisional)** | Teaser, completo y resumen semanal generados con datos reales. | El test del teaser no detecta datos identificativos; los PDF se generan sin errores. |
| **F5 Telegram y programación** | Bot, botones, comandos y ejecución semanal. | Dos ejecuciones semanales seguidas sin intervención; botones y alertas de fallo funcionando. |
| **F6 Ampliación** | Sevilla, Málaga y Huelva; ActCon, Escrapalia, Procuradores y Registro Público Concursal; alerta de desiertas y venta directa; cola de revisión asistida con Claude con navegador. | Una semana completa con las 4 provincias y al menos 4 fuentes activas. |
| **F7 Mercado secundario** | Servicers, ocupados y nuda propiedad; portales solo con la API oficial o por revisión asistida. | A definir al llegar. |
| **Fase de diseño** (aparte) | Identidad premium de los dossieres y del resumen. | Se especifica en otro documento. |

Al terminar cada fase, Claude Code enseña un resultado real y comprueba los criterios antes de pasar a la siguiente.

---

## 15. Fuera de alcance por ahora

- Diseño visual final.
- Envío directo a inversores.
- WhatsApp.
- Portal web para inversores.
- Pujas o registros automáticos en plataformas (nunca).

---

## 16. Decisiones abiertas (preguntar antes de la F0)

1. Hosting: VPS (unos 5 €/mes) o GitHub Actions con webhook serverless.
2. Presupuesto mensual máximo para la API de Claude.
3. ¿Compran los inversores a través de una sociedad? Afecta al ITP y al IVA.
4. Validar los márgenes y costes por defecto de §6.
5. ¿Quién más recibe los avisos de Telegram, además de Jesús?
6. ¿Se integra el escenario actual de Make.com (RSS del BOE) o se sustituye?
7. Carpeta de intercambio con Claude con navegador: ¿Google Drive u otra opción?

---

## Anexo A — Prompt de arranque para Claude Code

```
Lee SPEC.md completo: es la especificación del proyecto y la fuente de verdad.

1. Hazme las preguntas de la sección 16 y cualquier otra duda que bloquee la Fase 0.
2. Después entrega la Fase 0: arquitectura propuesta, hosting recomendado con coste
   mensual estimado, esquema de base de datos y estructura de carpetas.
3. No escribas código hasta que yo apruebe la Fase 0.
4. Trabaja fase a fase (sección 14). Al terminar cada fase, enséñame un resultado real
   y comprueba sus criterios de aceptación antes de pasar a la siguiente.
5. Si algo de SPEC.md es técnicamente inviable o hay una forma mejor de hacerlo,
   dímelo y propón el cambio antes de implementarlo.

No soy programador: explícame cada decisión en lenguaje sencillo.
```

---

## Anexo B — Prompt para la tarea programada de Claude con navegador

**Dos usos:** (1) MVP inmediato sin código, para validar desde ya si hay oportunidades y si interesan al grupo; (2) más adelante, procesar la cola de revisión asistida (§3, componente C).

**Requisito:** la app de escritorio de Claude abierta y el ordenador encendido a la hora programada.

```
Cada lunes a las 8:00 (hora de Madrid):

1. Abre subastas.boe.es → Búsqueda avanzada. Busca inmuebles en subastas judiciales
   (concursales, de apremio y voluntarias) y de la Agencia Tributaria, en las provincias
   de Córdoba, Sevilla, Málaga y Huelva, con estado "celebrándose" o "próxima apertura".
2. Revisa también las subastas y ventas concursales de ActCon y de Escrapalia Inmuebles
   en esas provincias.
3. Solo lectura: no inicies sesión, no te registres, no pujes ni envíes formularios.
   Si una web pide captcha o login, sáltala y anótalo.
4. Descarta garajes y trasteros sueltos, participaciones inferiores al 50 % y subastas
   que cierren en menos de 5 días.
5. Para cada candidato anota: identificador, enlace, dirección, tipo, superficie, valor de
   subasta, tasación, puja mínima, depósito, fecha de cierre, cargas, ocupación y
   administrador concursal (si lo hay).
6. Estima el €/m² de mercado de la zona con fuentes públicas citadas y calcula el
   descuento. Lo que no conste, márcalo como "pendiente de verificar". No inventes datos.
7. Entrégame una tabla ordenada por descuento y una ficha breve de las 3 mejores
   (tesis, números, riesgos y siguiente paso).
8. Señala aparte las subastas concursales que hayan concluido sin pujas en las últimas
   semanas: son candidatas a venta directa con el administrador concursal.
```
