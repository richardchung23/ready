import csv
import uuid
import random

def generate_mock_locations(filename="mock_locations.csv", num_rows=1000):
    """
    Generates a mock CSV matching the provided dataset format:
    location_id, latitude, longitude
    """
    # Define bounding boxes for different terrains to test the logic
    regions = {
        "Appalachian_Mountains": {"lat": (35.0, 39.0), "lon": (-84.0, -79.0)}, # Hilly, high trees
        "Great_Plains": {"lat": (40.0, 43.0), "lon": (-100.0, -95.0)},         # Flat, low trees
        "Pacific_Northwest": {"lat": (45.0, 48.0), "lon": (-124.0, -120.0)}    # Mountains, massive trees
    }

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["location_id", "latitude", "longitude"])
        
        for _ in range(num_rows):
            # Pick a random region
            region_name = random.choice(list(regions.keys()))
            bounds = regions[region_name]
            
            # Generate random coordinate within the bounding box
            lat = round(random.uniform(bounds["lat"][0], bounds["lat"][1]), 6)
            lon = round(random.uniform(bounds["lon"][0], bounds["lon"][1]), 6)
            
            # Create a realistic UUID
            loc_id = f"loc_{uuid.uuid4().hex[:12]}"
            
            writer.writerow([loc_id, lat, lon])

    print(f"Successfully generated {num_rows} mock locations in {filename}")

if __name__ == "__main__":
    generate_mock_locations()