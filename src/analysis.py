import os
import time
import requests
from data_tool import get_db_pool
from psycopg2.extras import execute_values

USE_LIVE_API = os.getenv("USE_LIVE_API", "false").lower() == "true"

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

def process_batch_analysis(chunk_size: int = 25000, max_batches: int = 1000):
    if USE_LIVE_API and chunk_size > 100:
        chunk_size = 100
        print("Live API mode: chunk size is capped to 100 for rate limits.")

    print("Starting batch processing...")
    db_pool = get_db_pool()
    conn = None
    MIN_ELEVATION_ANGLE_DEG = 20.0

    query = """
        UPDATE location_evaluation AS l
        SET
            tcc_percentage = v.tcc_percentage,
            elevation = v.elevation,
            obstruction_height = v.obstruction_height,
            obstruction_angle = v.obstruction_angle,
            risk_tier = v.risk_tier,
            status = v.final_status,
            updated_at = now()
        FROM (VALUES %s) AS v(
            location_id, tcc_percentage, elevation, obstruction_height, obstruction_angle, risk_tier, final_status
        )
        WHERE l.location_id = v.location_id;
    """

    try:
        conn = db_pool.getconn()
        batches_processed = 0
        while batches_processed < max_batches:
            batches_processed += 1
            start = time.time()

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        l.location_id, 
                        ST_Y(l.geom) as lat, 
                        ST_X(l.geom) as lon,
                        COALESCE(ST_Value(r.rast, l.geom), 0) as real_tcc
                    FROM location_evaluation l
                    LEFT JOIN nlcd_tcc r 
                      ON ST_Intersects(r.rast, l.geom)
                    WHERE l.status = 'P'
                    LIMIT %s;
                """, (chunk_size,))

                records = cursor.fetchall()

            if not records:
                print("All pending records were evaluated.")
                break

            updates = []
            for loc_id, lat, lon, tcc in records:
                tcc_percentage = int(tcc)

                if elevation < 0 or tcc_percentage < 0 or tcc_percentage > 100:
                    updates.append((loc_id, None, None, None, None, None, 'A'))
                    continue
                tcc_percentage = max(0, min(tcc, 100))
                if USE_LIVE_API:
                    elevation = fetch_elevation(lat, lon)
                    time.sleep(0.1)
                else:
                    elevation = 200.0

                obstruction_angle = float((tcc_percentage * 0.4) % 40)
                obstruction_height = elevation + (tcc_percentage * 0.3)

                if obstruction_angle < MIN_ELEVATION_ANGLE_DEG:
                    tier = 'A'
                elif obstruction_angle <= 35.0:
                    tier = 'B'
                else:
                    tier = 'C'

                updates.append((
                    loc_id, tcc_percentage, elevation, obstruction_height, obstruction_angle, tier, 'D'
                ))

            with conn.cursor() as cursor:
                execute_values(
                    cursor, query, updates, template="(%s, %s, %s, %s, %s, %s, %s)"
                )
            conn.commit()

            elapsed = time.time() - start
            print(f"Processed batch {batches_processed} ({len(records)} records) in {elapsed: .2f} seconds.")

        if batches_processed >= max_batches:
            print("Max batch limit exceeded")

    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise Exception("Execution failed during analytical batching") from e
    
    finally:
        if conn is not None:
            db_pool.putconn(conn)

if __name__ == "__main__":
    process_batch_analysis(max_batches=10)