from data_tool import get_db_pool

def fetch_test_suite_ids():
    db_pool = get_db_pool()
    conn = db_pool.getconn()
    
    query = """
        (SELECT 'Tier A (Clear)' AS label, location_id FROM location_evaluation WHERE status = 'D' AND risk_tier = 'A' LIMIT 1)
        UNION ALL
        (SELECT 'Tier B (Moderate)' AS label, location_id FROM location_evaluation WHERE status = 'D' AND risk_tier = 'B' LIMIT 1)
        UNION ALL
        (SELECT 'Tier C (Obstructed)' AS label, location_id FROM location_evaluation WHERE status = 'D' AND risk_tier = 'C' LIMIT 1)
        UNION ALL
        (SELECT 'Anomaly' AS label, location_id FROM location_evaluation WHERE status = 'A' LIMIT 1);
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            records = cursor.fetchall()
            
            print("\n=== AGENT TEST SUITE LOCATIONS ===")
            for label, loc_id in records:
                print(f"{label:<20} -> Location ID: {loc_id}")
            print("===================================\n")
            
    except Exception as e:
        print(f"Failed to pull test data: {e}")
    finally:
        db_pool.putconn(conn)

if __name__ == "__main__":
    fetch_test_suite_ids()