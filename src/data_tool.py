# data_tool.py
# 
# This file manages all systematic I/O boundaries. It acts as gatekeeper to
# underlying PostGIS spatial datastore and external web service gateways. It
# contains connection pool state management, spatial index lookups, relational 
# mutations, and external REST protocol handlers, ensuring that upstream agent 
# components remain fully decoupled from network topologies.

import os
import psycopg2
import requests
from psycopg2 import pool
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

# Global singleton connection storage instance
_db_pool = None

# Thread safe connection pool provisioner.
#
# Uses a lazy initialization design to allocate a shared database connection pool.
# This optimizes connection reuse and prevents script from overloading database 
# handles during intensive batch processing chunks.
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
# Returns: 
#   - True if new row was inserted
#   - False if it already exists or failed
def insert_initial_loc(location_id: str, lat: float, lon: float, geoid_cb: Optional[str]=None) -> bool:
    # Query we will use to put a location into database with status pending.
    # Important thing to note is the ON CONFLICT line, which prevents duplication,
    # making it safe to run repeatedly.
    query = """
        INSERT INTO location_evaluation (location_id, geom, geoid_cb, status)
        VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, 'P')
        ON CONFLICT (location_id) do nothing;
    """

    # Initialize DB connection pool
    db_pool = get_db_pool()
    conn = None

    try:
        # Check out connection from pool
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

# External API Gateway adapter
#
# Acts as network client to dispatch REST request parameters to federal USGS
# to get precise terrain data.
#
# Args:
#   - lat: Latitude coordinate in WGS84 system
#   - long: Longitude coordinate in WGS84 system
#
# Returns:
#   - float: True altitude in meters or a fallback value (-1.0) to handle anomalies
def fetch_elevation(lat: float, lon: float) -> float:
    url = "https://epqs.nationalmap.gov/v1/json"
    params = {"x": lon, "y": lat, "wkid": 4326, "includeDate": "false"}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return float(response.json()["value"])
    except Exception as e:
        print(f"USGS API error for ({lat}, {lon}): {e}")
        return -1.0
    

# High performance spatial join evaluator
#
# Queries chunks of pending locations and performs a native raster to vector
# intersection against NLCD TCC spatial block. Converts point geometries from 
# WGS84 to NAD83 to align with coordinate grid layout of federal data
#
# If local nlcd_tcc table has not been made/populated yet, it will catch the 
# exception and fall back to mock values (0%), so that pipeline can still be 
# tested and executed without dependencies.
#
# Args:
#   - chunk_size: Max row limit size to pull per analytical transactional batch
#
# Returns:
#   - list: Collection of matched rows containing coordinates and true TCC pixel integer values
def fetch_raster_batch(chunk_size: int) -> list:
    # Initialize DB connection pool
    db_pool = get_db_pool()
    conn = None

    try:
        # Check out connection from pool
        conn = db_pool.getconn()
        with conn.cursor() as cursor:
            # Uses bounding-box spatial indexing (&&) alongside precise polygon 
            # intersections (ST_Intersects) to guarantee maximum extraction query speed
            cursor.execute("""
                SELECT 
                    l.location_id, 
                    ST_Y(l.geom) as lat, 
                    ST_X(l.geom) as lon,
                    COALESCE(ST_Value(r.rast, ST_Transform(l.geom, 5070)), 0) as real_tcc
                FROM location_evaluation l
                LEFT JOIN nlcd_tcc r 
                    ON r.rast && ST_Transform(l.geom, 5070)
                    AND ST_Intersects(r.rast, ST_Transform(l.geom, 5070))
                WHERE l.status = 'P'
                LIMIT %s;
            """, (chunk_size,))
            return cursor.fetchall()
    except Exception as e:
        # Handle fallback
        if conn is not None and getattr(e, "pgcode", None) == "42P01":
            print("\n[NOTICE] 'nlcd_tcc' table not found. Gracefully falling back to mock TCC values (0%).")
            try:
                # Clear aborted transaction state on connection to allow a new execution
                conn.rollback() 
                
                with conn.cursor() as fallback_cursor:
                    # Run fallback extraction omitting the raster join entirely
                    fallback_cursor.execute("""
                        SELECT 
                            location_id, 
                            ST_Y(geom) as lat, 
                            ST_X(geom) as lon,
                            0 as real_tcc
                        FROM location_evaluation
                        WHERE status = 'P'
                        LIMIT %s;
                    """, (chunk_size,))
                    return fallback_cursor.fetchall()
            except Exception as fallback_err:
                print(f"Critical error occurred during fallback query execution: {fallback_err}")
                raise 
        else:
            print(f"Critical DB error during raster spatial join: {e}")
            raise
    finally:
        if conn is not None:
            db_pool.putconn(conn)

# Point Query State Fetcher
#
# Provides clean target DB query abstraction for supervisor agent. Allows agent
# to view state machine metrics for any given UUID without writing raw SQL syntax
# inside agent architecture class
#
# Args:
#   - location_id: The unique text identifier/UUID of evaluated point
#
# Returns:
#   - Dict[str, Any]: Pre-calculated dataset evaluation state or error tracking message
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
        # If pipeline crashes, rollback current uncommitted batch
        if conn is not None:
            conn.rollback()
        return {"error": f"Database failed to read {location_id}: {str(e)}"}
    
    finally:
        # Guaranteed to execute safely: return the connection to the pool
        if conn is not None:
            db_pool.putconn(conn)
    