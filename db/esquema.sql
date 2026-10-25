-- Esquema de la base de datos del radar (SPEC.md §5, docs/FASE0.md §5).
-- Una tabla = una "hoja" de datos. Todas las fechas en formato ISO (AAAA-MM-DD).
-- Este archivo se puede ejecutar varias veces sin romper nada.

PRAGMA foreign_keys = ON;

-- Cada anuncio publicado en el BOE (una subasta puede tener varios).
CREATE TABLE IF NOT EXISTS anuncio_boe (
    boe_id            TEXT PRIMARY KEY,          -- BOE-B-2026-33903
    subasta_id        INTEGER REFERENCES subasta(id),
    fecha_publicacion TEXT NOT NULL,
    seccion           TEXT NOT NULL,             -- 4, 5B...
    titulo            TEXT NOT NULL,
    texto             TEXT,                      -- texto íntegro del anuncio
    url_html          TEXT,
    url_pdf           TEXT,
    documento_id      INTEGER REFERENCES documento(id)
);

-- Una subasta o procedimiento de venta (identificador SUB-… del portal,
-- o el del BOE si la subasta no está en el portal).
CREATE TABLE IF NOT EXISTS subasta (
    id                    INTEGER PRIMARY KEY,
    id_externo            TEXT NOT NULL UNIQUE,  -- SUB-JA-2026-267476
    fuente                TEXT NOT NULL,         -- boe_sumario, portal_subastas...
    tipo                  TEXT,                  -- JA, JC, JV, AT, SS, NO, PE (patrimonio del Estado)...
    tipo_texto            TEXT,                  -- "judicial en vía de apremio"
    autoridad             TEXT,                  -- "Sección Civil TI Córdoba. Plz.n 9"
    localidad_autoridad   TEXT,
    num_expediente        TEXT,
    provincia             INTEGER,               -- código INE; NULL si no se conoce aún
    provincia_origen      TEXT NOT NULL,         -- partido_judicial | titulo_anuncio | ficha | desconocida
    ambito                TEXT,                  -- para AEAT: "Andalucía (U.R. 41)"
    url_portal            TEXT,
    estado                TEXT NOT NULL DEFAULT 'anunciada',
    fecha_publicacion_boe TEXT,
    fecha_deteccion       TEXT NOT NULL,
    ultima_comprobacion   TEXT NOT NULL
);

