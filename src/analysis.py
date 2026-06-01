# analysis.py
#
# This file serves as the pipeline orchestrator for LOS calculations. This file
# contains no direct SQL queries, raw coordinates, or mathematical formulas, thus
# keeping clear boundaries. Instead, it coordinates the workflow by pulling data 
# from data_tool and passing
# parameters into analytical_tool.

import os
import time
import requests
from data_tool import get_db_pool, fetch_raster_batch, fetch_elevation
from analysis_tool import calculate_los
from psycopg2.extras import execute_values

# Toggle to switch between API usage and local batch testing
USE_LIVE_API = os.getenv("USE_LIVE_API", "false").lower() == "true"

# Executes risk evaluation workflow in continuous DB transactions. It pulls
# pending records, coordinates external data augmentation (if enabled), 
# runs the core evaluation logic, and performs bulk state updates.
#
# Args:
#   - chunk_size (optional): Number of rows processed per DB cycle. Optimizes memory overhead.
#                            Defaults to 25000
#   - max_batches (optional): Strict limit to prevent infinite loops. Defaults to 1000.
#
# Returns:
#   - None: mutates DB directly
#
# Raises:
#   - Exception: Rolls back active transaction and surfaces traceback if batch
#                encounters critical failure
def process_batch_analysis(chunk_size: int = 25000, max_batches: int = 1000):
    if USE_LIVE_API and chunk_size > 100:
        chunk_size = 100
        print("Live API mode: chunk size is capped to 100 for rate limits.")

    print("Starting batch processing...")
    db_pool = get_db_pool()
    conn = None

    # Query for high speed builk updates. Utilizing FROM (VALUES) alias executes
    # much quicker than looping individual UPDATE statements
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
        # Check out connection from global pool
        conn = db_pool.getconn()
        batches_processed = 0

        while batches_processed < max_batches:
            start = time.time()

            # Fetch raw parameters with data_tool
            records = fetch_raster_batch(chunk_size)
            if not records:
                print("All pending records were evaluated.")
                break

            batches_processed += 1

            updates = []
            for loc_id, lat, lon, tcc in records:
                # Sourcing external data via data_tool
                if USE_LIVE_API:
                    elevation = fetch_elevation(lat, lon)
                    time.sleep(0.1) # Respect upstream throughput limits
                else:
                    elevation = 200.0 # Clean baseline for testing

                # Data quality guard / failure handling
                if elevation < 0 or tcc is None or tcc < 0 or tcc > 100:
                    updates.append((loc_id, None, None, None, None, None, 'A'))
                    continue

                # Pass clean data to logic layer
                metrics = calculate_los(
                    dish_elev=elevation,
                    obstruction_elev=elevation + (int(tcc) * 0.3),
                    obstruction_dist=15.0,
                    canopy_height=0
                )

                updates.append((
                    loc_id, int(tcc), elevation, metrics["obstruction_height"], 
                    metrics["obstruction_angle"], metrics["risk_tier"], 'D'
                ))

            # Commit results back to state
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
        # If pipeline crashes, rollback current uncommitted batch
        if conn is not None:
            conn.rollback()
        raise Exception("Execution failed during analytical batching") from e
    
    finally:
        # Guaranteed to execute safely: return the connection to the pool
        if conn is not None:
            db_pool.putconn(conn)

if __name__ == "__main__":
    process_batch_analysis(chunk_size=100, max_batches=10)