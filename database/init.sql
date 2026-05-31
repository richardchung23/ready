CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

CREATE TABLE location_evaluation (
    location_id VARCHAR PRIMARY KEY,
    geom        GEOMETRY(Point, 4326) NOT NULL,
    geoid_cb    VARCHAR(20),

    tcc_percentage      SMALLINT,
    elevation           REAL,       -- ground elevation
    obstruction_height  REAL,       -- derived obstruction height

    obstruction_angle  REAL,
    risk_tier          CHAR(1),

    -- Pipeline status
    -- status can be P (pending), D (done), A (anomaly), E (error)
    status      CHAR(1) NOT NULL DEFAULT 'P',
    updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_geom ON location_evaluation USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_status ON location_evaluation (status);
CREATE INDEX IF NOT EXISTS idx_geoid ON location_evaluation (geoid_cb);