import os
import psycopg2
from psycopg2 import pool
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_db_pool = None

# We use lazy initialization to return a global database connection pool
def get_db_pool():
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = psycopg2.pool.SimpleConnectionsPool(
                1, 10,
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                user=os.getenv("DB_USER", "ready_user"),
                password=os.getenv("DB_PASSWORD", "ready_password"),
                name=os.getenv("DB_NAME", "broadband_risk"),
            )
        except psycopg2.Error as e:
            raise Exception(f"Error initializing database pool: {e}")

    return _db_pool


# Insert new location into database with P (pending) status. We take advantage 
# of ST_MakePoint and ST_SetSRID to handle the PostGIS geometry insertion.
#
# @returns: True if new row was inserted, False if it already exists or failed
def insert_initial_loc(location_id: str, lat: float, lon: float) -> bool:
    # Query we will use to put a location into database with status pending.
    # Important thing to note is the ON CONFLICT line, which prevents duplication,
    # making it safe to run repeatedly.
    query = """
        INSERT INTO location_evaluation (location_id, geom, geoid_cb, status)
        VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), 'P)
        ON CONFLICT (location_id) do nothing;
    """

    db_pool = get_db_pool()
    conn = None

    try:
        conn = db_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query, (location_id, lon, lat))
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

    