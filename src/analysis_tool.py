# analysis_tool.py
#
# This file is the logic and math layer of system. It isolates all geometric
# computation, trigonometry, and risk tier away from DB cycles and network I/O.
# By keeping this deterministic, we can safely wrap it into JSON schemas for LLM.

import math
from typing import Dict, Any


# LOS calculator
#
# Used primarily by supervisor agent to evaluate physical environment. It uses
# geometry to compute if an obtruction blocks the dish's view.
#
# Args:
#   - dish_elev: Elevation of where dish would be installed in meters
#   - obstruction_elev: Elevation at base of obstruction in meters
#   - obstruction_dist: Distance of obstruction from dish in meters
#   - canopy_height: Physical height of obstruction in meters
#   - dish_height: Height of dish mount. Defaults to a conservative 2.0
#
# Returns:
#   - Dict[str, Any]: A dictionary containing absolute height, the angular 
# vector in degrees, the risk tier assignment, and a human-readable natural language reason.
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
    
    # Check for bad data to prevent bad division
    if obstruction_dist <= 0:
        result["risk_tier"] = "C"
        result["reason"] = "Invalid or zero distance, high risk."
        return result
    
    # Check if obstruction is vertically shorter than dish elevation
    height = total_obstacle_elev - total_dish_elev
    if height <= 0:
        result["reason"] = "Obstruction is below or level with dish. Sky is clear."
        return result
    
    # Geometric calculation using arctangent
    angle_rad = math.atan(height / obstruction_dist)
    angle = round(math.degrees(angle_rad), 2)

    # Evaluate risk tier against predefined thresholds
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


# A high throughput batch proxy classifier
#
# Used by core DB batch pipeline. Since raw Canopy Height Model (CHM) raster 
# grid is not in dataset, this function applies linear mathematical formula to
# translate TCC percentages directly into estimated obstructions over many rows.
#
# Args:
#   - tcc_percentage: Canopy density value ranging from 0 to 100
#   - elevation: Baseline terrain altitude in meters
#
# Returns:
#   - dict: Metrics containing estimated obstruction height, angle, and corresponding
#           risk tier.
def evaluate_risk(tcc_percentage: int, elevation: float) -> dict:
    MIN_ELEVATION_ANGLE_DEG = 20.0
    # strict clamping to handle edge cases or corrupted data
    tcc_percentage = max(0, min(tcc_percentage, 100))

    # Continuous linear formulas: deriving synthetic geometry from proxy canopy attributes
    obstruction_angle = float(tcc_percentage * 0.4)
    obstruction_height = elevation + (tcc_percentage * 0.3)

    # Threshold evaluation
    if obstruction_angle > MIN_ELEVATION_ANGLE_DEG:
        tier = 'C'
    elif obstruction_angle > 15.0:
        tier = 'B'
    else:
        tier = 'A'

    return {
        "obstruction_angle": obstruction_angle,
        "obstruction_height": obstruction_height,
        "risk_tier": tier
    }
