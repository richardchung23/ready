import math
from typing import Dict, Any


def calculate_los(
        dish_elev: float, 
        obstruction_elev: float, 
        obstruction_dist: float,
        canopy_height: float,
        dish_height: float = 2.0
    )-> Dict[str, Any]: 
    
    MIN_ELEVATION_ANGLE_DEG = 20.0
    total_dish_elev = dish_elev + dish_height
    total_obstacle_elev = obstruction_elev + canopy_height

    result = {
        "obstruction_height" : round(total_obstacle_elev, 2),
        "obstruction_angle" : -1.0,    # this will be to denote no obstruction
        "risk_tier" : 'A',
        "reason" : ""
    }
    
    if obstruction_dist <= 0:
        result["risk_tier"] = "C"
        result["reason"] = "Invalid or zero distance, high risk."
        return result
    
    height = total_obstacle_elev - total_dish_elev
    if height <= 0:
        result["reason"] = "Obstruction is below or level with dish. Sky is clear."
        return result
    
    angle_rad = math.atan(height / obstruction_dist)
    angle = round(math.degrees(angle_rad), 2)

    result["obstruction_angle"] = angle 
    if angle > MIN_ELEVATION_ANGLE_DEG:
        result["risk_tier"] = "C"
        result["reason"] = f"Obstruction angle ({angle}) exceeds 20 degree threshold."
    elif angle > 15:
        result["risk_tier"] = "B"
        result["reason"] = f"Obstruction angle ({angle}) is fine but nears 20 degree threshold."
    else:
        result["reason"] = f"Clear view. Obstruction angle ({angle}) is below threshold."

    return result
