# Database Infrastructure and Schema Initialization

import psycopg2
from data_tool import get_db_pool

def setup_database():
    print("Initializing database...")
    # Define core table, with an explicit WGS84 declaration
    query = """
        CREATE TABLE IF NOT EXISTS location_evaluation (
            location_id VARCHAR PRIMARY KEY,
            geom        GEOMETRY(Point, 4326) NOT NULL,
            geoid_cb    VARCHAR(20),
            tcc_percentage      SMALLINT,
            elevation           REAL,
            obstruction_height  REAL,
            obstruction_angle  REAL,
            risk_tier          CHAR(1),
            status      CHAR(1) NOT NULL DEFAULT 'P',
            updated_at  TIMESTAMPTZ DEFAULT now()
        );
    """
    db_pool = get_db_pool()
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cursor:
            # Enable GIS
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_raster;")

            # Build primary table
            cursor.execute(query)

            # Build spatial and operational indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_geom ON location_evaluation USING GIST (geom);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON location_evaluation (status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_geoid ON location_evaluation (geoid_cb);")
        conn.commit() # Save schema changes
        print("Schema created successfully.")

    except Exception as e:
        if conn is not None:
            conn.rollback()
        print(f"Failed to create schema: {e}")

    finally:
        # Guarantee connection is added back to pool
        if conn is not None:
            db_pool.putconn(conn)

if __name__ == "__main__":
    setup_database()