-- Un inmueble físico.
CREATE TABLE IF NOT EXISTS activo (
    id                    INTEGER PRIMARY KEY,
    tipo                  TEXT,                  -- vivienda, edificio, local, suelo, garaje...
    provincia             INTEGER,
    municipio             TEXT,
    direccion             TEXT,
    direccion_normalizada TEXT,
    cp                    TEXT,
    ref_catastral         TEXT,
    finca_registral       TEXT,
    registro              TEXT,
    sup_catastro_m2       REAL,
    sup_nota_simple_m2    REAL,
    sup_util_m2           REAL,
    sup_construida_m2     REAL,
    anio_construccion     INTEGER,
    estado_conservacion   TEXT,
    lat                   REAL,
    lon                   REAL,
    fotos                 TEXT,                  -- JSON con las URL
    creado                TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_activo_catastral ON activo(ref_catastral) WHERE ref_catastral IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_activo_finca ON activo(finca_registral, registro);
CREATE INDEX IF NOT EXISTS ix_activo_direccion ON activo(direccion_normalizada);

-- Una vez que el inmueble sale a la venta: un lote de una subasta, una venta directa...
CREATE TABLE IF NOT EXISTS evento_venta (
    id                   INTEGER PRIMARY KEY,
    subasta_id           INTEGER REFERENCES subasta(id),
    fuente               TEXT NOT NULL,
    id_externo           TEXT NOT NULL,
    lote                 INTEGER,                -- NULL = lote único
    tipo                 TEXT,
    autoridad            TEXT,
    admin_concursal      TEXT,                   -- nombre y contacto profesional
    valor_subasta        REAL,
    tasacion             REAL,
    puja_minima          REAL,
    deposito             REAL,
    comision_plataforma  REAL,
    participacion        REAL,                   -- 1.0 = pleno dominio completo
    fecha_inicio         TEXT,
    fecha_fin            TEXT,
    estado               TEXT,
    puja_maxima          REAL,
    url                  TEXT,
    fecha_deteccion      TEXT NOT NULL,
    ultima_comprobacion  TEXT NOT NULL,
    UNIQUE (fuente, id_externo, lote)
);

-- Enlace lote ↔ bienes (un lote puede incluir vivienda + garaje + trastero).
CREATE TABLE IF NOT EXISTS evento_activo (
    evento_id  INTEGER NOT NULL REFERENCES evento_venta(id),
    activo_id  INTEGER NOT NULL REFERENCES activo(id),
    PRIMARY KEY (evento_id, activo_id)
);

-- Cada dato jurídico por separado, con su fuente, confianza y cita literal.
CREATE TABLE IF NOT EXISTS dato_verificable (
    id         INTEGER PRIMARY KEY,
    activo_id  INTEGER REFERENCES activo(id),
    evento_id  INTEGER REFERENCES evento_venta(id),
    campo      TEXT NOT NULL,                    -- ocupacion, cargas_anteriores, posesion, deuda_comunidad...
    valor      TEXT,
    fuente     TEXT NOT NULL,
    confianza  TEXT NOT NULL CHECK (confianza IN ('verificado','extraido','estimado','desconocido')),
    cita       TEXT,
    fecha      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referencia_mercado (
    id              INTEGER PRIMARY KEY,
    fuente          TEXT NOT NULL,
    ambito_tipo     TEXT NOT NULL,               -- municipio | cp | barrio
    ambito          TEXT NOT NULL,
    tipologia       TEXT,
    tipo            TEXT NOT NULL CHECK (tipo IN ('escriturado','oferta','alquiler')),
    periodo         TEXT,
    eur_m2          REAL NOT NULL,
    n_operaciones   INTEGER,
    fecha_descarga  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coste_reforma (
    id      INTEGER PRIMARY KEY,
    ciudad  TEXT NOT NULL,
    zona    TEXT,
    nivel   TEXT NOT NULL CHECK (nivel IN ('ligera','media','integral')),
    eur_m2  REAL NOT NULL,
    fuente  TEXT NOT NULL,
    fecha   TEXT NOT NULL
);

-- Cada versión de config.yaml usada en un cálculo.
CREATE TABLE IF NOT EXISTS parametros (
    version    TEXT PRIMARY KEY,                 -- huella del contenido
    contenido  TEXT NOT NULL,
    fecha      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS valoracion (
    id                  INTEGER PRIMARY KEY,
    evento_id           INTEGER NOT NULL REFERENCES evento_venta(id),
    parametros_version  TEXT NOT NULL REFERENCES parametros(version),
    v_conservador       REAL,
    v_base              REAL,
    v_optimista         REAL,
    p_max               REAL,
    inversion_total     REAL,
    margen              REAL,
    rent_bruta_alquiler REAL,
    tir                 REAL,
    sensibilidad        TEXT,                    -- JSON
    score               REAL,
    semaforos           TEXT,                    -- JSON
    explicacion         TEXT,                    -- JSON: cada cifra con su fórmula y origen
    confianza           TEXT,
    fecha               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oportunidad (
    id              INTEGER PRIMARY KEY,
    activo_id       INTEGER REFERENCES activo(id),
    evento_id       INTEGER REFERENCES evento_venta(id),
    estado          TEXT NOT NULL DEFAULT 'detectada',
    motivo_descarte TEXT,
    creada          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historial_estado (
    id              INTEGER PRIMARY KEY,
    oportunidad_id  INTEGER NOT NULL REFERENCES oportunidad(id),
    de              TEXT,
    a               TEXT NOT NULL,
    fecha           TEXT NOT NULL,
    motivo          TEXT,
    quien           TEXT NOT NULL                -- sistema | jesus
);

CREATE TABLE IF NOT EXISTS envio (
    id              INTEGER PRIMARY KEY,
    oportunidad_id  INTEGER NOT NULL REFERENCES oportunidad(id),
    version         TEXT NOT NULL CHECK (version IN ('teaser','completo')),
    destinatario    TEXT NOT NULL,
    fecha           TEXT NOT NULL,
    archivo         TEXT
);

-- Cada HTML/PDF/JSON original descargado, guardado como evidencia.
CREATE TABLE IF NOT EXISTS documento (
    id         INTEGER PRIMARY KEY,
    url        TEXT NOT NULL UNIQUE,
    tipo       TEXT,                             -- content-type
    hash       TEXT NOT NULL,                    -- sha256 del contenido
    ruta       TEXT NOT NULL,                    -- dónde está guardado (comprimido)
    fecha      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ejecucion (
    id        INTEGER PRIMARY KEY,
    tipo      TEXT NOT NULL,                     -- descubrir | semanal | diaria | boton
    inicio    TEXT NOT NULL,
    fin       TEXT,
    resultado TEXT,                              -- ok | aviso | error
    resumen   TEXT                               -- JSON
);

CREATE TABLE IF NOT EXISTS salud_fuente (
    id             INTEGER PRIMARY KEY,
    ejecucion_id   INTEGER NOT NULL REFERENCES ejecucion(id),
    fuente         TEXT NOT NULL,
    n_resultados   INTEGER NOT NULL DEFAULT 0,
    n_errores      INTEGER NOT NULL DEFAULT 0,
    bloqueos       TEXT,                         -- captcha, login, robots...
    detalle        TEXT
);

-- Garantiza que un aviso de Telegram no se envía dos veces.
CREATE TABLE IF NOT EXISTS alerta_enviada (
    clave  TEXT PRIMARY KEY,
    fecha  TEXT NOT NULL
);
