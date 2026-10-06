\set ON_ERROR_STOP on

-- Ejecutar desde PostgreSQL con un usuario capaz de crear BD/extensiones:
-- psql -U postgres -f database.sql

SELECT 'CREATE DATABASE nehnemi'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nehnemi')\gexec

\connect nehnemi

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN CREATE TYPE tipo_zona AS ENUM ('CDMX','ALCALDIA','AGEB'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE tipo_procedencia AS ENUM ('OFICIAL','NEHNEMI','SIMULADO','DERIVADO'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE tipo_propulsion AS ENUM ('ELECTRICO','HIBRIDO_ENCHUFABLE','HIBRIDO','COMBUSTION','OTRO','SIN_AUTOMOVIL'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE respuesta_consideracion AS ENUM ('SI','NO','NO_SE'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE tipo_barrera_declarada AS ENUM ('PRECIO','CARGA','AUTONOMIA','INFORMACION_DUDAS','CARACTERISTICAS_VEHICULO','NO_INTERESA','OTRA','NINGUNA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE estado_solicitud AS ENUM ('REGISTRADA','EN_REVISION','ATENDIDA','DESCARTADA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE dimension_indicador AS ENUM ('ADOPCION','INFRAESTRUCTURA','PARTICIPACION','ACCESIBILIDAD'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE nivel_indicador AS ENUM ('MUY_BAJA','BAJA','MEDIA','ALTA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE nivel_confianza AS ENUM ('BAJA','MEDIA','ALTA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE tipo_barrera_diagnosticada AS ENUM ('INFRAESTRUCTURA','PARTICIPACION','ACCESIBILIDAD_ECONOMICA','INFORMACION','EVIDENCIA_INSUFICIENTE','SIN_CUELLO_PRIORITARIO'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE accion_recomendada AS ENUM ('RECOPILAR_MAS_DATOS','EVALUAR_EXPANSION_CARGA','AUMENTAR_PARTICIPACION','EVALUAR_ACCESIBILIDAD_ECONOMICA','INTERVENCION_INFORMATIVA','MONITOREAR','INVESTIGAR'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE prioridad_recomendacion AS ENUM ('BAJA','MEDIA','ALTA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS zonas (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clave varchar(32) NOT NULL UNIQUE,
    tipo tipo_zona NOT NULL,
    nombre varchar(160) NOT NULL,
    zona_padre_id uuid REFERENCES zonas(id),
    geometria geometry(MultiPolygon,4326),
    activa boolean NOT NULL DEFAULT true,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_zonas_geometria ON zonas USING GIST (geometria);
CREATE INDEX IF NOT EXISTS idx_zonas_tipo ON zonas(tipo);

CREATE TABLE IF NOT EXISTS fuentes_datos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clave varchar(80) NOT NULL UNIQUE,
    nombre varchar(200) NOT NULL,
    tipo_procedencia tipo_procedencia NOT NULL,
    referencia text,
    fecha_referencia date,
    fecha_descarga date,
    notas text
);

CREATE TABLE IF NOT EXISTS observaciones (
    id bigserial PRIMARY KEY,
    zona_id uuid NOT NULL REFERENCES zonas(id) ON DELETE CASCADE,
    clave_metrica varchar(100) NOT NULL,
    valor_numerico numeric,
    valor_texto text,
    unidad varchar(60),
    periodo varchar(30) NOT NULL,
    fuente_id uuid NOT NULL REFERENCES fuentes_datos(id),
    creado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_observacion UNIQUE (zona_id, clave_metrica, periodo, fuente_id)
);
CREATE INDEX IF NOT EXISTS idx_observaciones_zona_metrica ON observaciones(zona_id, clave_metrica);

CREATE TABLE IF NOT EXISTS estaciones_carga (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    identificador_fuente varchar(100),
    nombre varchar(250) NOT NULL,
    direccion text,
    ubicacion geometry(Point,4326) NOT NULL,
    zona_id uuid REFERENCES zonas(id),
    fuente_id uuid NOT NULL REFERENCES fuentes_datos(id),
    estado_demostracion varchar(50),
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_estacion_fuente UNIQUE (fuente_id, identificador_fuente)
);
CREATE INDEX IF NOT EXISTS idx_estaciones_ubicacion ON estaciones_carga USING GIST (ubicacion);
CREATE INDEX IF NOT EXISTS idx_estaciones_zona ON estaciones_carga(zona_id);

CREATE TABLE IF NOT EXISTS conectores_carga (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    estacion_id uuid NOT NULL REFERENCES estaciones_carga(id) ON DELETE CASCADE,
    numero_grupo smallint NOT NULL,
    cantidad integer NOT NULL CHECK (cantidad > 0),
    tipo_conector varchar(120),
    potencia_kw numeric,
    estado_operativo varchar(50),
    procedencia_estado tipo_procedencia,
    CONSTRAINT uq_conector_grupo UNIQUE(estacion_id, numero_grupo)
);

CREATE TABLE IF NOT EXISTS perfiles_ciudadanos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    zona_id uuid REFERENCES zonas(id),
    tiene_automovil boolean,
    propulsion tipo_propulsion,
    consideraria_ev respuesta_consideracion,
    barrera_principal tipo_barrera_declarada,
    consentimiento_agregado boolean NOT NULL DEFAULT false,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS solicitudes_infraestructura (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    perfil_ciudadano_id uuid REFERENCES perfiles_ciudadanos(id) ON DELETE SET NULL,
    zona_id uuid REFERENCES zonas(id),
    ubicacion geometry(Point,4326),
    motivo varchar(250),
    comentario text,
    estado estado_solicitud NOT NULL DEFAULT 'REGISTRADA',
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_solicitudes_ubicacion ON solicitudes_infraestructura USING GIST(ubicacion);

CREATE TABLE IF NOT EXISTS interacciones (
    id bigserial PRIMARY KEY,
    perfil_ciudadano_id uuid REFERENCES perfiles_ciudadanos(id) ON DELETE SET NULL,
    zona_id uuid REFERENCES zonas(id),
    tipo varchar(80) NOT NULL,
    metadatos jsonb NOT NULL DEFAULT '{}'::jsonb,
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluaciones_indicadores (
    id bigserial PRIMARY KEY,
    zona_id uuid NOT NULL REFERENCES zonas(id) ON DELETE CASCADE,
    dimension dimension_indicador NOT NULL,
    puntuacion numeric(6,2) NOT NULL CHECK (puntuacion BETWEEN 0 AND 100),
    nivel nivel_indicador NOT NULL,
    confianza nivel_confianza NOT NULL,
    tamano_muestra integer,
    version_formula varchar(80) NOT NULL,
    componentes jsonb NOT NULL DEFAULT '{}'::jsonb,
    explicacion text,
    calculado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_evaluaciones_zona_dimension ON evaluaciones_indicadores(zona_id, dimension, calculado_en DESC);

CREATE TABLE IF NOT EXISTS recomendaciones (
    id bigserial PRIMARY KEY,
    zona_id uuid NOT NULL REFERENCES zonas(id) ON DELETE CASCADE,
    barrera_principal tipo_barrera_diagnosticada NOT NULL,
    accion accion_recomendada NOT NULL,
    prioridad prioridad_recomendacion NOT NULL,
    confianza nivel_confianza NOT NULL,
    razones jsonb NOT NULL DEFAULT '[]'::jsonb,
    evidencia jsonb NOT NULL DEFAULT '[]'::jsonb,
    version_reglas varchar(80) NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW indicadores_actuales AS
SELECT DISTINCT ON (zona_id, dimension)
    id, zona_id, dimension, puntuacion, nivel, confianza,
    tamano_muestra, version_formula, componentes, explicacion, calculado_en
FROM evaluaciones_indicadores
ORDER BY zona_id, dimension, calculado_en DESC, id DESC;

CREATE OR REPLACE VIEW resumen_infraestructura_ageb AS
SELECT z.id AS zona_id, z.clave, z.nombre,
       COUNT(DISTINCT e.id) AS estaciones,
       COALESCE(SUM(c.cantidad),0) AS conectores,
       COALESCE(SUM(c.cantidad * COALESCE(c.potencia_kw,0)),0) AS potencia_total_kw
FROM zonas z
LEFT JOIN estaciones_carga e ON e.zona_id=z.id
LEFT JOIN conectores_carga c ON c.estacion_id=e.id
WHERE z.tipo='AGEB'
GROUP BY z.id, z.clave, z.nombre;

\echo 'Esquema Nehnemi creado correctamente.'
