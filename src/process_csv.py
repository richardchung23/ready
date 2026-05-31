import os
import csv
import psycopg2
from psycopg2 import extras
from data_tool import get_db_pool

def bulk_ingest_locations(csv_filepath: str, batch_size: int = 10000):
    """
    Reads the locations CSV and performs high-speed bulk inserts into PostGIS.
    """
    print(f"Starting bulk ingestion from {csv_filepath}...")
    
    db_pool = get_db_pool()
    conn = None
    
    # The SQL template for execute_values
    insert_query = """
        INSERT INTO location_evaluation (location_id, geom, geoid_cb, status)
        VALUES %s
        ON CONFLICT (location_id) DO NOTHING;
    """
    template = "(%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, 'P')"
    
    rows_processed = 0
    batch = []

    try:
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
                    except (ValueError, KeyError) as e:
                        loc_id = row.get('location_id', 'unknown')
                        print(f"Skipping malformed row {loc_id}: {e}")
                        continue
                        
                    # Execute batch insert when the threshold is reached
                    if len(batch) >= batch_size:
                        extras.execute_values(cursor, insert_query, batch, template=template)
                        conn.commit()
                        rows_processed += len(batch)
                        print(f"Inserted {rows_processed} rows...")
                        batch.clear()

                    if rows_processed >= 50:
                        break
                
                # Insert any remaining rows in the final partial batch
                if batch:
                    extras.execute_values(cursor, insert_query, batch, template=template)
                    conn.commit()
                    rows_processed += len(batch)
                    
        print(f"Ingestion complete. Total rows processed: {rows_processed}")

    except Exception as e:
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
    bulk_ingest_locations(csv_path, batch_size=1000)