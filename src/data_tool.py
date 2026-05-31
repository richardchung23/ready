import os
import psycopg2
from psycopg2 import pool
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

_db_pool = None

# We use lazy initialization to return a global database connection pool
def get_db_pool():
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                user=os.getenv("DB_USER", "ready_user"),
                password=os.getenv("DB_PASSWORD", "ready_password"),
                dbname=os.getenv("DB_NAME", "broadband_risk"),
            )
        except psycopg2.Error as e:
            raise Exception(f"Error initializing database pool: {e}")

    return _db_pool


# Insert new location into database with P (pending) status. We take advantage 
# of ST_MakePoint and ST_SetSRID to handle the PostGIS geometry insertion.
#
# @returns: True if new row was inserted, False if it already exists or failed
def insert_initial_loc(location_id: str, lat: float, lon: float, geoid_cb: Optional[str]=None) -> bool:
    # Query we will use to put a location into database with status pending.
    # Important thing to note is the ON CONFLICT line, which prevents duplication,
    # making it safe to run repeatedly.
    query = """
        INSERT INTO location_evaluation (location_id, geom, geoid_cb, status)
        VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, 'P')
        ON CONFLICT (location_id) do nothing;
    """

    db_pool = get_db_pool()
    conn = None

    try:
        conn = db_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query, (location_id, lon, lat, geoid_cb))
            inserted = cursor.rowcount > 0

        conn.commit()
        return inserted
    except psycopg2.Error as e:
        if conn is not None:
            conn.rollback()

        print(f"Database error for {location_id}: {e}")
        return False
    
    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if conn is not None:
            db_pool.putconn(conn)


def fetch_location_data(location_id: str) -> Dict[str, Any]:
    query = """
        SELECT tcc_percentage, elevation, obstruction_height
        FROM location_evaluation
        WHERE location_id = %s;
    """

    db_pool = get_db_pool()
    conn = None
    try:
        conn = db_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query, (location_id,))
            row = cursor.fetchone()

            if not row:
                return {"error": f"Location {location_id} not found in database"}
            
            return {
                "location_id": location_id,
                "tcc_percentage": row[0],
                "elevation": row[1],
                "obstruction_height": row[2]
            }
        
    except psycopg2.Error as e:
        if conn is not None:
            conn.rollback()
        return {"error": f"Database failed to read {location_id}: {str(e)}"}
    
    finally:
        if conn is not None:
            db_pool.putconn(conn)
    