-- ============================================================
-- NEHNEMI
-- Migración 002: Valores predeterminados de solicitudes
--
-- Requiere:
--   001_contrato_final.sql
--
-- Objetivo:
--   Garantizar que las solicitudes tengan identificador,
--   estado y fechas predeterminadas.
--
-- No elimina ni modifica registros existentes.
-- ============================================================

BEGIN;

-- UUID generado por PostgreSQL cuando no se proporciona.
-- La función gen_random_uuid() está disponible en PostgreSQL 16.

ALTER TABLE solicitudes_infraestructura
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- Estado inicial de una solicitud.

ALTER TABLE solicitudes_infraestructura
    ALTER COLUMN estado SET DEFAULT 'REGISTRADA'::estado_solicitud;

-- Fecha de creación automática.

ALTER TABLE solicitudes_infraestructura
    ALTER COLUMN creado_en SET DEFAULT NOW();

-- Fecha inicial de actualización automática.

ALTER TABLE solicitudes_infraestructura
    ALTER COLUMN actualizado_en SET DEFAULT NOW();

COMMIT;