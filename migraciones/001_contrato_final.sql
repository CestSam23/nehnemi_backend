BEGIN;

-- ============================================================
-- NEHNEMI
-- Migración 001: Contrato final v1.0
-- ============================================================


-- ============================================================
-- 1. TIPOS
-- ============================================================

CREATE TYPE rol_gobierno AS ENUM (
    'ANALISTA',
    'ADMINISTRADOR'
);

CREATE TYPE motivo_solicitud AS ENUM (
    'VIVO_CERCA',
    'TRABAJO_CERCA',
    'TRANSITO_FRECUENTE',
    'TENGO_EV',
    'CONSIDERARIA_EV_CON_CARGA',
    'OTRO'
);


-- ============================================================
-- 2. USUARIOS DE GOBIERNO
-- ============================================================

CREATE TABLE usuarios_gobierno (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre varchar(160) NOT NULL,
    correo varchar(200) NOT NULL UNIQUE,
    contrasena_hash text NOT NULL,
    rol rol_gobierno NOT NULL DEFAULT 'ANALISTA',
    activo boolean NOT NULL DEFAULT true,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);


-- ============================================================
-- 3. CONTENIDOS INFORMATIVOS
-- ============================================================

CREATE TABLE contenidos_informativos (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug varchar(120) NOT NULL UNIQUE,
    titulo varchar(180) NOT NULL,
    resumen text NOT NULL,
    contenido text NOT NULL,
    categoria varchar(80) NOT NULL,
    orden integer NOT NULL DEFAULT 0,
    publicado boolean NOT NULL DEFAULT false,
    creado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);


-- ============================================================
-- 4. SOLICITUDES DE INFRAESTRUCTURA
-- ============================================================

ALTER TABLE solicitudes_infraestructura
    ALTER COLUMN motivo TYPE motivo_solicitud
    USING motivo::motivo_solicitud;

ALTER TABLE solicitudes_infraestructura
    ALTER COLUMN motivo SET NOT NULL,
    ALTER COLUMN ubicacion SET NOT NULL;


COMMIT;
