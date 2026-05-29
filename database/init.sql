CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE location_evaluation (
    location_id VARCHAR PRIMARY KEY,
    geom        GEOMETRY(Point, 4326) NOT NULL,

    tcc_percentage      SMALLINT,
    elevation           REAL,       -- ground elevation
    obstruction_height  REAL,       -- derived obstruction height

    obstruction_angle  REAL,
    risk_tier          CHAR(1),

    -- Pipeline status
    -- status can be P (pending), D (done), A (anomaly), E (error)
    status      CHAR(1) NOT NULL DEFAULT 'P',
    updated_at  TIMESTAMPTZ DEFAULT now(),
);

CREATE INDEX idx_geom ON location_evaluation USING GIST (geom);
CREATE INDEX idx_status ON location_evaluation (status);