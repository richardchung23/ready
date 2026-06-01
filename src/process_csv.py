# process_csv.py
#
# This file handles bulk ingestion of location data from a CSV file into the 
# PostGIS database. This is the first stage of the pipeline, utilizing
# psycopg2.extras.execute_values to optimize round trips with batch insertions.
# It also converts raw latitude and longitude into native PostGIS Point objects.

import os
import csv
import psycopg2
from psycopg2 import extras
from data_tool import get_db_pool

# Reads CSV file with location data and does bulk insert into DB in batches.
# Args:
#   - csv_filepath: Path to CSV file
#   - batch_size: Number of rows to insert per SQL transaction. 
#                 Optimizes memory/ network I/O. Defaults to 10000.
#   - max_rows: Strict limit on total # of rows to process (for testing).
#
# Returns:
#   - None. It mutates DB directly
#
# Raises:
#   - Exception: If critical database error occurs during process, it rolls back
#                connection to prevent partial data corruption and surfaces traceback.
def bulk_ingest_locations(csv_filepath: str, batch_size: int = 10000, max_rows: int = None):
    print(f"Starting bulk ingestion from {csv_filepath}...")
    
    # Initialize DB connection pool
    db_pool = get_db_pool()
    conn = None
    
    # The SQL template for execute_values
    # ON CONFLICT ensures that it is safe to re-run without duplicating
    insert_query = """
        INSERT INTO location_evaluation (location_id, geom, geoid_cb, status)
        VALUES %s
        ON CONFLICT (location_id) DO NOTHING;
    """

    # Maps raw tuple to SQL values. ST_SetSRID(...) creates native spatial vector point in WGS84
    template = "(%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, 'P')"
    
    rows_processed = 0
    batch = []

    try:
        # Check out connection from pool
        conn = db_pool.getconn()
        
        with open(csv_filepath, mode='r') as file:
            reader = csv.DictReader(file)
            
            with conn.cursor() as cursor:
                for row in reader:
                    # Data quality guard: safely handle missing or malformed data
                    try:
                        batch.append((
                            row['location_id'], 
                            float(row['longitude']), 
                            float(row['latitude']), 
                            row.get('geoid_cb')  # Safely defaults to None if missing
                        ))
                        # Enforce testing limits
                        if max_rows and (rows_processed + len(batch)) >= max_rows:
                            break
                    except (ValueError, KeyError) as e:
                        # Catch casting errors or missing required columns without crashing whole thing
                        loc_id = row.get('location_id', 'unknown')
                        print(f"Skipping malformed row {loc_id}: {e}")
                        continue
                        
                    # Execute batch insert when the threshold is reached
                    if len(batch) >= batch_size:
                        extras.execute_values(cursor, insert_query, batch, template=template)
                        conn.commit() # Hard save on disk
                        rows_processed += len(batch)
                        print(f"Inserted {rows_processed} rows...")
                        batch.clear() # Flush memory buffer

                # Insert any remaining rows in the final partial batch
                if batch:
                    extras.execute_values(cursor, insert_query, batch, template=template)
                    conn.commit()
                    rows_processed += len(batch)
                    
        print(f"Ingestion complete. Total rows processed: {rows_processed}")

    except Exception as e:
        # If pipeline crashes, rollback current uncommitted batch
        if conn is not None:
            conn.rollback()
        # Explicitly chain the exception to preserve the original traceback
        raise Exception("Failed during bulk ingestion") from e
        
    finally:
        # Guaranteed to execute safely: return the connection to the pool
        if conn is not None:
            db_pool.putconn(conn)

if __name__ == "__main__":
    # Ensure locations file is named correctly and in the right folder
    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, "../locations.csv")
    bulk_ingest_locations(csv_path, batch_size=1000, max_rows=1000)