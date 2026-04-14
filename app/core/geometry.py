import numpy as np
from typing import List, Dict, Tuple

def get_point_side(point: Tuple[float, float], line_points: List[Dict[str, float]]) -> str:
    """
    Determines which side of a defined polyline a given point is located.
    Uses the cross product of vectors to determine orientation.
    
    Args:
        point: Tuple containing the (x, y) coordinates of the target point.
        line_points: List of dictionaries representing vertices of the polyline.
                     Example: [{'x': 10.0, 'y': 20.0}, {'x': 50.0, 'y': 60.0}]
                     
    Returns:
        str: 'right', 'left', or 'on_line'.
    """
    if len(line_points) < 2:
        return 'on_line'
        
    x, y = point
    
    # We use the first and last points to define the main vector of the line
    p1 = np.array([line_points[0]['x'], line_points[0]['y']])
    p2 = np.array([line_points[-1]['x'], line_points[-1]['y']])
    target_point = np.array([x, y])
    
    # Cross product formula: (B_x - A_x) * (P_y - A_y) - (B_y - A_y) * (P_x - A_x)
    cross_product = np.cross(p2 - p1, target_point - p1)
    
    # Threshold applied to handle floating point inaccuracies and edge cases
    tolerance = 20.0
    
    if cross_product > tolerance:
        return 'right'
    elif cross_product < -tolerance:
        return 'left'
        
    return 'on_line'