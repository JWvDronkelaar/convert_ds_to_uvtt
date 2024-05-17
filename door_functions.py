import math

from generic_functions import *


def get_door_type(polylines, polygons):
    # returns 0 for invalid type, otherwise "A" or "B"
    polylines_count = len(polylines)
    polygons_count = len(polygons[0])

    polylines_point_count = 0
    for polyline in polylines:
        polylines_point_count += len(polyline)

    polygons_point_count = 0
    for polygon in polygons[0]:
        polygons_point_count += len(polygon)

    # rectangle with small wall segments on either end
    if (polylines_count == 2 
            and polygons_count == 1
            and polylines_point_count == 4
            and polygons_point_count == 4):  # rectangle has one overlapping point!
        return "A"
    
    # just a plain rectangle stretching
    if (polylines_count == 0 
            and polygons_count == 1):
        return "B"

    return 0
        

def calculate_line_for_door_A(door_polylines, door_polygons):
    return [{"x":door_polylines[0][0][0], "y":door_polylines[0][0][1]},
            {"x":door_polylines[1][1][0], "y":door_polylines[1][1][1]}]


def calculate_line_for_door_B(door_polylines, door_polygons):
    # this type of door only contains one rectangular polygon
    polygon = door_polygons[0][0]

    # coordinates start at long edge of the rectangle
    long_edge = [polygon[0], polygon[1]]
    
    offset = [(polygon[1][0] - polygon[2][0])/2,
              (polygon[1][1] - polygon[2][1])/2]
    
    midline = [[long_edge[0][0] - offset[0], long_edge[0][1] - offset[1]],
               [long_edge[1][0] - offset[0], long_edge[1][1] - offset[1]]]

    return [{"x":midline[0][0], "y":midline[0][1]},
            {"x":midline[1][0], "y":midline[1][1]}]


def generate_door_obstruction_lines(map_data, geometry_ids):
    geometry = map_data["data"]["geometry"]
    obstruction_lines = []
    
    for geometry_id in geometry_ids:
        layer_geometry = geometry[geometry_id]
        door_polylines = layer_geometry["polylines"]
        door_polygons = layer_geometry["polygons"]
        door_type = get_door_type(door_polylines, door_polygons)

        print(f"Calculating door: {geometry_id}")
        print(f"Door type: {door_type}")

        if door_type == 0:
            continue
        elif door_type == "A":
            door_obstruction_line = calculate_line_for_door_A(door_polylines, door_polygons)
        elif door_type == "B":
            door_obstruction_line = calculate_line_for_door_B(door_polylines, door_polygons)
        
        obstruction_lines.append(door_obstruction_line)

    return obstruction_lines


def calculate_midpoint(p1, p2):
    mx = (p1["x"] + p2["x"]) / 2
    my = (p1["y"] + p2["y"]) / 2
    
    return {"x": mx, "y": my}


def calculate_angle(p1, p2):
    dx = p2["x"] - p1["x"]
    dy = p2["y"] - p1["y"]

    # Calculate the angle in radians
    return math.atan2(dy, dx)


def generate_portals(map_data, geometry_ids):
    door_obstruction_lines = generate_door_obstruction_lines(map_data, geometry_ids)
    door_obstruction_lines = scale_and_offset_coordinates(door_obstruction_lines)
    portals = []

    for line in door_obstruction_lines:
        position = calculate_midpoint(line[0], line[1])
        rotation = calculate_angle(line[0], line[1])

        portal = {}
        portal["position"] = position
        portal["bounds"] = line
        # portal["rotation"] = 1.570796,
        portal["rotation"] = rotation
        portal["closed"] = True,
        portal["freestanding"] = False
        portals.append(portal)
    
    return portals
